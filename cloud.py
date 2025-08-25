import asyncio
import websockets
import mysql.connector as ms
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database connection
try:
    con = ms.connect(
        host="localhost", 
        user="root", 
        password="yatin_ysp_207619", 
        database='iotify',
        auth_plugin='mysql_native_password'
    )
    sql = con.cursor(buffered=True)
    logger.info("Database connected successfully")
except Exception as e:
    logger.error(f"Database connection failed: {e}")
    sql = None

class ESPController:
    """Real ESP32 controller using WebSocket communication"""
    
    def __init__(self):
        self.esp_websocket = None
        self.connected = False
        self.device_states = {
            "5": "0", "6": "0", "7": "0", "8": "0"  # Default states
        }
        logger.info("ESP Controller initialized")

    async def set_esp_connection(self, websocket):
        """Set the ESP32 WebSocket connection"""
        self.esp_websocket = websocket
        self.connected = True
        logger.info("ESP32 connected to cloud server")

    async def disconnect_esp(self):
        """Handle ESP32 disconnection"""
        self.esp_websocket = None
        self.connected = False
        logger.warning("ESP32 disconnected from cloud server")

    async def send_command(self, pin, state):
        """Send command to ESP32"""
        try:
            if not self.connected or not self.esp_websocket:
                logger.error("ESP32 not connected")
                return False

            pin_str = str(pin)
            state_str = str(state)
            
            # Send command in format "pin,state"
            command = f"{pin_str},{state_str}"
            await self.esp_websocket.send(command)
            
            # Update local state
            self.device_states[pin_str] = state_str
            logger.info(f"Sent to ESP32: Pin {pin} set to {state}")
            return True
            
        except websockets.ConnectionClosedError:
            logger.error("ESP32 connection lost during command")
            await self.disconnect_esp()
            return False
        except Exception as e:
            logger.error(f"ESP command error: {e}")
            return False

    async def get_device_states(self):
        """Get current state of all devices"""
        try:
            if not self.connected or not self.esp_websocket:
                logger.warning("ESP32 not connected, returning last known states")
                return None

            # Request status from ESP32
            await self.esp_websocket.send("status")
            
            # Wait for response (with timeout)
            try:
                response = await asyncio.wait_for(self.esp_websocket.recv(), timeout=5.0)
                # Parse response format: "5:0,6:1,7:0,8:0"
                if ':' in response:
                    states = {}
                    pairs = response.split(',')
                    for pair in pairs:
                        if ':' in pair:
                            pin, state = pair.split(':')
                            states[pin.strip()] = state.strip()
                    
                    self.device_states.update(states)
                    logger.info(f"Received ESP32 states: {self.device_states}")
                    
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for ESP32 status")
            
            return self.device_states.copy()
            
        except websockets.ConnectionClosedError:
            logger.error("ESP32 connection lost during status request")
            await self.disconnect_esp()
            return None
        except Exception as e:
            logger.error(f"ESP states error: {e}")
            return None

# Initialize ESP controller
esp_controller = ESPController()

# Store connected clients
connected_clients = set()

async def handle_client(websocket):
    """Handle client connections (port 8765)"""
    client_address = websocket.remote_address
    logger.info(f"Client connected: {client_address}")
    connected_clients.add(websocket)
    
    try:
        async for message in websocket:
            logger.info(f"Received from client {client_address}: {message}")
            await process_client_message(websocket, message)
            
    except websockets.ConnectionClosedError as e:
        logger.info(f"Client {client_address} disconnected: {e}")
    except Exception as e:
        logger.error(f"Error handling client {client_address}: {e}")
    finally:
        connected_clients.discard(websocket)
        logger.info(f"Client {client_address} handler finished")

async def handle_esp32(websocket):
    """Handle ESP32 connections (port 8766)"""
    esp_address = websocket.remote_address
    logger.info(f"ESP32 connected: {esp_address}")
    
    # Set the ESP32 connection
    await esp_controller.set_esp_connection(websocket)
    
    try:
        async for message in websocket:
            logger.info(f"Received from ESP32 {esp_address}: {message}")
            await process_esp32_message(websocket, message)
            
    except websockets.ConnectionClosedError as e:
        logger.info(f"ESP32 {esp_address} disconnected: {e}")
    except Exception as e:
        logger.error(f"Error handling ESP32 {esp_address}: {e}")
    finally:
        await esp_controller.disconnect_esp()
        logger.info(f"ESP32 {esp_address} handler finished")

async def process_client_message(websocket, message):
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
            logger.error(f"Invalid client message format: {message}")
            await websocket.send("{'error': 'Invalid message format'}")
            return

        if not isinstance(data, dict):
            logger.error(f"Client message is not a dictionary: {message}")
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
        logger.error(f"Error processing client message: {e}")
        await websocket.send("{'error': 'Message processing error'}")

async def process_esp32_message(websocket, message):
    """Process incoming messages from ESP32"""
    try:
        logger.info(f"ESP32 message: {message}")
        
        # Handle status updates from ESP32
        if ':' in message:
            # Status update format: "5:0,6:1,7:0,8:0"
            states = {}
            pairs = message.split(',')
            for pair in pairs:
                if ':' in pair:
                    pin, state = pair.split(':')
                    states[pin.strip()] = state.strip()
            
            esp_controller.device_states.update(states)
            logger.info(f"Updated device states: {states}")
            
        elif message.startswith("ack:"):
            # Acknowledgment from ESP32
            logger.info(f"ESP32 acknowledged: {message}")
            
        else:
            logger.info(f"ESP32 info: {message}")
            
    except Exception as e:
        logger.error(f"Error processing ESP32 message: {e}")

async def handle_device_control(websocket, message):
    """Handle device control commands from clients (format: "pin,state")"""
    try:
        pin_str, state_str = message.split(',')
        pin = int(pin_str)
        state = int(state_str)
        
        logger.info(f"Client device control: pin={pin}, state={state}")

        # Send command to ESP32
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
    """Handle device list request from clients"""
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
        val = (username,)
        sql.execute(query, val)
        devices_data = sql.fetchall()

        if not devices_data:
            # Create some fake devices for testing if none exist in DB
            fake_devices = [
                [username, "Living Room Light", "dev1", 5, "0"],
                [username, "Bedroom Fan", "dev2", 6, "1"],
                [username, "Desk Lamp", "dev3", 7, "0"]
            ]
            devices_data = fake_devices

        # Get current states from ESP32
        
        
        
        result_devices = []
        for device in devices_data:
            device_copy = list(device)
                          
            result_devices.append(device_copy+['0',])

        await websocket.send(str(result_devices))
        logger.info(f"Sent devices for {username}: {len(result_devices)} devices")
        

    except Exception as e:
        logger.error(f"Error handling devices request: {e}")
        await websocket.send("['Database Error']")

async def start_servers():
    """Start both WebSocket servers"""
    client_host = "0.0.0.0"
    client_port = 8765
    esp_host = "0.0.0.0"
    esp_port = 8766

    logger.info(f"Starting IOTIFY Cloud Server")
    logger.info(f"Client server: {client_host}:{client_port}")
    logger.info(f"ESP32 server: {esp_host}:{esp_port}")

    # Start client server
    client_server = await websockets.serve(
        handle_client,
        client_host,
        client_port,
        ping_interval=60,
        ping_timeout=30
    )

    # Start ESP32 server
    esp_server = await websockets.serve(
        handle_esp32,
        esp_host,
        esp_port,
        ping_interval=30,
        ping_timeout=15
    )

    logger.info("Cloud servers are running!")
    logger.info(f"Client WebSocket endpoint: ws://{client_host}:{client_port}")
    logger.info(f"ESP32 WebSocket endpoint: ws://{esp_host}:{esp_port}")
    logger.info("Waiting for connections...")

    # Keep both servers running
    await asyncio.gather(
        client_server.wait_closed(),
        esp_server.wait_closed()
    )

if __name__ == "__main__":
    try:
        asyncio.run(start_servers())
    except KeyboardInterrupt:
        logger.info("Servers shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")