import logging
import multiprocessing
import time

from pymobiledevice3.lockdown import create_using_usbmux, LockdownClient

from pymobiledevice3.cli.remote import RemoteServiceDiscoveryService
from pymobiledevice3.cli.remote import start_tunnel
from pymobiledevice3.cli.remote import verify_tunnel_imports

from pymobiledevice3.services.amfi import AmfiService

from pymobiledevice3.exceptions import NoDeviceConnectedError

def get_usbmux_lockdownclient(stop_event=None, interactive=True, poll_interval=0.5):
    while True:
        if stop_event is not None and stop_event.is_set():
            raise RuntimeError("已取消等待设备连接")
        try:
            lockdown = create_using_usbmux()
        except NoDeviceConnectedError:
            if interactive:
                print("请连接设备后按回车...")
                input()
            else:
                time.sleep(poll_interval)
                continue
        else:
            break
    while True:
        if stop_event is not None and stop_event.is_set():
            raise RuntimeError("已取消等待设备解锁")
        lockdown = create_using_usbmux()
        if lockdown.all_values.get("PasswordProtected"):
            if interactive:
                print("请解锁设备后按回车...")
                input()
            else:
                time.sleep(poll_interval)
                continue
        else:
            break
    return create_using_usbmux()

def get_version(lockdown: LockdownClient):
    return lockdown.all_values.get("ProductVersion")

def get_developer_mode_status(lockdown: LockdownClient):
    return lockdown.developer_mode_status

def reveal_developer_mode(lockdown: LockdownClient):
    AmfiService(lockdown).reveal_developer_mode_option_in_ui()

def enable_developer_mode(lockdown: LockdownClient):
    AmfiService(lockdown).enable_developer_mode()

async def tunnel(rsd: RemoteServiceDiscoveryService, queue: multiprocessing.Queue):
    async with start_tunnel(rsd, None) as tunnel_result:
        queue.put((tunnel_result.address, tunnel_result.port))
        await tunnel_result.client.wait_closed()
