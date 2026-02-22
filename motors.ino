const int M1_IN1 = D1; 
const int M1_IN2 = D2;
const int M2_IN3 = D3;
const int M2_IN4 = D4;

void setup() {
  Serial.begin(9600);
  pinMode(M1_IN1, OUTPUT);
  pinMode(M1_IN2, OUTPUT);
  pinMode(M2_IN3, OUTPUT);
  pinMode(M2_IN4, OUTPUT);

  // Ensure everything is OFF at start
  stopMotors();
}

void stopMotors() {
  digitalWrite(M1_IN1, LOW);
  digitalWrite(M1_IN2, LOW);
  digitalWrite(M2_IN3, LOW);
  digitalWrite(M2_IN4, LOW);
}

void runAttackSequence() {
  Serial.println("ACK: Executing 12-second attack!");
  for (int i = 0; i < 6; i++) {
    // FORWARD
    digitalWrite(M1_IN1, HIGH); digitalWrite(M1_IN2, LOW);
    digitalWrite(M2_IN3, HIGH); digitalWrite(M2_IN4, LOW);
    delay(1000); 

    stopMotors();
    delay(200);

    // BACKWARD
    digitalWrite(M1_IN1, LOW); digitalWrite(M1_IN2, HIGH);
    digitalWrite(M2_IN3, LOW); digitalWrite(M2_IN4, HIGH);
    delay(1000);

    stopMotors();
    delay(200);
  }
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "ATTACK") {
      runAttackSequence();
    }
  }
}