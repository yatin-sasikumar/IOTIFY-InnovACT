import customtkinter as ctk

APP_TITLE = "IOTIFY"
LOGIN_USER = "admin"
LOGIN_PASS = "admin123"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("560x360")
        self.resizable(False, False)

        # container for all frames
        container = ctk.CTkFrame(self, corner_radius=0)
        container.pack(fill="both", expand=True)

        self.frames = {}
        for F in (SplashPage, LoginPage, DevicesPage):
            page = F(parent=container, controller=self)
            self.frames[F.__name__] = page
            page.grid(row=0, column=0, sticky="nsew")

        self.show("SplashPage")

    def show(self, name: str):
        frame = self.frames[name]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show()

class SplashPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0)
        self.controller = controller

        self.label_title = ctk.CTkLabel(self, text="IOTIFY launching", font=("Segoe UI", 22, "bold"))
        self.label_title.pack(pady=(60, 12))

        self.label_anim = ctk.CTkLabel(self, text="", font=("Segoe UI", 18))
        self.label_anim.pack()

        self._count = 0
        self._anim_job = None
        self._switch_job = None

    def on_show(self):
        self._count = 0
        self._animate()
        # switch to login after 5s
        self._switch_job = self.after(5000, lambda: self.controller.show("LoginPage"))

    def _animate(self):
        dots = ["   ", ".  ", ".. ", "..."]
        self.label_anim.configure(text=f"Launching{dots[self._count % 4]}")
        self._count += 1
        self._anim_job = self.after(120, self._animate)

    def destroy(self):
        if self._anim_job: self.after_cancel(self._anim_job)
        if self._switch_job: self.after_cancel(self._switch_job)
        super().destroy()

class LoginPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0)
        self.controller = controller

        card = ctk.CTkFrame(self, corner_radius=15)
        card.pack(expand=True, padx=40, pady=40)

        ctk.CTkLabel(card, text="Login", font=("Segoe UI", 20, "bold")).pack(pady=(10, 20))

        self.entry_user = ctk.CTkEntry(card, placeholder_text="Username", width=220, height=32)
        self.entry_user.pack(pady=(0, 15))

        self.entry_pass = ctk.CTkEntry(card, placeholder_text="Password", show="*", width=220, height=32)
        self.entry_pass.pack(pady=(0, 20))

        self.msg = ctk.CTkLabel(card, text="", text_color="red")
        self.msg.pack()

        login_btn = ctk.CTkButton(card, text="Login", command=self._login, width=220, height=36)
        login_btn.pack(pady=(14, 0))

    def on_show(self):
        self.entry_user.focus_set()
        self.msg.configure(text="")

    def _login(self):
        u = self.entry_user.get().strip()
        p = self.entry_pass.get().strip()
        if u == LOGIN_USER and p == LOGIN_PASS:
            self.controller.show("DevicesPage")
        else:
            self.msg.configure(text="Invalid credentials!")

class DevicesPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0)
        self.controller = controller

        ctk.CTkLabel(self, text="Device Details", font=("Segoe UI", 20, "bold")).pack(pady=(16, 8))
        self.status = ctk.CTkLabel(self, text="No devices connected yet.")
        self.status.pack(pady=(0, 12))

        btn_row = ctk.CTkFrame(self, corner_radius=0)
        btn_row.pack(pady=20)

        ctk.CTkButton(btn_row, text="Device 0 ON", command=lambda: self._set("Device 0", True)).grid(row=0, column=0, padx=10, pady=5)
        ctk.CTkButton(btn_row, text="Device 0 OFF", command=lambda: self._set("Device 0", False)).grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkButton(self, text="Logout", command=lambda: controller.show("LoginPage")).pack(pady=12)

    def _set(self, name, val):
        self.status.configure(text=f"{name}: {'ON' if val else 'OFF'}")

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    App().mainloop()
