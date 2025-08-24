import customtkinter as ctk
import tkinter as tk
import asyncio
import websockets
import threading
import json

CLOUD_SERVER_URL = "ws://localhost:8765"  # Change this to your cloud server IP

class WebSocketClient:
    def __init__(self):
        self.websocket = None
        self.connected = False

    async def connect(self):
        """Connect to cloud server"""
        try:
            self.websocket = await websockets.connect(CLOUD_SERVER_URL, ping_interval=30, ping_timeout=10)
            self.connected = True
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            self.connected = False
            return False

    async def send_message(self, message):
        """Send message to cloud server"""
        if self.websocket and self.connected:
            try:
                await self.websocket.send(str(message))
                return True
            except Exception as e:
                print(f"Send failed: {e}")
                self.connected = False
                return False
        return False

    async def receive_message(self):
        """Receive message from cloud server"""
        if self.websocket and self.connected:
            try:
                message = await self.websocket.recv()
                return message
            except Exception as e:
                print(f"Receive failed: {e}")
                self.connected = False
                return None
        return None

    async def close(self):
        """Close connection"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("IOTIFY")
        self.geometry("560x360")
        self.resizable(False, False)

        # Initialize WebSocket client
        self.ws_client = WebSocketClient()
        self.current_user = None
        
        # Create event loop for async operations
        self.loop = asyncio.new_event_loop()
        self.ws_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.ws_thread.start()

        container = ctk.CTkFrame(self, corner_radius=0)
        container.pack(fill="both", expand=True)

        self.frames = {}
        for F in (SplashPage, LoginPage, DevicesPage):
            page = F(parent=container, controller=self)
            self.frames[F.__name__] = page
            page.grid(row=0, column=0, sticky="nsew")

        self.show("SplashPage")

    def _run_event_loop(self):
        """Run asyncio event loop in separate thread"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def show(self, name: str):
        frame = self.frames[name]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show()

    def schedule_async(self, coro):
        """Schedule async coroutine in the event loop"""
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

class SplashPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0)
        self.controller = controller

        self.label_title = ctk.CTkLabel(self, text="IOTIFY", font=("Oswald", 50, "bold"))
        self.label_title.pack(pady=(60, 40))

        self.label_anim = ctk.CTkLabel(self, text="", font=("Oswald", 18))
        self.label_anim.pack()

        self.status_label = ctk.CTkLabel(self, text="", font=("Oswald", 14), text_color="gray")
        self.status_label.pack(pady=(10, 0))

        self._count = 0
        self._anim_job = None
        self._connection_job = None

    def on_show(self):
        self._count = 0
        self._animate()
        self.status_label.configure(text="Connecting to server...")
        self._connection_job = self.after(1000, self._try_connect)

    def _animate(self):
        dots = ["   ", ".  ", ".. ", "..."]
        self.label_anim.configure(text=f"Launching{dots[self._count % 4]}")
        self._count += 1
        self._anim_job = self.after(120, self._animate)

    def _try_connect(self):
        """Try to connect to cloud server"""
        future = self.controller.schedule_async(self._connect_to_server())
        self.after(100, lambda: self._check_connection(future))

    async def _connect_to_server(self):
        """Async connection to server"""
        return await self.controller.ws_client.connect()

    def _check_connection(self, future):
        """Check if connection was successful"""
        if future.done():
            try:
                success = future.result()
                if success:
                    self.status_label.configure(text="Connected successfully!", text_color="green")
                    self.after(1500, lambda: self.controller.show("LoginPage"))
                else:
                    self.status_label.configure(text="Connection failed! Retrying...", text_color="red")
                    self.after(2000, self._try_connect)
            except Exception as e:
                print(f"Connection error: {e}")
                self.status_label.configure(text="Connection error! Retrying...", text_color="red")
                self.after(2000, self._try_connect)
        else:
            self.after(100, lambda: self._check_connection(future))

    def destroy(self):
        if self._anim_job: self.after_cancel(self._anim_job)
        if self._connection_job: self.after_cancel(self._connection_job)
        super().destroy()

class LoginPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0)
        self.controller = controller

        card = ctk.CTkFrame(self, corner_radius=15)
        card.pack(expand=True, padx=175, pady=60)

        ctk.CTkLabel(card, text="Login", font=("Oswald", 20, "bold")).pack(pady=(10, 20))

        self.entry_user = ctk.CTkEntry(card, placeholder_text="Username", width=220, height=32)
        self.entry_user.pack(pady=(0, 15))

        self.entry_pass = ctk.CTkEntry(card, placeholder_text="Password", show="*", width=220, height=32)
        self.entry_pass.pack(pady=(0, 20))

        self.msg = ctk.CTkLabel(card, text="", text_color="red")
        self.msg.pack()

        self.login_btn = ctk.CTkButton(card, text="Login", command=self._login, width=220, height=36)
        self.login_btn.pack(pady=(14, 0))

    def on_show(self):
        self.entry_user.focus_set()
        self.msg.configure(text="")

    def _login(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        
        if not username or not password:
            self.msg.configure(text="Please enter both username and password!")
            return

        # Disable login button and show loading
        self.login_btn.configure(state="disabled", text="Logging in...")
        self.msg.configure(text="Authenticating...", text_color="blue")

        # Send login request to cloud server
        login_data = {"action": "login", "username": username, "password": password}
        future = self.controller.schedule_async(self._send_login_request(login_data))
        self.after(100, lambda: self._check_login_response(future, username))

    async def _send_login_request(self, login_data):
        """Send login request to server and get response"""
        try:
            success = await self.controller.ws_client.send_message(login_data)
            if success:
                response = await self.controller.ws_client.receive_message()
                return response
            return None
        except Exception as e:
            print(f"Login request error: {e}")
            return None

    def _check_login_response(self, future, username):
        """Check login response"""
        if future.done():
            try:
                response = future.result()
                if response:
                    response_data = eval(response)  # Parse the response
                    if response_data['action'] == 'login':
                        if response_data['status'] == 'affirmed':
                            self.msg.configure(text="Login successful!", text_color="green")
                            self.controller.current_user = username
                            self.after(1000, lambda: self.controller.show("DevicesPage"))
                        elif response_data['status'] == 'not_found':
                            self.msg.configure(text="Username not found!", text_color="red")
                        elif response_data['status'] == 'not_affirmed':
                            self.msg.configure(text="Incorrect password!", text_color="red")
                        else:
                            self.msg.configure(text="Login failed!", text_color="red")
                    else:
                        self.msg.configure(text="Invalid server response!", text_color="red")
                else:
                    self.msg.configure(text="Server connection lost!", text_color="red")
            except Exception as e:
                print(f"Login response error: {e}")
                self.msg.configure(text="Login error occurred!", text_color="red")
            
            # Re-enable login button
            self.login_btn.configure(state="normal", text="Login")
        else:
            self.after(100, lambda: self._check_login_response(future, username))

class DevicesPage(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.parent = parent

        # Header with title and logout button
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(10, 0))

        self.title_label = ctk.CTkLabel(header_frame, text="My Devices", font=("Oswald", 25))
        self.title_label.pack(side="left")

        logout_btn = ctk.CTkButton(header_frame, text="Logout", command=self.logout, 
                                  width=80, height=30, fg_color="red")
        logout_btn.pack(side="right")

        self.device_list_frame = ctk.CTkFrame(self)
        self.device_list_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.device_states = {}
        self.devices_data = []

    def on_show(self):
        # Clear old widgets
        for widget in self.device_list_frame.winfo_children():
            widget.destroy()
        self.device_states = {}
        
        # Load devices from server
        self._show_message("Loading devices...")
        self.load_devices()

    def load_devices(self):
        """Request device list from server"""
        if not self.controller.current_user:
            self._show_message("Error: No user logged in")
            return

        devices_request = {"action": "devices", "username": self.controller.current_user}
        future = self.controller.schedule_async(self._request_devices(devices_request))
        self.after(100, lambda: self._check_devices_response(future))

    async def _request_devices(self, devices_request):
        """Request devices from server"""
        try:
            success = await self.controller.ws_client.send_message(devices_request)
            if success:
                response = await self.controller.ws_client.receive_message()
                return response
            return None
        except Exception as e:
            print(f"Devices request error: {e}")
            return None

    def _check_devices_response(self, future):
        """Check devices response and update UI"""
        if future.done():
            try:
                response = future.result()
                if response:
                    devices_data = eval(response)  # Parse the response
                    if isinstance(devices_data, list) and devices_data:
                        if devices_data[0] == 'ESP8266 Disconnected':
                            self._show_message("ESP8266 Device Disconnected")
                        else:
                            self.devices_data = devices_data
                            self._display_devices(devices_data)
                    else:
                        self._show_message("No devices found")
                else:
                    self._show_message("Server connection lost")
            except Exception as e:
                print(f"Devices response error: {e}")
                self._show_message("Error loading devices")
        else:
            self.after(100, lambda: self._check_devices_response(future))

    def _display_devices(self, devices_data):
        """Display devices in the UI"""
        # Clear existing widgets
        for widget in self.device_list_frame.winfo_children():
            widget.destroy()

        for device_info in devices_data:
            # device_info format: [userid, device_name, device_id, pin_number, state]
            if len(device_info) >= 5:
                userid, device_name, device_id, pin_number, state = device_info[:5]
                self._add_device_row({
                    'name': device_name,
                    'id': device_id,
                    'pin': pin_number,
                    'state': 'On' if state == '1' else 'Off'
                })

    def _add_device_row(self, device):
        frame = ctk.CTkFrame(self.device_list_frame, corner_radius=5)
        frame.pack(fill="x", padx=10, pady=6)
        
        info_text = f"{device['name']}  |  ID: {device['id']}  |  PIN: {device['pin']}"
        ctk.CTkLabel(frame, text=info_text, font=("Oswald", 17)).pack(side="left", padx=(8, 10))

        # Prepare the state variable for the radio buttons
        state_var = tk.StringVar(value=device["state"])
        self.device_states[device["id"]] = state_var

        # "On" Radio Button
        r_on = ctk.CTkRadioButton(
            frame, text="On", variable=state_var, value="On",
            command=lambda dev=device: self.control_device(dev, "On"), font=("Oswald", 16)
        )
        r_on.pack(side="right", padx=(0, 5))

        # "Off" Radio Button
        r_off = ctk.CTkRadioButton(
            frame, text="Off", variable=state_var, value="Off",
            command=lambda dev=device: self.control_device(dev, "Off"), font=("Oswald", 16)
        )
        r_off.pack(side="right", padx=(0, 5))

    def control_device(self, device, state):
        """Send device control command to server"""
        device_id = device['id']
        pin = device['pin']
        state_value = "1" if state == "On" else "0"

        print(f"Controlling device: {device_id}, pin: {pin}, state: {state}")

        # Send control command to server (format: "pin,state")
        control_message = f"{pin},{state_value}"
        future = self.controller.schedule_async(self._send_control_command(control_message))
        self.after(100, lambda: self._check_control_response(future, device_id, state))

    async def _send_control_command(self, control_message):
        """Send control command to server"""
        try:
            success = await self.controller.ws_client.send_message(control_message)
            if success:
                response = await self.controller.ws_client.receive_message()
                return response
            return None
        except Exception as e:
            print(f"Control command error: {e}")
            return None

    def _check_control_response(self, future, device_id, state):
        """Check control response"""
        if future.done():
            try:
                response = future.result()
                if response:
                    print(f"Control response: {response}")
                    # Update UI state
                    if device_id in self.device_states:
                        self.device_states[device_id].set(state)
                else:
                    print("No response from server for control command")
            except Exception as e:
                print(f"Control response error: {e}")
        else:
            self.after(100, lambda: self._check_control_response(future, device_id, state))

    def _show_message(self, msg):
        # Remove old widgets
        for widget in self.device_list_frame.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.device_list_frame, text=msg, font=("Oswald", 18)).pack(pady=12)

    def logout(self):
        # Clear user data
        self.controller.current_user = None
        # Show login page
        if self.controller:
            self.controller.show("LoginPage")

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    App().mainloop()