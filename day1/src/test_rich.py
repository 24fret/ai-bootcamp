#!/usr/bin/env python3
"""
Rich测试：验证安装并学习美化输出
"""

from rich import print
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track
from rich.syntax import Syntax
from rich.tree import Tree
import time

console = Console()

def test_basic_print():
    """测试基础彩色打印"""
    print("[bold red]粗体红色[/bold red]")
    print("[green]绿色[/green] [blue]蓝色[/blue] [yellow]黄色[/yellow]")
    print("[italic]斜体[/italic] [underline]下划线[/underline]")
    print("[strike]删除线[/strike]")

def test_console():
    """测试Console高级功能"""
    console.print("\n[bold cyan]=== Console测试 ===[/bold cyan]")
    
    # 样式文本
    console.print("成功", style="bold green")
    console.print("警告", style="bold yellow")
    console.print("错误", style="bold red on white")
    
    # 面板
    console.print(Panel.fit(
        "这是一个带边框的面板\n可以有多行内容",
        title="[bold]面板标题[/bold]",
        border_style="blue"
    ))

def test_table():
    """测试表格"""
    table = Table(title="🚀 项目统计")
    
    table.add_column("日期", style="cyan", no_wrap=True)
    table.add_column("任务", style="magenta")
    table.add_column("完成度", justify="right", style="green")
    table.add_column("状态", style="bold")
    
    table.add_row("Day 1", "环境搭建", "100%", "[green]✓[/green]")
    table.add_row("Day 2", "Python工程化", "80%", "[yellow]进行中[/yellow]")
    table.add_row("Day 3", "数据处理", "0%", "[red]待开始[/red]")
    
    console.print(table)

def test_progress():
    """测试进度条"""
    console.print("\n[yellow]模拟任务进度...[/yellow]")
    
    # 简单进度条
    for i in track(range(20), description="处理中..."):
        time.sleep(0.05)  # 模拟工作
    
    console.print("[green]✓ 完成！[/green]")

def test_syntax():
    """测试代码高亮"""
    code = '''
def hello_world():
    print("Hello, World!")
    return 42
'''
    syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="Python代码"))

def test_tree():
    """测试树形结构"""
    tree = Tree("📁 ai-bootcamp")
    
    day01 = tree.add("📂 day01")
    day01.add("📄 main.py")
    day01.add("📄 test_typer.py")
    day01.add("📄 test_rich.py")
    
    day02 = tree.add("📂 day02")
    day02.add("📄 file_manager.py")
    
    tree.add("📂 .venv")
    
    console.print(tree)

def test_logging_style():
    """模拟日志输出"""
    console.print("[dim]2024-01-15 10:30:15[/dim] [blue]INFO[/blue] 应用启动")
    console.print("[dim]2024-01-15 10:30:16[/dim] [yellow]WARNING[/yellow] 配置加载延迟")
    console.print("[dim]2024-01-15 10:30:17[/dim] [green]SUCCESS[/green] 数据库连接成功")
    console.print("[dim]2024-01-15 10:30:18[/dim] [red]ERROR[/red] 请求超时，重试中...")

if __name__ == "__main__":
    test_basic_print()
    test_console()
    test_table()
    test_progress()
    test_syntax()
    test_tree()
    test_logging_style()
    
    console.print("\n[bold green]🎉 所有Rich测试通过！[/bold green]")
