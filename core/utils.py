import os
from pathlib import Path

def format_file_size(size: int) -> str:
    """统一的文件大小格式化"""
    if size is None:
        return "未知"
    try:
        size = float(size)
    except (ValueError, TypeError):
        return str(size)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def get_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()

def build_path_string(path_parts: list) -> str:
    """将 [(id, name), ...] 转换为 /dir1/dir2 格式"""
    parts = [name for _, name in path_parts if name != "根目录"]
    return "/" + "/".join(parts) if parts else "/"