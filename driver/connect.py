import logging
import time

from pymobiledevice3.lockdown import create_using_usbmux, LockdownClient
from pymobiledevice3 import usbmux

from pymobiledevice3.services.amfi import AmfiService

from pymobiledevice3.exceptions import NoDeviceConnectedError

def list_connected_devices(connection_type="USB"):
    devices = usbmux.list_devices()
    if connection_type is None:
        return devices
    return [device for device in devices if device.connection_type == connection_type]

def list_connected_udids(connection_type="USB"):
    return [device.serial for device in list_connected_devices(connection_type=connection_type)]

def get_connected_device_count(connection_type="USB"):
    return len(list_connected_devices(connection_type=connection_type))

def _wait_for_target_devices(serials=None, require_count=None, stop_event=None, interactive=True, poll_interval=0.5):
    while True:
        if stop_event is not None and stop_event.is_set():
            raise RuntimeError("已取消等待设备连接")
        devices = list_connected_devices(connection_type="USB")
        if serials is not None:
            matched_devices = []
            for serial in serials:
                matched_device = next((device for device in devices if device.matches_udid(serial)), None)
                if matched_device is None:
                    matched_devices = None
                    break
                matched_devices.append(matched_device)
            if matched_devices is not None:
                return matched_devices
            wait_message = "请连接目标设备后按回车..."
        elif require_count is not None:
            if len(devices) == require_count:
                return devices
            wait_message = f"当前已连接 {len(devices)} 台设备，请保持恰好 {require_count} 台设备连接后按回车..."
        else:
            if devices:
                return [devices[0]]
            wait_message = "请连接设备后按回车..."

        if interactive:
            print(wait_message)
            input()
        else:
            time.sleep(poll_interval)

def get_usbmux_lockdownclients(serials=None, stop_event=None, interactive=True, poll_interval=0.5, require_count=None):
    while True:
        target_devices = _wait_for_target_devices(
            serials=serials,
            require_count=require_count,
            stop_event=stop_event,
            interactive=interactive,
            poll_interval=poll_interval,
        )
        lockdowns = [create_using_usbmux(device.serial) for device in target_devices]
        password_protected_devices = [lockdown for lockdown in lockdowns if lockdown.all_values.get("PasswordProtected")]
        if not password_protected_devices:
            return lockdowns
        if stop_event is not None and stop_event.is_set():
            raise RuntimeError("已取消等待设备解锁")
        if interactive:
            print("请解锁全部设备后按回车...")
            input()
        else:
            time.sleep(poll_interval)

def get_usbmux_lockdownclient(stop_event=None, interactive=True, poll_interval=0.5):
    lockdowns = get_usbmux_lockdownclients(
        stop_event=stop_event,
        interactive=interactive,
        poll_interval=poll_interval,
        require_count=1,
    )
    if not lockdowns:
        raise NoDeviceConnectedError()
    return lockdowns[0]

def get_version(lockdown: LockdownClient):
    return lockdown.all_values.get("ProductVersion")

def get_developer_mode_status(lockdown: LockdownClient):
    return lockdown.developer_mode_status

def reveal_developer_mode(lockdown: LockdownClient):
    AmfiService(lockdown).reveal_developer_mode_option_in_ui()

def enable_developer_mode(lockdown: LockdownClient):
    AmfiService(lockdown).enable_developer_mode()
