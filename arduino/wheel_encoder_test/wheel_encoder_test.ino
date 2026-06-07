#define ENCODER_A 18
#define ENCODER_B 19

volatile long encoderCount = 0;
volatile byte lastAB = 0;

void updateEncoder() {
  byte A = digitalRead(ENCODER_A);
  byte B = digitalRead(ENCODER_B);

  byte currentAB = (A << 1) | B;
  byte transition = (lastAB << 2) | currentAB;

  // Quadrature encoder transition table
  // 방향이 반대로 나오면 +1, -1을 서로 바꾸면 됨
  switch (transition) {
    case 0b0001:
    case 0b0111:
    case 0b1110:
    case 0b1000:
      encoderCount++;
      break;

    case 0b0010:
    case 0b1011:
    case 0b1101:
    case 0b0100:
      encoderCount--;
      break;

    default:
      // 잘못된 전이 또는 노이즈는 무시
      break;
  }

  lastAB = currentAB;
}

void setup() {
  Serial.begin(57600);

  pinMode(ENCODER_A, INPUT_PULLUP);
  pinMode(ENCODER_B, INPUT_PULLUP);

  byte A = digitalRead(ENCODER_A);
  byte B = digitalRead(ENCODER_B);
  lastAB = (A << 1) | B;

  attachInterrupt(digitalPinToInterrupt(ENCODER_A), updateEncoder, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENCODER_B), updateEncoder, CHANGE);

  Serial.println("DMC-16 Encoder test start");
}

void loop() {
  static unsigned long lastMs = 0;
  static long lastCount = 0;

  if (millis() - lastMs >= 100) {
    long nowCount;

    noInterrupts();
    nowCount = encoderCount;
    interrupts();

    long dCount = nowCount - lastCount;

    Serial.print("ENC: ");
    Serial.print(nowCount);
    Serial.print(" | dCount/100ms: ");
    Serial.print(dCount);
    Serial.print(" | A: ");
    Serial.print(digitalRead(ENCODER_A));
    Serial.print(" | B: ");
    Serial.println(digitalRead(ENCODER_B));

    lastCount = nowCount;
    lastMs = millis();
  }
}