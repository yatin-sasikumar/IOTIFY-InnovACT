#include <ESP8266WiFi.h>
#include <ArduinoWebsockets.h>
#include <SoftwareSerial.h>

// WiFi Configuration - CHANGE THESE TO YOUR NETWORK
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD"; 

// Cloud Server Configuration - CHANGE TO YOUR CLOUD SERVER IP
const char* websocket_server = "localhost";  // Change to your cloud server IP
const int websocket_port = 8766;             // ESP32/ESP8266 WebSocket port

// Serial Communication with Arduino
SoftwareSerial arduino(D2, D1);  // RX=D2 (GPIO4), TX=D1 (GPIO5)

// WebSocket Client
using namespace websockets;
WebsocketsClient client;

// State variables
bool connected_to_wifi = false;
bool connected_to_server = false;
unsigned long last_heartbeat = 0;
unsigned long last_reconnect_attempt = 0;
const unsigned long HEARTBEAT_INTERVAL = 30000;  // 30 seconds
const unsigned long RECONNECT_INTERVAL = 5000;   // 5 seconds

void setup() {
  // Initialize serial communications
  Serial.begin(115200);  // For debug output
  arduino.begin(9600);   // Communication with Arduino
  
  delay(1000);
  Serial.println("ESP8266 WiFi-Serial Bridge Starting...");
  
  // Connect to WiFi
  connectToWiFi();
  
  // Setup WebSocket callbacks
  setupWebSocket();
  
  // Connect to WebSocket server
  connectToServer();
  
  Serial.println("Bridge ready!");
}

void loop() {
  // Handle WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    connected_to_wifi = false;
    if (millis() - last_reconnect_attempt > RECONNECT_INTERVAL) {
      Serial.println("WiFi disconnected, reconnecting...");
      connectToWiFi();
      last_reconnect_attempt = millis();
    }
    delay(100);
    return;
  }
  
  // Handle WebSocket connection
  if (!client.available()) {
    connected_to_server = false;
    if (millis() - last_reconnect_attempt > RECONNECT_INTERVAL) {
      Serial.println("WebSocket disconnected, reconnecting...");
      connectToServer();
      last_reconnect_attempt = millis();
    }
    delay(100);
    return;
  }
  
  // Poll WebSocket for incoming messages
  client.poll();
  
  // Handle serial data from Arduino
  handleArduinoData();
  
  // Send periodic heartbeat/status request
  if (millis() - last_heartbeat > HEARTBEAT_INTERVAL) {
    requestArduinoStatus();
    last_heartbeat = millis();
  }
  
  delay(10);  // Small delay to prevent watchdog timeout
}

void connectToWiFi() {
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    connected_to_wifi = true;
    Serial.println();
    Serial.print("Connected to WiFi! IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println();
    Serial.println("Failed to connect to WiFi");
  }
}

void setupWebSocket() {
  // WebSocket event handlers
  client.onMessage([&](WebsocketsMessage message) {
    String data = message.data();
    Serial.println("Received from cloud: " + data);
    
    // Forward command to Arduino
    arduino.println(data);
  });

  client.onEvent([&](WebsocketsEvent event, String data) {
    if (event == WebsocketsEvent::ConnectionOpened) {
      connected_to_server = true;
      Serial.println("WebSocket connected to cloud server!");
      
      // Request initial status from Arduino
      requestArduinoStatus();
      
    } else if (event == WebsocketsEvent::ConnectionClosed) {
      connected_to_server = false;
      Serial.println("WebSocket connection closed");
      
    } else if (event == WebsocketsEvent::GotPing) {
      Serial.println("Received ping from server");
      client.pong();
      
    } else if (event == WebsocketsEvent::GotPong) {
      Serial.println("Received pong from server");
    }
  });
}

void connectToServer() {
  if (!connected_to_wifi) return;
  
  String server_url = "ws://";
  server_url += websocket_server;
  server_url += ":";
  server_url += websocket_port;
  
  Serial.println("Connecting to WebSocket server: " + server_url);
  
  bool connected = client.connect(server_url);
  if (connected) {
    Serial.println("WebSocket connection successful!");
  } else {
    Serial.println("WebSocket connection failed!");
  }
}

void handleArduinoData() {
  if (arduino.available()) {
    String response = arduino.readStringUntil('\\n');
    response.trim();
    
    if (response.length() > 0) {
      Serial.println("Received from Arduino: " + response);
      
      // Forward Arduino responses to cloud server
      if (connected_to_server && client.available()) {
        client.send(response);
        Serial.println("Sent to cloud: " + response);
      }
    }
  }
}

void requestArduinoStatus() {
  if (arduino) {
    arduino.println("status");
    Serial.println("Requested status from Arduino");
  }
}

// Function to send periodic heartbeat to server
void sendHeartbeat() {
  if (connected_to_server && client.available()) {
    client.ping();
  }
}
