#include <ESP8266WiFi.h>
#include <WebSocketsClient.h>

// --- CONFIGURATION ---
const char* WIFI_SSID     = "Tharun's Galaxy A15";
const char* WIFI_PASSWORD = "1234567890";

const char* WS_HOST = "192.168.176.53";  // your WebSocket server domain or IP
const uint16_t WS_PORT =  8766;              // your WebSocket server port
const char* WS_PATH = "/ws";                 // the WebSocket endpoint path

// GPIO pins driving your relay modules or bulbs
const uint8_t LIGHT1_PIN = D5;  // GPIO14
const uint8_t LIGHT2_PIN = D6;  // GPIO12

WebSocketsClient webSocket;

// --- WEBSOCKET EVENT HANDLER ---
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  if(type == WStype_TEXT) {
    String msg = String((char*) payload);
    msg.toLowerCase();  // normalize
    Serial.printf("Received: %s\n", msg.c_str());

    if(msg == "light1:on")  digitalWrite(LIGHT1_PIN, HIGH);
    else if(msg == "light1:off") digitalWrite(LIGHT1_PIN, LOW);
    else if(msg == "light2:on")  digitalWrite(LIGHT2_PIN, HIGH);
    else if(msg == "light2:off") digitalWrite(LIGHT2_PIN, LOW);
    else Serial.println("Unknown command");
  }
}

// --- SETUP ---
void setup() {
  Serial.begin(115200);
  delay(10);

  // Initialize pins
  pinMode(LIGHT1_PIN, OUTPUT);
  pinMode(LIGHT2_PIN, OUTPUT);
  digitalWrite(LIGHT1_PIN, LOW);
  digitalWrite(LIGHT2_PIN, LOW);

  // Connect to Wi-Fi
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\nConnected. IP: %s\n", WiFi.localIP().toString().c_str());

  // Initialize WebSocket
  webSocket.begin(WS_HOST, WS_PORT, WS_PATH);
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000);  // try reconnect every 5 sec
}

// --- MAIN LOOP ---
void loop() {
  webSocket.loop();  // maintain WebSocket connection
}
