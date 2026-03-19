import threading
import time
import tkinter as tk
from tkinter import filedialog
from queue import Queue
import json
import os
import sys
import logging
import tkinter.messagebox as messagebox
from concurrent.futures import ThreadPoolExecutor
import urllib.request
import webbrowser

from ping_service import ping_once, is_valid_ip

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_version() -> str:
    """Load version from VERSION file, fallback to '0.0.0' if not found."""
    try:
        with open("VERSION", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0.0"


class MonitorApp:
    """A Tkinter-based application for monitoring network devices via ICMP ping."""

    MAX_PING_WORKERS = 10
    MAX_PING_HISTORY = 100
    MAX_DEVICES = 100
    DEVICE_TYPES = ["Computer", "Printer", "Server", "AP", "Router", "Other"]
    PING_INTERVALS = [
        ("10 seconds", 10),
        ("60 seconds", 60),
        ("5 minutes", 300),
    ]
    TABLE_HEADERS = [
        "Name",
        "IP",
        "Type",
        "Status",
        "Latency",
        "Edit",
        "Remove",
        "History",
    ]

    def __init__(self, master: tk.Tk, ping_interval: int = 10) -> None:
        self.master = master
        self.ping_interval = ping_interval
        self.devices: list[dict] = []
        self.update_queue: Queue = Queue()
        self.device_widgets: dict = {}
        self._needs_persist = False
        self.search_var = tk.StringVar()
        self.type_filter_var = tk.StringVar(value="All")
        self.sort_column = 0
        self.sort_reverse = False
        self.version = _get_version()

        self.master.title("Ping Monitor")
        self._load_window_geometry()
        self._build_ui()
        self._load_persisted_devices()
        self._start_ping_loop()
        self._save_window_geometry_on_close()

        # Keyboard shortcuts
        self.master.bind("<Command-q>", lambda e: self._quit_app())
        self.master.bind("<Control-q>", lambda e: self._quit_app())
        self.master.bind("<Command-w>", lambda e: self.master.destroy())
        self.master.bind("<Control-w>", lambda e: self.master.destroy())

    def _load_window_geometry(self) -> None:
        """Load and apply window geometry from config file."""
        config_path = "config.json"
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
                geometry = config.get("window_geometry")
                if geometry:
                    self.master.geometry(geometry)
        except Exception as e:
            logger.warning(f"Failed to load window geometry: {e}")

    def _save_window_geometry_on_close(self) -> None:
        """Save window geometry when app closes."""
        self.master.bind("<Destroy>", lambda e: self._save_window_geometry())

    def _save_window_geometry(self) -> None:
        """Save window geometry to config file."""
        config_path = "config.json"
        try:
            geometry = self.master.geometry()
            config = {}
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
            config["window_geometry"] = geometry
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save window geometry: {e}")

    def _clear_inputs(self) -> None:
        """Clear the name and IP input fields."""
        self.name_entry.delete(0, tk.END)
        self.ip_entry.delete(0, tk.END)
        self.name_entry.focus_set()

    def _build_ui(self) -> None:
        # Menu bar
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        # File menu for Import/Export
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Devices", command=self._export_devices)
        file_menu.add_command(label="Import Devices", command=self._import_devices)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self._quit_app)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
        help_menu.add_command(
            label="Check for Updates", command=self._check_for_updates
        )

        # Input frame
        input_frame = tk.Frame(self.master)
        input_frame.pack(fill=tk.X, padx=8, pady=6)

        tk.Label(input_frame, text="Name").grid(row=0, column=0, padx=4)
        self.name_entry = tk.Entry(input_frame)
        self.name_entry.grid(row=0, column=1, padx=4)
        self.name_entry.bind("<Return>", lambda e: self._add_device())
        self.name_entry.bind("<Escape>", lambda e: self._clear_inputs())

        tk.Label(input_frame, text="IP").grid(row=0, column=2, padx=4)
        self.ip_entry = tk.Entry(input_frame)
        self.ip_entry.grid(row=0, column=3, padx=4)
        self.ip_entry.bind("<Return>", lambda e: self._add_device())
        self.ip_entry.bind("<Escape>", lambda e: self._clear_inputs())

        tk.Label(input_frame, text="Type").grid(row=0, column=4, padx=4)
        self.type_var = tk.StringVar()
        self.type_var.set(self.DEVICE_TYPES[0])
        self.type_dropdown = tk.OptionMenu(
            input_frame, self.type_var, *self.DEVICE_TYPES
        )
        self.type_dropdown.grid(row=0, column=5, padx=4)

        add_btn = tk.Button(input_frame, text="Add Device", command=self._add_device)
        add_btn.grid(row=0, column=6, padx=4)

        # Search frame
        search_frame = tk.Frame(self.master)
        search_frame.pack(fill=tk.X, padx=8, pady=2)

        tk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=4)
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.search_var.trace_add("write", self._filter_devices)

        tk.Label(search_frame, text="Type:").pack(side=tk.LEFT, padx=4)
        self.type_filter_var = tk.StringVar(value="All")
        type_filter = tk.OptionMenu(
            search_frame, self.type_filter_var, "All", *self.DEVICE_TYPES
        )
        type_filter.pack(side=tk.LEFT, padx=4)
        self.type_filter_var.trace_add("write", self._filter_devices)

        # Ping interval selector
        interval_frame = tk.Frame(self.master)
        interval_frame.pack(fill=tk.X, padx=8, pady=2)

        tk.Label(interval_frame, text="Ping interval:").grid(
            row=0, column=0, padx=4, sticky="e"
        )
        self.interval_var = tk.StringVar()
        menu = tk.OptionMenu(
            interval_frame, self.interval_var, *[opt for opt, _ in self.PING_INTERVALS]
        )
        menu.grid(row=0, column=1, padx=4, sticky="w")
        self.interval_var.set("10 seconds")  # default

        apply_btn = tk.Button(
            interval_frame, text="Apply", command=self._apply_interval
        )
        apply_btn.grid(row=0, column=2, padx=4)

        # Status frame with horizontal scrollbar
        self.scroll_frame = tk.Frame(self.master)
        self.scroll_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        self.canvas = tk.Canvas(self.scroll_frame)
        self.h_scrollbar = tk.Scrollbar(
            self.scroll_frame, orient="horizontal", command=self.canvas.xview
        )
        self.canvas.configure(xscrollcommand=self.h_scrollbar.set)

        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.scroll_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas.bind("<Shift-MouseWheel>", self._on_shift_scroll)

        # Header
        self.header_widgets = []
        sortable_columns = [
            "Name",
            "IP",
            "Type",
            "Status",
            "Latency",
            "Edit",
            "Remove",
            "History",
        ]
        for i, h in enumerate(sortable_columns):
            btn = tk.Button(
                self.scroll_frame,
                text=h,
                font=("Helvetica", 10, "bold"),
                borderwidth=1,
                relief="solid",
                width=20,
                command=lambda col=i: self._sort_devices(col),
            )
            btn.grid(row=0, column=i, sticky="ew")
            self.header_widgets.append(btn)

        self.rows_start = 1  # data rows start

        # Status bar
        self._create_status_bar()
        self._sort_devices(0)  # Initial sort by name

    def _on_shift_scroll(self, event):
        """Handle Shift+MouseWheel for horizontal scrolling."""
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _create_status_bar(self) -> None:
        """Create status bar at bottom of window."""
        self.status_bar = tk.Frame(self.master, relief=tk.SUNKEN, bd=1)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_devices = tk.Label(self.status_bar, text="Devices: 0")
        self.status_online = tk.Label(self.status_bar, text="Online: 0")
        self.status_offline = tk.Label(self.status_bar, text="Offline: 0")
        self.status_last_ping = tk.Label(self.status_bar, text="Last ping: --")
        self.status_version = tk.Label(self.status_bar, text=f"v{self.version}")

        for label in [
            self.status_devices,
            self.status_online,
            self.status_offline,
            self.status_last_ping,
        ]:
            label.pack(side=tk.LEFT, padx=10)

        self.status_version.pack(side=tk.RIGHT, padx=10)

    def _update_status_bar(self) -> None:
        """Update status bar with current stats."""
        total = len(self.devices)
        online = sum(1 for d in self.devices if d.get("online") is True)
        offline = sum(1 for d in self.devices if d.get("online") is False)

        last_ping = time.strftime("%H:%M:%S")

        self.status_devices.config(text=f"Devices: {total}")
        self.status_online.config(text=f"Online: {online}")
        self.status_offline.config(text=f"Offline: {offline}")
        self.status_last_ping.config(text=f"Last ping: {last_ping}")

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About",
            f"Ping Monitor {self.version}\n\nDeveloped by Brennan Wade",
        )

    def _check_for_updates(self) -> None:
        """Check GitHub for latest version and show update dialog."""
        url = "https://api.github.com/repos/oaftobar/pingMonitor/releases/latest"

        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read())

            latest = data.get("tag_name", "v0.0.0").lstrip("v")
            release_url = data.get(
                "html_url", "https://github.com/oaftobar/pingMonitor/releases"
            )

            latest_tuple = tuple(int(x) for x in latest.split("."))
            current_tuple = tuple(int(x) for x in self.version.split("."))

            if latest_tuple > current_tuple:
                response = messagebox.askyesno(
                    "Update Available",
                    f"You're on v{self.version}.\n"
                    f"v{latest} is available.\n\n"
                    "Open download page?",
                )
                if response:
                    webbrowser.open(release_url)
            else:
                messagebox.showinfo(
                    "Up to Date", f"You're on v{self.version}, the latest version!"
                )
        except Exception as e:
            logger.warning(f"Failed to check for updates: {e}")
            messagebox.showinfo(
                "Updates", "Unable to check for updates. Please try again later."
            )

    def _add_device(self) -> None:
        name = self.name_entry.get().strip()
        ip = self.ip_entry.get().strip()
        device_type = self.type_var.get()
        if not name:
            messagebox.showerror("Invalid Name", "Please enter a device name")
            return
        if not ip:
            messagebox.showerror("Invalid IP", "Please enter an IP address")
            return
        if not is_valid_ip(ip):
            messagebox.showerror(
                "Invalid IP", "Please enter a valid IPv4 address (e.g., 192.168.1.1)"
            )
            return
        if any(d.get("ip") == ip for d in self.devices):
            messagebox.showerror("Duplicate IP", "A device with this IP already exists")
            return
        if len(self.devices) >= self.MAX_DEVICES:
            messagebox.showerror(
                "Max Devices Reached",
                f"Maximum of {self.MAX_DEVICES} devices allowed. Remove a device to add more.",
            )
            return
        device = {
            "name": name,
            "ip": ip,
            "type": device_type,
            "online": None,
            "latency": None,
            "history": [],
        }
        self.devices.append(device)
        self._render_devices()
        self._clear_inputs()
        self._persist_devices()

    def _filter_devices(self, *args) -> None:
        """Filter devices based on search text."""
        self._render_devices()

    def _sort_devices(self, column: int) -> None:
        """Sort devices by the specified column."""
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False

        sortable_columns = ["name", "ip", "type", "online", "latency"]
        sort_key = (
            sortable_columns[column] if column < len(sortable_columns) else "name"
        )

        self.devices.sort(
            key=lambda d: self._get_sort_key(d, sort_key), reverse=self.sort_reverse
        )
        self._update_header_arrows()
        self._render_devices()

    def _get_sort_key(self, dev: dict, key: str) -> tuple:
        """Get sort key for a device, handling None values."""
        if key == "online":
            val = dev.get(key)
            return (val is None, val)
        elif key == "latency":
            val = dev.get(key)
            return (val is None, val if val is not None else -1)
        else:
            val = dev.get(key, "")
            return (isinstance(val, str) and val.lower(), val)

    def _update_header_arrows(self) -> None:
        """Update header buttons to show sort direction."""
        sortable_columns = ["Name", "IP", "Type", "Status", "Latency"]
        arrow = " ▼" if self.sort_reverse else " ▲"
        for i, btn in enumerate(self.header_widgets[: len(sortable_columns)]):
            text = sortable_columns[i]
            if i == self.sort_column:
                btn.config(text=text + arrow)
            else:
                btn.config(text=text)

    def _open_edit_dialog(self, device_index: int) -> None:
        """Open a dialog to edit a device's name and type."""
        if device_index >= len(self.devices):
            return

        dev = self.devices[device_index]

        dialog = tk.Toplevel(self.master)
        dialog.title("Edit Device")
        dialog.transient(self.master)
        dialog.grab_set()

        tk.Label(dialog, text="Name:").grid(
            row=0, column=0, padx=10, pady=5, sticky="e"
        )
        name_entry = tk.Entry(dialog, width=30)
        name_entry.grid(row=0, column=1, padx=10, pady=5)
        name_entry.insert(0, dev["name"])

        tk.Label(dialog, text="IP:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        ip_label = tk.Label(
            dialog, text=dev["ip"], relief="sunken", width=28, anchor="w"
        )
        ip_label.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(dialog, text="Type:").grid(
            row=2, column=0, padx=10, pady=5, sticky="e"
        )
        type_var = tk.StringVar()
        type_var.set(dev.get("type", "Other"))
        type_dropdown = tk.OptionMenu(dialog, type_var, *self.DEVICE_TYPES)
        type_dropdown.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        def save_changes() -> None:
            new_name = name_entry.get().strip()
            new_type = type_var.get()

            if not new_name:
                messagebox.showerror(
                    "Invalid Name", "Please enter a device name", parent=dialog
                )
                return

            dev["name"] = new_name
            dev["type"] = new_type
            self._render_devices()
            self._persist_devices()
            dialog.destroy()

        btn_frame = tk.Frame(dialog)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=15)

        tk.Button(btn_frame, text="Update", command=save_changes, width=12).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=12).pack(
            side=tk.LEFT, padx=5
        )

        dialog.geometry("400x180")
        dialog.resizable(False, False)

    def _render_devices(self) -> None:
        """Update device rows in-place without destroying/recreating widgets."""
        raw_search = self.search_var.get()
        type_filter = self.type_filter_var.get()

        text_only = raw_search.lower().strip()
        modifier_type = None

        if "type:" in raw_search.lower():
            idx = raw_search.lower().find("type:")
            before = raw_search[:idx].lower().strip()
            after = raw_search[idx + 5 :].lower().strip()
            text_only = before
            if after:
                modifier_type = after

        visible_indices = []
        for idx, dev in enumerate(self.devices):
            name_match = text_only in dev.get("name", "").lower()
            ip_match = text_only in dev.get("ip", "").lower()

            effective_type = type_filter if type_filter != "All" else modifier_type
            device_type = dev.get("type", "Other").lower()
            type_match = (effective_type is None) or (
                device_type == effective_type.lower()
            )

            if (name_match or ip_match) and type_match:
                visible_indices.append(idx)

        # Update existing widgets (only if values changed)
        for idx, dev in enumerate(self.devices):
            if idx in self.device_widgets:
                widgets = self.device_widgets[idx]
                if idx in visible_indices:
                    # Only update if values changed
                    if widgets["name"].cget("text") != dev["name"]:
                        widgets["name"].config(text=dev["name"])
                    if widgets["ip"].cget("text") != dev["ip"]:
                        widgets["ip"].config(text=dev["ip"])

                    device_type = dev.get("type", "Other")
                    if widgets["type"].cget("text") != device_type:
                        widgets["type"].config(text=device_type)

                    status_txt, color = self._get_status_info(dev.get("online"))
                    if (
                        widgets["status"].cget("text") != status_txt
                        or widgets["status"].cget("bg") != color
                    ):
                        widgets["status"].config(text=status_txt, bg=color)

                    latency_text = self._format_latency(dev.get("latency"))
                    if widgets["latency"].cget("text") != latency_text:
                        widgets["latency"].config(text=latency_text)

                    # Show the row
                    for widget in widgets.values():
                        widget.grid()
                else:
                    # Hide the row
                    for widget in widgets.values():
                        widget.grid_remove()

        # Remove widgets for deleted devices
        for idx in list(self.device_widgets.keys()):
            if idx >= len(self.devices):
                for widget in self.device_widgets[idx].values():
                    widget.destroy()
                del self.device_widgets[idx]

        # Create new widgets for new devices
        for idx, dev in enumerate(self.devices):
            if idx not in self.device_widgets:
                self.device_widgets[idx] = self._create_device_row(idx, dev)

        # Update status bar if no matches
        if visible_indices:
            self._status_bar_label.grid_remove() if hasattr(
                self, "_status_bar_label"
            ) else None
        else:
            if not hasattr(self, "_status_bar_label"):
                self._status_bar_label = tk.Label(
                    self.scroll_frame, text="No matching devices", fg="gray"
                )
                self._status_bar_label.grid(
                    row=len(visible_indices) + 1, column=0, columnspan=5, pady=20
                )
            else:
                self._status_bar_label.grid(
                    row=len(visible_indices) + 1, column=0, columnspan=5, pady=20
                )

    @staticmethod
    def _get_status_info(online: bool | None) -> tuple[str, str]:
        """Get status text and color for a device.

        Returns:
            Tuple of (status_text, background_color)
        """
        if online is None:
            return "Unknown", "gray"
        return ("Online", "green") if online else ("Offline", "red")

    @staticmethod
    def _format_latency(latency: float | None) -> str:
        """Format latency for display."""
        return "" if latency is None else f"{latency:.0f} ms"

    def _create_device_row(self, idx: int, dev: dict) -> dict:
        """Create a new device row and return widget references."""
        row = self.rows_start + idx

        name_lbl = tk.Label(
            self.scroll_frame, text=dev["name"], borderwidth=1, relief="solid", width=20
        )
        ip_lbl = tk.Label(
            self.scroll_frame, text=dev["ip"], borderwidth=1, relief="solid", width=20
        )

        device_type = dev.get("type", "Other")
        type_lbl = tk.Label(
            self.scroll_frame, text=device_type, borderwidth=1, relief="solid", width=12
        )

        status_txt, color = self._get_status_info(dev.get("online"))
        status_lbl = tk.Label(
            self.scroll_frame,
            text=status_txt,
            borderwidth=1,
            relief="solid",
            width=20,
            bg=color,
        )

        latency_text = self._format_latency(dev.get("latency"))
        latency_lbl = tk.Label(
            self.scroll_frame,
            text=latency_text,
            borderwidth=1,
            relief="solid",
            width=20,
        )

        remove_btn = tk.Button(
            self.scroll_frame,
            text="Remove",
            command=lambda i=idx: self._remove_device(i),
        )

        edit_btn = tk.Button(
            self.scroll_frame,
            text="Edit",
            command=lambda i=idx: self._open_edit_dialog(i),
        )

        history_btn = tk.Button(
            self.scroll_frame,
            text="History",
            command=lambda i=idx: self._show_history(i),
        )

        name_lbl.grid(row=row, column=0, sticky="ew")
        ip_lbl.grid(row=row, column=1, sticky="ew")
        type_lbl.grid(row=row, column=2, sticky="ew")
        status_lbl.grid(row=row, column=3, sticky="ew")
        latency_lbl.grid(row=row, column=4, sticky="ew")
        edit_btn.grid(row=row, column=5, sticky="ew")
        remove_btn.grid(row=row, column=6, sticky="ew")
        history_btn.grid(row=row, column=7, sticky="ew")

        return {
            "name": name_lbl,
            "ip": ip_lbl,
            "type": type_lbl,
            "status": status_lbl,
            "latency": latency_lbl,
            "edit": edit_btn,
            "remove": remove_btn,
            "history": history_btn,
        }

    def _start_ping_loop(self) -> None:
        self.ping_thread = threading.Thread(target=self._ping_loop, daemon=True)
        self.ping_thread.start()
        self._process_queue()

    def _ping_loop(self) -> None:
        """Ping all devices in parallel using ThreadPoolExecutor."""
        while True:
            if self.devices:
                max_workers = min(len(self.devices), self.MAX_PING_WORKERS)
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

            # Add to history
            history = dev.get("history", [])
            history.append(
                {"timestamp": time.time(), "online": online, "latency": latency}
            )
            # Cap history at MAX_PING_HISTORY
            if len(history) > self.MAX_PING_HISTORY:
                history = history[-self.MAX_PING_HISTORY :]
            dev["history"] = history

            if latency is not None:
                self._needs_persist = True
            updated = True

        # Persist once per cycle if any device was updated
        if updated and self._needs_persist:
            self._persist_devices()
            self._needs_persist = False

        if updated:
            self._render_devices()
            self._update_status_bar()

        # Adaptive polling: check more frequently when queue has items
        if not self.update_queue.empty():
            self.master.after(50, self._process_queue)
        else:
            self.master.after(500, self._process_queue)

    def _apply_interval(self) -> None:
        selected_label = self.interval_var.get()
        mapping = {label: value for label, value in self.PING_INTERVALS}
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
                    if isinstance(item, dict):
                        ip = item.get("ip", "").strip()
                        name = item.get("name", "").strip()
                        device_type = item.get("type", "Other")
                        if ip and is_valid_ip(ip) and name:
                            self.devices.append(
                                {
                                    "name": name,
                                    "ip": ip,
                                    "type": device_type,
                                    "online": None,
                                    "latency": None,
                                    "history": [],
                                }
                            )
                self._render_devices()
        except Exception as e:
            logger.warning(f"Failed to load persisted devices: {e}")

    def _persist_devices(self, path: str = "devices.json") -> None:
        to_save = [
            {
                "name": d.get("name", ""),
                "ip": d.get("ip", ""),
                "type": d.get("type", "Other"),
            }
            for d in self.devices
            if d.get("ip")
        ]
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(to_save, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist devices: {e}")

    def _remove_device(self, index: int) -> None:
        if 0 <= index < len(self.devices):
            self.devices.pop(index)
            self._persist_devices()
            self._render_devices()

    def _show_history(self, index: int) -> None:
        """Show ping history for a device."""
        # Check if popup already exists and destroy it
        if hasattr(self, "_history_popup") and self._history_popup.winfo_exists():
            self._history_popup.destroy()

        if index >= len(self.devices):
            return

        dev = self.devices[index]
        history = dev.get("history", [])

        if not history:
            messagebox.showinfo("History", f"No history for {dev['name']} yet")
            return

        # Calculate stats
        total = len(history)
        online_count = sum(1 for h in history if h.get("online"))
        uptime_pct = (online_count / total) * 100 if total > 0 else 0

        latencies = [h["latency"] for h in history if h.get("latency") is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        min_latency = min(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0

        # Build history text
        history_lines = []

        for h in reversed(history[-10:]):  # Last 10 pings
            timestamp = time.strftime("%H:%M:%S", time.localtime(h["timestamp"]))
            status = "Online" if h.get("online") else "Offline"
            latency_str = f"{h['latency']:.0f}ms" if h.get("latency") else "N/A"
            history_lines.append(f"{timestamp}: {status} ({latency_str})")

        history_text = "\n".join(history_lines)

        stats_text = f"""Device: {dev["name"]} ({dev["ip"]})

Statistics:
- Total pings: {total}
- Uptime: {uptime_pct:.1f}%
- Avg latency: {avg_latency:.0f}ms
- Min latency: {min_latency:.0f}ms
- Max latency: {max_latency:.0f}ms

Last 10 pings:
{history_text}"""

        # Show popup
        self._history_popup = tk.Toplevel(self.master)
        popup = self._history_popup
        popup.title(f"History - {dev['name']}")
        popup.geometry("400x450")

        text_widget = tk.Text(popup, wrap=tk.WORD, padx=10, pady=10)
        text_widget.insert("1.0", stats_text)
        text_widget.config(state="disabled")
        text_widget.pack(fill=tk.BOTH, expand=True)

        tk.Button(popup, text="Close", command=popup.destroy).pack(pady=5)

    def _quit_app(self) -> None:
        """Quit the application."""
        sys.exit()

    def _export_devices(self) -> None:
        """Export devices to a JSON file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Devices",
        )
        if not file_path:
            return

        devices_to_export = [
            {
                "name": d.get("name", ""),
                "ip": d.get("ip", ""),
                "type": d.get("type", "Other"),
            }
            for d in self.devices
        ]

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(devices_to_export, f, indent=2)
            messagebox.showinfo("Success", f"Exported {len(devices_to_export)} devices")
        except Exception as e:
            logger.warning(f"Failed to export devices: {e}")
            messagebox.showerror("Error", f"Failed to export: {e}")

    def _import_devices(self) -> None:
        """Import devices from a JSON file."""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import Devices",
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                messagebox.showerror("Error", "Invalid file format - expected a list")
                return

            # Limit import size
            if len(data) > self.MAX_DEVICES:
                messagebox.showerror(
                    "Error", f"Import too large. Maximum {self.MAX_DEVICES} devices."
                )
                return

            existing_ips = {d.get("ip") for d in self.devices}
            imported_count = 0
            skipped_count = 0

            for item in data:
                if not isinstance(item, dict):
                    skipped_count += 1
                    continue

                ip = item.get("ip", "").strip()
                name = item.get("name", "").strip()

                # Validate IP format
                if not ip or not is_valid_ip(ip):
                    skipped_count += 1
                    continue

                # Validate name
                if not name:
                    skipped_count += 1
                    continue

                # Check for duplicates
                if ip not in existing_ips:
                    device_type = item.get("type", "Other")
                    self.devices.append(
                        {
                            "name": name,
                            "ip": ip,
                            "type": device_type,
                            "online": None,
                            "latency": None,
                            "history": [],
                        }
                    )
                    existing_ips.add(ip)
                    imported_count += 1
                else:
                    skipped_count += 1

            self._persist_devices()
            self._render_devices()
            if skipped_count > 0:
                messagebox.showinfo(
                    "Import Complete",
                    f"Imported {imported_count} devices, skipped {skipped_count} invalid/duplicate entries",
                )
            else:
                messagebox.showinfo("Success", f"Imported {imported_count} devices")
        except Exception as e:
            logger.warning(f"Failed to import devices: {e}")
            messagebox.showerror("Error", f"Failed to import: {e}")


def main() -> None:
    """Initialize and run the PingMonitor application."""
    root = tk.Tk()
    try:
        icon_path = "pingMonitorICON.png"
        if os.path.exists(icon_path):
            root.iconphoto(True, tk.PhotoImage(file=icon_path))
    except Exception as e:
        logger.warning(f"Failed to load application icon: {e}")
    MonitorApp(root, ping_interval=10)
    root.mainloop()


if __name__ == "__main__":
    main()
