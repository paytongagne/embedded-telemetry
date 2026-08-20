#include "system_state.h"

SystemState determineSystemState(bool bmeHealthy, bool imuHealthy) {
    if (bmeHealthy && imuHealthy) {
        return SystemState::NORMAL;
    }

    if (bmeHealthy || imuHealthy) {
        return SystemState::DEGRADED;
    }

    return SystemState::FAULT;
}

const char *stateToString(SystemState state) {
    switch (state) {
        case SystemState::NORMAL:
            return "NORMAL";
        case SystemState::DEGRADED:
            return "DEGRADED";
        case SystemState::FAULT:
            return "FAULT";
    }

    return "UNKNOWN";
}
