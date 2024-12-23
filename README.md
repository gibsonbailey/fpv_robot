# FPV Camera Car

## Main Components
- Custom 3D Printed Camera Turret
- Raspberry Pi 4B
- Raspberry Pi Camera Module
- TMC2209 Motor Drivers
- 2x NEMA 17 Stepper Motors
- Traxxas Bandit Chassis
- Arduino Nano Every
- Quest 3 VR Headset


### PWM Control
The Arduino Nano Every is used to control the Traxxas 2056 Servo for steering and the Traxxas XL-5 for throttle. The TCA timer in the Nano is used to generate the PWM signals for the servos.

The clock speed of the nano is 16 MHz. This is prescaled by 64x. Then the TCA timer's top value is set to 4,999. This gives a PWM frequency of 50 Hz. This frequency is shared between two channels. The duty cycle is set by two compare registers.
