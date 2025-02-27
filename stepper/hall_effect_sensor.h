#ifndef HALL_SENSOR_H
#define HALL_SENSOR_H

#include <Arduino.h>

class HallSensor {
public:
  // Constructor: sensorPin is the input pin;
  // bufferSize is the number of trigger timestamps to store;
  // validWindow is the time window (in µs) for frequency calculation.
  HallSensor(uint8_t sensorPin, int bufferSize = 10, unsigned long validWindow = 100000UL);
  
  // Initialize sensor pin and attach the interrupt.
  void begin();

  // Calculate the frequency based on stored trigger times (in Hz).
  float getFrequency();

  // Returns distance in inches (based on trigger count and conversion factors).
  float getDistance();

  // Returns speed in mph (based on frequency and conversion factors).
  float getSpeed();

  // Returns the total trigger count.
  unsigned long getTriggerCount();

  // Instance interrupt handler called by the static ISR wrapper.
  void handleInterrupt();

  // Static ISR wrapper for attachInterrupt.
  static void isrWrapper();

private:
  uint8_t _sensorPin;
  int _bufferSize;
  unsigned long _validWindow;
  volatile unsigned long* _triggerTimes;
  volatile int _triggerHead;
  volatile unsigned long _triggerCount;

  // For ISR routing (assumes one instance)
  static HallSensor* instance;
};

#endif
