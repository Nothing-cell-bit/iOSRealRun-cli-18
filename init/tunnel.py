import asyncio
import logging
import re
import subprocess
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def start_tunnel_for_udid(udid, timeout=20):
    command = [
        sys.executable,
        "-m",
        "pymobiledevice3",
        "lockdown",
        "start-tunnel",
        "--script-mode",
    ]
    if udid is not None:
        command.extend(["--udid", udid])

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=creationflags,
    )

    logging.info(f"正在为设备 {udid} 建立 tunnel")

    script_mode_pattern = re.compile(r"^(\S+)\s+(\d+)$")
    deadline = time.time() + timeout

    while time.time() < deadline:
        output = process.stdout.readline()
        if process.poll() is not None and not output:
            break
        output = output.strip()
        if not output:
            continue
        logging.info(f"[{udid}] {output}")
        match = script_mode_pattern.match(output)
        if match:
            address, port = match.group(1), int(match.group(2))
            return process, address, port

    stop_tunnel_processes_sync([process])
    return None, None, None

async def start_tunnels(lockdowns, timeout=20):
    tunnel_processes = []
    endpoints = []
    try:
        for lockdown in lockdowns:
            udid = getattr(lockdown, "udid", None)
            process, address, port = start_tunnel_for_udid(udid, timeout=timeout)
            if not address:
                raise RuntimeError(f"无法为设备 {udid} 建立隧道")
            tunnel_processes.append(process)
            endpoints.append((udid, address, port))
        return tunnel_processes, endpoints
    except Exception:
        await stop_tunnel_processes(tunnel_processes)
        raise

async def stop_tunnel_processes(processes):
    stop_tunnel_processes_sync(processes)
    await asyncio.sleep(0)

def stop_tunnel_processes_sync(processes):
    for process in processes:
        if process is None:
            continue
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)

async def tunnel():
    processes, endpoints = await start_tunnels([type("LockdownRef", (), {"udid": None})()], timeout=20)
    if not endpoints:
        return [], None, None
    _udid, address, port = endpoints[0]
    return processes, address, port
