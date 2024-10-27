from loguru import logger
import sys
from pathlib import Path

def setup_logger():
    """配置日志"""
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 移除默认的 sink
    logger.remove()
    
    # 添加控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>",
        level="DEBUG",
        colorize=True
    )
    
    # 添加文件日志
    logger.add(
        str(log_dir / "app_{time:YYYY-MM-DD}.log"),
        rotation="00:00",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="DEBUG",
        encoding="utf-8"
    )
    
    return logger

# 初始化并导出 logger
logger = setup_logger()