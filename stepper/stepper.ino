#include <AccelStepper.h>
#include <TMCStepper.h>


#define dirPin 21
#define stepPin 19

#define yawDirPin 15
#define yawStepPin 14

#define R_sense 0.1f

// TMC2209 is addressed based on the MS1 and MS2 pins
// If both pins are connected to GND, the address is 0b00
#define DRIVER_ADDRESS 0b00
#define YAW_DRIVER_ADDRESS 0b01


AccelStepper stepper(AccelStepper::DRIVER, stepPin, dirPin);
TMC2209Stepper driver(&Serial1, R_sense, DRIVER_ADDRESS);

AccelStepper yawStepper(AccelStepper::DRIVER, yawStepPin, yawDirPin);
TMC2209Stepper yawDriver(&Serial1, R_sense, YAW_DRIVER_ADDRESS);


const int MAX_SPEED = 3000;
const int MAX_ACCELERATION = 10000;
const int BAUD_RATE = 9600;
const int MICROSTEPS = 4;


int degrees_to_microsteps(int degrees) {
    // MICROSTEPS microsteps per step
    // 200 steps per revolution
    // 1 revolution = 360 degrees
    // 1 degree = 200 / 360 steps
    float microsteps = static_cast<float>(degrees) * 200.0f * static_cast<float>(MICROSTEPS) / 360.0f;
    return static_cast<int>(microsteps);
}

void prepare_driver(TMC2209Stepper& driver) {
  driver.beginSerial(BAUD_RATE);
  // Prepare for UART communication
  driver.pdn_disable(true);
  driver.mstep_reg_select(true);

  driver.rms_current(800);
  driver.microsteps(MICROSTEPS);
}

void prepare_stepper(AccelStepper& stepper) {
  stepper.setMaxSpeed(MAX_SPEED);
  stepper.setAcceleration(MAX_ACCELERATION);
}


void update_stepper_angles(AccelStepper& pitch_stepper, int32_t pitch_angle, AccelStepper& yaw_stepper, int32_t yaw_angle) {
    float yaw_gear_ratio = 75.0 / 30.0;
    float pitch_gear_ratio = 40.0 / 20.0;

    // multiplied by 10 for debugging
    const float half_turn_pitch_angle = 90.0f * 10.0f;

    // multiplied by 10 for debugging
    const float YAW_MAX_ANGLE =  10.0f * (360.0 * 5.0 / yaw_gear_ratio) / 2.0;

    // If yaw limit is reached, do not write
    if (yaw_angle < -YAW_MAX_ANGLE || yaw_angle > YAW_MAX_ANGLE) {
      Serial.println("Yaw limit reached");
      return;
    }

    // If pitch limit is reached, do not write
    if (pitch_angle < -half_turn_pitch_angle || pitch_angle > half_turn_pitch_angle) {
      Serial.println("Pitch limit reached");
      return;
    }

    // Translate the pitch and yaw angles to the servo angles.
    // 0, 0 -> half of max angle, half of max angle

    int yaw_stepper_angle = yaw_angle * yaw_gear_ratio;
    int pitch_stepper_angle = pitch_angle * pitch_gear_ratio;

    // Adjust pitch angle based on yaw angle
    pitch_stepper_angle = pitch_stepper_angle - yaw_angle;

    // translate angles to step
    pitch_stepper.moveTo(degrees_to_microsteps(pitch_stepper_angle));
    yaw_stepper.moveTo(degrees_to_microsteps(yaw_stepper_angle));
}

void setup() {
  Serial.begin(BAUD_RATE);
  Serial1.begin(BAUD_RATE);

  while (!Serial) {
    ;
  }
  while (!Serial1) {
    ;
  }
  Serial.println("Serial ready");

  prepare_driver(driver);
  Serial.println("Pitch TMC2209 ready");

  prepare_driver(yawDriver);
  Serial.println("Yaw TMC2209 ready");

  prepare_stepper(stepper);
  Serial.println("Stepper ready");

  prepare_stepper(yawStepper);
  Serial.println("Yaw Stepper ready");

  stepper.moveTo(4000);
  yawStepper.moveTo(4000);
}

int dir = -1;
int yawDir = 1;

int32_t pitch_angle = 0;
int32_t yaw_angle = 0;

void loop() {
    while (Serial.available() >= 8) {
      // Read 4 bytes for pitch and 4 bytes for yaw
        pitch_angle = (int32_t)Serial.read() << 24 | (int32_t)Serial.read() << 16 | (int32_t)Serial.read() << 8 | (int32_t)Serial.read();
        yaw_angle = (int32_t)Serial.read() << 24 | (int32_t)Serial.read() << 16 | (int32_t)Serial.read() << 8 | (int32_t)Serial.read();

        // Serial.print("Pitch angle: ");
        // Serial.println(pitch_angle);
        // Serial.print("Yaw angle: ");
        // Serial.println(yaw_angle);

        update_stepper_angles(stepper, pitch_angle, yawStepper, yaw_angle);
    }

    stepper.run();
    yawStepper.run();
}
