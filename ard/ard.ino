void setup() {
  // Initialize pins as outputs
  pinMode(5, OUTPUT);
  pinMode(6, OUTPUT);
  pinMode(7, OUTPUT);
  pinMode(8, OUTPUT);
  
  // Initialize all pins to LOW (OFF)
  digitalWrite(5, LOW);
  digitalWrite(6, LOW);
  digitalWrite(7, LOW);
  digitalWrite(8, LOW);
  
  // Start serial communication at 9600 baud
  Serial.begin(9600);
  
  // Send ready message
  Serial.println("Arduino ready");
}

void loop() {
  String command;
  
  if (Serial.available() > 0) {
    // Read the incoming command until newline
    command = Serial.readStringUntil('\\n');
    command.trim(); // Remove any whitespace
    
    // Process the command
    processCommand(command);
  }
}

void processCommand(String cmd) {
  // Handle status request
  if (cmd == "status") {
    sendStatus();
    return;
  }
  
  // Handle device control commands in format "pin,state"
  if (cmd.indexOf(',') != -1) {
    int commaIndex = cmd.indexOf(',');
    
    // Extract pin and state
    String pinStr = cmd.substring(0, commaIndex);
    String stateStr = cmd.substring(commaIndex + 1);
    
    int pin = pinStr.toInt();
    int state = stateStr.toInt();
    
    // Validate pin number (only accept pins 5, 6, 7, 8)
    if (pin == 5 || pin == 6 || pin == 7 || pin == 8) {
      // Validate state (only accept 0 or 1)
      if (state == 0 || state == 1) {
        // Set the pin state
        digitalWrite(pin, state == 1 ? HIGH : LOW);
        
        // Send acknowledgment back to ESP8266/Cloud
        Serial.print("ack:");
        Serial.print(pin);
        Serial.print(",");
        Serial.println(state);
        
        // Also send updated status
        sendStatus();
      } else {
        Serial.println("error: invalid state");
      }
    } else {
      Serial.println("error: invalid pin");
    }
  } else {
    Serial.println("error: invalid command format");
  }
}

void sendStatus() {
  // Send status in format "5:0,6:1,7:0,8:0" as expected by cloud
  String status = "";
  
  status += "5:";
  status += digitalRead(5) ? "1" : "0";
  status += ",6:";
  status += digitalRead(6) ? "1" : "0"; 
  status += ",7:";
  status += digitalRead(7) ? "1" : "0";
  status += ",8:";
  status += digitalRead(8) ? "1" : "0";
  
  Serial.println(status);
}