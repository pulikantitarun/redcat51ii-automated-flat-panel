// ===========================================================================
// RedCat 51 II automated flat panel - Revision C firmware
// ESP32-S3-WROOM-1, Arduino-ESP32 core 3.x, ESP32Servo library
//
// WHAT CHANGED FROM REV B, AND WHY
// ---------------------------------
// 1. THE ASIAIR INPUT IS NO LONGER A DUTY-CYCLE MEASUREMENT.
//    Rev B called pulseIn() on an opto-isolator to recover the ASIAIR's PWM
//    duty. That cannot work on an ASIAIR Plus:
//      - the Plus capacitively filters its power outputs, so with the ~5 mA
//        the Rev B opto drew, the port never falls away from 12 V and every
//        slider position reads as 100 %;
//      - the port period is 20 ms, and Rev B's pulseIn timeout was 30 ms, so
//        a missed edge returned 0 -> "command 0" -> the flap flung open in
//        the middle of a flat sequence.
//    Rev C loads the port properly and measures its AVERAGE VOLTAGE on an
//    ADC. The same filtering that destroys duty-sniffing is exactly what makes
//    the average track the slider: 50 % reads ~6 V, 100 % reads ~12 V.
//
// 2. A FAILED MOVE NO LONGER RETRIES FOREVER.
//    Rev B's moveFlap() set isClosed=false on timeout regardless of which way
//    it was moving. A jammed flap therefore reported "open", so the next loop
//    pass commanded "close" again, ~50 ms later, forever - holding a stalled
//    DS3218 at ~2.7 A until something gave up. Rev C latches a FAULT after
//    MAX_MOVE_ATTEMPTS, detaches the servo, and refuses to move again until a
//    human clears it.
//
// 3. THE MOVE IS NON-BLOCKING. Rev B blocked inside moveFlap() for up to 5 s
//    with interrupts servicing nothing, so the button was dead during a move.
//
// 4. THE ASIAIR BOOT TRANSIENT IS HANDLED. Every ASIAIR drives all power
//    ports to FULL for a few seconds at boot, before it loads its saved port
//    settings. Rev B would have read that as "100 % - close and light up".
//    Rev C ignores the input until it has been stable for SETTLE_MS.
//
// 5. THRESHOLDS NO LONGER COLLIDE. Rev B used 3 % / 8 % boundaries when the
//    ASIAIR slider's minimum non-zero step is 5 %, and had no hysteresis, so
//    a reading sitting on a boundary would dither the flap open/closed.
// ===========================================================================

#include <ESP32Servo.h>

// --------------------------------------------------------------------------
// Pin map - matches the Rev C PCB (unchanged from Rev B; it was correct)
// --------------------------------------------------------------------------
constexpr int PIN_ASIAIR       = 4;   // ADC1_CH3 - divided average of the port
constexpr int PIN_LED          = 5;   // panel MOSFET gate, 20 kHz
constexpr int PIN_OPEN_LIMIT   = 6;   // NO to GND: LOW = at the open stop
constexpr int PIN_CLOSED_LIMIT = 7;   // NO to GND: LOW = at the closed stop
constexpr int PIN_BUTTON       = 9;   // NO to GND
constexpr int PIN_SERVO        = 18;
constexpr int PIN_STATUS       = 15;

// --------------------------------------------------------------------------
// Servo travel
// --------------------------------------------------------------------------
constexpr int OPEN_ANGLE   = 112;
constexpr int CLOSED_ANGLE = 8;

// --------------------------------------------------------------------------
// ASIAIR input scaling
//
// Divider on the board is 10k (top) / 3.3k (bottom), so the ADC sees
//   V_adc = V_port * 3.3 / 13.3 = V_port * 0.2481
// and 12 V at the port -> 2.977 V at the pin, just inside the ESP32-S3's
// ~3.1 V full scale at 12 dB attenuation.
//
// CALIBRATION: if your panel lights at the wrong slider position, put a
// voltmeter on the ASIAIR port at 100 % and set PORT_FULL_V to what you read
// (a "12 V" supply is usually 12.2-13.8 V). Nothing else needs touching.
// --------------------------------------------------------------------------
constexpr float DIVIDER_RATIO = 3.3f / (10.0f + 3.3f);
constexpr float PORT_FULL_V   = 12.0f;

// Command thresholds in PORT VOLTS, not percent - percent is a property of
// the ASIAIR's slider, volts are what this board can actually observe.
// The ASIAIR slider's minimum non-zero position is 5 % (~0.6 V), so "off"
// must sit well below that.
constexpr float V_OPEN_MAX  = 0.80f;  // below this: port off -> park OPEN
constexpr float V_COVER_MAX = 2.80f;  // 0.8-2.8 V: CLOSED, panel dark
constexpr float V_LIGHT_MIN = 3.20f;  // above this: CLOSED, panel lit
constexpr float V_HYST      = 0.30f;  // applied at every boundary

// --------------------------------------------------------------------------
// Timing / limits
// --------------------------------------------------------------------------
constexpr unsigned long MOVE_TIMEOUT_MS  = 4000;  // one attempt
constexpr unsigned long MOVE_REST_MS     = 1500;  // servo OFF between attempts
constexpr int           MAX_MOVE_ATTEMPTS = 3;
constexpr unsigned long LIMIT_DEBOUNCE_MS = 40;
constexpr unsigned long SETTLE_MS        = 6000;  // ASIAIR boot transient
constexpr unsigned long BUTTON_DEBOUNCE_MS = 250;
constexpr unsigned long FAULT_CLEAR_HOLD_MS = 2000;
constexpr unsigned long SAMPLE_INTERVAL_MS = 100;

constexpr int LED_PWM_BITS = 12;
constexpr int LED_PWM_MAX  = (1 << LED_PWM_BITS) - 1;
constexpr int LED_PWM_HZ   = 20000;

// --------------------------------------------------------------------------
// State
// --------------------------------------------------------------------------
enum FlapState : uint8_t { FLAP_UNKNOWN, FLAP_OPEN, FLAP_CLOSED, FLAP_MOVING, FLAP_FAULT };
enum Command   : uint8_t { CMD_OPEN, CMD_COVER, CMD_LIGHT };

Servo flapServo;

FlapState flapState   = FLAP_UNKNOWN;
Command   lastCommand = CMD_OPEN;
bool      manualOverride = false;   // button has taken control from the ASIAIR
bool      manualWantClosed = false;

// move engine
bool          moveActive     = false;
bool          moveWantClosed = false;
int           moveAttempt    = 0;
unsigned long moveStartedMs  = 0;
unsigned long moveRestUntil  = 0;

unsigned long bootMs          = 0;
unsigned long lastSampleMs    = 0;
unsigned long buttonDownMs    = 0;
bool          buttonWasDown   = false;
bool          settled         = false;
float         settleRefV      = 0.0f;
unsigned long settleSinceMs   = 0;

float  ledDuty = 0.0f;
String faultReason = "";

// ===========================================================================
// Panel
// ===========================================================================
// The panel is only ever allowed to light when the cover is CONFIRMED closed.
// An illuminated panel with the cover open points a light source at whatever
// the scope is aimed at, and ruins the sub anyway.
void setLed(float duty) {
  if (flapState != FLAP_CLOSED) duty = 0.0f;
  duty = constrain(duty, 0.0f, 1.0f);
  ledDuty = duty;
  ledcWrite(PIN_LED, (int)(duty * LED_PWM_MAX));
}

// ===========================================================================
// ASIAIR port sensing
// ===========================================================================
// Oversample and take the MEDIAN, then average the middle of the distribution.
// The port is a filtered 20 ms PWM: there is residual ripple, and the ESP32-S3
// SAR ADC is noisy and non-linear near the rails. A median rejects both the
// ripple peaks and the occasional wild sample.
float readPortVolts() {
  constexpr int N = 33;
  uint16_t mv[N];
  for (int i = 0; i < N; i++) {
    mv[i] = analogReadMilliVolts(PIN_ASIAIR);
    delayMicroseconds(600);              // spread across ~20 ms = one period
  }
  // insertion sort - N is tiny
  for (int i = 1; i < N; i++) {
    uint16_t k = mv[i];
    int j = i - 1;
    while (j >= 0 && mv[j] > k) { mv[j + 1] = mv[j]; j--; }
    mv[j + 1] = k;
  }
  // mean of the middle third
  uint32_t acc = 0;
  int lo = N / 3, hi = N - N / 3;
  for (int i = lo; i < hi; i++) acc += mv[i];
  float vAdc = (acc / (float)(hi - lo)) / 1000.0f;
  return vAdc / DIVIDER_RATIO;
}

// Hysteresis: a boundary only counts if we cross it by V_HYST in the
// direction we are not already in.
Command classify(float v, Command prev) {
  float openMax  = V_OPEN_MAX  + (prev == CMD_OPEN  ? V_HYST : 0.0f);
  float coverMax = V_COVER_MAX + (prev == CMD_COVER ? V_HYST : 0.0f);
  float lightMin = V_LIGHT_MIN - (prev == CMD_LIGHT ? V_HYST : 0.0f);

  if (v < openMax)  return CMD_OPEN;
  if (v < coverMax) return CMD_COVER;
  if (v >= lightMin) return CMD_LIGHT;
  return prev == CMD_LIGHT ? CMD_LIGHT : CMD_COVER;  // inside the dead band
}

float brightnessFor(float v) {
  float span = (PORT_FULL_V - 0.5f) - V_LIGHT_MIN;
  if (span <= 0.1f) return 1.0f;
  return constrain((v - V_LIGHT_MIN) / span, 0.0f, 1.0f);
}

// ===========================================================================
// Limit switches
// ===========================================================================
bool limitAsserted(int pin) {
  if (digitalRead(pin) != LOW) return false;
  delay(LIMIT_DEBOUNCE_MS);
  return digitalRead(pin) == LOW;
}

// ===========================================================================
// Move engine - non-blocking, bounded retries, latching fault
// ===========================================================================
void enterFault(const char *why) {
  flapServo.detach();
  moveActive = false;
  flapState  = FLAP_FAULT;
  faultReason = why;
  ledcWrite(PIN_LED, 0);
  ledDuty = 0.0f;
  Serial.printf("[FAULT] %s\n", why);
}

void beginMove(bool wantClosed) {
  if (flapState == FLAP_FAULT) return;
  if (moveActive && moveWantClosed == wantClosed) return;
  ledcWrite(PIN_LED, 0);           // never move a lit panel
  ledDuty = 0.0f;
  moveActive     = true;
  moveWantClosed = wantClosed;
  moveAttempt    = 0;
  moveRestUntil  = 0;
  moveStartedMs  = 0;              // forces attempt 1 to start immediately
  flapState      = FLAP_MOVING;
  Serial.printf("[MOVE] -> %s\n", wantClosed ? "CLOSED" : "OPEN");
}

void serviceMove() {
  if (!moveActive) return;
  unsigned long now = millis();
  if (now < moveRestUntil) return;

  // start an attempt
  if (moveStartedMs == 0) {
    moveAttempt++;
    if (moveAttempt > MAX_MOVE_ATTEMPTS) {
      enterFault(moveWantClosed ? "flap did not reach the CLOSED stop"
                                : "flap did not reach the OPEN stop");
      return;
    }
    flapServo.attach(PIN_SERVO, 500, 2500);
    flapServo.write(moveWantClosed ? CLOSED_ANGLE : OPEN_ANGLE);
    moveStartedMs = now;
    Serial.printf("[MOVE] attempt %d/%d\n", moveAttempt, MAX_MOVE_ATTEMPTS);
    return;
  }

  // arrived?
  int limitPin = moveWantClosed ? PIN_CLOSED_LIMIT : PIN_OPEN_LIMIT;
  if (limitAsserted(limitPin)) {
    delay(120);                    // let it settle onto the stop
    flapServo.detach();            // stop holding torque: no buzz, no heat
    moveActive = false;
    flapState  = moveWantClosed ? FLAP_CLOSED : FLAP_OPEN;
    digitalWrite(PIN_STATUS, flapState == FLAP_CLOSED ? HIGH : LOW);
    Serial.printf("[MOVE] reached %s\n", moveWantClosed ? "CLOSED" : "OPEN");
    return;
  }

  // timed out - back off, de-energise, and try again a bounded number of times
  if (now - moveStartedMs > MOVE_TIMEOUT_MS) {
    flapServo.detach();            // <-- the line Rev B never had
    moveStartedMs = 0;
    moveRestUntil = now + MOVE_REST_MS;
    Serial.printf("[MOVE] attempt %d timed out, resting\n", moveAttempt);
  }
}

// ===========================================================================
// Status LED
//   solid   = closed
//   off     = open
//   slow    = moving
//   fast    = FAULT
// ===========================================================================
void serviceStatusLed() {
  unsigned long t = millis();
  switch (flapState) {
    case FLAP_CLOSED: digitalWrite(PIN_STATUS, HIGH); break;
    case FLAP_OPEN:   digitalWrite(PIN_STATUS, LOW);  break;
    case FLAP_MOVING: digitalWrite(PIN_STATUS, (t / 400) & 1); break;
    case FLAP_FAULT:  digitalWrite(PIN_STATUS, (t / 100) & 1); break;
    default:          digitalWrite(PIN_STATUS, (t / 900) & 1); break;
  }
}

// ===========================================================================
// Button: short press toggles and takes manual control.
//         hold 2 s clears a fault and hands control back to the ASIAIR.
// ===========================================================================
void serviceButton() {
  bool down = (digitalRead(PIN_BUTTON) == LOW);
  unsigned long now = millis();

  if (down && !buttonWasDown) {
    buttonDownMs = now;
  } else if (down && buttonWasDown) {
    if (now - buttonDownMs > FAULT_CLEAR_HOLD_MS && flapState == FLAP_FAULT) {
      Serial.println("[BTN] fault cleared by hold");
      flapState = FLAP_UNKNOWN;
      faultReason = "";
      manualOverride = false;
      settled = false;             // re-settle before trusting the ASIAIR
      settleSinceMs = now;
      buttonDownMs = now + 3600000UL;   // don't retrigger on this press
    }
  } else if (!down && buttonWasDown) {
    unsigned long held = now - buttonDownMs;
    if (held > BUTTON_DEBOUNCE_MS && held < FAULT_CLEAR_HOLD_MS &&
        flapState != FLAP_FAULT) {
      manualOverride   = true;
      manualWantClosed = !(flapState == FLAP_CLOSED);
      Serial.printf("[BTN] manual -> %s\n", manualWantClosed ? "CLOSED" : "OPEN");
      beginMove(manualWantClosed);
    }
  }
  buttonWasDown = down;
}

// ===========================================================================
void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\nRedCat 51 II flat panel - Rev C");

  pinMode(PIN_OPEN_LIMIT,   INPUT_PULLUP);
  pinMode(PIN_CLOSED_LIMIT, INPUT_PULLUP);
  pinMode(PIN_BUTTON,       INPUT_PULLUP);
  pinMode(PIN_STATUS,       OUTPUT);
  digitalWrite(PIN_STATUS, LOW);

  // ADC1_CH3 on GPIO4. 12 dB attenuation -> ~0-3.1 V usable.
  analogSetPinAttenuation(PIN_ASIAIR, ADC_11db);
  analogReadResolution(12);

  ledcAttach(PIN_LED, LED_PWM_HZ, LED_PWM_BITS);
  ledcWrite(PIN_LED, 0);

  bootMs        = millis();
  settleSinceMs = bootMs;
  settleRefV    = readPortVolts();

  // Do NOT move on boot. Rev B blindly drove to OPEN in setup(), which slams
  // the flap against its stop before anyone has checked the mechanism, and
  // does it every time the ASIAIR's own 12 V rail browns out on mount slew.
  // Instead, adopt whatever state the limit switches say we are already in.
  if (limitAsserted(PIN_CLOSED_LIMIT))    flapState = FLAP_CLOSED;
  else if (limitAsserted(PIN_OPEN_LIMIT)) flapState = FLAP_OPEN;
  else                                    flapState = FLAP_UNKNOWN;
  Serial.printf("[BOOT] flap is %s\n",
                flapState == FLAP_CLOSED ? "CLOSED" :
                flapState == FLAP_OPEN   ? "OPEN" : "UNKNOWN (between stops)");
}

void loop() {
  serviceButton();
  serviceMove();
  serviceStatusLed();

  if (millis() - lastSampleMs < SAMPLE_INTERVAL_MS) return;
  lastSampleMs = millis();

  float v = readPortVolts();

  // --- ASIAIR boot transient guard -------------------------------------
  // All ASIAIR power ports come up at FULL for a few seconds before the saved
  // per-port settings are applied. Refuse to act on the input until it has
  // held still for SETTLE_MS.
  if (!settled) {
    if (fabsf(v - settleRefV) > 0.6f) {
      settleRefV    = v;
      settleSinceMs = millis();
    } else if (millis() - settleSinceMs > SETTLE_MS) {
      settled     = true;
      lastCommand = classify(v, CMD_OPEN);
      Serial.printf("[SETTLE] port stable at %.2f V, taking control\n", v);
    }
    return;
  }

  Command cmd = classify(v, lastCommand);

  if (cmd != lastCommand) {
    Serial.printf("[ASIAIR] %.2f V -> %s\n", v,
                  cmd == CMD_OPEN ? "OPEN" : cmd == CMD_COVER ? "COVER" : "LIGHT");
    // any deliberate ASIAIR change takes control back from the button
    manualOverride = false;
    lastCommand = cmd;
  }

  if (flapState == FLAP_FAULT || manualOverride) return;

  switch (cmd) {
    case CMD_OPEN:
      setLed(0.0f);
      if (flapState != FLAP_OPEN && !moveActive) beginMove(false);
      break;
    case CMD_COVER:
      setLed(0.0f);
      if (flapState != FLAP_CLOSED && !moveActive) beginMove(true);
      break;
    case CMD_LIGHT:
      if (flapState != FLAP_CLOSED) {
        if (!moveActive) beginMove(true);   // setLed() refuses until confirmed
      } else {
        setLed(brightnessFor(v));
      }
      break;
  }
}
