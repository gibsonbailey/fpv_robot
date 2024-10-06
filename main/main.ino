#include <Arduino.h>
#include <Servo.h>
#include "ServoManager.h"


Servo pitchServo;  // Create a servo object
Servo yawServo;  // Create a servo object

const uint8_t PITCH_SERVO_PIN = 9;
const uint8_t YAW_SERVO_PIN = 10;

ServoManager servoManager(pitchServo, yawServo);

int32_t pitch_angle = 0;
int32_t yaw_angle = 0;


void setup() {
  pitchServo.attach(PITCH_SERVO_PIN, 500, 2500);  // Attach the servo to pin 9
  yawServo.attach(YAW_SERVO_PIN, 500, 2500);  // Attach the servo to pin 10

  Serial.begin(9600);

  Serial.println("Setting up Serial");
  while (!Serial) {}
  Serial.println("Finished setting up Serial");
}


 void loop() {
   while (Serial.available() >= 8) {
     // Read 4 bytes for pitch and 4 bytes for yaw
     pitch_angle = (int32_t)Serial.read() << 24 | (int32_t)Serial.read() << 16 | (int32_t)Serial.read() << 8 | (int32_t)Serial.read();
     yaw_angle = (int32_t)Serial.read() << 24 | (int32_t)Serial.read() << 16 | (int32_t)Serial.read() << 8 | (int32_t)Serial.read();

     servoManager.update_angles(pitch_angle, yaw_angle);
   }
 }
