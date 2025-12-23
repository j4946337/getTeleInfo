#!/bin/bash
# ============================================
# Telegram API 服务 Linux 安全部署脚本
# ============================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Telegram API 服务安全部署 ===${NC}"

# 检查是否以 root 运行
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}警告: 建议不要以 root 用户运行此脚本${NC}"
fi

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_USER="telegram-api"
SERVICE_NAME="telegram-api"

# 1. 创建专用系统用户（更安全）
create_user() {
    echo -e "${GREEN}[1/6] 创建专用服务用户...${NC}"
    if ! id "$SERVICE_USER" &>/dev/null; then
        sudo useradd --system --no-create-home --shell /bin/false "$SERVICE_USER"
        echo -e "${GREEN}✅ 用户 $SERVICE_USER 创建成功${NC}"
    else
        echo -e "${YELLOW}用户 $SERVICE_USER 已存在${NC}"
    fi
}

# 2. 创建安装目录
setup_directories() {
    echo -e "${GREEN}[2/6] 设置目录结构...${NC}"
    INSTALL_DIR="/opt/telegram-api"

    sudo mkdir -p "$INSTALL_DIR"
    sudo mkdir -p "$INSTALL_DIR/data"
    sudo mkdir -p "$INSTALL_DIR/logs"

    # 复制文件
    sudo cp "$SCRIPT_DIR/app.py" "$INSTALL_DIR/"
    sudo cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"

    # 如果存在会话文件，也复制过去
    if [ -d "$SCRIPT_DIR/data" ]; then
        sudo cp -r "$SCRIPT_DIR/data/"* "$INSTALL_DIR/data/" 2>/dev/null || true
    fi

    # 设置权限
    sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    sudo chmod 700 "$INSTALL_DIR/data"  # 会话文件只有服务用户可访问
    sudo chmod 755 "$INSTALL_DIR"

    echo -e "${GREEN}✅ 目录设置完成: $INSTALL_DIR${NC}"
}

# 3. 创建 Python 虚拟环境
setup_venv() {
    echo -e "${GREEN}[3/6] 创建 Python 虚拟环境...${NC}"
    INSTALL_DIR="/opt/telegram-api"

    sudo -u "$SERVICE_USER" python3 -m venv "$INSTALL_DIR/venv" 2>/dev/null || \
        sudo python3 -m venv "$INSTALL_DIR/venv"

    sudo "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
    sudo "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

    echo -e "${GREEN}✅ 虚拟环境创建完成${NC}"
}

# 4. 创建环境变量文件
create_env_file() {
    echo -e "${GREEN}[4/6] 创建环境变量文件...${NC}"
    ENV_FILE="/opt/telegram-api/.env"

    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${YELLOW}请输入你的 Telegram API 配置:${NC}"
        read -p "TELEGRAM_API_ID: " api_id
        read -p "TELEGRAM_API_HASH: " api_hash

        sudo tee "$ENV_FILE" > /dev/null << EOF
# Telegram API 配置
TELEGRAM_API_ID=$api_id
TELEGRAM_API_HASH=$api_hash

# 服务配置
API_PORT=50001
API_HOST=127.0.0.1
EOF

        # 严格权限 - 只有 root 和服务用户可读
        sudo chown root:"$SERVICE_USER" "$ENV_FILE"
        sudo chmod 640 "$ENV_FILE"

        echo -e "${GREEN}✅ 环境变量文件创建完成${NC}"
    else
        echo -e "${YELLOW}环境变量文件已存在: $ENV_FILE${NC}"
    fi
}

# 5. 创建 systemd 服务文件
create_systemd_service() {
    echo -e "${GREEN}[5/6] 创建 systemd 服务...${NC}"

    sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << 'EOF'
[Unit]
Description=Telegram User Query API Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=telegram-api
Group=telegram-api
WorkingDirectory=/opt/telegram-api

# 环境变量文件
EnvironmentFile=/opt/telegram-api/.env

# 启动命令
ExecStart=/opt/telegram-api/venv/bin/python /opt/telegram-api/app.py

# 重启策略
Restart=always
RestartSec=10

# 安全加固
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/opt/telegram-api/data /opt/telegram-api/logs

# 资源限制
MemoryMax=512M
CPUQuota=50%

# 日志
StandardOutput=journal
StandardError=journal
SyslogIdentifier=telegram-api

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    echo -e "${GREEN}✅ systemd 服务创建完成${NC}"
}

# 6. 配置防火墙
setup_firewall() {
    echo -e "${GREEN}[6/6] 配置防火墙...${NC}"

    # 检查 ufw
    if command -v ufw &> /dev/null; then
        echo "检测到 UFW 防火墙"
        # 只允许本地访问 50001 端口（如果需要外部访问，请手动开放）
        # sudo ufw allow from 127.0.0.1 to any port 50001
        echo -e "${YELLOW}提示: 服务默认只监听 127.0.0.1，如需外部访问请配置反向代理${NC}"
    fi

    # 检查 firewalld
    if command -v firewall-cmd &> /dev/null; then
        echo "检测到 firewalld 防火墙"
        echo -e "${YELLOW}提示: 服务默认只监听 127.0.0.1，如需外部访问请配置反向代理${NC}"
    fi
}

# 显示完成信息
show_completion() {
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}✅ 部署完成！${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo "常用命令:"
    echo "  启动服务:   sudo systemctl start telegram-api"
    echo "  停止服务:   sudo systemctl stop telegram-api"
    echo "  重启服务:   sudo systemctl restart telegram-api"
    echo "  查看状态:   sudo systemctl status telegram-api"
    echo "  查看日志:   sudo journalctl -u telegram-api -f"
    echo "  开机自启:   sudo systemctl enable telegram-api"
    echo ""
    echo -e "${YELLOW}⚠️ 首次运行需要验证 Telegram 账号:${NC}"
    echo "  cd /opt/telegram-api"
    echo "  sudo -u telegram-api ./venv/bin/python app.py"
    echo ""
    echo -e "${YELLOW}⚠️ 修改环境变量:${NC}"
    echo "  sudo nano /opt/telegram-api/.env"
    echo ""
}

# 主函数
main() {
    create_user
    setup_directories
    setup_venv
    create_env_file
    create_systemd_service
    setup_firewall
    show_completion
}

# 运行
main

