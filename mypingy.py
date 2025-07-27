import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import csv
import os
import threading
import subprocess
import time

CONFIG_FILE = "config.csv"
PING_INTERVAL = 5  # default

class Device:
    def __init__(self, name, ip, room):
        self.name = name
        self.ip = ip
        self.room = room
        self.status = False

    def ping(self):
        try:
            output = subprocess.check_output(
                ["ping", "-n", "1", "-w", "1000", self.ip],
                stderr=subprocess.DEVNULL,
                universal_newlines=True
            )
            self.status = "TTL=" in output
        except:
            self.status = False

class PingMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Ping Monitor")
        self.devices = []
        self.ping_interval = PING_INTERVAL

        # Dark theme setup
        self.root.configure(bg="#2e2e2e")
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#3e3e3e", fieldbackground="#3e3e3e", foreground="white")
        style.configure("Treeview.Heading", background="#2e2e2e", foreground="white")

        self.tree = ttk.Treeview(root, columns=("Name", "IP", "Status"), show="tree headings")
        self.tree.heading("#0", text="Raum")
        self.tree.heading("Name", text="Gerätename")
        self.tree.heading("IP", text="IP")
        self.tree.heading("Status", text="Status")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Controls
        control_frame = tk.Frame(root, bg="#2e2e2e")
        control_frame.pack(fill="x", padx=10)

        self.add_button = tk.Button(control_frame, text="+", command=self.add_device, bg="#444", fg="white")
        self.add_button.pack(side="left")

        self.interval_label = tk.Label(control_frame, text="Intervall (Sek):", bg="#2e2e2e", fg="white")
        self.interval_label.pack(side="left", padx=10)

        self.interval_slider = tk.Scale(control_frame, from_=2, to=300, orient="horizontal", length=200,
                                        bg="#2e2e2e", fg="white", troughcolor="#666", highlightthickness=0,
                                        command=self.update_interval)
        self.interval_slider.set(self.ping_interval)
        self.interval_slider.pack(side="left")

        self.read_config()
        self.start_ping_thread()

    def add_device(self):
        dialog = AddDeviceDialog(self.root)
        self.root.wait_window(dialog.top)
        if dialog.result:
            name, ip, room = dialog.result
            self.devices.append(Device(name, ip, room))
            self.save_config()
            self.refresh_tree()

    def update_interval(self, val):
        try:
            self.ping_interval = int(val)
        except:
            pass

    def read_config(self):
        if not os.path.exists(CONFIG_FILE):
            return
        with open(CONFIG_FILE, newline='') as f:
            reader = csv.reader(f, delimiter=';')
            for row in reader:
                if len(row) == 3:
                    name, ip, room = row
                    self.devices.append(Device(name, ip, room))

    def save_config(self):
        with open(CONFIG_FILE, "w", newline='') as f:
            writer = csv.writer(f, delimiter=';')
            for dev in self.devices:
                writer.writerow([dev.name, dev.ip, dev.room])

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        rooms = {}
        for dev in self.devices:
            if dev.room not in rooms:
                rooms[dev.room] = self.tree.insert("", "end", text=dev.room, open=True)
            color = "green" if dev.status else "red"
            self.tree.insert(rooms[dev.room], "end", values=(dev.name, dev.ip, "OK" if dev.status else "Offline"),
                             tags=(color,))
        self.tree.tag_configure("green", background="#2f4f2f")
        self.tree.tag_configure("red", background="#4f2f2f")

    def ping_loop(self):
        while True:
            for dev in self.devices:
                dev.ping()
            self.refresh_tree()
            time.sleep(self.ping_interval)

    def start_ping_thread(self):
        thread = threading.Thread(target=self.ping_loop, daemon=True)
        thread.start()

class AddDeviceDialog:
    def __init__(self, parent):
        self.result = None
        top = self.top = tk.Toplevel(parent)
        top.title("Gerät hinzufügen")
        top.configure(bg="#2e2e2e")

        tk.Label(top, text="Name:", bg="#2e2e2e", fg="white").pack()
        self.name_entry = tk.Entry(top)
        self.name_entry.pack()

        tk.Label(top, text="IP:", bg="#2e2e2e", fg="white").pack()
        self.ip_entry = tk.Entry(top)
        self.ip_entry.pack()

        tk.Label(top, text="Raum:", bg="#2e2e2e", fg="white").pack()
        self.room_entry = tk.Entry(top)
        self.room_entry.pack()

        btn = tk.Button(top, text="Hinzufügen", command=self.on_submit, bg="#444", fg="white")
        btn.pack(pady=10)

    def on_submit(self):
        name = self.name_entry.get().strip()
        ip = self.ip_entry.get().strip()
        room = self.room_entry.get().strip()
        if name and ip and room:
            self.result = (name, ip, room)
            self.top.destroy()
        else:
            messagebox.showerror("Fehler", "Bitte alle Felder ausfüllen.")

if __name__ == "__main__":
    root = tk.Tk()
    app = PingMonitorApp(root)
    root.mainloop()