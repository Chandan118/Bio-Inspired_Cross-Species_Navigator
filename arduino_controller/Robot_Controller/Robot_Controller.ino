// (Content is the same as provided in the previous answer)

// Define the pins for your motor driver
// Motor A
const int ENA = 5; // PWM Speed Control
const int IN1 = 6;
const int IN2 = 7;
// Motor B
const int ENB = 10; // PWM Speed Control
const int IN3 = 8;
const int IN4 = 9;

// Define the analog pins for the sensors
const int MQ2_PIN = A0;
const int MQ135_PIN = A1;
const int CO2_PIN = A2;

// Ultrasonic sensor pins
const int ULTRASONIC_TRIG_PIN = 11;
const int ULTRASONIC_ECHO_PIN = 12;

const int MAX_COMMAND_LENGTH = 32; // Define a maximum command length

void setup() {
  // Set all the motor control pins to outputs
  pinMode(ENA, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(ENB, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  // Initialize serial communication with the Jetson Nano
  Serial.begin(115200);

  // Configure sensor pins
  pinMode(ULTRASONIC_TRIG_PIN, OUTPUT);
  pinMode(ULTRASONIC_ECHO_PIN, INPUT);
  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);
}

void loop() {
  // Check for incoming commands from the Jetson Nano
  if (Serial.available() > 0) {
    char cmd[MAX_COMMAND_LENGTH];
    int len = Serial.readBytesUntil('\n', cmd, MAX_COMMAND_LENGTH - 1);
    cmd[len] = '\0';  // Null-terminate the string

    // Convert char array to String object for processCommand function
    String cmdString = String(cmd);
    
    processCommand(cmdString);
  }

  // Send sensor data periodically (e.g., every 200ms)
  static unsigned long lastReadTime = 0;
  if (millis() - lastReadTime > 200) {
    readAndSendSensors();
    lastReadTime = millis();
  }
}

void processCommand(String cmd) {
  // Command format: "m,left_speed,right_speed"
  // e.g., "m,200,-200"
  if (cmd.startsWith("m")) {
    int firstComma = cmd.indexOf(',');
    int secondComma = cmd.indexOf(',', firstComma + 1);

    if (firstComma > 0 && secondComma > 0) {
      String leftSpeedStr = cmd.substring(firstComma + 1, secondComma);
      String rightSpeedStr = cmd.substring(secondComma + 1);
      int leftSpeed = leftSpeedStr.toInt();
      int rightSpeed = rightSpeedStr.toInt();
      setMotorSpeeds(leftSpeed, rightSpeed);
    }
  }
}

void setMotorSpeeds(int leftSpeed, int rightSpeed) {
  // Control Left Motor
  if (leftSpeed > 0) {
    digitalWrite(IN1, HIGH);
    digitalWrite(IN2, LOW);
  } else {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, HIGH);
  }
  analogWrite(ENA, constrain(abs(leftSpeed), 0, 255));

  // Control Right Motor
  if (rightSpeed > 0) {
    digitalWrite(IN3, HIGH);
    digitalWrite(IN4, LOW);
  } else {
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, HIGH);
  }
  analogWrite(ENB, constrain(abs(rightSpeed), 0, 255));
}

void readAndSendSensors() {
  int mq2Value = analogRead(MQ2_PIN);
  int mq135Value = analogRead(MQ135_PIN);
  int co2Value = analogRead(CO2_PIN);
  long ultrasonicRaw = readUltrasonicDistance();
  int ultrasonicDistance = constrain(static_cast<int>(ultrasonicRaw), 0, 400); // distance in cm

  // Send data in a structured format with identifiers to help parsing on the Jetson
  Serial.print("s,");
  Serial.print("mq2=");
  Serial.print(mq2Value);
  Serial.print(",");
  Serial.print("mq135=");
  Serial.print(mq135Value);
  Serial.print(",");
  Serial.print("co2=");
  Serial.print(co2Value);
  Serial.print(",");
  Serial.print("ultrasonic=");
  Serial.println(ultrasonicDistance);
}

long readUltrasonicDistance() {
  // Trigger the ultrasonic pulse
  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(ULTRASONIC_TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);

  // Measure the duration of the echo pulse
  long duration = pulseIn(ULTRASONIC_ECHO_PIN, HIGH, 30000); // 30 ms timeout (~5 m)
  if (duration <= 0) {
    return 0;
  }

  // Convert the time into distance (speed of sound ~343 m/s)
  long distanceCm = duration / 58; // standard conversion factor
  return distanceCm;
}
