#!/usr/bin/env python3
"""
Typer + Rich 结合测试：生产级CLI工具风格
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
import time
import random

app = typer.Typer(help="🛠️ 高级CLI工具演示")
console = Console()

@app.command()
def status():
    """显示系统状态（美化版）"""
    # 创建信息面板
    info = Panel.fit(
        "[bold]Python版本:[/bold] 3.11\n"
        "[bold]虚拟环境:[/bold] .venv\n"
        "[bold]内存:[/bold] 8GB (M2 MacBook)\n"
        "[bold]状态:[/bold] [green]运行正常[/green]",
        title="[bold blue]系统信息[/bold blue]",
        border_style="blue"
    )
    console.print(info)

@app.command()
def tasks():
    """显示任务列表（交互式表格）"""
    table = Table(
        title="📋 今日任务",
        show_header=True,
        header_style="bold magenta"
    )
    
    table.add_column("ID", style="dim", width=6)
    table.add_column("任务名称", min_width=20)
    table.add_column("优先级", justify="center")
    table.add_column("进度", justify="right")
    
    tasks_data = [
        ("1", "安装环境", "高", "[green]100%[/green]"),
        ("2", "学习Typer", "高", "[green]100%[/green]"),
        ("3", "学习Rich", "中", "[yellow]80%[/yellow]"),
        ("4", "实战项目", "中", "[red]0%[/red]"),
    ]
    
    for row in tasks_data:
        table.add_row(*row)
    
    console.print(table)
    
    # 统计
    completed = sum(1 for t in tasks_data if "100%" in t[3])
    console.print(f"\n[bold]完成度: {completed}/{len(tasks_data)}[/bold]")

@app.command()
def process(
    task_name: str = typer.Argument(..., help="任务名称"),
    duration: int = typer.Option(3, "--duration", "-d", help="模拟耗时（秒）")
):
    """模拟任务处理（带进度动画）"""
    console.print(f"[bold]开始处理: {task_name}[/bold]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # 多个阶段
        stages = ["初始化", "数据加载", "处理中", "保存结果", "清理"]
        
        for stage in stages:
            task = progress.add_task(f"[cyan]{stage}...", total=None)
            time.sleep(duration / len(stages))
            progress.update(task, completed=True, description=f"[green]✓ {stage}[/green]")
    
    # 随机结果
    success = random.random() > 0.2
    if success:
        console.print(f"\n[bold green]✅ {task_name} 处理成功！[/bold green]")
    else:
        console.print(f"\n[bold red]❌ {task_name} 处理失败（模拟）[/bold red]")

@app.command()
def demo():
    """完整演示所有功能"""
    console.print(Panel.fit(
        "[bold]欢迎使用 AI Bootcamp CLI[/bold]\n"
        "这是一个 Typer + Rich 的演示工具",
        title="[bold yellow]🚀 Demo[/bold yellow]",
        border_style="yellow"
    ))
    
    console.print("\n[bold]1. 系统状态:[/bold]")
    status()
    
    console.print("\n[bold]2. 任务列表:[/bold]")
    tasks()
    
    console.print("\n[bold]3. 模拟处理:[/bold]")
    process("数据清洗", duration=2)

if __name__ == "__main__":
    app()
