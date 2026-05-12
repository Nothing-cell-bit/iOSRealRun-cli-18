import multiprocessing
import sys
import os

# 修复 PyInstaller --windowed 模式下 stdin/stdout/stderr 为 None 的问题
# 必须在导入任何第三方库（特别是 blessed/inquirer3）之前执行
# 这是一个更彻底的 monkey patch，直接在最顶层执行
class NullWriter:
    def write(self, s): pass
    def flush(self): pass
    def fileno(self): return -1
    def isatty(self): return False

class NullReader:
    def read(self, n=-1): return ""
    def readline(self, n=-1): return ""
    def fileno(self): return -1
    def isatty(self): return False

# 核心修复：blessed 库不仅检查 sys.stdout，还检查 sys.__stdout__
# 如果 stream 参数未提供，它默认使用 sys.__stdout__
# 在 PyInstaller --windowed 模式下，sys.stdout 和 sys.__stdout__ 都是 None
# 因此必须全部修补

if sys.stdout is None:
    sys.stdout = NullWriter()
if sys.stderr is None:
    sys.stderr = NullWriter()
if sys.stdin is None:
    sys.stdin = NullReader()

# 强制修复 dunder streams，防止 blessed 绕过 sys.stdout 直接访问 __stdout__
if getattr(sys, '__stdout__', None) is None:
    sys.__stdout__ = sys.stdout
if getattr(sys, '__stderr__', None) is None:
    sys.__stderr__ = sys.stderr
if getattr(sys, '__stdin__', None) is None:
    sys.__stdin__ = sys.stdin

import tkinter as tk
from tkinter import messagebox, scrolledtext
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import threading
import asyncio
import logging
import signal
import time

# 导入原有逻辑
from init import init as init_module
from init import tunnel as tunnel_module
from init import route as route_module
import run
import config

class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')
        self.text_widget.after(0, append)

class ZjuRunGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ZjuRun - iOS 虚拟跑步工具")
        self.root.geometry("600x500")
        self.style = ttk.Style(theme="cosmo")
        
        self.running = False
        self.loop = None
        self.tunnel_process = None
        self.stop_event = None
        self.run_id = 0
        
        self.setup_ui()
        self.setup_logging()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)

        # 标题
        title_label = ttk.Label(main_frame, text="ZjuRun 控制台", font=("Helvetica", 18, "bold"), bootstyle=PRIMARY)
        title_label.pack(pady=(0, 20))

        # 配置区域
        config_frame = ttk.Labelframe(main_frame, text="运行配置", padding=10)
        config_frame.pack(fill=X, pady=10)

        # 速度设置
        speed_frame = ttk.Frame(config_frame)
        speed_frame.pack(fill=X, pady=5)
        ttk.Label(speed_frame, text="模拟速度 (m/s):").pack(side=LEFT)
        self.speed_var = tk.DoubleVar(value=config.config.v)
        self.speed_entry = ttk.Entry(speed_frame, textvariable=self.speed_var, width=10)
        self.speed_entry.pack(side=LEFT, padx=10)
        self.speed_entry.bind("<FocusOut>", self.on_speed_changed)
        self.speed_entry.bind("<Return>", self.on_speed_changed)
        ttk.Label(speed_frame, text="(默认 4.2 约 4min/km)", font=("", 9), bootstyle=SECONDARY).pack(side=LEFT)

        # 路线选择
        route_frame = ttk.Frame(config_frame)
        route_frame.pack(fill=X, pady=5)
        ttk.Label(route_frame, text="当前路线:").pack(side=LEFT)
        self.route_var = tk.StringVar(value=config.config.routeConfig)
        
        # 获取目录下所有 txt 文件作为路线候选
        routes = [f for f in os.listdir('.') if f.endswith('route.txt')]
        if not routes: routes = ["ZJGroute.txt", "YQroute.txt", "HNroute.txt"]
        
        self.route_combo = ttk.Combobox(route_frame, textvariable=self.route_var, values=routes, state="readonly")
        self.route_combo.pack(side=LEFT, padx=10, fill=X, expand=YES)
        self.route_combo.bind("<<ComboboxSelected>>", self.on_route_changed)

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=20)

        self.start_btn = ttk.Button(btn_frame, text="开始运行", command=self.toggle_run, bootstyle=SUCCESS, width=15)
        self.start_btn.pack(side=LEFT, padx=10, expand=YES)

        # 日志区域
        log_frame = ttk.Labelframe(main_frame, text="运行日志", padding=10)
        log_frame.pack(fill=BOTH, expand=YES)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state='disabled', font=("Consolas", 9))
        self.log_text.pack(fill=BOTH, expand=YES)

    def setup_logging(self):
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        handler = TextHandler(self.log_text)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # 重定向 stdout
        class StdoutRedirector:
            def __init__(self, logger): self.logger = logger
            def write(self, s):
                if s.strip(): self.logger.info(s.strip())
            def flush(self): pass
        sys.stdout = StdoutRedirector(self.logger)

    def toggle_run(self):
        if not self.running:
            self.start_run()
        else:
            self.stop_run()

    def on_route_changed(self, _event=None):
        config.config.routeConfig = self.route_var.get()
        config.config.save()
        self.logger.info(f"已保存路线配置: {config.config.routeConfig}")

    def on_speed_changed(self, _event=None):
        try:
            config.config.v = float(self.speed_var.get())
        except (ValueError, tk.TclError):
            self.speed_var.set(config.config.v)
            self.logger.error("速度格式无效，请输入数字")
            return
        config.config.save()
        self.logger.info(f"已保存速度配置: {config.config.v} m/s")

    def start_run(self):
        # 更新配置
        config.config.v = self.speed_var.get()
        config.config.routeConfig = self.route_var.get()
        config.config.save()
        
        self.run_id += 1
        self.running = True
        self.stop_event = threading.Event()
        self.start_btn.configure(text="停止运行", bootstyle=DANGER)
        self.speed_entry.configure(state='disabled')
        self.route_combo.configure(state='disabled')
        
        # 在新线程中运行 asyncio 循环
        current_run_id = self.run_id
        self.thread = threading.Thread(target=self.run_async_logic, args=(current_run_id,), daemon=True)
        self.thread.start()

    def run_async_logic(self, run_id):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.main_logic(run_id))
        except Exception as e:
            self.logger.error(f"发生错误: {e}")
        finally:
            self.loop.close()

    async def main_logic(self, run_id):
        try:
            # 1. 环境检查
            init_module.init(stop_event=self.stop_event, interactive=False)
            self.logger.info("环境检查通过")

            # 2. 建立隧道
            self.logger.info("正在建立隧道 (可能需要几秒)...")
            self.tunnel_process, address, port = tunnel_module.tunnel()
            
            if not address:
                self.logger.error("无法建立隧道，请确保设备已连接并信任电脑")
                self.root.after(0, self.stop_run)
                return

            self.logger.info(f"隧道建立成功: {address}:{port}")

            # 3. 获取路线
            loc = route_module.get_route()
            self.logger.info(f"成功加载路线: {config.config.routeConfig}")

            # 4. 开始模拟
            self.logger.info(f"开始模拟跑步，速度: {config.config.v} m/s")
            await run.run(address, port, loc, config.config.v, stop_event=self.stop_event)
            
        except SystemExit:
            self.logger.error("程序已退出 (可能是权限不足或设备未开启开发者模式)")
        except RuntimeError as e:
            self.logger.info(str(e))
        except Exception as e:
            self.logger.error(f"运行异常: {e}")
        finally:
            if self.tunnel_process:
                self.tunnel_process.terminate()
                self.tunnel_process = None
            self.root.after(0, lambda: self.finish_stop(run_id))

    def stop_run(self):
        if not self.running: return
        
        self.logger.info("正在停止运行并清理定位...")
        if self.stop_event is not None:
            self.stop_event.set()
        self.start_btn.configure(text="停止中...", state='disabled')
        # 如果还没建好 tunnel，说明仍处于“等设备/等解锁”阶段，此时可以直接恢复界面
        if self.tunnel_process is None:
            self.finish_stop(self.run_id)

    def finish_stop(self, run_id=None):
        if run_id is not None and run_id != self.run_id:
            return
        self.running = False
        self.stop_event = None
        self.start_btn.configure(text="开始运行", bootstyle=SUCCESS)
        self.start_btn.configure(state='normal')
        self.speed_entry.configure(state='normal')
        self.route_combo.configure(state='readonly')
        self.logger.info("已停止")

    def on_closing(self):
        if self.running:
            if messagebox.askokcancel("退出", "程序正在运行，确定要退出并还原定位吗？"):
                self.stop_run()
                self.root.after(200, self.close_when_stopped)
        else:
            self.root.destroy()

    def close_when_stopped(self):
        if self.running:
            self.root.after(200, self.close_when_stopped)
        else:
            self.root.destroy()

if __name__ == "__main__":
    multiprocessing.freeze_support() # 为 PyInstaller 打包做准备
    
    root = ttk.Window(themename="cosmo")
    gui = ZjuRunGUI(root)
    root.protocol("WM_DELETE_WINDOW", gui.on_closing)
    root.mainloop()
