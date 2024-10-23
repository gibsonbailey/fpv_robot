#include <Stream.h>
#include <AccelStepper.h>
#include <TMCStepper.h>
#include <SoftwareSerial.h>

// Define SoftwareSerial pins
#define SW_TX 18 // Arduino TX (to TMC2209 RX)
#define SW_RX 17 // Arduino RX (to TMC2209 TX)
                
// Pin definitions
#define dirPin 21
#define stepPin 19

// Define R_sense for current settings (e.g., 0.1 ohm)
#define R_sense 0.1f

#define DRIVER_ADDRESS 0b00 // TMC2209 Driver address according to MS1 and MS2


String byteToBinary(uint8_t byte) {
  String binary = "";
  for (int i = 0; i < 8; i++) {
    binary += (byte & (1 << i)) ? '1' : '0';
  }
  return binary;
}

class DualSerial : public SoftwareSerial {
  public:
    // Constructor calls SoftwareSerial's constructor
    DualSerial(int rxPin, int txPin, HardwareSerial &hSerial)
      : SoftwareSerial(rxPin, txPin), hardwareSerial(hSerial) {}

    void begin(long baudRate) {
      SoftwareSerial::begin(baudRate); // Start software serial
      hardwareSerial.begin(baudRate);  // Start hardware serial
    }

    // Override the write method to mirror output to both serial instances
    size_t write(uint8_t byte) override {
      // convert the byte to a series of 0s and 1s if not a newline
      if (byte != '\n') {
        hardwareSerial.print("Data Write: ");
        hardwareSerial.println(byteToBinary(byte));
      } else {
        hardwareSerial.write(byte);
      }

      // size_t hwCount = hardwareSerial.write(byte); // Write to hardware serial
      size_t swCount = SoftwareSerial::write(byte); // Write to software serial
      return swCount;
    }

    int read() override {
      hardwareSerial.print("Data Read: ");
      int data = SoftwareSerial::read();
      if (data != -1) {
        hardwareSerial.println(data);
      } else {
        hardwareSerial.println("No data");
      }
      return data;
    }

  private:
    HardwareSerial &hardwareSerial;
};


// Create SoftwareSerial instance
SoftwareSerial softSerial(SW_RX, SW_TX);
// DualSerial softSerial(SW_RX, SW_TX, Serial);
// DualHardwareSerial dualHardwareSerial(Serial, Serial1);
// SoftwareSerial mySerial(17, 18);


// Create instances
AccelStepper stepper(AccelStepper::DRIVER, stepPin, dirPin);
TMC2209Stepper driver(&Serial1, R_sense, DRIVER_ADDRESS);


const int MAX_SPEED = 400;


void setup() {

  const int BAUD_RATE = 115200;

  Serial1.begin(BAUD_RATE);
  Serial.begin(BAUD_RATE); // Communication with computer
  softSerial.begin(BAUD_RATE); // Communication with TMC2209

  while (!Serial) ; // Wait for Serial to be ready
  Serial.println("Serial ready");

  while (!Serial1) ; // Wait for Serial to be ready
  Serial1.println("Serial1 ready");
  Serial.println("Serial1 ready");

  // Initialize TMC2209
  // softSerial.begin(BAUD_RATE); // Communication with TMC2209
  driver.beginSerial(BAUD_RATE); // Communication with TMC2209
	driver.pdn_disable(true);
	driver.mstep_reg_select(true);
  // driver.begin(9600);       // Initialize driver
  driver.toff(4);       // Enable driver with a minimum off time (recommended setting)
  driver.rms_current(400); // Set motor current to 400mA
  driver.microsteps(0); // Set microsteps to 2

  Serial.println("TMC2209 ready");

  // Setup AccelStepper
  stepper.setMaxSpeed(MAX_SPEED); // Set max speed (steps/second)
  stepper.setAcceleration(100); // Set acceleration (steps/second^2)
  Serial.println("AccelStepper ready");

  stepper.moveTo(100);         // Move to position
}

int dir = 1;

int speed = 400;

int count = 0;

// Time how long it takes to do 10000 steps
unsigned long startMillis = 0;


const int count_interval = 300000;


void loop() {
  count++;
  if (stepper.distanceToGo() == 0) {
    dir = -dir; // Change direction
    stepper.moveTo((400 * dir) - 700); // Move to new position
  }

  stepper.run(); // Continuously run the stepper
}
