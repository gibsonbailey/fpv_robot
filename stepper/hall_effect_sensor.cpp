#include "hall_effect_sensor.h"

HallSensor* HallSensor::instance = nullptr;

HallSensor::HallSensor(uint8_t sensorPin, int bufferSize, unsigned long validWindow)
  : _sensorPin(sensorPin),
    _bufferSize(bufferSize),
    _validWindow(validWindow),
    _triggerHead(0),
    _triggerCount(0)
{
  _triggerTimes = new unsigned long[_bufferSize];
  for (int i = 0; i < _bufferSize; i++) {
    _triggerTimes[i] = 0;
  }
  instance = this; // Set the static instance pointer
}

void HallSensor::begin() {
  pinMode(_sensorPin, INPUT);
  attachInterrupt(digitalPinToInterrupt(_sensorPin), HallSensor::isrWrapper, RISING);
}

void HallSensor::handleInterrupt() {
  unsigned long currentTime = micros();
  if (_triggerHead >= _bufferSize) {
    _triggerHead = 0;
  }
  _triggerTimes[_triggerHead++] = currentTime;
  _triggerCount++;
}

void HallSensor::isrWrapper() {
  if (instance) {
    instance->handleInterrupt();
  }
}

float HallSensor::getFrequency() {
  unsigned long currentTime = micros();
  
  // Determine the index of the latest trigger
  int latestIndex = _triggerHead - 1;
  if (latestIndex < 0) {
    latestIndex = _bufferSize - 1;
  }
  
  // Find the earliest valid trigger within the valid time window
  int earliestIndex = latestIndex;
  for (int i = 0; i < _bufferSize; i++) {
    if (earliestIndex < 0) {
      earliestIndex = _bufferSize - 1;
    }
    // Stop if we have looped back to the current head
    if (earliestIndex == _triggerHead) {
      break;
    }
    unsigned long t = _triggerTimes[earliestIndex];
    unsigned long elapsed = currentTime - t;
    if (t == 0 || elapsed > _validWindow) {
      break;
    }
    earliestIndex--;
  }
  
  if (earliestIndex < 0) {
    earliestIndex = _bufferSize - 1;
  }
  if (earliestIndex == latestIndex) {
    return 0;
  }
  
  float timeDiff = _triggerTimes[latestIndex] - _triggerTimes[earliestIndex];
  int indexDiff = latestIndex - earliestIndex;
  if (indexDiff < 0) {
    indexDiff += _bufferSize;
  }
  
  float avgTimeDiff = timeDiff / indexDiff;
  if (avgTimeDiff == 0) {
    return 0;
  }
  
  return 1e6 / avgTimeDiff;
}

float HallSensor::getDistance() {
  // Conversion factors based on:
  // - 3.35" wheel diameter => 10.52" circumference.
  // - 9 sensor triggers per wheel revolution.
  return _triggerCount * 10.52 / 9.0;
}

float HallSensor::getSpeed() {
  // Conversion factor: frequency (Hz) / 15.03 ≈ mph.
  return getFrequency() / 15.03;
}

unsigned long HallSensor::getTriggerCount() {
  return _triggerCount;
}
