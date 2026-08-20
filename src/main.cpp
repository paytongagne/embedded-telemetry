#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_BME280.h>
#include <VL53L0X.h>

Adafruit_BME280 bme;
VL53L0X tof;

const uint8_t MPU_ADDR = 0x68;

unsigned long sequenceNumber = 0;

bool bmeOnline = false;
bool imuOnline = false;
bool tofOnline = false;

uint8_t readRegister(uint8_t address, uint8_t reg) {
    Wire.beginTransmission(address);
    Wire.write(reg);

    if (Wire.endTransmission(false) != 0) {
        return 0xFF;
    }

    Wire.requestFrom(address, (uint8_t)1);

    if (Wire.available()) {
        return Wire.read();
    }

    return 0xFF;
}

void writeRegister(uint8_t address, uint8_t reg, uint8_t value) {
    Wire.beginTransmission(address);
    Wire.write(reg);
    Wire.write(value);
    Wire.endTransmission();
}

int16_t readWord(uint8_t address, uint8_t reg) {
    Wire.beginTransmission(address);
    Wire.write(reg);

    if (Wire.endTransmission(false) != 0) {
        return 0;
    }

    Wire.requestFrom(address, (uint8_t)2);

    if (Wire.available() >= 2) {
        int16_t value =
            (static_cast<int16_t>(Wire.read()) << 8) |
            Wire.read();

        return value;
    }

    return 0;
}

void scanI2C() {
    Serial.println();
    Serial.println("=== I2C DEVICE SCAN ===");

    int deviceCount = 0;

    for (uint8_t address = 1; address < 127; address++) {
        Wire.beginTransmission(address);

        if (Wire.endTransmission() == 0) {
            Serial.print("Found: 0x");

            if (address < 16) {
                Serial.print("0");
            }

            Serial.println(address, HEX);
            deviceCount++;
        }
    }

    Serial.print("Total devices: ");
    Serial.println(deviceCount);
}

void setupBME() {
    Serial.println();
    Serial.println("=== ENVIRONMENTAL SENSOR ===");

    bmeOnline = bme.begin(0x76);

    if (bmeOnline) {
        Serial.println("BME280: ONLINE");
    } else {
        Serial.println("FAULT: BME280 initialization failed");
    }
}

void setupIMU() {
    Serial.println();
    Serial.println("=== IMU ===");

    uint8_t whoAmI = readRegister(MPU_ADDR, 0x75);

    Serial.print("WHO_AM_I: 0x");

    if (whoAmI < 0x10) {
        Serial.print("0");
    }

    Serial.println(whoAmI, HEX);

    if (whoAmI == 0x71) {
        writeRegister(MPU_ADDR, 0x6B, 0x00);
        delay(100);

        imuOnline = true;

        Serial.println("MPU-9250 compatible IMU: ONLINE");
    } else {
        imuOnline = false;

        Serial.println("FAULT: Unexpected IMU ID");
    }
}

void setupTOF() {
    Serial.println();
    Serial.println("=== DISTANCE SENSOR ===");

    tof.setTimeout(500);

    if (tof.init()) {
        tofOnline = true;

        tof.startContinuous(100);

        Serial.println("VL53L0X compatible sensor: ONLINE");
    } else {
        tofOnline = false;

        Serial.println("VL53L0X initialization failed");
        Serial.println("Device at 0x29 remains unidentified");
    }
}

void printTelemetry() {
    sequenceNumber++;

    Serial.print("TEL,");
    Serial.print(sequenceNumber);

    Serial.print(",TIME=");
    Serial.print(millis());

    if (bmeOnline) {
        float temperature = bme.readTemperature();
        float pressure = bme.readPressure() / 100.0F;
        float humidity = bme.readHumidity();

        Serial.print(",TEMP=");
        Serial.print(temperature, 2);

        Serial.print(",PRESS=");
        Serial.print(pressure, 2);

        Serial.print(",HUM=");
        Serial.print(humidity, 2);
    }

    if (imuOnline) {
        int16_t rawAx = readWord(MPU_ADDR, 0x3B);
        int16_t rawAy = readWord(MPU_ADDR, 0x3D);
        int16_t rawAz = readWord(MPU_ADDR, 0x3F);

        int16_t rawGx = readWord(MPU_ADDR, 0x43);
        int16_t rawGy = readWord(MPU_ADDR, 0x45);
        int16_t rawGz = readWord(MPU_ADDR, 0x47);

        float ax = rawAx / 16384.0F;
        float ay = rawAy / 16384.0F;
        float az = rawAz / 16384.0F;

        float gx = rawGx / 131.0F;
        float gy = rawGy / 131.0F;
        float gz = rawGz / 131.0F;

        Serial.print(",AX=");
        Serial.print(ax, 3);

        Serial.print(",AY=");
        Serial.print(ay, 3);

        Serial.print(",AZ=");
        Serial.print(az, 3);

        Serial.print(",GX=");
        Serial.print(gx, 2);

        Serial.print(",GY=");
        Serial.print(gy, 2);

        Serial.print(",GZ=");
        Serial.print(gz, 2);
    }

    if (tofOnline) {
        uint16_t distance = tof.readRangeContinuousMillimeters();

        Serial.print(",DIST=");
        Serial.print(distance);

        Serial.print(",TOF_TIMEOUT=");

        if (tof.timeoutOccurred()) {
            Serial.print("1");
        } else {
            Serial.print("0");
        }
    }

    Serial.print(",STATUS=");

    if (bmeOnline && imuOnline && tofOnline) {
        Serial.println("NORMAL");
    } else if (bmeOnline && imuOnline) {
        Serial.println("DEGRADED");
    } else {
        Serial.println("FAULT");
    }
}

void setup() {
    Serial.begin(115200);
    Wire.begin();

    delay(1000);

    Serial.println();
    Serial.println("========================================");
    Serial.println(" EMBEDDED TELEMETRY PLATFORM");
    Serial.println(" Firmware v0.4.0");
    Serial.println("========================================");

    scanI2C();

    setupBME();
    setupIMU();
    setupTOF();

    Serial.println();
    Serial.println("=== TELEMETRY STREAM START ===");
}

void loop() {
    printTelemetry();

    delay(1000);
}