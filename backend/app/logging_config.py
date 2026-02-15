"""
结构化日志配置模块

功能：
- JSON 格式日志输出
- 多日志级别支持（DEBUG、INFO、WARNING、ERROR）
- 请求 ID 追踪
"""
import logging
import sys
import json
from datetime import datetime
from typing import Any
from contextvars import ContextVar
from pythonjsonlogger import jsonlogger

# 请求 ID 上下文变量
request_id_context: ContextVar[str] = ContextVar("request_id", default="")


class RequestIdFilter(logging.Filter):
    """添加请求 ID 到日志记录"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get("")
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """自定义 JSON 格式化器"""

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)

        # 添加时间戳
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # 添加日志级别
        log_record["level"] = record.levelname

        # 添加请求 ID
        log_record["request_id"] = getattr(record, "request_id", "")

        # 添加模块信息
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    配置结构化日志

    Args:
        log_level: 日志级别（DEBUG、INFO、WARNING、ERROR）

    Returns:
        配置好的 Logger 实例
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # 1. 配置 root logger，让所有模块的日志都能输出到终端
    # 使用简洁的文本格式，便于开发调试
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除 root logger 现有处理器（避免重复）
    root_logger.handlers.clear()

    # 创建控制台处理器（文本格式）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # 设置文本格式化器
    text_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(text_formatter)

    # 添加请求 ID 过滤器
    console_handler.addFilter(RequestIdFilter())

    root_logger.addHandler(console_handler)

    # 2. 为 stock_api logger 配置 JSON 格式（可选，用于结构化日志收集）
    stock_api_logger = logging.getLogger("stock_api")
    stock_api_logger.setLevel(level)
    stock_api_logger.handlers.clear()

    json_handler = logging.StreamHandler(sys.stdout)
    json_handler.setLevel(level)
    json_formatter = CustomJsonFormatter(
        "%(timestamp)s %(level)s %(name)s %(message)s",
        rename_fields={"levelname": "level", "name": "logger"}
    )
    json_handler.setFormatter(json_formatter)
    json_handler.addFilter(RequestIdFilter())

    # 设置不向上传播，避免重复输出
    stock_api_logger.propagate = False
    stock_api_logger.addHandler(json_handler)

    return stock_api_logger


def get_logger(name: str = "stock_api") -> logging.Logger:
    """
    获取日志器实例

    Args:
        name: 日志器名称

    Returns:
        Logger 实例
    """
    return logging.getLogger(name)
