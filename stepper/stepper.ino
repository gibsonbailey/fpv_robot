#include <AccelStepper.h>
#include <TMCStepper.h>
#include "hall_effect_sensor.h"

HallSensor hallSensor(5, 10, 100000); // Pin 5, buffer size 10, valid window 100us

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


const int MAX_STEPPER_SPEED = 3000;
const int MAX_STEPPER_ACCELERATION = 10000;
const int TMC2209_BAUD_RATE = 9600;
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
    return s;
}

void prepare_driver(TMC2209Stepper& driver) {
  driver.beginSerial(TMC2209_BAUD_RATE);
  // Prepare for UART communication
  driver.pdn_disable(true);
  driver.mstep_reg_select(true);

  driver.rms_current(750);
  driver.microsteps(MICROSTEPS);
}

// Define steering angle constants
const float L = 0.3;          // Wheelbase in meters
const float a_c_max = 9.8;    // Maximum centripetal acceleration in m/s²
const float delta_max = 0.5236; // Maximum steering angle in radians (approximately 30 degrees)

float get_speed_limited_steering_angle(float steering_input, float speed_mph) {
  // Convert speed to m/s
  float speed_ms = speed_mph * 0.44704;

  float r_min = speed_ms * speed_ms / a_c_max;

  // Calculate maximum steering angle based on speed
  float delta = atan(L / r_min);

  float k = min(delta / delta_max, 1.0f);

  // Limit steering angle based on speed
  return steering_input * k;
}

// Optional argument for slow acceleration
void prepare_stepper(AccelStepper& stepper, bool slow = false) {
  if (slow) {
    stepper.setMaxSpeed(static_cast<float>(MAX_STEPPER_SPEED));// / (75.0f / 30.0f) / 1.1f);
    stepper.setAcceleration(static_cast<float>(MAX_STEPPER_ACCELERATION) / (75.0f / 30.0f) / 1.1f);
  } else {
    stepper.setMaxSpeed(MAX_STEPPER_SPEED);
    stepper.setAcceleration(MAX_STEPPER_ACCELERATION);
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


int lipo_average_percentage = 0;
int nimh_average_percentage = 0;

uint8_t lipo_percentage_buffer[10];
uint8_t nimh_percentage_buffer[10];

uint8_t lipo_percentage_index = 0;
uint8_t nimh_percentage_index = 0;

// Use 8.4 V as 100%
// This voltage is cut in half by the voltage divider
// before being read by the analog pin
const float MAX_NIMH_BATTERY_VOLTAGE = 8.4;
const float MIN_NIMH_BATTERY_VOLTAGE = 7.0;
const float MAX_LIPO_BATTERY_VOLTAGE = 8.4;
const float MIN_LIPO_BATTERY_VOLTAGE = 6.4;
const float BATTERY_VOLTAGE_DIVIDER = 2.0;

int get_lipo_battery_percentage() {
  int battery_voltage = analogRead(A2);
  float voltage = battery_voltage * 4.3f / 1023.0f * BATTERY_VOLTAGE_DIVIDER;
  int percentage = remap(voltage, MIN_LIPO_BATTERY_VOLTAGE, MAX_LIPO_BATTERY_VOLTAGE, 0, 100);
  if (percentage < 0) {
    percentage = 0;
  }
  return percentage;
}

int get_nimh_battery_percentage() {
  int battery_voltage = analogRead(A3);
  float voltage = battery_voltage * 4.3f / 1023.0f * BATTERY_VOLTAGE_DIVIDER;
  int percentage = remap(voltage, MIN_NIMH_BATTERY_VOLTAGE, MAX_NIMH_BATTERY_VOLTAGE, 0, 100);
  if (percentage < 0) {
    percentage = 0;
  }
  return percentage;
}

void setup() {
  // Initialize Serial1 and set up drivers immediately, otherwise
  // the current will not be limited on start up and the motors may get hot.
  Serial1.begin(TMC2209_BAUD_RATE);

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

   // Disable interrupts during setup
  noInterrupts();

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

  // Use this to set the analog reference voltage
  // for the ADC
  analogReference(INTERNAL4V3);
  
  interrupts();        // Re-enable interrupts

  // Set up hall effect sensor
  hallSensor.begin();

  // initialize battery percentages
  int initial_lipo_percentage = get_lipo_battery_percentage();
  int initial_nimh_percentage = get_nimh_battery_percentage();
  for (int i = 0; i < 10; i++) {
    lipo_percentage_buffer[i] = initial_lipo_percentage;
    nimh_percentage_buffer[i] = initial_nimh_percentage;
  }
}


int loop_counter = 0;

// 4 bytes for header, 
// 1 byte for sequence number,
// 4 bytes for pitch,
// 4 bytes for yaw,
// 4 bytes for throttle,
// 4 bytes for steering
// 1 byte for checksum
const int buffer_size = 22;
const int header_size = 4;
byte serial_buffer[buffer_size];
int serial_buffer_index = 0;
int32_t HEADER = 0xDEADBEEF;

unsigned long last_control_update = 0;
uint8_t expected_sequence_number = 0;

void loop() {
    if (loop_counter % 100000 == 0) {
        lipo_percentage_buffer[lipo_percentage_index] = get_lipo_battery_percentage();
        nimh_percentage_buffer[nimh_percentage_index] = get_nimh_battery_percentage();
        lipo_percentage_index = (lipo_percentage_index + 1) % 10;
        nimh_percentage_index = (nimh_percentage_index + 1) % 10;

        int sum = 0;
        for (int i = 0; i < 10; i++) {
            sum += lipo_percentage_buffer[i];
        }
        lipo_average_percentage = sum / 10;
        
        sum = 0;
        for (int i = 0; i < 10; i++) {
            sum += nimh_percentage_buffer[i];
        }
        nimh_average_percentage = sum / 10;
    }

    if (loop_counter % 1000 == 0) {
        float distance = hallSensor.getDistance();
        float speed = hallSensor.getSpeed();

        Serial.print("tel: ");
        Serial.print(speed);
        Serial.print(" ");
        Serial.print(distance / 12.0f); // inches to feet
        Serial.print(" ");
        Serial.print(lipo_average_percentage);
        Serial.print(" ");
        Serial.print(nimh_average_percentage);
        Serial.println();
    }

    loop_counter++;

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
            uint8_t receieved_sequence_number = serial_buffer[header_size]; 
            uint8_t received_checksum = serial_buffer[buffer_size - 1];
            
            uint8_t computed_checksum = 0;
            for (int i = 0; i < buffer_size - 1; i++) {
                computed_checksum ^= serial_buffer[i];
            }
            
            if (computed_checksum == received_checksum) {
                if (receieved_sequence_number == expected_sequence_number) {
                    expected_sequence_number = (expected_sequence_number + 1) % 256;

                    memcpy(&pitch_angle, serial_buffer + header_size + 1, 4);
                    memcpy(&yaw_angle, serial_buffer + header_size + 1 + 4, 4);
                    memcpy(&throttle_value, serial_buffer + header_size + 1 + 8, 4);
                    memcpy(&steering_value, serial_buffer + header_size + 1 + 12, 4);

                    update_stepper_angles(stepper, pitch_angle, yawStepper, yaw_angle);

                    Serial.print("Pitch: ");
                    Serial.println(pitch_angle);
                    Serial.print("Yaw: ");
                    Serial.println(yaw_angle);
                    Serial.print("Throttle: ");
                    Serial.println(throttle_value);
                    Serial.print("Steering: ");
                    Serial.println(steering_value);
                    
                    // Adjust steering angle based on speed
                    steering_value = get_speed_limited_steering_angle(steering_value, hallSensor.getSpeed());

                    // There is a dead zone in the middle of the throttle signal from -0.1 to 0.1 in the ESC
                    // Compress that dead zone to -0.02 to 0.02, so the throttle is more responsive
                    if (throttle_value > 0.02) {
                        throttle_value = remap(throttle_value, 0.0, 1.0, 0.1, 1.0);
                    } else if (throttle_value < -0.02) {
                        // Make reverse half as fast
                        throttle_value = remap(throttle_value, -1.0, 0.0, -0.5, -0.1);
                    } else {
                        throttle_value = 0.0;
                    }

                    const float steering_val = remap(-steering_value, -1.0f, 1.0f, 0.0f, 1.0f);
                    const float throttle_val = remap(throttle_value, 0.0f, 1.0f, 0.5f, 1.0f);

                    last_control_update = millis();

                    // pin 9 (steering)
                    TCA0.SINGLE.CMP0 = mapSteering(steering_val);
                    // pin 10 (throttle)
                    TCA0.SINGLE.CMP1 = mapThrottle(throttle_val);
                } else {
                    Serial.println("Sequence number mismatch");
                    expected_sequence_number = (receieved_sequence_number + 1) % 256;
                }
            } else {
                Serial.println("Checksum mismatch");
            }
            serial_buffer_index = 0;
        }
    }

    if (millis() - last_control_update > 400) {
        // pin 9 (steering)
        TCA0.SINGLE.CMP0 = mapSteering(0.5);
        // pin 10 (throttle)
        TCA0.SINGLE.CMP1 = mapThrottle(0.5);
    }

    stepper.run();
    yawStepper.run();
}
