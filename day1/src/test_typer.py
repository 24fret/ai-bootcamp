#!/usr/bin/env python3
"""
Typer测试：验证安装并学习基础用法
"""

import typer
from typing import Optional
from pathlib import Path

# 创建Typer应用实例
app = typer.Typer(help="🚀 Typer测试工具")

@app.command()
def hello(
    name: str = typer.Argument("World", help="要问候的名字"),
    count: int = typer.Option(1, "--count", "-c", help="重复次数"),
    uppercase: bool = typer.Option(False, "--upper", "-u", help="大写输出")
):
    """
    简单的问候命令
    """
    message = f"Hello, {name}!"
    if uppercase:
        message = message.upper()
    
    for _ in range(count):
        typer.echo(message)

@app.command()
def calc(
    operation: str = typer.Argument(..., help="操作: add/sub/mul/div"),
    x: float = typer.Argument(..., help="第一个数"),
    y: float = typer.Argument(..., help="第二个数")
):
    """
    简易计算器
    """
    result = {
        "add": x + y,
        "sub": x - y,
        "mul": x * y,
        "div": x / y if y != 0 else "错误：除零"
    }.get(operation, "未知操作")
    
    typer.echo(f"结果: {result}")

@app.command()
def file_info(
    path: Path = typer.Argument(..., help="文件路径", exists=True)
):
    """
    显示文件信息（验证Path类型）
    """
    stat = path.stat()
    typer.echo(f"📁 文件: {path.name}")
    typer.echo(f"📍 绝对路径: {path.resolve()}")
    typer.echo(f"📏 大小: {stat.st_size} bytes")
    typer.echo(f"📅 修改时间: {stat.st_mtime}")

if __name__ == "__main__":
    app()
