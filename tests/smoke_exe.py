"""Check the actual EXE startup without connecting to or changing a device."""
import argparse
from pathlib import Path
import subprocess
import time

import psutil
from pywinauto import Desktop


def check_startup(executable, screenshot=None):
    process = subprocess.Popen(
        [str(executable)], cwd=executable.parent.parent,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f'EXE exited before showing its GUI: {process.returncode}')
            family = {process.pid}
            family.update(child.pid for child in psutil.Process(process.pid).children(recursive=True))
            for window in Desktop(backend='win32').windows():
                if window.process_id() not in family:
                    continue
                title = window.window_text()
                if title.startswith('ZjuRun -'):
                    if screenshot:
                        window.capture_as_image().save(screenshot)
                    time.sleep(1)
                    if process.poll() is not None:
                        raise RuntimeError('EXE exited after creating its GUI')
                    print(f'PASS: {title}')
                    return
                if 'Unhandled exception' in title or 'Error' in title:
                    detail = '\n'.join(window.texts())
                    raise RuntimeError(f'EXE showed an error dialog: {detail}')
            time.sleep(0.2)
        raise TimeoutError('EXE did not show its GUI within 45 seconds')
    finally:
        if process.poll() is None:
            for child in psutil.Process(process.pid).children(recursive=True):
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            process.kill()
        process.wait(timeout=10)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('executable', type=Path)
    parser.add_argument('--screenshot', type=Path)
    args = parser.parse_args()
    check_startup(args.executable.resolve(), args.screenshot)
