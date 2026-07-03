# Linux Share WiFi

独立的 **PySide6** Linux WiFi 热点图形界面。使用系统 [`create_ap`](https://github.com/lakinduakash/linux-wifi-hotspot) 脚本作为后端（与 GTK 版 `wihotspot` 相同）。

可将整个 `linux-share-wifi` 文件夹复制到任意位置单独使用。

## 功能

- 创建 / 停止 WiFi 热点（NAT 共享）
- WiFi 网卡与上网网卡选择
- SSID、密码、开放网络、2.4 / 5 GHz 频段
- 运行中热点列表，每行 **Stop** / **QR**
- 右键热点行查看详情（SSID、密码、网关等）
- 已连接设备列表与刷新
- 非 root 用户通过 `pkexec` 授权（与 C 版 GUI 一致）
- 密码框旁 **Show / Hide** 按钮可切换明文显示

## 快速开始

```bash
cd linux-share-wifi
chmod +x run.sh
./run.sh
```

或手动：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m linux_share_wifi
```

**建议用普通用户运行**（不要用 `sudo ./run.sh`）。创建或停止热点时 Polkit 会弹出授权对话框。

默认热点 SSID 为 **LinuxShareWifi**，可在界面中修改。

## 全新 Ubuntu 上能否运行？

**可以运行**，但不能只复制 `linux-share-wifi` 文件夹就完事——还需要安装系统依赖和 `create_ap` 后端。

### 本项目自带、可独立运行的部分

- 复制整个文件夹到任意位置即可
- `./run.sh` 会自动创建虚拟环境并安装 **PySide6**、**qrcode**
- **不需要**编译 GTK/C 版 `wihotspot`

### 全新 Ubuntu 还缺什么

| 类别 | 需要安装 | 说明 |
|------|----------|------|
| Python | `python3`、`python3-venv` | 最小化安装有时默认没有 venv |
| Qt 界面 | 桌面环境（GNOME 等） | 无图形界面无法显示窗口 |
| 热点后端 | **`create_ap`** | GUI 只是前端，真正建热点靠它 |
| 系统工具 | hostapd、dnsmasq、iptables、iw、iproute2 | `create_ap` 运行时需要 |
| 权限 | `pkexec`（policykit-1） | 创建/停止热点时会弹授权框 |
| 可选 | haveged | 随机数不足时有用 |

**全新 Ubuntu 默认没有 `create_ap`**，这是最容易漏掉的一步。

### 推荐安装步骤（Ubuntu Desktop）

```bash
# 1. 系统依赖
sudo apt update
sudo apt install -y python3 python3-venv python3-pip \
  hostapd dnsmasq iptables iw iproute2 policykit-1 haveged git

# 2. 安装 create_ap（任选一种）

# 方式 A：PPA（最简单）
sudo add-apt-repository ppa:lakinduakash/lwh
sudo apt update
sudo apt install linux-wifi-hotspot   # 会带上 create_ap

# 方式 B：从源码只装 CLI
git clone https://github.com/lakinduakash/linux-wifi-hotspot.git
cd linux-wifi-hotspot
sudo make install-cli-only

# 3. 运行 Linux Share WiFi
cd /path/to/linux-share-wifi
chmod +x run.sh
./run.sh
```

### 可能遇到的问题

1. **界面能开，但列表里没有 WiFi 网卡**  
   检查 `iw dev`，确认驱动正常、网卡支持 AP 模式。

2. **创建热点失败**  
   多半是 `hostapd` / `dnsmasq` 未装，或 NetworkManager 占用网卡。  
   可试：`sudo systemctl stop hostapd dnsmasq` 后再创建。

3. **PySide6 启动报错（缺少 libxcb 等）**  
   桌面版 Ubuntu 一般不会有；Server 或无头环境需要额外装 Qt/X11 库。

4. **热点详情读不全**  
   需要较新的 `create_ap`（带 `--show-info` 支持）。

5. **复制 `.venv` 到新机器**  
   不建议。到新机器后删掉 `.venv`，重新 `./run.sh` 让它重建。

### 与 GTK 版对比

| | GTK 原版 | Linux Share WiFi |
|---|---------|------------------|
| 编译 | 需要 gcc、gtk 开发包 | **不需要** |
| Python | 不需要 | 需要 3.9+ |
| create_ap | 需要 | **同样需要** |
| 系统热点工具 | 需要 | **同样需要** |

在**带桌面的全新 Ubuntu** 上，装好依赖和 `create_ap` 后，**可以正常运行**，且比 C/GTK 版更容易部署（不用编译）。

## 依赖说明

### Python 包（由 `run.sh` / pip 自动安装）

- Python 3.9+
- PySide6 >= 6.5.0
- qrcode[pil] >= 7.4.2

见 `requirements.txt`。

### 系统工具

- `create_ap`（必须单独安装，见上文）
- `hostapd`、`dnsmasq`、`iptables`、`iw`、`iproute2`、`bash`、`pkexec`
- 可选：`haveged`

`create_ap` 可从 [linux-wifi-hotspot](https://github.com/lakinduakash/linux-wifi-hotspot) 或发行版包安装。

可选环境变量，指向自定义脚本：

```bash
export CREATE_AP_BIN=/path/to/create_ap
export CREATE_AP_CONFIG=/etc/create_ap.conf
```

## 项目结构

```
linux-share-wifi/
  README.md
  requirements.txt
  pyproject.toml
  run.sh
  linux_share_wifi/
    __main__.py          # python -m linux_share_wifi
    main_window.py       # Qt 主界面
    create_ap_cli.py     # create_ap 封装
    workers.py           # 后台线程
    qr_utils.py          # QR 生成
    qr_dialog.py
```

## 与 linux-wifi-hotspot 的关系

| | GTK 原版 | Linux Share WiFi |
|---|-------------|------------------|
| UI | GTK 3 + Glade | PySide6 |
| 后端 | create_ap | create_ap |
| 语言 | C | Python |
| 仓库 | 可同 monorepo | **独立仓库** |

## License

FreeBSD（与上游 create_ap 精神一致）。完整条款见上游项目。
