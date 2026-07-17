#include <ESP32Servo.h>

// ESP32-S3 DevKitC-1 pin assignments used by the supplied PCB.
constexpr int PIN_ASIAIR = 4;       // PC817 collector; active LOW PWM
constexpr int PIN_LED = 5;          // 20 kHz LED PWM
constexpr int PIN_OPEN_LIMIT = 6;   // NO switch: LOW means endpoint reached
constexpr int PIN_CLOSED_LIMIT = 7; // NO switch: LOW means endpoint reached
constexpr int PIN_BUTTON = 9;       // NO button to GND
constexpr int PIN_SERVO = 18;
constexpr int PIN_STATUS = 15;

constexpr int OPEN_ANGLE = 112;
constexpr int CLOSED_ANGLE = 8;
constexpr unsigned long MOVE_TIMEOUT_MS = 5000;
constexpr int LED_PWM_BITS = 12;
constexpr int LED_PWM_MAX = (1 << LED_PWM_BITS) - 1;

Servo flapServo;
bool isClosed = false;
bool manualClosed = false;
unsigned long lastButtonMs = 0;

void setLed(float duty) {
  duty = constrain(duty, 0.0f, 1.0f);
  if (!isClosed) duty = 0.0f;
  ledcWrite(PIN_LED, int(duty * LED_PWM_MAX));
}

bool moveFlap(bool closeRequested) {
  setLed(0);
  const int target = closeRequested ? CLOSED_ANGLE : OPEN_ANGLE;
  const int limitPin = closeRequested ? PIN_CLOSED_LIMIT : PIN_OPEN_LIMIT;
  flapServo.attach(PIN_SERVO, 500, 2500);
  flapServo.write(target);
  unsigned long started = millis();
  while (millis() - started < MOVE_TIMEOUT_MS) {
    if (digitalRead(limitPin) == LOW) {
      delay(150);
      flapServo.detach();
      isClosed = closeRequested;
      digitalWrite(PIN_STATUS, isClosed ? HIGH : LOW);
      return true;
    }
    delay(10);
  }
  flapServo.detach();
  isClosed = false;
  digitalWrite(PIN_STATUS, LOW);
  return false;
}

float readAsiairDuty() {
  unsigned long lowUs = pulseIn(PIN_ASIAIR, LOW, 30000);
  unsigned long highUs = pulseIn(PIN_ASIAIR, HIGH, 30000);
  if (lowUs == 0 && highUs == 0) return digitalRead(PIN_ASIAIR) == LOW ? 1.0f : 0.0f;
  if (highUs == 0 && digitalRead(PIN_ASIAIR) == LOW) return 1.0f;
  if (lowUs == 0) return 0.0f;
  return float(lowUs) / float(lowUs + highUs);
}

void setup() {
  pinMode(PIN_ASIAIR, INPUT_PULLUP);
  pinMode(PIN_OPEN_LIMIT, INPUT_PULLUP);
  pinMode(PIN_CLOSED_LIMIT, INPUT_PULLUP);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  pinMode(PIN_STATUS, OUTPUT);
  ledcAttach(PIN_LED, 20000, LED_PWM_BITS);
  setLed(0);
  moveFlap(false);
}

void loop() {
  if (digitalRead(PIN_BUTTON) == LOW && millis() - lastButtonMs > 400) {
    lastButtonMs = millis();
    manualClosed = !manualClosed;
    moveFlap(manualClosed);
  }

  float command = readAsiairDuty();
  if (command < 0.03f) {
    if (isClosed) moveFlap(false);
    setLed(0);
  } else if (command < 0.08f) {
    if (!isClosed) moveFlap(true);
    setLed(0); // 5% is closed dust-cover mode.
  } else {
    if (!isClosed) moveFlap(true);
    setLed((command - 0.08f) / 0.92f);
  }
  delay(50);
}
