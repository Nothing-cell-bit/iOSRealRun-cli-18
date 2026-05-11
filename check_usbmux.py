import socket
import sys

def check_port(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    try:
        s.connect((ip, port))
        print(f"✅ 成功连接到 {ip}:{port} (Apple Mobile Device Service 看起来正在运行)")
        s.close()
        return True
    except Exception as e:
        print(f"❌ 无法连接到 {ip}:{port} - 错误: {e}")
        print("   -> 这意味着 Apple Mobile Device Service 可能没有正确监听，或者被防火墙拦截。")
        return False

if __name__ == "__main__":
    print("正在检查 Apple Mobile Device Service (usbmuxd) 端口...")
    check_port("127.0.0.1", 27015)
