#pragma once

#include <Adafruit_BME280.h>
#include <Arduino.h>

struct EnvironmentSample {
    bool valid = false;
    float temperature = 0.0F;
    float pressure = 0.0F;
    float humidity = 0.0F;
};

struct MotionSample {
    bool valid = false;
    float ax = 0.0F;
    float ay = 0.0F;
    float az = 0.0F;
    float gx = 0.0F;
    float gy = 0.0F;
    float gz = 0.0F;
};

struct HealthCounters {
    unsigned long i2cErrors = 0;
    unsigned long recoveryAttempts = 0;
    unsigned long successfulRecoveries = 0;
    unsigned long bmeFailures = 0;
    unsigned long imuFailures = 0;
};

class SensorManager {
public:
    void begin();
    void scanI2C();
    void serviceHealth(unsigned long now);
    void healthCheck();

    EnvironmentSample readEnvironment();
    MotionSample readMotion();

    bool bmeHealthy() const;
    bool imuHealthy() const;
    bool auxPresent() const;

    void injectFault(const String &target);
    void clearInjectedFaults();

    const HealthCounters &counters() const;

private:
    Adafruit_BME280 bme_;

    bool bmeOnline_ = false;
    bool imuOnline_ = false;
    bool auxPresent_ = false;
    bool injectedBmeFault_ = false;
    bool injectedImuFault_ = false;

    unsigned long lastHealthCheckMs_ = 0;
    HealthCounters counters_;

    bool devicePresent(uint8_t address);
    uint8_t readRegister(uint8_t address, uint8_t reg);
    bool writeRegister(uint8_t address, uint8_t reg, uint8_t value);
    bool readWord(uint8_t address, uint8_t reg, int16_t &value);

    bool setupBME();
    bool setupIMU();
    void setupAux();
    bool recoverBME();
    bool recoverIMU();
};
