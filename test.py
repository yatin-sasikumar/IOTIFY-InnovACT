import customtkinter as ctk

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.geometry("400x200")
root.title("Test Window")

label = ctk.CTkLabel(root, text="If you see this, CTk works!", font=("Segoe UI", 20))
label.pack(pady=40)

root.mainloop()