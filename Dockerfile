# ============================================
# Telegram API 服务 Docker 镜像
# 多阶段构建，安全且轻量
# ============================================

FROM python:3.11-slim as builder

WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 创建虚拟环境并安装依赖
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================
# 最终镜像
# ============================================
FROM python:3.11-slim

# 安全：创建非 root 用户
RUN groupadd -r telegram && useradd -r -g telegram telegram

WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码
COPY --chown=telegram:telegram app.py .

# 创建数据目录
RUN mkdir -p /app/data && chown telegram:telegram /app/data

# 切换到非 root 用户
USER telegram

# 暴露端口
EXPOSE 50001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:50001/api/health')" || exit 1

# 启动命令
CMD ["python", "app.py"]

