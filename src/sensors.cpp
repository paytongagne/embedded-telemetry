#include "sensors.h"

#include <Wire.h>
#include <math.h>

#include "config.h"

void SensorManager::begin() {
    Wire.begin();
    setupBME();
    setupIMU();
    setupAux();
    lastHealthCheckMs_ = millis();
}

bool SensorManager::devicePresent(uint8_t address) {
    Wire.beginTransmission(address);
    return Wire.endTransmission() == 0;
}

uint8_t SensorManager::readRegister(uint8_t address, uint8_t reg) {
    Wire.beginTransmission(address);
    Wire.write(reg);

    if (Wire.endTransmission(false) != 0) {
        counters_.i2cErrors++;
        return 0xFF;
    }

    Wire.requestFrom(address, static_cast<uint8_t>(1));
    if (!Wire.available()) {
        counters_.i2cErrors++;
        return 0xFF;
    }

    return Wire.read();
}

bool SensorManager::writeRegister(uint8_t address, uint8_t reg, uint8_t value) {
    Wire.beginTransmission(address);
    Wire.write(reg);
    Wire.write(value);

    if (Wire.endTransmission() != 0) {
        counters_.i2cErrors++;
        return false;
    }

    return true;
}

bool SensorManager::readWord(uint8_t address, uint8_t reg, int16_t &value) {
    Wire.beginTransmission(address);
    Wire.write(reg);

    if (Wire.endTransmission(false) != 0) {
        counters_.i2cErrors++;
        return false;
    }

    Wire.requestFrom(address, static_cast<uint8_t>(2));
    if (Wire.available() < 2) {
        counters_.i2cErrors++;
        return false;
    }

    value = (static_cast<int16_t>(Wire.read()) << 8) | Wire.read();
    return true;
}

void SensorManager::scanI2C() {
    Serial.println();
    Serial.println("=== I2C DEVICE SCAN ===");

    int deviceCount = 0;
    for (uint8_t address = 1; address < 127; address++) {
        if (!devicePresent(address)) {
            continue;
        }

        Serial.print("Found: 0x");
        if (address < 16) {
            Serial.print("0");
        }
        Serial.println(address, HEX);
        deviceCount++;
    }

    Serial.print("Total devices: ");
    Serial.println(deviceCount);
}

bool SensorManager::setupBME() {
    bmeOnline_ = bme_.begin(config::BME_ADDRESS);
    return bmeOnline_;
}

bool SensorManager::setupIMU() {
    const uint8_t whoAmI = readRegister(config::MPU_ADDRESS, 0x75);
    imuOnline_ = whoAmI == 0x71 && writeRegister(config::MPU_ADDRESS, 0x6B, 0x00);

    if (imuOnline_) {
        delay(100);
    }

    return imuOnline_;
}

void SensorManager::setupAux() {
    auxPresent_ = devicePresent(config::AUX_ADDRESS);
}

bool SensorManager::recoverBME() {
    counters_.recoveryAttempts++;
    if (setupBME()) {
        counters_.successfulRecoveries++;
        return true;
    }
    return false;
}

bool SensorManager::recoverIMU() {
    counters_.recoveryAttempts++;
    if (setupIMU()) {
        counters_.successfulRecoveries++;
        return true;
    }
    return false;
}

void SensorManager::healthCheck() {
    const bool previousBme = bmeOnline_;
    const bool previousImu = imuOnline_;

    if (!injectedBmeFault_) {
        const bool identityOk = readRegister(config::BME_ADDRESS, 0xD0) == 0x60;
        bmeOnline_ = bmeOnline_ && identityOk;
        if (!bmeOnline_) {
            recoverBME();
        }
    }

    if (!injectedImuFault_) {
        const bool identityOk = readRegister(config::MPU_ADDRESS, 0x75) == 0x71;
        imuOnline_ = imuOnline_ && identityOk;
        if (!imuOnline_) {
            recoverIMU();
        }
    }

    if (previousBme && !bmeOnline_) {
        counters_.bmeFailures++;
    }
    if (previousImu && !imuOnline_) {
        counters_.imuFailures++;
    }

    setupAux();
}

void SensorManager::serviceHealth(unsigned long now) {
    if (now - lastHealthCheckMs_ < config::HEALTH_CHECK_INTERVAL_MS) {
        return;
    }

    lastHealthCheckMs_ = now;
    healthCheck();
}

EnvironmentSample SensorManager::readEnvironment() {
    EnvironmentSample sample;
    if (!bmeHealthy()) {
        return sample;
    }

    sample.temperature = bme_.readTemperature();
    sample.pressure = bme_.readPressure() / 100.0F;
    sample.humidity = bme_.readHumidity();

    if (isnan(sample.temperature) || isnan(sample.pressure) || isnan(sample.humidity)) {
        bmeOnline_ = false;
        counters_.bmeFailures++;
        return sample;
    }

    sample.valid = true;
    return sample;
}

MotionSample SensorManager::readMotion() {
    MotionSample sample;
    if (!imuHealthy()) {
        return sample;
    }

    int16_t rawAx = 0;
    int16_t rawAy = 0;
    int16_t rawAz = 0;
    int16_t rawGx = 0;
    int16_t rawGy = 0;
    int16_t rawGz = 0;

    const bool readOk =
        readWord(config::MPU_ADDRESS, 0x3B, rawAx) &&
        readWord(config::MPU_ADDRESS, 0x3D, rawAy) &&
        readWord(config::MPU_ADDRESS, 0x3F, rawAz) &&
        readWord(config::MPU_ADDRESS, 0x43, rawGx) &&
        readWord(config::MPU_ADDRESS, 0x45, rawGy) &&
        readWord(config::MPU_ADDRESS, 0x47, rawGz);

    if (!readOk) {
        imuOnline_ = false;
        counters_.imuFailures++;
        return sample;
    }

    sample.ax = rawAx / 16384.0F;
    sample.ay = rawAy / 16384.0F;
    sample.az = rawAz / 16384.0F;
    sample.gx = rawGx / 131.0F;
    sample.gy = rawGy / 131.0F;
    sample.gz = rawGz / 131.0F;
    sample.valid = true;
    return sample;
}

bool SensorManager::bmeHealthy() const {
    return bmeOnline_ && !injectedBmeFault_;
}

bool SensorManager::imuHealthy() const {
    return imuOnline_ && !injectedImuFault_;
}

bool SensorManager::auxPresent() const {
    return auxPresent_;
}

void SensorManager::injectFault(const String &target) {
    if (target == "BME") {
        injectedBmeFault_ = true;
    } else if (target == "IMU") {
        injectedImuFault_ = true;
    }
}

void SensorManager::clearInjectedFaults() {
    injectedBmeFault_ = false;
    injectedImuFault_ = false;
    healthCheck();
}

const HealthCounters &SensorManager::counters() const {
    return counters_;
}
