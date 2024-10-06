#include "ServoManager.h"


ServoManager::ServoManager(Servo& pitch_servo, Servo& yaw_servo) : pitch_servo_(pitch_servo), yaw_servo_(yaw_servo) {}


void ServoManager::update_angles(int pitch, int yaw) {
  // half turn of pitch up or down is allowed at any given yaw angle.

  float yaw_gear_ratio = 50.0 / 15.0;
  float pitch_gear_ratio = 40.0 / 20.0;

  const float half_turn_pitch_angle = 90;

  const float YAW_MAX_ANGLE = (360.0 * 5.0 / yaw_gear_ratio) / 2.0;

  // If yaw limit is reached, do not write
  if (yaw < -YAW_MAX_ANGLE || yaw > YAW_MAX_ANGLE) {
    Serial.println("Yaw limit reached");
    return;
  }

  // If pitch limit is reached, do not write
  if (pitch < -half_turn_pitch_angle || pitch > half_turn_pitch_angle) {
    Serial.println("Pitch limit reached");
    return;
  }

  // Translate the pitch and yaw angles to the servo angles.
  // 0, 0 -> half of max angle, half of max angle

  int yaw_servo_angle = yaw * yaw_gear_ratio;
  int pitch_servo_angle = pitch * pitch_gear_ratio;

  // Adjust pitch angle based on yaw angle
  pitch_servo_angle = pitch_servo_angle - yaw;

  const int BILDA_SERVO_MAX_ANGLE = 360 * 5;
  const float BILDA_MIN_MS = 500;
  const float BILDA_MAX_MS = 2500;

  yaw_servo_.writeMicroseconds(map(yaw_servo_angle, -BILDA_SERVO_MAX_ANGLE / 2, BILDA_SERVO_MAX_ANGLE / 2, BILDA_MIN_MS, BILDA_MAX_MS));
  pitch_servo_.writeMicroseconds(map(pitch_servo_angle, -BILDA_SERVO_MAX_ANGLE / 2, BILDA_SERVO_MAX_ANGLE / 2, BILDA_MIN_MS, BILDA_MAX_MS));
}

