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
#define YAW_DRIVER_ADDRESS 0b10


AccelStepper stepper(AccelStepper::DRIVER, stepPin, dirPin);
TMC2209Stepper driver(&Serial1, R_sense, DRIVER_ADDRESS);

AccelStepper yawStepper(AccelStepper::DRIVER, yawStepPin, yawDirPin);
TMC2209Stepper yawDriver(&Serial1, R_sense, YAW_DRIVER_ADDRESS);


const int MAX_SPEED = 3000;
const int MAX_ACCELERATION = 10000;
const int BAUD_RATE = 9600;
const int MICROSTEPS = 4;


int degrees_to_microsteps(float degrees) {
    // MICROSTEPS microsteps per step
    // 200 steps per revolution
    // 1 revolution = 360 degrees
    // 1 degree = 200 / 360 steps
    float microsteps_setting = static_cast<float>(MICROSTEPS);
    if (MICROSTEPS == 0) {
      microsteps_setting = 1;
    }
    float microsteps = degrees * 200.0f * microsteps_setting / 360.0f;
    int s = static_cast<int>(microsteps);
    // Serial.print("Steps: ");
    // Serial.println(s);
    return s;
}

void prepare_driver(TMC2209Stepper& driver) {
  driver.beginSerial(BAUD_RATE);
  // Prepare for UART communication
  driver.pdn_disable(true);
  driver.mstep_reg_select(true);

  driver.rms_current(750);
  driver.microsteps(MICROSTEPS);
}

// Optional argument for slow acceleration
void prepare_stepper(AccelStepper& stepper, bool slow = false) {
  if (slow) {
    stepper.setMaxSpeed(static_cast<float>(MAX_SPEED));// / (75.0f / 30.0f) / 1.1f);
    stepper.setAcceleration(static_cast<float>(MAX_ACCELERATION) / (75.0f / 30.0f) / 1.1f);
  } else {
    stepper.setMaxSpeed(MAX_SPEED);
    stepper.setAcceleration(MAX_ACCELERATION);
  }
}

void update_stepper_angles(AccelStepper& pitch_stepper, float pitch_angle, AccelStepper& yaw_stepper, float yaw_angle) {
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

    float yaw_stepper_angle = yaw_angle * yaw_gear_ratio;
    float pitch_stepper_angle = pitch_angle * pitch_gear_ratio;

    // Adjust pitch angle based on yaw angle
    pitch_stepper_angle = pitch_stepper_angle - yaw_angle;

    // translate angles to step
    pitch_stepper.moveTo(degrees_to_microsteps(pitch_stepper_angle));
    yaw_stepper.moveTo(degrees_to_microsteps(yaw_stepper_angle));
}

float remap(float value, float fromLow, float fromHigh, float toLow, float toHigh) {
  return (value - fromLow) * (toHigh - toLow) / (fromHigh - fromLow) + toLow;
}

const float min_steering_duty = 0.052;
const float max_steering_duty = 0.098;
const float top = 4999;
const float steering_trim = -22.0;

uint16_t mapSteering(float fraction) {
  // Constrain fraction to [0.0, 1.0]
  if (fraction < 0.0f) fraction = 0.0f;
  if (fraction > 1.0f) fraction = 1.0f;

  // Linear interpolation
  float mapped = remap(fraction, 0.0f, 1.0f, min_steering_duty * top, max_steering_duty * top);

  // Add trim
  mapped += steering_trim;

  if (mapped > top) mapped = top; // Safety clamp

  return (uint16_t)mapped;
}

const float min_throttle_duty = 0.05;
const float max_throttle_duty = 0.1;

uint16_t mapThrottle(float fraction) {
  // Constrain fraction to [0.0, 1.0]
  if (fraction < 0.0f) fraction = 0.0f;
  if (fraction > 1.0f) fraction = 1.0f;

  // Linear interpolation
  float mapped = remap(fraction, 0.0f, 1.0f, min_throttle_duty * top, max_throttle_duty * top);
  if (mapped > top) mapped = top; // Safety clamp

  return (uint16_t)mapped;
}

void setup() {
  // Initialize Serial1 and set up drivers immediately, otherwise
  // the current will not be limited on start up and the motors may get hot.
  Serial1.begin(BAUD_RATE);

  while (!Serial1) {
    ;
  }

  prepare_driver(driver);
  prepare_driver(yawDriver);

  // Start talking to command computer
  Serial.begin(115200);
  while (!Serial) {
    ;
  }
  Serial.println("Pitch TMC2209 ready");
  Serial.println("Yaw TMC2209 ready");

  prepare_stepper(stepper, true);
  Serial.println("Stepper ready");

  prepare_stepper(yawStepper);
  Serial.println("Yaw Stepper ready");

  stepper.moveTo(0);
  yawStepper.moveTo(0);

  // Begin setup for RC car motor controls
  pinMode(9, OUTPUT); // TCA channel 0
  pinMode(10, OUTPUT); // TCA channel 1

  noInterrupts();      // Disable interrupts during setup

  // Set up TCA0 for 50 Hz PWM on channels 0 & 1

  // Clear TCA0 before configuring
  TCA0.SINGLE.CTRLA = 0;

  // Single-slope PWM mode; enable compare channels 0 & 1
  TCA0.SINGLE.CTRLB = TCA_SINGLE_WGMODE_SINGLESLOPE_gc
                    | TCA_SINGLE_CMP0EN_bm
                    | TCA_SINGLE_CMP1EN_bm;

  // Clock source = 16 MHz / 64 = 250 kHz
  // Set period for 50 Hz
  TCA0.SINGLE.PER = 4999;
  // Set period for 500 Hz
  // TCA0.SINGLE.PER = 9999;

  // Example duty cycles (50% here)
  TCA0.SINGLE.CMP0 = mapSteering(0.5);
  TCA0.SINGLE.CMP1 = mapThrottle(0.5);

  // Clear any pending interrupts
  TCA0.SINGLE.INTFLAGS = TCA_SINGLE_OVF_bm;

  // Enable the timer; prescaler = 64
  TCA0.SINGLE.CTRLA = TCA_SINGLE_CLKSEL_DIV64_gc
                    | TCA_SINGLE_ENABLE_bm;
  // Enable the timer; prescaler = 4
  // TCA0.SINGLE.CTRLA = TCA_SINGLE_CLKSEL_DIV4_gc
  //                   | TCA_SINGLE_ENABLE_bm;

  interrupts();        // Re-enable interrupts
}

int dir = -1;
int yawDir = 1;

int counter = 0;

// 4 bytes for header, 
// 4 bytes for pitch,
// 4 bytes for yaw,
// 4 bytes for throttle,
// 4 bytes for steering
const int buffer_size = 20;
const int header_size = 4;
byte serial_buffer[buffer_size];
int serial_buffer_index = 0;
int32_t HEADER = 0xDEADBEEF;

uint16_t test_val = 0;
int increment = 1;

void loop() {
    if (Serial.available()) {
        byte b = Serial.read();
        if (serial_buffer_index < buffer_size) {
            serial_buffer[serial_buffer_index] = b;
            serial_buffer_index += 1;
        }

        // if there are 4 bytes in the buffer, check for a valid header
        if (serial_buffer_index == 4) {
            int32_t header = 0;
            memcpy(&header, serial_buffer, 4);
            if (header != HEADER) {
                // Shift the buffer by 1 byte
                for (int i = 0; i < buffer_size - 1; i++) {
                    serial_buffer[i] = serial_buffer[i + 1];
                }
                serial_buffer_index--;
            }
        }

        float pitch_angle = 0;
        float yaw_angle = 0;
        float throttle_value = 0;
        float steering_value = 0;

        if (serial_buffer_index == buffer_size) {
            memcpy(&pitch_angle, serial_buffer + header_size, 4);
            memcpy(&yaw_angle, serial_buffer + header_size + 4, 4);
            memcpy(&throttle_value, serial_buffer + header_size + 8, 4);
            memcpy(&steering_value, serial_buffer + header_size + 12, 4);

            serial_buffer_index = 0;

            // Serial.print("Yaw angle: ");
            // Serial.println(yaw_angle);

            update_stepper_angles(stepper, pitch_angle, yawStepper, yaw_angle);

            Serial.print("Pitch: ");
            Serial.println(pitch_angle);
            Serial.print("Yaw: ");
            Serial.println(yaw_angle);
            Serial.print("Throttle: ");
            Serial.println(throttle_value);
            Serial.print("Steering: ");
            Serial.println(steering_value);

            const float steering_yaw = remap(-steering_value, -1.0f, 1.0f, 0.0f, 1.0f);
            const float throttle_val = remap(throttle_value, 0.0f, 1.0f, 0.5f, 1.0f);

            // pin 9 (steering)
            TCA0.SINGLE.CMP0 = mapSteering(steering_yaw);
            // pin 10 (throttle)
            TCA0.SINGLE.CMP1 = mapThrottle(throttle_val);
        }
    }

    stepper.run();
    yawStepper.run();
}
