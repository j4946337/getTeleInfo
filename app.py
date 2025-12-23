#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram 用户查询 API 服务
提供 HTTP 接口供 PHP 调用
支持后台常驻运行
"""

import asyncio
import re
import logging
import os
import threading
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.users import GetFullUserRequest
from telethon.errors import UsernameNotOccupiedError, UsernameInvalidError
from flask import Flask, jsonify, request
from flask_cors import CORS
import time

# ============================================
# 配置信息（从环境变量读取，更安全）
# ============================================
API_ID = int(os.environ.get('TELEGRAM_API_ID', '0'))
API_HASH = os.environ.get('TELEGRAM_API_HASH', '')
API_PORT = int(os.environ.get('API_PORT', '50001'))
API_HOST = os.environ.get('API_HOST', '127.0.0.1')  # 默认只监听本地，更安全

# 检查必要的配置
if not API_ID or not API_HASH:
    raise ValueError("请设置环境变量 TELEGRAM_API_ID 和 TELEGRAM_API_HASH")

# 获取脚本所在目录，确保会话文件使用绝对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 创建 data 目录用于存储会话文件（确保有写入权限）
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
SESSION_FILE = os.path.join(DATA_DIR, 'api_session')

# ============================================
# 日志配置（日志文件放在 data 目录，确保可写）
# ============================================
LOG_FILE = os.path.join(DATA_DIR, 'telegram_api.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# Flask 应用
# ============================================
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局 Telegram 客户端和事件循环
client = None
main_loop = None

# 数据中心映射
DC_LOCATIONS = {
    1: "美国 迈阿密",
    2: "荷兰 阿姆斯特丹",
    3: "美国 迈阿密",
    4: "荷兰 阿姆斯特丹",
    5: "新加坡"
}

# 简单的内存缓存（可选）
cache = {}
CACHE_EXPIRE = 300  # 缓存5分钟


# ============================================
# UID 注册时间映射
# ============================================
def estimate_registration_year(user_id):
    """根据 UID 估算注册时间（精确到月份）"""
    if user_id < 1000000:
        return "~ 2013-06"
    elif user_id < 10000000:
        return "~ 2014-03"
    elif user_id < 50000000:
        return "~ 2015-02"
    elif user_id < 100000000:
        return "~ 2015-08"
    elif user_id < 200000000:
        return "~ 2016-02"
    elif user_id < 300000000:
        return "~ 2016-06"
    elif user_id < 400000000:
        return "~ 2016-10"
    elif user_id < 500000000:
        return "~ 2017-01"
    elif user_id < 600000000:
        return "~ 2017-04"
    elif user_id < 700000000:
        return "~ 2017-06"
    elif user_id < 800000000:
        return "~ 2017-08"
    elif user_id < 900000000:
        return "~ 2017-10"
    elif user_id < 1000000000:
        return "~ 2017-12"
    elif user_id < 1100000000:
        return "~ 2018-02"
    elif user_id < 1200000000:
        return "~ 2018-04"
    elif user_id < 1300000000:
        return "~ 2018-06"
    elif user_id < 1400000000:
        return "~ 2018-08"
    elif user_id < 1500000000:
        return "~ 2018-10"
    elif user_id < 1600000000:
        return "~ 2018-12"
    elif user_id < 1700000000:
        return "~ 2019-02"
    elif user_id < 1800000000:
        return "~ 2019-04"
    elif user_id < 1900000000:
        return "~ 2019-06"
    elif user_id < 2000000000:
        return "~ 2019-08"
    elif user_id < 2100000000:
        return "~ 2019-10"
    elif user_id < 2200000000:
        return "~ 2019-12"
    elif user_id < 2400000000:
        return "~ 2020-03"
    elif user_id < 2600000000:
        return "~ 2020-06"
    elif user_id < 2800000000:
        return "~ 2020-09"
    elif user_id < 3000000000:
        return "~ 2020-12"
    elif user_id < 3200000000:
        return "~ 2021-03"
    elif user_id < 3400000000:
        return "~ 2021-06"
    elif user_id < 3600000000:
        return "~ 2021-09"
    elif user_id < 3800000000:
        return "~ 2021-12"
    elif user_id < 4000000000:
        return "~ 2022-02"
    elif user_id < 4200000000:
        return "~ 2022-04"
    elif user_id < 4400000000:
        return "~ 2022-06"
    elif user_id < 4600000000:
        return "~ 2022-08"
    elif user_id < 4800000000:
        return "~ 2022-10"
    elif user_id < 5000000000:
        return "~ 2022-12"
    elif user_id < 5200000000:
        return "~ 2023-02"
    elif user_id < 5400000000:
        return "~ 2023-04"
    elif user_id < 5600000000:
        return "~ 2023-06"
    elif user_id < 5800000000:
        return "~ 2023-08"
    elif user_id < 6000000000:
        return "~ 2023-10"
    elif user_id < 6200000000:
        return "~ 2023-12"
    elif user_id < 6400000000:
        return "~ 2024-02"
    elif user_id < 6600000000:
        return "~ 2024-04"
    elif user_id < 6800000000:
        return "~ 2024-06"
    elif user_id < 7000000000:
        return "~ 2024-08"
    elif user_id < 7200000000:
        return "~ 2024-10"
    elif user_id < 7400000000:
        return "~ 2024-12"
    else:
        return "~ 2025-01"


def calculate_account_age(registration_estimate):
    """计算账号年龄（精确到月份）"""
    match = re.search(r'(\d{4})-(\d{2})', registration_estimate)
    if match:
        reg_year = int(match.group(1))
        reg_month = int(match.group(2))

        current_year = datetime.now().year
        current_month = datetime.now().month

        # 计算总月数
        total_months = (current_year - reg_year) * 12 + (current_month - reg_month)

        if total_months < 1:
            return "< 1 个月"
        elif total_months < 12:
            return f"~ {total_months} 个月"
        else:
            years = total_months // 12
            months = total_months % 12
            if months > 0:
                return f"~ {years} 年 {months} 个月"
            else:
                return f"~ {years} 年"
    return "未知"


# ============================================
# Telegram 客户端初始化
# ============================================
async def init_client():
    """初始化 Telegram 客户端"""
    global client
    try:
        logger.info("正在初始化 Telegram 客户端...")
        logger.info(f"会话文件路径: {SESSION_FILE}")
        logger.info(f"数据目录: {DATA_DIR} (存在: {os.path.exists(DATA_DIR)}, 可写: {os.access(DATA_DIR, os.W_OK)})")
        client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
        await client.start()
        logger.info("✅ Telegram 客户端初始化成功")
        return True
    except Exception as e:
        logger.error(f"❌ Telegram 客户端初始化失败: {e}")
        logger.error(f"调试信息 - 会话文件: {SESSION_FILE}")
        return False


# ============================================
# 核心查询函数
# ============================================
async def get_user_info(username):
    """获取用户详细信息"""
    try:
        # 移除 @ 符号
        username = username.lstrip('@')

        # 检查缓存
        cache_key = username.lower()
        if cache_key in cache:
            cached_data = cache[cache_key]
            if time.time() - cached_data['timestamp'] < CACHE_EXPIRE:
                logger.info(f"从缓存返回用户信息: {username}")
                return cached_data['data']

        logger.info(f"正在查询用户: {username}")

        # 获取用户实体
        user = await client.get_entity(username)

        # 获取完整用户信息
        full = await client(GetFullUserRequest(user))

        # 收集用户名
        usernames = []
        if user.username:
            usernames.append(f"@{user.username}")

        # 额外用户名
        if hasattr(user, 'usernames') and user.usernames:
            for username_obj in user.usernames:
                if hasattr(username_obj, 'username'):
                    usernames.append(f"@{username_obj.username}")

        # 数据中心
        dc_id = user.photo.dc_id if user.photo else None

        # 估算注册时间
        registration_time = estimate_registration_year(user.id)

        # 构建结果
        result = {
            'success': True,
            'data': {
                'user_id': user.id,
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'username': user.username or '',
                'usernames': usernames,
                'phone': user.phone or '',
                'is_bot': user.bot,
                'is_premium': user.premium or False,
                'is_verified': user.verified or False,
                'is_restricted': user.restricted or False,
                'dc_id': dc_id,
                'dc_location': DC_LOCATIONS.get(dc_id, '未知') if dc_id else '未知',
                'registration_time': registration_time,
                'account_age': calculate_account_age(registration_time),
                'bio': full.full_user.about if full.full_user.about else '',
                'profile_photo': user.photo is not None,
                'query_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        }

        # 存入缓存
        cache[cache_key] = {
            'data': result,
            'timestamp': time.time()
        }

        logger.info(f"✅ 成功查询用户: {username} (UID: {user.id})")
        return result

    except UsernameNotOccupiedError:
        logger.warning(f"用户名不存在: {username}")
        return {'success': False, 'error': '用户名不存在'}
    except UsernameInvalidError:
        logger.warning(f"无效的用户名: {username}")
        return {'success': False, 'error': '无效的用户名格式'}
    except ValueError as e:
        logger.error(f"值错误: {e}")
        return {'success': False, 'error': '用户不存在或已被删除'}
    except Exception as e:
        logger.error(f"查询失败: {e}")
        return {'success': False, 'error': f'查询失败: {str(e)}'}


# ============================================
# API 路由
# ============================================
@app.route('/api/user/<username>', methods=['GET'])
def query_user(username):
    """查询用户 API 端点"""
    try:
        # 使用主事件循环运行异步函数
        future = asyncio.run_coroutine_threadsafe(get_user_info(username), main_loop)
        result = future.result(timeout=30)  # 30秒超时
        return jsonify(result)
    except Exception as e:
        logger.error(f"API 请求处理失败: {e}")
        return jsonify({
            'success': False,
            'error': f'服务器内部错误: {str(e)}'
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        'status': 'ok',
        'service': 'telegram-user-api',
        'version': '1.0.0',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """清除缓存"""
    global cache
    cache_size = len(cache)
    cache.clear()
    logger.info(f"缓存已清除，清除了 {cache_size} 条记录")
    return jsonify({
        'success': True,
        'message': f'已清除 {cache_size} 条缓存'
    })


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    return jsonify({
        'cache_size': len(cache),
        'uptime': 'running',
        'client_connected': client is not None and client.is_connected()
    })


# ============================================
# 主函数
# ============================================
def run_event_loop(loop):
    """在后台线程中运行事件循环"""
    asyncio.set_event_loop(loop)
    loop.run_forever()


def main():
    """主函数"""
    global main_loop
    logger.info("=" * 50)
    logger.info("Telegram 用户查询 API 服务")
    logger.info("=" * 50)

    # 创建事件循环
    main_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(main_loop)

    # 初始化 Telegram 客户端
    success = main_loop.run_until_complete(init_client())

    if not success:
        logger.error("❌ 初始化失败，服务无法启动")
        return

    # 在后台线程中运行事件循环
    loop_thread = threading.Thread(target=run_event_loop, args=(main_loop,), daemon=True)
    loop_thread.start()

    # 启动 Flask 服务
    logger.info(f"🚀 API 服务启动中...")
    logger.info(f"📡 监听地址: http://{API_HOST}:{API_PORT}")
    logger.info(f"📝 日志文件: telegram_api.log")
    logger.info(f"✅ 服务已就绪，等待请求...")
    logger.info("=" * 50)

    try:
        app.run(
            host=API_HOST,
            port=API_PORT,
            debug=False,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("\n👋 收到停止信号，正在关闭服务...")
    except Exception as e:
        logger.error(f"❌ 服务异常: {e}")
    finally:
        # 停止事件循环
        if main_loop and main_loop.is_running():
            main_loop.call_soon_threadsafe(main_loop.stop)
        if client:
            asyncio.run_coroutine_threadsafe(client.disconnect(), main_loop).result(timeout=5)
        logger.info("✅ 服务已停止")


if __name__ == '__main__':
    main()