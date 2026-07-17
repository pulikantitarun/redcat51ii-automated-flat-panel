#!/usr/bin/env python3
"""ASCOM Alpaca CoverCalibrator bridge for the Rev C USB controller."""

from __future__ import annotations

import argparse
import json
import os
import socket
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import serial
from serial.tools import list_ports

APP_NAME = "Universal Flat Panel Rev C"
DEVICE_UID = "9f5b26bc-68c5-4bb7-a6f3-51c0fa7c0c01"
DEFAULT_HTTP_PORT = 11111
DISCOVERY_PORT = 32227
MAX_BRIGHTNESS = 4095


def auto_port() -> str | None:
    ports = list(list_ports.comports())
    preferred = [p for p in ports if p.vid == 0x303A or "ESP32" in (p.description or "").upper()]
    return (preferred or ports)[0].device if ports else None


class Controller:
    def __init__(self, port: str | None):
        self.configured_port = port
        self.serial: serial.Serial | None = None
        self.lock = threading.RLock()
        self.connected = False
        self.stop_event = threading.Event()
        self.status = {
            "cover": "UNKNOWN", "moving": False, "fault": "NONE", "brightness": 0,
            "requested": 0, "calibratorChanging": False, "mainPower": False,
        }
        self.worker = threading.Thread(target=self._worker, daemon=True)
        self.worker.start()

    def connect(self) -> None:
        with self.lock:
            if self.connected and self.serial and self.serial.is_open:
                return
            port = self.configured_port or auto_port()
            if not port:
                raise RuntimeError("No ESP32 USB serial port found")
            self.serial = serial.Serial(port, 115200, timeout=1.2, write_timeout=1.2)
            time.sleep(0.35)
            self.serial.reset_input_buffer()
            reply = self.command("HELLO", claim=False)
            if not reply.startswith("OK UNIVERSAL-FLAT-PANEL"):
                raise RuntimeError(f"Unexpected controller response: {reply!r}")
            self.command("CLAIM", claim=False)
            self.connected = True
            self.configured_port = port
            self.refresh_status()

    def disconnect(self) -> None:
        with self.lock:
            if self.serial:
                try:
                    self.command("RELEASE", claim=False)
                except Exception:
                    pass
                self.serial.close()
            self.serial = None
            self.connected = False

    def command(self, text: str, claim: bool = True) -> str:
        with self.lock:
            if not self.serial or not self.serial.is_open:
                raise RuntimeError("Controller is not connected")
            self.serial.write((text.strip() + "\n").encode("ascii"))
            self.serial.flush()
            deadline = time.monotonic() + 1.5
            while time.monotonic() < deadline:
                line = self.serial.readline().decode("utf-8", errors="replace").strip()
                if not line or line.startswith("BOOT "):
                    continue
                if line.startswith("ERR "):
                    raise RuntimeError(line)
                return line
            raise TimeoutError(f"No response to {text!r}")

    def refresh_status(self) -> dict:
        with self.lock:
            if not self.connected:
                return self.status
            reply = self.command("STATUS", claim=False)
            self.status = json.loads(reply)
            return self.status

    def _worker(self) -> None:
        heartbeat_at = 0.0
        while not self.stop_event.wait(0.35):
            if not self.connected:
                continue
            try:
                if time.monotonic() >= heartbeat_at:
                    self.command("HEARTBEAT", claim=False)
                    heartbeat_at = time.monotonic() + 5.0
                self.refresh_status()
            except Exception:
                self.connected = False
                try:
                    if self.serial:
                        self.serial.close()
                finally:
                    self.serial = None


class AlpacaApp:
    def __init__(self, controller: Controller, http_port: int):
        self.controller = controller
        self.http_port = http_port
        self.transaction = 0
        self.lock = threading.Lock()

    def next_transaction(self) -> int:
        with self.lock:
            self.transaction += 1
            return self.transaction

    def response(self, params: dict, value=None, error: int = 0, message: str = "") -> dict:
        tx = int(params.get("clienttransactionid", 0) or 0)
        body = {"ClientTransactionID": tx, "ServerTransactionID": self.next_transaction(),
                "ErrorNumber": error, "ErrorMessage": message}
        if value is not None:
            body["Value"] = value
        return body

    def device_value(self, name: str):
        c = self.controller
        status = c.refresh_status() if c.connected else c.status
        cover = status.get("cover", "UNKNOWN")
        fault = status.get("fault", "NONE")
        if name == "connected": return c.connected
        if name == "connecting": return False
        if name == "name": return APP_NAME
        if name == "description": return "USB/ASIAIR automated telescope flat panel"
        if name == "driverinfo": return "Universal Flat Panel Alpaca bridge 1.0"
        if name == "driverversion": return "1.0"
        if name == "interfaceversion": return 2
        if name == "supportedactions": return ["ClearFault", "GetFirmwareStatus"]
        if name == "coverstate":
            return {"CLOSED": 1, "MOVING": 2, "OPEN": 3, "UNKNOWN": 4, "ERROR": 5}.get(cover, 4)
        if name == "covermoving": return bool(status.get("moving", False))
        if name == "calibratorstate":
            if fault != "NONE": return 5
            if status.get("calibratorChanging", False): return 2
            return 3 if int(status.get("brightness", 0)) > 0 else 1
        if name == "calibratorchanging": return bool(status.get("calibratorChanging", False))
        if name == "brightness": return int(status.get("brightness", 0))
        if name == "maxbrightness": return MAX_BRIGHTNESS
        if name == "devicestate":
            stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + ".000Z"
            return [
                {"Name": "Brightness", "Value": int(status.get("brightness", 0))},
                {"Name": "CalibratorChanging", "Value": bool(status.get("calibratorChanging", False))},
                {"Name": "CalibratorState", "Value": self.device_value("calibratorstate")},
                {"Name": "CoverMoving", "Value": bool(status.get("moving", False))},
                {"Name": "CoverState", "Value": self.device_value("coverstate")},
                {"Name": "TimeStamp", "Value": stamp},
            ]
        raise KeyError(name)

    def put_device(self, name: str, params: dict):
        c = self.controller
        if name in ("connect", "connected"):
            desired = True if name == "connect" else str(params.get("connected", "true")).lower() == "true"
            c.connect() if desired else c.disconnect()
            return None
        if name == "disconnect": c.disconnect(); return None
        if not c.connected: raise RuntimeError("Controller is not connected")
        if name == "opencover": c.command("OPEN"); return None
        if name == "closecover": c.command("CLOSE"); return None
        if name == "haltcover": c.command("HALT"); return None
        if name == "calibratoroff": c.command("OFF"); return None
        if name == "calibratoron":
            brightness = max(0, min(MAX_BRIGHTNESS, int(params.get("brightness", 0))))
            c.command(f"LIGHT {brightness}")
            return None
        if name == "action":
            action = str(params.get("action", params.get("actionname", ""))).lower()
            if action == "clearfault": c.command("CLEAR"); return "OK"
            if action == "getfirmwarestatus": return json.dumps(c.refresh_status(), separators=(",", ":"))
            raise NotImplementedError(action)
        raise KeyError(name)


def make_handler(app: AlpacaApp):
    class Handler(BaseHTTPRequestHandler):
        server_version = "UniversalFlatPanelAlpaca/1.0"

        def log_message(self, fmt, *args):
            print("%s - %s" % (self.address_string(), fmt % args))

        def params(self) -> dict:
            parsed = urlparse(self.path)
            values = {k.lower(): v[-1] for k, v in parse_qs(parsed.query).items()}
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length:
                raw = self.rfile.read(length)
                ctype = self.headers.get("Content-Type", "")
                if "json" in ctype:
                    obj = json.loads(raw.decode("utf-8"))
                    values.update({str(k).lower(): v for k, v in obj.items()})
                else:
                    values.update({k.lower(): v[-1] for k, v in parse_qs(raw.decode("utf-8")).items()})
            return values

        def send_json(self, obj, status=HTTPStatus.OK):
            data = json.dumps(obj, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)

        def route(self, method: str):
            parsed = urlparse(self.path)
            path = parsed.path.lower().rstrip("/")
            params = self.params()
            if path == "/management/apiversions": return self.send_json({"Value": [1]})
            if path == "/management/v1/description":
                return self.send_json({"Value": {"ServerName": APP_NAME, "Manufacturer": "Open hardware project",
                                                  "ManufacturerVersion": "1.0", "Location": "Local USB bridge"}})
            if path == "/management/v1/configureddevices":
                return self.send_json({"Value": [{"DeviceName": APP_NAME, "DeviceType": "CoverCalibrator",
                                                  "DeviceNumber": 0, "UniqueID": DEVICE_UID}]})
            parts = [p for p in path.split("/") if p]
            if len(parts) != 5 or parts[:3] != ["api", "v1", "covercalibrator"] or parts[3] != "0":
                return self.send_json({"ErrorNumber": 1024, "ErrorMessage": "Unknown endpoint"}, HTTPStatus.NOT_FOUND)
            name = parts[4]
            try:
                value = app.device_value(name) if method == "GET" else app.put_device(name, params)
                return self.send_json(app.response(params, value))
            except NotImplementedError as exc:
                return self.send_json(app.response(params, error=1024, message=f"Not implemented: {exc}"))
            except KeyError as exc:
                return self.send_json(app.response(params, error=1024, message=f"Unknown member: {exc}"))
            except Exception as exc:
                return self.send_json(app.response(params, error=1025, message=str(exc)))

        def do_GET(self): self.route("GET")
        def do_PUT(self): self.route("PUT")
        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, PUT, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

    return Handler


def discovery_worker(port: int, stop_event: threading.Event):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", DISCOVERY_PORT))
    sock.settimeout(0.5)
    while not stop_event.is_set():
        try:
            data, address = sock.recvfrom(1024)
            if data.strip().lower() == b"alpacadiscovery1":
                sock.sendto(json.dumps({"AlpacaPort": port}).encode("ascii"), address)
        except socket.timeout:
            pass
    sock.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="COM port; omitted enables ESP32 auto-detection")
    parser.add_argument("--http-port", type=int, default=DEFAULT_HTTP_PORT)
    parser.add_argument("--connect", action="store_true", help="connect to the controller immediately")
    args = parser.parse_args()
    controller = Controller(args.port)
    if args.connect:
        controller.connect()
    app = AlpacaApp(controller, args.http_port)
    discovery = threading.Thread(target=discovery_worker, args=(args.http_port, controller.stop_event), daemon=True)
    discovery.start()
    server = ThreadingHTTPServer(("0.0.0.0", args.http_port), make_handler(app))
    print(f"{APP_NAME} Alpaca bridge listening on port {args.http_port}; serial={args.port or 'auto'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        controller.stop_event.set()
        controller.disconnect()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
