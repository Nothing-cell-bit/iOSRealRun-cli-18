# iOSRealRun-cli-18

通过 USB 连接 iPhone / iPad，按照路线文件循环模拟定位。项目基于 [iOSRealRun-cli-17](https://github.com/iOSRealRun/iOSRealRun-cli-17)，使用 `pymobiledevice3` 建立设备隧道和调用定位服务。

当前主要入口是 **Windows 的 `ZjuRun.exe`** 和 **源码图形界面 `gui.py`**。首次使用请阅读 [使用指南](docs/使用指南.md)，其中包含设备准备、DDI 挂载、自定义路线和故障排查。

## 功能与默认配置

- 图形界面支持单机运行、双机同步运行，并显示 USB 设备数和运行日志。
- 单机要求恰好连接 1 台设备；双机要求恰好连接 2 台设备。**界面默认选择双机，只有一台设备时需切换为单机。**
- 双机使用同一路线和速度同步模拟；运行过程中不能修改模式、速度和路线。
- 默认路线为 `ZJGroute.txt`，默认速度为 `4.2 m/s`，约 `3 分 58 秒 / 公里`。
- 自带 `ZJGroute.txt`、`YQroute.txt`、`HNroute.txt`、`CUFEroute.txt`，也可添加自己的路线。
- 路线持续循环，需要手动点击“停止运行”。停止流程会尝试清除模拟定位并关闭隧道。

## 环境说明

| 项目 | 说明 |
| --- | --- |
| 电脑系统 | 程序检查允许 Windows 和 macOS；仓库中的 EXE 仅用于 Windows |
| Python | 源码运行和 Windows 打包建议使用 Python 3.11；EXE 启动无需另装 Python |
| 设备系统 | 项目原记录的测试版本为 iOS 18.3.1；代码允许 iOS 17 及以上，其他版本需自行验证 |
| Windows 驱动 | 按项目原有安装方式安装 iTunes，确认电脑能够识别设备 |
| 设备状态 | 使用 USB 数据线连接，解锁、信任电脑并开启开发者模式 |
| 权限 | Windows 以管理员身份运行；macOS 使用 root 权限运行源码 GUI |

当前本地 Python 环境为 Windows、Python 3.11.9。已有测试覆盖配置路径、路线路径和隧道启动命令；这些测试不代表真机连接、DDI 挂载和定位恢复已在所有系统版本上验证。

## Windows EXE 快速开始

1. 下载整个项目并解压，保留以下文件在同一目录。使用 EXE 本身无需安装 Python；如需用源码命令准备 DDI，则需要指南中的 Python 环境。

   ```text
   iOSRealRun-cli-18/
   ├── ZjuRun.exe
   ├── config.yaml
   ├── ZJGroute.txt
   ├── YQroute.txt
   ├── HNroute.txt
   └── CUFEroute.txt
   ```

2. 按 [使用指南：设备准备](docs/使用指南.md#设备准备) 完成驱动、信任、开发者模式和 DDI 准备。
3. 右键 `ZjuRun.exe` → **以管理员身份运行**。
4. 根据设备数量选择“单机运行”或“双机运行”，确认界面显示的设备数匹配。
5. 选择路线，输入大于 0 的速度，点击 **开始运行**。日志应依次出现环境检查、隧道建立、路线加载和开始模拟的信息。
6. 结束时点击 **停止运行**，等日志显示“已停止”后再关闭窗口、拔线，并检查设备实际定位是否恢复。

配置和路线从 **EXE 所在目录** 读取。目录应允许当前用户写入，以便保存配置。

## Windows 源码 GUI

先安装 Python 3.11。在 PowerShell 中进入项目目录，创建虚拟环境并安装固定版本依赖：

```powershell
git clone https://github.com/Nothing-cell-bit/iOSRealRun-cli-18.git
cd iOSRealRun-cli-18
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

完成设备准备后，**以管理员身份** 打开 PowerShell，进入项目目录并启动：

```powershell
.\.venv\Scripts\python.exe gui.py
```

直接使用虚拟环境的 Python，无需激活环境。macOS 安装和启动命令见 [完整使用指南](docs/使用指南.md#macos-源码-gui)。

## 配置与路线

仓库中的 `config.yaml` 默认内容：

```yaml
v: 4.2
routeConfig: ZJGroute.txt
libimobiledeviceDir: libimobiledevice
imageDir: DeveloperDiskImage
```

`v` 是速度，单位为米/秒；`routeConfig` 是路线文件名或路径。GUI 选择路线后会保存配置，修改速度后按回车或离开输入框也会保存，点击开始时再次保存。运行模式不保存在此配置中，重新启动界面后仍默认双机。

源码从 `config.py` 所在目录读取配置和相对路线；EXE 从自身所在目录读取。GUI 在该目录扫描 `*route.txt`，新增路线后需要重启界面。路线格式和坐标说明见 [使用指南：自定义路线](docs/使用指南.md#自定义路线)。

## 已知问题

- **旧命令行入口 `main.py` 暂不可作为正常启动方式。** 它仍按旧接口调用 `tunnel.tunnel()`，与当前异步接口及返回值不兼容，请使用 `gui.py` 或 EXE。
- 当前本地 Python 环境和仓库 EXE 的 `mounter auto-mount --help` 均报 `ModuleNotFoundError: No module named 'ipsw_parser.img4'`。DDI 挂载存在依赖兼容问题，详见 [使用指南：DDI 挂载](docs/使用指南.md#ddi-挂载)。
- 强制结束进程、拔线或设备连接中断时，定位清理可能失败。确认设备定位恢复；未恢复时可重启设备。

## 测试与重新打包

在已有 Python 3.11 虚拟环境中安装测试依赖并执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

打包 Windows EXE：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\build_exe.ps1
```

输出位于 `dist/`，包含 EXE、配置和所有 `*route.txt` 文件。打包不会自动替换仓库根目录的 `ZjuRun.exe`。详细检查步骤见 [使用指南：测试与打包](docs/使用指南.md#测试与打包)。

## 项目来源

- [iOSRealRun-cli-17](https://github.com/iOSRealRun/iOSRealRun-cli-17)
- [pymobiledevice3](https://github.com/doronz88/pymobiledevice3)
- [iOSEasyRun](https://github.com/BiancoChiu/iOSEasyRun)：原文档提供的手动操作参考，兼容性请按其自身说明确认。

许可证见 [LICENSE](LICENSE)。
