import asyncio
import websockets
import mysql.connector as ms
import logging
import json


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
try:
    con = ms.connect(host="localhost", user="root", password="yatin_ysp_207619", database='iotify',auth_plugin='mysql_native_password')
    sql = con.cursor(buffered=True)
    logger.info("Database connected successfully")
except Exception as e:
    logger.error(f"Database connection failed: {e}")
    sql = None

# Fake device states (simulating ESP8266/Arduino)
# This will be replaced with real ESP8266 communication later
fake_device_states = {
    "5": "0",  # Pin 5 OFF
    "6": "1",  # Pin 6 ON
    "7": "0",  # Pin 7 OFF
    "8": "0",  # Pin 8 OFF
}

class FakeESPController:
    """Fake ESP controller to simulate Arduino/ESP8266 responses"""
    
    def __init__(self):
        self.device_states = fake_device_states.copy()
        logger.info("Fake ESP Controller initialized")
    
    async def send_command(self, pin, state):
        """Simulate sending command to ESP8266"""
        try:
            pin_str = str(pin)
            state_str = str(state)
            
            # Update fake state
            self.device_states[pin_str] = state_str
            
            logger.info(f"Fake ESP: Pin {pin} set to {state}")
            
            # Simulate some processing delay
            await asyncio.sleep(0.1)
            
            return True
        except Exception as e:
            logger.error(f"Fake ESP command error: {e}")
            return False
    
    async def get_device_states(self):
        """Get current state of all devices (fake)"""
        try:
            # Simulate some processing delay
            await asyncio.sleep(0.05)
            
            logger.info(f"Fake ESP states: {self.device_states}")
            return self.device_states.copy()
        except Exception as e:
            logger.error(f"Fake ESP states error: {e}")
            return None

# Initialize fake ESP controller
esp_controller = FakeESPController()

async def handle_client(websocket):
    
    client_address = websocket.remote_address
    logger.info(f"Client connected: {client_address}")
    
    try:
        async for message in websocket:
            logger.info(f"Received from {client_address}: {message}")
            await process_message(websocket, message)
            
    except websockets.ConnectionClosedError as e:
        logger.info(f"Client {client_address} disconnected: {e}")
    except Exception as e:
        logger.error(f"Error handling client {client_address}: {e}")
    finally:
        logger.info(f"Client {client_address} handler finished")

async def process_message(websocket, message):
    """Process incoming messages from clients"""
    try:
        # Check if message is a device control command (format: "pin,state")
        if isinstance(message, str) and ',' in message and message.replace(',', '').replace('-', '').isdigit():
            await handle_device_control(websocket, message)
            return
        
        # Try to parse as dictionary (login, devices requests)
        try:
            data = eval(message)  # In production, use json.loads() for safety
        except:
            logger.error(f"Invalid message format: {message}")
            await websocket.send("{'error': 'Invalid message format'}")
            return
        
        if not isinstance(data, dict):
            logger.error(f"Message is not a dictionary: {message}")
            await websocket.send("{'error': 'Message must be a dictionary'}")
            return
        
        action = data.get('action')
        
        if action == 'login':
            await handle_login(websocket, data)
        elif action == 'devices':
            await handle_devices_request(websocket, data)
        else:
            logger.error(f"Unknown action: {action}")
            await websocket.send(f"'{{'error': 'Unknown action: {action}'}}'")
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await websocket.send("{'error': 'Message processing error'}")

async def handle_device_control(websocket, message):
    """Handle device control commands (format: "pin,state")"""
    try:
        pin_str, state_str = message.split(',')
        pin = int(pin_str)
        state = int(state_str)
        
        logger.info(f"Device control: pin={pin}, state={state}")
        
        # Send command to fake ESP
        success = await esp_controller.send_command(pin, state)
        
        if success:
            response = f"'{{'action': 'control', 'status': 'success', 'pin': {pin}, 'state': {state}}}'"
            logger.info(f"Control successful: pin={pin}, state={state}")
        else:
            response = f"'{{'action': 'control', 'status': 'failed', 'pin': {pin}, 'state': {state}}}'"
            logger.error(f"Control failed: pin={pin}, state={state}")
        
        await websocket.send(response)
        
    except ValueError:
        logger.error(f"Invalid control command format: {message}")
        await websocket.send("{'error': 'Invalid control command format'}")
    except Exception as e:
        logger.error(f"Error handling device control: {e}")
        await websocket.send("{'error': 'Device control error'}")

async def handle_login(websocket, data):
    """Handle user login authentication"""
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    logger.info(f"Login attempt: username={username}")
    print(password)
    
    if not username or not password:
        response = "{'action': 'login', 'status': 'missing_credentials'}"
        await websocket.send(response)
        return
    
    if not sql:
        logger.error("Database not available")
        response = "{'action': 'login', 'status': 'database_error'}"
        await websocket.send(response)
        return
    
    try:
        # Query user from database
        query = "SELECT * FROM login WHERE username=%s"
        val = (username,)
        sql.execute(query, val)
        dat = sql.fetchone()
        
        if dat is None:
            response = "{'action': 'login', 'status': 'not_found'}"
            logger.info(f"Login failed - user not found: {username}")
        elif dat[2] == password:
            response = "{'action': 'login', 'status': 'affirmed'}"
            logger.info(f"Login successful: {username}")
        else:
            response = "{'action': 'login', 'status': 'not_affirmed'}"
            logger.info(f"Login failed - wrong password: {username}")
        
        await websocket.send(response)
        
    except Exception as e:
        logger.error(f"Database error during login: {e}")
        response = "{'action': 'login', 'status': 'database_error'}"
        await websocket.send(response)

async def handle_devices_request(websocket, data):
    """Handle device list request"""
    username = data.get('username', '')
    logger.info(f"Device request from: {username}")
    
    if not username:
        await websocket.send("{'error': 'Username required'}")
        return
    
    if not sql:
        logger.error("Database not available")
        await websocket.send("['Database Disconnected']")
        return
    
    try:
        # Get user's devices from database
        query = "SELECT * FROM devices WHERE userid=%s"
        val = (username,)  # Using username as userid for now
        sql.execute(query, val)
        devices_data = sql.fetchall()
        
        if not devices_data:
            # Create some fake devices for testing if none exist in DB
            fake_devices = [
                [username, "Living Room Light", "dev1", 5, "0"],
                [username, "Bedroom Fan", "dev2", 6, "1"], 
                [username, "Desk Lamp", "dev3", 7, "0"]
            ]
            
            # Get current states from fake ESP
            esp_states = await esp_controller.get_device_states()
            
            if esp_states:
                result_devices = []
                for device in fake_devices:
                    device_copy = list(device)
                    pin_number = str(device[3])  # Pin number
                    current_state = esp_states.get(pin_number, '0')
                    device_copy[4] = current_state  # Update state
                    result_devices.append(device_copy)
                
                await websocket.send(str(result_devices))
                logger.info(f"Sent fake devices for {username}: {len(result_devices)} devices")
            else:
                await websocket.send("['ESP8266 Disconnected']")
                logger.error("ESP controller not available")
        else:
            # Get current states from fake ESP
            esp_states = await esp_controller.get_device_states()
            
            if esp_states:
                result_devices = []
                for device in devices_data:
                    device_list = list(device)
                    pin_number = str(device[3])  # Assuming pin number is at index 3
                    current_state = esp_states.get(pin_number, '1')
                    device_list.append(current_state)  # Append current state
                    result_devices.append(device_list)
                
                await websocket.send(str(result_devices))
                logger.info(f"Sent devices for {username}: {len(result_devices)} devices")
            else:
                await websocket.send("['ESP8266 Disconnected']")
                logger.error("ESP controller not available")
    
    except Exception as e:
        logger.error(f"Error handling devices request: {e}")
        await websocket.send("['Database Error']")

async def start_server():
    """Start the WebSocket server"""
    host = "0.0.0.0"
    port = 8765
    
    logger.info(f"Starting Cloud Server on {host}:{port}")
    logger.info("Fake ESP8266 controller active (for testing)")
    
    server = await websockets.serve(
        handle_client, 
        host, 
        port,
        ping_interval=60, 
        ping_timeout=30
    )
    
    logger.info("Cloud server is running!")
    logger.info(f"WebSocket endpoint: ws://{host}:{port}")
    logger.info("Waiting for client connections...")
    
    # Keep the server running forever
    await server.wait_closed()

if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")


        