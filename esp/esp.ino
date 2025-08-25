#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

// WiFi credentials
const char* ssid = "Tharun's Galaxy A15";        // Replace with your WiFi SSID
const char* password = "1234567890";             // Replace with your WiFi password

// WebSocket server details
const char* ws_host = "192.168.176.53";          // Replace with your cloud server IP
const int ws_port = 8766;                         // Hardware port on cloud server
const char* ws_path = "/";

// WebSocket client
WebSocketsClient webSocket;

// Device configuration
const int PINS[] = {5, 6, 7, 8};                  // GPIO pins to control
const int NUM_PINS = sizeof(PINS) / sizeof(PINS[0]);

// Timing variables
unsigned long lastReconnectAttempt = 0;
unsigned long lastStatusSend = 0;
unsigned long lastWiFiCheck = 0;
const unsigned long RECONNECT_INTERVAL = 5000;   // 5 seconds
const unsigned long STATUS_INTERVAL = 10000;     // 10 seconds
const unsigned long WIFI_CHECK_INTERVAL = 30000; // 30 seconds

// Connection status
bool wifiConnected = false;
bool websocketConnected = false;

void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n=== IOTIFY ESP32 Client Starting ===");

    // Initialize GPIO pins
    initializePins();

    // Connect to WiFi
    connectToWiFi();

    // Initialize WebSocket
    initializeWebSocket();

    Serial.println("=== Setup Complete ===");
}

void loop() {
    unsigned long currentMillis = millis();

    // Check WiFi connection periodically
    checkWiFiConnection(currentMillis);

    // Handle WebSocket
    webSocket.loop();

    // Reconnect WebSocket if needed
    handleWebSocketReconnection(currentMillis);

    // Send periodic status updates
    sendPeriodicStatus(currentMillis);

    delay(100); // Small delay to prevent watchdog issues
}

void initializePins() {
    Serial.println("Initializing GPIO pins...");

    for (int i = 0; i < NUM_PINS; i++) {
        pinMode(PINS[i], OUTPUT);
        digitalWrite(PINS[i], LOW); // Start with all pins LOW
        Serial.printf("Pin %d initialized as OUTPUT (LOW)\n", PINS[i]);
    }
}

void connectToWiFi() {
    Serial.printf("Connecting to WiFi: %s\n", ssid);

    WiFi.begin(ssid, password);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        wifiConnected = true;
        Serial.println("\nWiFi connected successfully!");
        Serial.printf("IP address: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("Signal strength: %d dBm\n", WiFi.RSSI());
    } else {
        wifiConnected = false;
        Serial.println("\nWiFi connection failed!");
    }
}

void initializeWebSocket() {
    if (!wifiConnected) {
        Serial.println("Cannot initialize WebSocket - WiFi not connected");
        return;
    }

    Serial.printf("Initializing WebSocket connection to %s:%d\n", ws_host, ws_port);

    // Configure WebSocket
    webSocket.begin(ws_host, ws_port, ws_path);
    webSocket.onEvent(webSocketEvent);
    webSocket.setAuthorization("ESP32-Device"); // Optional: Set device identifier
    webSocket.setReconnectInterval(RECONNECT_INTERVAL);
    webSocket.enableHeartbeat(15000, 3000, 2); // 15s interval, 3s timeout, 2 retries
}

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    String message;

    switch(type) {
        case WStype_DISCONNECTED:
            websocketConnected = false;
            Serial.println("[WSc] Disconnected from cloud server");
            break;

        case WStype_CONNECTED:
            websocketConnected = true;
            Serial.printf("[WSc] Connected to cloud server: %s\n", payload);

            // Send initial status
            sendCurrentStatus();
            break;

        case WStype_TEXT:
            message = String((char*)payload);
            Serial.printf("[WSc] Received: %s\n", message.c_str());

            // Process incoming command
            processCommand(message);
            break;

        case WStype_BIN:
            Serial.printf("[WSc] Received binary data: %u bytes\n", length);
            break;

        case WStype_PING:
            Serial.println("[WSc] Received ping");
            break;

        case WStype_PONG:
            Serial.println("[WSc] Received pong");
            break;

        case WStype_ERROR:
            Serial.printf("[WSc] Error: %s\n", payload);
            break;

        default:
            Serial.printf("[WSc] Unknown event type: %d\n", type);
            break;
    }
}

void processCommand(String command) {
    command.trim();

    if (command == "status") {
        // Cloud server requesting current status
        sendCurrentStatus();
    }
    else if (command.indexOf(',') > 0) {
        // Device control command: "pin,state"
        int commaIndex = command.indexOf(',');

        if (commaIndex > 0 && commaIndex < command.length() - 1) {
            String pinStr = command.substring(0, commaIndex);
            String stateStr = command.substring(commaIndex + 1);

            int pin = pinStr.toInt();
            int state = stateStr.toInt();

            if (controlDevice(pin, state)) {
                // Send acknowledgment
                String ack = "ack:" + command;
                webSocket.sendTXT(ack);

                // Send updated status
                sendCurrentStatus();
            } else {
                // Send error response
                String error = "error:Invalid pin " + String(pin);
                webSocket.sendTXT(error);
            }
        }
    }
    else {
        Serial.printf("Unknown command: %s\n", command.c_str());
    }
}

bool controlDevice(int pin, int state) {
    // Validate pin
    bool validPin = false;
    for (int i = 0; i < NUM_PINS; i++) {
        if (PINS[i] == pin) {
            validPin = true;
            break;
        }
    }

    if (!validPin) {
        Serial.printf("Invalid pin: %d\n", pin);
        return false;
    }

    // Validate state
    if (state != 0 && state != 1) {
        Serial.printf("Invalid state: %d (must be 0 or 1)\n", state);
        return false;
    }

    // Control the device
    digitalWrite(pin, state == 1 ? HIGH : LOW);
    Serial.printf("Pin %d set to %s\n", pin, state == 1 ? "HIGH" : "LOW");

    return true;
}

void sendCurrentStatus() {
    if (!websocketConnected) {
        return;
    }

    // Create status message in format: "5:0,6:1,7:0,8:0"
    String status = "";

    for (int i = 0; i < NUM_PINS; i++) {
        if (i > 0) status += ",";

        int pinState = digitalRead(PINS[i]);
        status += String(PINS[i]) + ":" + String(pinState);
    }

    webSocket.sendTXT(status);
    Serial.printf("Sent status: %s\n", status.c_str());
}

void checkWiFiConnection(unsigned long currentMillis) {
    if (currentMillis - lastWiFiCheck >= WIFI_CHECK_INTERVAL) {
        lastWiFiCheck = currentMillis;

        if (WiFi.status() != WL_CONNECTED) {
            if (wifiConnected) {
                Serial.println("WiFi connection lost! Attempting to reconnect...");
                wifiConnected = false;
                websocketConnected = false;
            }

            WiFi.reconnect();

            // Wait a bit for reconnection
            int attempts = 0;
            while (WiFi.status() != WL_CONNECTED && attempts < 10) {
                delay(500);
                attempts++;
            }

            if (WiFi.status() == WL_CONNECTED) {
                wifiConnected = true;
                Serial.println("WiFi reconnected!");

                // Reinitialize WebSocket after WiFi reconnection
                initializeWebSocket();
            }
        } else {
            if (!wifiConnected) {
                wifiConnected = true;
                Serial.println("WiFi connection restored");
            }
        }
    }
}

void handleWebSocketReconnection(unsigned long currentMillis) {
    if (!websocketConnected && wifiConnected) {
        if (currentMillis - lastReconnectAttempt >= RECONNECT_INTERVAL) {
            lastReconnectAttempt = currentMillis;
            Serial.println("Attempting to reconnect WebSocket...");

            // Try to reconnect
            initializeWebSocket();
        }
    }
}

void sendPeriodicStatus(unsigned long currentMillis) {
    if (websocketConnected && (currentMillis - lastStatusSend >= STATUS_INTERVAL)) {
        lastStatusSend = currentMillis;
        sendCurrentStatus();
    }
}

void printSystemInfo() {
    Serial.println("\n=== System Information ===");
    Serial.printf("Chip Model: %s\n", ESP.getChipModel());
    Serial.printf("Chip Revision: %d\n", ESP.getChipRevision());
    Serial.printf("CPU Frequency: %d MHz\n", ESP.getCpuFreqMHz());
    Serial.printf("Flash Size: %d bytes\n", ESP.getFlashChipSize());
    Serial.printf("Free Heap: %d bytes\n", ESP.getFreeHeap());

    if (wifiConnected) {
        Serial.printf("WiFi SSID: %s\n", WiFi.SSID().c_str());
        Serial.printf("WiFi IP: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("WiFi Signal: %d dBm\n", WiFi.RSSI());
    }

    Serial.printf("WebSocket Status: %s\n", websocketConnected ? "Connected" : "Disconnected");
    Serial.println("=============================\n");
}
