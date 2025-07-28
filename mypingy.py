import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os
import threading
import subprocess
import time

CONFIG_FILE = "config.csv"
PING_INTERVAL = 5  # default

class Device:
    def __init__(self, name, ip, room, product_type=""):
        self.name = name
        self.ip = ip
        self.room = room
        self.product_type = product_type
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

        self.root.configure(bg="#2e2e2e")
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#3e3e3e", fieldbackground="#3e3e3e", foreground="white")
        style.configure("Treeview.Heading", background="#2e2e2e", foreground="white")

        # Spalten und deren aktuelle Reihenfolge (ohne #0)
        self.columns = ["Name", "IP", "Status", "ProduktTyp"]

        self.tree = ttk.Treeview(root, columns=self.columns, show="tree headings")
        self.tree.heading("#0", text="Raum", command=lambda: self.sort_tree("#0", False))
        for col in self.columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_tree(c, False))
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Bindings für Drag & Drop der Spaltenüberschriften
        self._dragging_col = None
        self._drag_start_x = 0
        self._drag_col_order = self.columns.copy()
        self.tree.bind("<ButtonPress-1>", self.on_heading_press)
        self.tree.bind("<B1-Motion>", self.on_heading_motion)
        self.tree.bind("<ButtonRelease-1>", self.on_heading_release)

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

        # Statusleiste unten links
        status_frame = tk.Frame(root, bg="#2e2e2e")
        status_frame.pack(fill="x", side="bottom", padx=10, pady=5, anchor="w")

        self.label_online = tk.Label(status_frame, text="Online: 00", bg="#2e2e2e", fg="#3f9f3f", font=("Arial", 10, "bold"))
        self.label_online.pack(side="left")

        self.label_offline = tk.Label(status_frame, text=" Offline: 00", bg="#2e2e2e", fg="#d9534f", font=("Arial", 10, "bold"))
        self.label_offline.pack(side="left")

        self.sort_reverse = False
        self.sort_column = None

        self.read_config()
        self.start_ping_thread()

    # ====== Drag & Drop der Spaltenüberschriften ======
    def on_heading_press(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "heading":
            col = self.tree.identify_column(event.x)
            if col == "#0":
                self._dragging_col = None
                return
            col_index = int(col.replace("#", "")) - 1
            self._dragging_col = self._drag_col_order[col_index]
            self._drag_start_x = event.x

    def on_heading_motion(self, event):
        if self._dragging_col is None:
            return
        dx = event.x - self._drag_start_x
        # Wenn der Mauszeiger mehr als 20px nach links oder rechts bewegt wurde, tausche Spalten
        if abs(dx) > 20:
            current_index = self._drag_col_order.index(self._dragging_col)
            if dx > 0 and current_index < len(self._drag_col_order) - 1:
                # Rechts tauschen
                self._drag_col_order[current_index], self._drag_col_order[current_index + 1] = \
                    self._drag_col_order[current_index + 1], self._drag_col_order[current_index]
                self._drag_start_x = event.x
                self.rebuild_columns()
            elif dx < 0 and current_index > 0:
                # Links tauschen
                self._drag_col_order[current_index], self._drag_col_order[current_index - 1] = \
                    self._drag_col_order[current_index - 1], self._drag_col_order[current_index]
                self._drag_start_x = event.x
                self.rebuild_columns()

    def on_heading_release(self, event):
        self._dragging_col = None

    def rebuild_columns(self):
        # Neue Spaltenreihenfolge anwenden
        self.columns = self._drag_col_order.copy()
        self.tree["displaycolumns"] = self.columns
        self.refresh_tree()

    # ====== Ende Drag & Drop ======

    def add_device(self):
        dialog = AddDeviceDialog(self.root)
        self.root.wait_window(dialog.top)
        if dialog.result:
            name, ip, room, product_type = dialog.result
            self.devices.append(Device(name, ip, room, product_type))
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
                    product_type = ""
                elif len(row) == 4:
                    name, ip, room, product_type = row
                else:
                    continue
                self.devices.append(Device(name, ip, room, product_type))

    def save_config(self):
        with open(CONFIG_FILE, "w", newline='') as f:
            writer = csv.writer(f, delimiter=';')
            for dev in self.devices:
                writer.writerow([dev.name, dev.ip, dev.room, dev.product_type])

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        devices_by_room = {}

        online_count = 0
        offline_count = 0

        for dev in self.devices:
            devices_by_room.setdefault(dev.room, []).append(dev)

        for room, devs in devices_by_room.items():
            statuses = [dev.status for dev in devs]
            if all(statuses):
                room_color = "green"
            elif not any(statuses):
                room_color = "red"
            else:
                room_color = "yellow"

            # Raum-Knoten einklappbar mit color-Tag
            rooms_node = self.tree.insert("", "end", text=room, open=True, tags=(room_color,))

            for dev in devs:
                color = "green" if dev.status else "red"
                if dev.status:
                    online_count += 1
                else:
                    offline_count += 1

                values = tuple()
                for col in self.columns:
                    if col == "Name":
                        values += (dev.name,)
                    elif col == "IP":
                        values += (dev.ip,)
                    elif col == "Status":
                        values += ("OK" if dev.status else "Offline",)
                    elif col == "ProduktTyp":
                        values += (dev.product_type,)
                self.tree.insert(rooms_node, "end", values=values, tags=(color,))

        self.tree.tag_configure("green", background="#2f4f2f")
        self.tree.tag_configure("red", background="#4f2f2f")
        self.tree.tag_configure("yellow", background="#665d2f")  # gelblich für gemischt

        self.label_online.config(text=f"Online: {online_count:02d}")
        self.label_offline.config(text=f" Offline: {offline_count:02d}")

    def sort_tree(self, col, reverse):
        items = [(self.tree.set(k, col) if col != "#0" else self.tree.item(k, "text"), k) for k in self.tree.get_children("")]
        
        if col == "Status":
            def status_key(val):
                v = val[0]
                return 0 if v == "OK" else 1
            items.sort(key=status_key, reverse=reverse)
        else:
            items.sort(key=lambda t: t[0].lower() if isinstance(t[0], str) else t[0], reverse=reverse)

        for index, (val, k) in enumerate(items):
            self.tree.move(k, "", index)

        self.sort_reverse = not reverse
        self.sort_column = col

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

        tk.Label(top, text="ProduktTyp:", bg="#2e2e2e", fg="white").pack()
        self.product_entry = tk.Entry(top)
        self.product_entry.pack()

        btn = tk.Button(top, text="Hinzufügen", command=self.on_submit, bg="#444", fg="white")
        btn.pack(pady=10)

    def on_submit(self):
        name = self.name_entry.get().strip()
        ip = self.ip_entry.get().strip()
        room = self.room_entry.get().strip()
        product_type = self.product_entry.get().strip()
        if name and ip and room:
            self.result = (name, ip, room, product_type)
            self.top.destroy()
        else:
            messagebox.showerror("Fehler", "Bitte alle Felder ausfüllen.")

if __name__ == "__main__":
    root = tk.Tk()
    app = PingMonitorApp(root)
    root.mainloop()
