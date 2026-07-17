#include <Arduino.h>
#include <ESP32Servo.h>
#include <Preferences.h>

// RedCat / Universal Automated Flat Panel Controller Rev C
// Board: ESP32-S3-WROOM-1-N8, Arduino-ESP32 3.x, USB CDC on boot enabled.

constexpr int PIN_ASIAIR = 4;          // optocoupler collector; active LOW PWM
constexpr int PIN_LED = 5;             // AO3400A LED MOSFET
constexpr int PIN_OPEN_LIMIT = 6;      // fail-safe NC: HIGH = open endpoint / open wire
constexpr int PIN_CLOSED_LIMIT = 7;    // fail-safe NC: HIGH = closed endpoint / open wire
constexpr int PIN_SERVO_POWER = 8;     // HIGH enables the 6 V servo high-side switch
constexpr int PIN_BUTTON = 9;          // local and filtered external button, active LOW
constexpr int PIN_POWER_SENSE = 10;    // 100k/22k divider from protected 12 V
constexpr int PIN_SERVO = 18;
constexpr int PIN_STATUS = 15;

constexpr uint32_t FIRMWARE_PROTOCOL = 1;
constexpr uint32_t MOVE_TIMEOUT_MS = 7000;
constexpr uint32_t OPPOSITE_CLEAR_MS = 1200;
constexpr uint32_t INPUT_DEBOUNCE_MS = 35;
constexpr uint32_t COMMAND_STABLE_MS = 400;
constexpr uint32_t ASCOM_LEASE_MS = 15000;
constexpr uint32_t ASCOM_HEARTBEAT_MS = 5000;
constexpr uint32_t MANUAL_LEASE_MS = 30000;
constexpr uint32_t LONG_PRESS_MS = 1200;
constexpr uint32_t LED_WARMUP_MS = 1000;
constexpr uint32_t LED_RAMP_MS = 600;
constexpr uint32_t SERVO_STEP_MS = 20;
constexpr uint32_t SERIAL_BAUD = 115200;
constexpr int LED_PWM_BITS = 12;
constexpr int LED_PWM_MAX = (1 << LED_PWM_BITS) - 1;
constexpr int POWER_PRESENT_MV = 1450;  // about 8.0 V at MAIN after divider tolerance

enum class CoverState { UNKNOWN, OPEN, CLOSED, MOVING, ERROR };
enum class MoveDirection { NONE, OPENING, CLOSING };
enum class CommandZone { OPEN, CLOSED_DARK, LIGHT };
enum class FaultCode {
  NONE,
  BOTH_LIMITS_OPEN,
  OPEN_LIMIT_WIRE,
  CLOSED_LIMIT_WIRE,
  MOVE_TIMEOUT,
  MAIN_POWER_MISSING,
  HALTED
};

struct DebouncedInput {
  int pin;
  bool stable;
  bool raw;
  uint32_t changedAt;

  void begin(int gpio, bool pullup = true) {
    pin = gpio;
    pinMode(pin, pullup ? INPUT_PULLUP : INPUT);
    raw = stable = digitalRead(pin);
    changedAt = millis();
  }

  void update() {
    const bool value = digitalRead(pin);
    if (value != raw) {
      raw = value;
      changedAt = millis();
    }
    if (raw != stable && millis() - changedAt >= INPUT_DEBOUNCE_MS) stable = raw;
  }
};

Servo flapServo;
Preferences prefs;
DebouncedInput openLimit;
DebouncedInput closedLimit;
DebouncedInput manualButton;

volatile uint32_t pwmLastEdgeUs = 0;
volatile uint32_t pwmLowUs = 0;
volatile uint32_t pwmHighUs = 0;
volatile uint32_t pwmLastPeriodMs = 0;
portMUX_TYPE pwmMux = portMUX_INITIALIZER_UNLOCKED;

CoverState coverState = CoverState::UNKNOWN;
MoveDirection moveDirection = MoveDirection::NONE;
FaultCode faultCode = FaultCode::NONE;
CommandZone activeZone = CommandZone::OPEN;
CommandZone candidateZone = CommandZone::OPEN;

int openAngle = 112;
int closedAngle = 8;
int servoAngle = 60;
int targetAngle = 60;
int requestedBrightness = 0;
int appliedBrightness = 0;
float ledGamma = 1.0f;
float filteredDuty = 0.0f;

uint32_t moveStartedMs = 0;
uint32_t lastServoStepMs = 0;
uint32_t candidateSinceMs = 0;
uint32_t ascomLeaseUntilMs = 0;
uint32_t manualLeaseUntilMs = 0;
uint32_t buttonPressedMs = 0;
uint32_t ledChangeStartedMs = 0;
bool oppositeCleared = false;
bool buttonWasPressed = false;
bool calibratorChanging = false;

String serialLine;

void IRAM_ATTR onAsiairEdge() {
  const uint32_t now = micros();
  const bool level = digitalRead(PIN_ASIAIR);
  const uint32_t elapsed = now - pwmLastEdgeUs;
  pwmLastEdgeUs = now;
  portENTER_CRITICAL_ISR(&pwmMux);
  if (level) pwmLowUs = elapsed; else pwmHighUs = elapsed;
  if (pwmLowUs > 0 && pwmHighUs > 0) pwmLastPeriodMs = millis();
  portEXIT_CRITICAL_ISR(&pwmMux);
}

const char *coverName() {
  switch (coverState) {
    case CoverState::OPEN: return "OPEN";
    case CoverState::CLOSED: return "CLOSED";
    case CoverState::MOVING: return "MOVING";
    case CoverState::ERROR: return "ERROR";
    default: return "UNKNOWN";
  }
}

const char *faultName() {
  switch (faultCode) {
    case FaultCode::BOTH_LIMITS_OPEN: return "BOTH_LIMITS_OPEN";
    case FaultCode::OPEN_LIMIT_WIRE: return "OPEN_LIMIT_WIRE";
    case FaultCode::CLOSED_LIMIT_WIRE: return "CLOSED_LIMIT_WIRE";
    case FaultCode::MOVE_TIMEOUT: return "MOVE_TIMEOUT";
    case FaultCode::MAIN_POWER_MISSING: return "MAIN_POWER_MISSING";
    case FaultCode::HALTED: return "HALTED";
    default: return "NONE";
  }
}

bool mainPowerPresent() {
  return analogReadMilliVolts(PIN_POWER_SENSE) >= POWER_PRESENT_MV;
}

void servoPower(bool enabled) {
  if (!enabled) flapServo.detach();
  digitalWrite(PIN_SERVO_POWER, enabled ? HIGH : LOW);
  if (enabled && !flapServo.attached()) {
    delay(15); // high-side rail and bulk capacitor settle before PWM starts
    flapServo.attach(PIN_SERVO, 500, 2500);
    flapServo.write(servoAngle);
  }
}

int brightnessToPwm(int brightness) {
  const float x = constrain(brightness, 0, LED_PWM_MAX) / float(LED_PWM_MAX);
  return constrain(int(powf(x, ledGamma) * LED_PWM_MAX + 0.5f), 0, LED_PWM_MAX);
}

void writeLed(int brightness) {
  if (coverState != CoverState::CLOSED || moveDirection != MoveDirection::NONE || faultCode != FaultCode::NONE) brightness = 0;
  appliedBrightness = constrain(brightness, 0, LED_PWM_MAX);
  ledcWrite(PIN_LED, brightnessToPwm(appliedBrightness));
}

void setFault(FaultCode code) {
  faultCode = code;
  moveDirection = MoveDirection::NONE;
  coverState = CoverState::ERROR;
  requestedBrightness = 0;
  calibratorChanging = false;
  writeLed(0);
  servoPower(false);
}

void clearFaultIfSafe() {
  if (!(openLimit.stable && closedLimit.stable)) {
    faultCode = FaultCode::NONE;
    if (closedLimit.stable) coverState = CoverState::CLOSED;
    else if (openLimit.stable) coverState = CoverState::OPEN;
    else coverState = CoverState::UNKNOWN;
  }
}

void requestMove(bool closeRequested) {
  writeLed(0);
  requestedBrightness = closeRequested ? requestedBrightness : 0;
  if (!mainPowerPresent()) {
    setFault(FaultCode::MAIN_POWER_MISSING);
    return;
  }
  if (openLimit.stable && closedLimit.stable) {
    setFault(FaultCode::BOTH_LIMITS_OPEN);
    return;
  }
  const bool targetReached = closeRequested ? closedLimit.stable : openLimit.stable;
  if (targetReached) {
    coverState = closeRequested ? CoverState::CLOSED : CoverState::OPEN;
    moveDirection = MoveDirection::NONE;
    faultCode = FaultCode::NONE;
    return;
  }
  faultCode = FaultCode::NONE;
  moveDirection = closeRequested ? MoveDirection::CLOSING : MoveDirection::OPENING;
  coverState = CoverState::MOVING;
  targetAngle = closeRequested ? closedAngle : openAngle;
  if (openLimit.stable) servoAngle = openAngle;
  else if (closedLimit.stable) servoAngle = closedAngle;
  oppositeCleared = false;
  moveStartedMs = lastServoStepMs = millis();
  servoPower(true);
}

void haltMotion() {
  moveDirection = MoveDirection::NONE;
  servoPower(false);
  writeLed(0);
  faultCode = FaultCode::HALTED;
  coverState = CoverState::ERROR;
}

void updateMotion() {
  if (moveDirection == MoveDirection::NONE) return;
  const bool targetLimit = moveDirection == MoveDirection::CLOSING ? closedLimit.stable : openLimit.stable;
  const bool oppositeLimit = moveDirection == MoveDirection::CLOSING ? openLimit.stable : closedLimit.stable;
  if (openLimit.stable && closedLimit.stable) {
    setFault(FaultCode::BOTH_LIMITS_OPEN);
    return;
  }
  if (!oppositeLimit) oppositeCleared = true;
  if (millis() - moveStartedMs > OPPOSITE_CLEAR_MS && oppositeLimit) {
    setFault(moveDirection == MoveDirection::CLOSING ? FaultCode::OPEN_LIMIT_WIRE : FaultCode::CLOSED_LIMIT_WIRE);
    return;
  }
  if (oppositeCleared && oppositeLimit) {
    setFault(moveDirection == MoveDirection::CLOSING ? FaultCode::OPEN_LIMIT_WIRE : FaultCode::CLOSED_LIMIT_WIRE);
    return;
  }
  if (targetLimit) {
    const bool closed = moveDirection == MoveDirection::CLOSING;
    moveDirection = MoveDirection::NONE;
    servoPower(false);
    coverState = closed ? CoverState::CLOSED : CoverState::OPEN;
    faultCode = FaultCode::NONE;
    ledChangeStartedMs = millis();
    calibratorChanging = closed && requestedBrightness > 0;
    return;
  }
  if (millis() - moveStartedMs >= MOVE_TIMEOUT_MS) {
    setFault(FaultCode::MOVE_TIMEOUT);
    return;
  }
  if (millis() - lastServoStepMs >= SERVO_STEP_MS) {
    lastServoStepMs = millis();
    if (servoAngle < targetAngle) servoAngle = min(servoAngle + 2, targetAngle);
    else if (servoAngle > targetAngle) servoAngle = max(servoAngle - 2, targetAngle);
    flapServo.write(servoAngle);
  }
}

float readAsiairDuty() {
  uint32_t lowUs, highUs, lastPeriod;
  portENTER_CRITICAL(&pwmMux);
  lowUs = pwmLowUs;
  highUs = pwmHighUs;
  lastPeriod = pwmLastPeriodMs;
  portEXIT_CRITICAL(&pwmMux);
  if (millis() - lastPeriod > 250 || lowUs + highUs < 100) return digitalRead(PIN_ASIAIR) == LOW ? 1.0f : 0.0f;
  return constrain(float(lowUs) / float(lowUs + highUs), 0.0f, 1.0f);
}

CommandZone classifyDuty(float duty) {
  // 1% hysteresis around the 3% cover and 8% illumination boundaries.
  if (activeZone == CommandZone::OPEN && duty < 0.04f) return CommandZone::OPEN;
  if (activeZone == CommandZone::CLOSED_DARK && duty >= 0.02f && duty < 0.09f) return CommandZone::CLOSED_DARK;
  if (activeZone == CommandZone::LIGHT && duty >= 0.07f) return CommandZone::LIGHT;
  if (duty < 0.03f) return CommandZone::OPEN;
  if (duty < 0.08f) return CommandZone::CLOSED_DARK;
  return CommandZone::LIGHT;
}

bool ascomOwnsControl() { return int32_t(ascomLeaseUntilMs - millis()) > 0; }
bool manualOwnsControl() { return int32_t(manualLeaseUntilMs - millis()) > 0; }

void applyAsiair() {
  static uint32_t lastSample = 0;
  if (millis() - lastSample < 50) return;
  lastSample = millis();
  filteredDuty = filteredDuty * 0.75f + readAsiairDuty() * 0.25f;
  const CommandZone zone = classifyDuty(filteredDuty);
  if (zone != candidateZone) {
    candidateZone = zone;
    candidateSinceMs = millis();
    return;
  }
  if (millis() - candidateSinceMs < COMMAND_STABLE_MS) return;
  if (zone == activeZone) {
    // Track brightness changes while remaining inside the LIGHT command zone.
    // Do not restart the panel warm-up/ramp for every small ASIAIR PWM update.
    if (zone == CommandZone::LIGHT) {
      const int newBrightness = constrain(
        int((filteredDuty - 0.08f) / 0.92f * LED_PWM_MAX), 1, LED_PWM_MAX);
      if (abs(newBrightness - requestedBrightness) >= 2) requestedBrightness = newBrightness;
    }
    return;
  }
  activeZone = zone;
  if (zone == CommandZone::OPEN) {
    requestedBrightness = 0;
    if (coverState != CoverState::OPEN) requestMove(false);
  } else if (zone == CommandZone::CLOSED_DARK) {
    requestedBrightness = 0;
    if (coverState != CoverState::CLOSED) requestMove(true);
    else writeLed(0);
  } else {
    requestedBrightness = constrain(int((filteredDuty - 0.08f) / 0.92f * LED_PWM_MAX), 1, LED_PWM_MAX);
    if (coverState != CoverState::CLOSED) requestMove(true);
    else { ledChangeStartedMs = millis(); calibratorChanging = true; }
  }
}

void updateLedRamp() {
  if (coverState != CoverState::CLOSED || requestedBrightness <= 0 || faultCode != FaultCode::NONE) {
    calibratorChanging = false;
    writeLed(0);
    return;
  }
  const uint32_t elapsed = millis() - ledChangeStartedMs;
  if (elapsed < LED_WARMUP_MS) {
    calibratorChanging = true;
    writeLed(0);
  } else if (elapsed < LED_WARMUP_MS + LED_RAMP_MS) {
    calibratorChanging = true;
    const float ramp = float(elapsed - LED_WARMUP_MS) / LED_RAMP_MS;
    writeLed(int(requestedBrightness * ramp));
  } else {
    calibratorChanging = false;
    writeLed(requestedBrightness);
  }
}

void sendStatus() {
  Serial.printf("{\"protocol\":%lu,\"cover\":\"%s\",\"moving\":%s,\"fault\":\"%s\",\"brightness\":%d,\"requested\":%d,\"calibratorChanging\":%s,\"mainPower\":%s,\"openLimit\":%s,\"closedLimit\":%s,\"asiairDuty\":%.4f,\"owner\":\"%s\"}\n",
    FIRMWARE_PROTOCOL, coverName(), moveDirection != MoveDirection::NONE ? "true" : "false", faultName(), appliedBrightness,
    requestedBrightness, calibratorChanging ? "true" : "false", mainPowerPresent() ? "true" : "false",
    openLimit.stable ? "true" : "false", closedLimit.stable ? "true" : "false", filteredDuty,
    ascomOwnsControl() ? "ASCOM" : (manualOwnsControl() ? "MANUAL" : "ASIAIR"));
}

void saveConfiguration() {
  prefs.begin("flatpanel", false);
  prefs.putInt("openAngle", openAngle);
  prefs.putInt("closedAngle", closedAngle);
  prefs.putFloat("ledGamma", ledGamma);
  prefs.end();
}

void processCommand(String line) {
  line.trim();
  if (!line.length()) return;
  String upper = line;
  upper.toUpperCase();
  if (upper == "HELLO") {
    Serial.printf("OK UNIVERSAL-FLAT-PANEL REV-C PROTOCOL %lu\n", FIRMWARE_PROTOCOL);
  } else if (upper == "CLAIM" || upper == "HEARTBEAT") {
    ascomLeaseUntilMs = millis() + ASCOM_LEASE_MS;
    Serial.println("OK CLAIMED");
  } else if (upper == "RELEASE") {
    ascomLeaseUntilMs = 0;
    Serial.println("OK RELEASED");
  } else if (upper == "STATUS") {
    sendStatus();
  } else if (upper == "OPEN") {
    ascomLeaseUntilMs = millis() + ASCOM_LEASE_MS;
    requestMove(false);
    Serial.println(faultCode == FaultCode::NONE ? "OK OPENING" : "ERR MOVE");
  } else if (upper == "CLOSE") {
    ascomLeaseUntilMs = millis() + ASCOM_LEASE_MS;
    requestMove(true);
    Serial.println(faultCode == FaultCode::NONE ? "OK CLOSING" : "ERR MOVE");
  } else if (upper == "HALT") {
    ascomLeaseUntilMs = millis() + ASCOM_LEASE_MS;
    haltMotion();
    Serial.println("OK HALTED");
  } else if (upper == "OFF") {
    ascomLeaseUntilMs = millis() + ASCOM_LEASE_MS;
    requestedBrightness = 0;
    writeLed(0);
    Serial.println("OK OFF");
  } else if (upper.startsWith("LIGHT ")) {
    const int value = constrain(upper.substring(6).toInt(), 0, LED_PWM_MAX);
    ascomLeaseUntilMs = millis() + ASCOM_LEASE_MS;
    requestedBrightness = value;
    if (coverState != CoverState::CLOSED) requestMove(true);
    else { ledChangeStartedMs = millis(); calibratorChanging = value > 0; }
    Serial.println("OK LIGHT");
  } else if (upper == "CLEAR") {
    clearFaultIfSafe();
    Serial.println(faultCode == FaultCode::NONE ? "OK CLEARED" : "ERR LIMITS");
  } else if (upper == "GETCFG") {
    Serial.printf("{\"openAngle\":%d,\"closedAngle\":%d,\"gamma\":%.3f}\n", openAngle, closedAngle, ledGamma);
  } else if (upper.startsWith("SET OPEN_ANGLE ")) {
    openAngle = constrain(upper.substring(15).toInt(), 0, 180);
    Serial.println("OK SET");
  } else if (upper.startsWith("SET CLOSED_ANGLE ")) {
    closedAngle = constrain(upper.substring(17).toInt(), 0, 180);
    Serial.println("OK SET");
  } else if (upper.startsWith("SET GAMMA ")) {
    ledGamma = constrain(upper.substring(10).toFloat(), 0.25f, 3.0f);
    Serial.println("OK SET");
  } else if (upper == "SAVE") {
    saveConfiguration();
    Serial.println("OK SAVED");
  } else {
    Serial.println("ERR UNKNOWN_COMMAND");
  }
}

void updateSerial() {
  while (Serial.available()) {
    const char c = char(Serial.read());
    if (c == '\n' || c == '\r') {
      if (serialLine.length()) processCommand(serialLine);
      serialLine = "";
    } else if (serialLine.length() < 120) serialLine += c;
  }
}

void updateManualButton() {
  const bool pressed = !manualButton.stable;
  if (pressed && !buttonWasPressed) buttonPressedMs = millis();
  if (!pressed && buttonWasPressed) {
    const uint32_t held = millis() - buttonPressedMs;
    if (held >= LONG_PRESS_MS) {
      manualLeaseUntilMs = millis() + MANUAL_LEASE_MS;
      ascomLeaseUntilMs = 0;
      clearFaultIfSafe();
      requestMove(coverState != CoverState::CLOSED);
    }
  }
  buttonWasPressed = pressed;
}

void updateStatusLed() {
  const uint32_t phase = millis() % 2000;
  bool on = false;
  if (faultCode != FaultCode::NONE) on = (phase < 120) || (phase > 260 && phase < 380) || (phase > 520 && phase < 640);
  else if (moveDirection != MoveDirection::NONE) on = (phase % 300) < 150;
  else if (ascomOwnsControl()) on = phase < 1000;
  else if (coverState == CoverState::CLOSED) on = true;
  else on = phase < 100;
  digitalWrite(PIN_STATUS, on ? HIGH : LOW);
}

void setup() {
  pinMode(PIN_SERVO_POWER, OUTPUT);
  digitalWrite(PIN_SERVO_POWER, LOW);
  pinMode(PIN_STATUS, OUTPUT);
  pinMode(PIN_ASIAIR, INPUT_PULLUP);
  pinMode(PIN_POWER_SENSE, INPUT);
  openLimit.begin(PIN_OPEN_LIMIT);
  closedLimit.begin(PIN_CLOSED_LIMIT);
  manualButton.begin(PIN_BUTTON);
  ledcAttach(PIN_LED, 20000, LED_PWM_BITS);
  writeLed(0);

  prefs.begin("flatpanel", true);
  openAngle = prefs.getInt("openAngle", openAngle);
  closedAngle = prefs.getInt("closedAngle", closedAngle);
  ledGamma = prefs.getFloat("ledGamma", ledGamma);
  prefs.end();

  Serial.begin(SERIAL_BAUD);
  attachInterrupt(digitalPinToInterrupt(PIN_ASIAIR), onAsiairEdge, CHANGE);
  delay(150);
  openLimit.update(); closedLimit.update();
  if (openLimit.stable && closedLimit.stable) setFault(FaultCode::BOTH_LIMITS_OPEN);
  else if (closedLimit.stable) { coverState = CoverState::CLOSED; servoAngle = closedAngle; }
  else if (openLimit.stable) { coverState = CoverState::OPEN; servoAngle = openAngle; }
  Serial.printf("BOOT UNIVERSAL-FLAT-PANEL REV-C PROTOCOL %lu\n", FIRMWARE_PROTOCOL);
}

void loop() {
  openLimit.update();
  closedLimit.update();
  manualButton.update();
  updateSerial();
  updateManualButton();
  updateMotion();
  if (!ascomOwnsControl() && !manualOwnsControl() && moveDirection == MoveDirection::NONE) applyAsiair();
  updateLedRamp();
  updateStatusLed();
  delay(2);
}
