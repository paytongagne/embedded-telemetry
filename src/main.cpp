#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_BME280.h>

Adafruit_BME280 bme;

const uint8_t MPU_ADDR = 0x68;
const uint8_t AUX_ADDR = 0x29;

const unsigned long MIN_TELEMETRY_INTERVAL_MS = 100;
const unsigned long MAX_TELEMETRY_INTERVAL_MS = 10000;

unsigned long sequenceNumber = 0;
unsigned long telemetryIntervalMs = 1000;
unsigned long lastTelemetryMs = 0;

bool telemetryPaused = false;
bool bmeOnline = false;
bool imuOnline = false;
bool auxPresent = false;

bool injectedBmeFault = false;
bool injectedImuFault = false;

uint8_t readRegister(uint8_t address, uint8_t reg) {
    Wire.beginTransmission(address);
    Wire.write(reg);

    if (Wire.endTransmission(false) != 0) {
        return 0xFF;
    }

    Wire.requestFrom(address, static_cast<uint8_t>(1));

    if (Wire.available()) {
        return Wire.read();
    }

    return 0xFF;
}

bool writeRegister(uint8_t address, uint8_t reg, uint8_t value) {
    Wire.beginTransmission(address);
    Wire.write(reg);
    Wire.write(value);

    return Wire.endTransmission() == 0;
}

bool readWord(uint8_t address, uint8_t reg, int16_t &value) {
    Wire.beginTransmission(address);
    Wire.write(reg);

    if (Wire.endTransmission(false) != 0) {
        return false;
    }

    Wire.requestFrom(address, static_cast<uint8_t>(2));

    if (Wire.available() < 2) {
        return false;
    }

    value =
        (static_cast<int16_t>(Wire.read()) << 8) |
        Wire.read();

    return true;
}

bool devicePresent(uint8_t address) {
    Wire.beginTransmission(address);
    return Wire.endTransmission() == 0;
}

void scanI2C() {
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

    if (whoAmI == 0x71 && writeRegister(MPU_ADDR, 0x6B, 0x00)) {
        delay(100);
        imuOnline = true;
        Serial.println("MPU-9250 compatible IMU: ONLINE");
    } else {
        imuOnline = false;
        Serial.println("FAULT: IMU initialization failed");
    }
}

void setupAux() {
    Serial.println();
    Serial.println("=== AUXILIARY I2C DEVICE ===");

    auxPresent = devicePresent(AUX_ADDR);

    if (auxPresent) {
        Serial.println("AUX 0x29: PRESENT (unidentified)");
    } else {
        Serial.println("AUX 0x29: NOT PRESENT");
    }
}

bool bmeHealthy() {
    return bmeOnline && !injectedBmeFault;
}

bool imuHealthy() {
    return imuOnline && !injectedImuFault;
}

const char *systemState() {
    const bool bmeOk = bmeHealthy();
    const bool imuOk = imuHealthy();

    if (bmeOk && imuOk) {
        return "NORMAL";
    }

    if (bmeOk || imuOk) {
        return "DEGRADED";
    }

    return "FAULT";
}

void printStatus() {
    Serial.print("STATUS,STATE=");
    Serial.print(systemState());

    Serial.print(",BME=");
    Serial.print(bmeHealthy() ? "OK" : "FAULT");

    Serial.print(",IMU=");
    Serial.print(imuHealthy() ? "OK" : "FAULT");

    Serial.print(",AUX=");
    Serial.print(auxPresent ? "PRESENT" : "ABSENT");

    Serial.print(",PAUSED=");
    Serial.print(telemetryPaused ? "1" : "0");

    Serial.print(",RATE_MS=");
    Serial.print(telemetryIntervalMs);

    Serial.println(",FW=0.5.0");
}

void printTelemetry() {
    sequenceNumber++;

    Serial.print("TEL,");
    Serial.print(sequenceNumber);

    Serial.print(",TIME=");
    Serial.print(millis());

    if (bmeHealthy()) {
        const float temperature = bme.readTemperature();
        const float pressure = bme.readPressure() / 100.0F;
        const float humidity = bme.readHumidity();

        Serial.print(",TEMP=");
        Serial.print(temperature, 2);

        Serial.print(",PRESS=");
        Serial.print(pressure, 2);

        Serial.print(",HUM=");
        Serial.print(humidity, 2);
    }

    if (imuHealthy()) {
        int16_t rawAx = 0;
        int16_t rawAy = 0;
        int16_t rawAz = 0;
        int16_t rawGx = 0;
        int16_t rawGy = 0;
        int16_t rawGz = 0;

        const bool readOk =
            readWord(MPU_ADDR, 0x3B, rawAx) &&
            readWord(MPU_ADDR, 0x3D, rawAy) &&
            readWord(MPU_ADDR, 0x3F, rawAz) &&
            readWord(MPU_ADDR, 0x43, rawGx) &&
            readWord(MPU_ADDR, 0x45, rawGy) &&
            readWord(MPU_ADDR, 0x47, rawGz);

        if (readOk) {
            const float ax = rawAx / 16384.0F;
            const float ay = rawAy / 16384.0F;
            const float az = rawAz / 16384.0F;

            const float gx = rawGx / 131.0F;
            const float gy = rawGy / 131.0F;
            const float gz = rawGz / 131.0F;

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
    }

    Serial.print(",BME=");
    Serial.print(bmeHealthy() ? "OK" : "FAULT");

    Serial.print(",IMU=");
    Serial.print(imuHealthy() ? "OK" : "FAULT");

    Serial.print(",AUX=");
    Serial.print(auxPresent ? "PRESENT" : "ABSENT");

    Serial.print(",STATUS=");
    Serial.println(systemState());
}

void acknowledge(const String &command) {
    Serial.print("ACK,");
    Serial.println(command);
}

void sendError(const String &error, const String &details = "") {
    Serial.print("ERR,");
    Serial.print(error);

    if (details.length() > 0) {
        Serial.print(",");
        Serial.print(details);
    }

    Serial.println();
}

void processCommand(String line) {
    line.trim();

    if (line.length() == 0) {
        return;
    }

    if (!line.startsWith("CMD,")) {
        sendError("BAD_FORMAT", line);
        return;
    }

    line.remove(0, 4);

    int separator = line.indexOf(',');
    String command = separator >= 0 ? line.substring(0, separator) : line;
    String value = separator >= 0 ? line.substring(separator + 1) : "";

    command.trim();
    value.trim();
    command.toUpperCase();
    value.toUpperCase();

    if (command == "STATUS") {
        acknowledge("STATUS");
        printStatus();
        return;
    }

    if (command == "PAUSE") {
        telemetryPaused = true;
        acknowledge("PAUSE");
        return;
    }

    if (command == "RESUME") {
        telemetryPaused = false;
        lastTelemetryMs = millis();
        acknowledge("RESUME");
        return;
    }

    if (command == "SET_RATE") {
        if (value.length() == 0) {
            sendError("MISSING_VALUE", "SET_RATE");
            return;
        }

        const long requestedRate = value.toInt();

        if (
            requestedRate < static_cast<long>(MIN_TELEMETRY_INTERVAL_MS) ||
            requestedRate > static_cast<long>(MAX_TELEMETRY_INTERVAL_MS)
        ) {
            sendError("RATE_RANGE", "100-10000");
            return;
        }

        telemetryIntervalMs = static_cast<unsigned long>(requestedRate);

        Serial.print("ACK,SET_RATE,");
        Serial.println(telemetryIntervalMs);
        return;
    }

    if (command == "INJECT_FAULT") {
        if (value == "IMU") {
            injectedImuFault = true;
            Serial.println("ACK,INJECT_FAULT,IMU");
            printStatus();
            return;
        }

        if (value == "BME") {
            injectedBmeFault = true;
            Serial.println("ACK,INJECT_FAULT,BME");
            printStatus();
            return;
        }

        sendError("BAD_TARGET", value);
        return;
    }

    if (command == "CLEAR_FAULTS") {
        injectedBmeFault = false;
        injectedImuFault = false;
        acknowledge("CLEAR_FAULTS");
        printStatus();
        return;
    }

    if (command == "RESET") {
        acknowledge("RESET");
        Serial.flush();
        delay(100);
        ESP.restart();
        return;
    }

    sendError("UNKNOWN_COMMAND", command);
}

void processSerialInput() {
    while (Serial.available() > 0) {
        String line = Serial.readStringUntil('\n');
        processCommand(line);
    }
}

void setup() {
    Serial.begin(115200);
    Serial.setTimeout(50);
    Wire.begin();

    delay(1000);

    Serial.println();
    Serial.println("========================================");
    Serial.println(" EMBEDDED TELEMETRY PLATFORM");
    Serial.println(" Firmware v0.5.0");
    Serial.println("========================================");

    scanI2C();
    setupBME();
    setupIMU();
    setupAux();

    Serial.println();
    printStatus();
    Serial.println("=== TELEMETRY STREAM START ===");

    lastTelemetryMs = millis();
}

void loop() {
    processSerialInput();

    const unsigned long now = millis();

    if (
        !telemetryPaused &&
        now - lastTelemetryMs >= telemetryIntervalMs
    ) {
        lastTelemetryMs = now;
        printTelemetry();
    }

    yield();
}
