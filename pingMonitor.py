import threading
import time
import tkinter as tk
from queue import Queue
import json
import os
import re
import logging
import tkinter.messagebox as messagebox
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from ping_service import ping_once

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MonitorApp:
    """A Tkinter-based application for monitoring network devices via ICMP ping."""

    def __init__(self, master: tk.Tk, ping_interval: int = 10) -> None:
        self.master = master
        self.ping_interval = ping_interval
        self.devices: list[dict] = []
        self.update_queue: Queue = Queue()
        self.device_widgets: dict = {}
        self.version = "0.1.4"

        self.master.title("Ping Monitor")
        self._build_ui()
        self._load_persisted_devices()
        self._start_ping_loop()

    def _build_ui(self):
        # Menu bar
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

        # Input frame
        input_frame = tk.Frame(self.master)
        input_frame.pack(fill=tk.X, padx=8, pady=6)

        tk.Label(input_frame, text="Name").grid(row=0, column=0, padx=4)
        self.name_entry = tk.Entry(input_frame)
        self.name_entry.grid(row=0, column=1, padx=4)

        tk.Label(input_frame, text="IP").grid(row=0, column=2, padx=4)
        self.ip_entry = tk.Entry(input_frame)
        self.ip_entry.grid(row=0, column=3, padx=4)

        add_btn = tk.Button(input_frame, text="Add Device", command=self._add_device)
        add_btn.grid(row=0, column=4, padx=4)

        # Ping interval selector
        interval_frame = tk.Frame(self.master)
        interval_frame.pack(fill=tk.X, padx=8, pady=2)

        tk.Label(interval_frame, text="Ping interval:").grid(
            row=0, column=0, padx=4, sticky="e"
        )
        self.interval_var = tk.StringVar()
        options = [
            ("10 seconds", 10),
            ("60 seconds", 60),
            ("5 minutes", 300),
        ]
        menu = tk.OptionMenu(
            interval_frame, self.interval_var, *[opt for opt, _ in options]
        )
        menu.grid(row=0, column=1, padx=4, sticky="w")
        self.interval_var.set("10 seconds")  # default

        apply_btn = tk.Button(
            interval_frame, text="Apply", command=self._apply_interval
        )
        apply_btn.grid(row=0, column=2, padx=4)

        # Status frame
        self.status_frame = tk.Frame(self.master)
        self.status_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # Header
        header = ["Name", "IP", "Status", "Latency", "Actions"]
        for i, h in enumerate(header):
            tk.Label(
                self.status_frame,
                text=h,
                font=("Helvetica", 10, "bold"),
                borderwidth=1,
                relief="solid",
                width=20,
            ).grid(row=0, column=i, sticky="ew")

        self.rows_start = 1  # data rows start

    def _show_about(self):
        messagebox.showinfo(
            "About",
            f"Ping Monitor {self.version}\n\nDeveloped by Brennan Wade",
        )

    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        ipv4_pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        return bool(re.match(ipv4_pattern, ip))

    def _add_device(self):
        name = self.name_entry.get().strip()
        ip = self.ip_entry.get().strip()
        if not name or not ip:
            return
        if not self._is_valid_ip(ip):
            messagebox.showerror(
                "Invalid IP", "Please enter a valid IPv4 address (e.g., 192.168.1.1)"
            )
            return
        device = {"name": name, "ip": ip, "online": None, "latency": None}
        self.devices.append(device)
        self._render_devices()
        self.name_entry.delete(0, tk.END)
        self.ip_entry.delete(0, tk.END)
        self._persist_devices()

    def _render_devices(self) -> None:
        """Update device rows in-place without destroying/recreating widgets."""
        # First: update existing widgets
        for idx, dev in enumerate(self.devices):
            if idx in self.device_widgets:
                widgets = self.device_widgets[idx]
                widgets["name"].config(text=dev["name"])
                widgets["ip"].config(text=dev["ip"])

                status_txt = (
                    "Unknown"
                    if dev["online"] is None
                    else ("Online" if dev["online"] else "Offline")
                )
                color = (
                    "gray"
                    if dev["online"] is None
                    else ("green" if dev["online"] else "red")
                )
                widgets["status"].config(text=status_txt, bg=color)

                latency_text = (
                    "" if dev.get("latency") is None else f"{dev['latency']:.0f} ms"
                )
                widgets["latency"].config(text=latency_text)

        # Second: remove widgets for deleted devices
        for idx in list(self.device_widgets.keys()):
            if idx >= len(self.devices):
                for widget in self.device_widgets[idx].values():
                    widget.destroy()
                del self.device_widgets[idx]

        # Third: create new widgets for new devices
        for idx, dev in enumerate(self.devices):
            if idx not in self.device_widgets:
                self.device_widgets[idx] = self._create_device_row(idx, dev)

    def _create_device_row(self, idx: int, dev: dict) -> dict:
        """Create a new device row and return widget references."""
        row = self.rows_start + idx

        name_lbl = tk.Label(
            self.status_frame, text=dev["name"], borderwidth=1, relief="solid", width=20
        )
        ip_lbl = tk.Label(
            self.status_frame, text=dev["ip"], borderwidth=1, relief="solid", width=20
        )

        status_txt = (
            "Unknown"
            if dev["online"] is None
            else ("Online" if dev["online"] else "Offline")
        )
        color = (
            "gray" if dev["online"] is None else ("green" if dev["online"] else "red")
        )
        status_lbl = tk.Label(
            self.status_frame,
            text=status_txt,
            borderwidth=1,
            relief="solid",
            width=20,
            bg=color,
        )

        latency_text = "" if dev.get("latency") is None else f"{dev['latency']:.0f} ms"
        latency_lbl = tk.Label(
            self.status_frame,
            text=latency_text,
            borderwidth=1,
            relief="solid",
            width=20,
        )

        remove_btn = tk.Button(
            self.status_frame,
            text="Remove",
            command=lambda i=idx: self._remove_device(i),
        )

        name_lbl.grid(row=row, column=0, sticky="ew")
        ip_lbl.grid(row=row, column=1, sticky="ew")
        status_lbl.grid(row=row, column=2, sticky="ew")
        latency_lbl.grid(row=row, column=3, sticky="ew")
        remove_btn.grid(row=row, column=4, sticky="ew")

        return {
            "name": name_lbl,
            "ip": ip_lbl,
            "status": status_lbl,
            "latency": latency_lbl,
            "remove": remove_btn,
        }

    def _start_ping_loop(self):
        self.ping_thread = threading.Thread(target=self._ping_loop, daemon=True)
        self.ping_thread.start()
        self._process_queue()

    def _ping_loop(self) -> None:
        """Ping all devices in parallel using ThreadPoolExecutor."""
        while True:
            if self.devices:
                max_workers = min(len(self.devices), 10)
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(ping_once, dev.get("ip", "")): dev
                        for dev in self.devices
                    }
                    for future in futures:
                        dev = futures[future]
                        ip = dev.get("ip", "")
                        if not ip:
                            self.update_queue.put((dev, False, None))
                            continue
                        try:
                            res = future.result()
                            online = bool(res.get("online"))
                            latency = res.get("latency_ms")
                            self.update_queue.put((dev, online, latency))
                        except Exception as e:
                            logger.warning(f"Ping failed for {ip}: {e}")
                            self.update_queue.put((dev, False, None))
            time.sleep(self.ping_interval)

    def _process_queue(self) -> None:
        """Process ping results from queue with adaptive polling."""
        updated = False
        while not self.update_queue.empty():
            dev, online, latency = self.update_queue.get()
            dev["online"] = online
            dev["latency"] = latency
            if latency is not None:
                self._persist_devices()
            updated = True

        if updated:
            self._render_devices()

        # Adaptive polling: check more frequently when queue has items
        if not self.update_queue.empty():
            self.master.after(50, self._process_queue)
        else:
            self.master.after(500, self._process_queue)

    def _apply_interval(self):
        selected_label = self.interval_var.get()
        mapping = {
            "10 seconds": 10,
            "60 seconds": 60,
            "5 minutes": 300,
        }
        new_interval = mapping.get(selected_label, 10)
        if new_interval != self.ping_interval:
            self.ping_interval = new_interval

    def _load_persisted_devices(self, path: str = "devices.json"):
        if not os.path.exists(path):
            self._persist_devices()
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("ip"):
                        self.devices.append(
                            {
                                "name": item.get("name", ""),
                                "ip": item["ip"],
                                "online": None,
                                "latency": None,
                            }
                        )
                self._render_devices()
        except Exception as e:
            logger.warning(f"Failed to load persisted devices: {e}")

    def _persist_devices(self, path: str = "devices.json"):
        to_save = [
            {"name": d.get("name", ""), "ip": d.get("ip", "")}
            for d in self.devices
            if d.get("ip")
        ]
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(to_save, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist devices: {e}")

    def _remove_device(self, index: int):
        if 0 <= index < len(self.devices):
            self.devices.pop(index)
            self._persist_devices()
            self._render_devices()


def main() -> None:
    """Initialize and run the PingMonitor application."""
    root = tk.Tk()
    try:
        icon_path = "pingMonitorICON.png"
        if os.path.exists(icon_path):
            root.iconphoto(True, tk.PhotoImage(file=icon_path))
    except Exception as e:
        logger.warning(f"Failed to load application icon: {e}")
    app = MonitorApp(root, ping_interval=10)
    root.mainloop()


if __name__ == "__main__":
    main()
