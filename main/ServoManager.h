#ifndef SERVOMANAGER_H
#define SERVOMANAGER_H

#include <Servo.h>
#include <Arduino.h>

class ServoManager {
  private:
    Servo& pitch_servo_;
    Servo& yaw_servo_;

  public:
    ServoManager(Servo& pitch_servo, Servo& yaw_servo);
    void init();
    void update_angles(int pitch, int yaw);
};

#endif
