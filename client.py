import customtkinter as ctk


def show_device_details():
    
    frame.destroy()
   
    device_frame = ctk.CTkFrame(root, corner_radius=15)
    device_frame.pack(padx=30, pady=30, fill="both", expand=True)
    label = ctk.CTkLabel(device_frame, text="Device Details", font=("Segoe UI", 20, "bold"))
    label.pack(pady=40)

def login():
    username = entry_user.get()
    password = entry_pass.get()
    if username == "admin" and password == "admin123":
        show_device_details()
    else:
        pass
        #ctk.CTkMessagebox(title="Login Failed", message="Invalid username or password.", icon="cancel")

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Login")
root.geometry("550x350")
root.resizable(False, False)

frame = ctk.CTkFrame(root, corner_radius=15)
frame.pack(padx=30, pady=30, fill="both", expand=True)

label_title = ctk.CTkLabel(frame, text="Login", font=("Segoe UI", 20, "bold"))
label_title.pack(pady=(10, 20))

entry_user = ctk.CTkEntry(frame, placeholder_text="Username", width=220, height=32, corner_radius=8)
entry_user.pack(pady=(0, 15))

entry_pass = ctk.CTkEntry(frame, placeholder_text="Password", show="*", width=220, height=32, corner_radius=8)
entry_pass.pack(pady=(0, 20))

login_btn = ctk.CTkButton(frame, text="Login", command=login, width=220, height=36, corner_radius=8)
login_btn.pack()

root.mainloop()