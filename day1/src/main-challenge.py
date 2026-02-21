# ~/ai-bootcamp/day01/src/level3_challenge.py
# 目标：整合所有技能，做一个迷你工具

from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Iterator, List, Optional
from datetime import datetime
import json
import sys
import time
from loguru import logger
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from decorator import log_call, timing
import heapq



# 配置结构化输出（JSON 格式，供分析）
logger.remove()  # 移除默认 handler
logger.add(sys.stderr, format="{time} | {level} | {message} | {extra}")
Path("logs").mkdir(parents=True, exist_ok=True)
logger.add("logs/app.json", serialize=True)  # JSON 格式，供分析


@dataclass
class Largest_file:
    path: str  # 用 str 方便 asdict 后直接 json.dumps
    lines: int
    size_kb: float
   

@dataclass
class CodeFile:
    """代码文件信息"""
    path: Path
    language: str
    lines: int
    last_modified: float
    
    @property
    def size_kb(self) -> float:
        return self.path.stat().st_size / 1024
    
    @property
    def is_recent(self) -> bool:
        """最近7天内修改"""
        days = (datetime.now().timestamp() - self.last_modified) / 86400
        return days <= 7

@dataclass
class CodeAnalyzer:
    """代码分析器（Day 1终极挑战）"""
    
    def __init__(self, root: Path, console: Optional[Console] = None):
        self.root = Path(root).expanduser()
        self.stats = {"total_files": 0, "total_lines": 0}
        self.console = console or Console()
        # 绑定上下文：每个analyzer实例有独立logger
        self.logger = logger.bind(analyzer_id=id(self), root=str(self.root))
        self.logger.info("CodeAnalyzer初始化")
    
    
    @log_call
    def scan(self, pattern: str = "*.py", show_progress: bool = True) -> Iterator[CodeFile]:
        """扫描代码文件（内存友好）"""
        # 先收集所有文件路径（用于进度条）
        all_files = list(self.root.rglob(pattern))
        total = len(all_files)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            disable=not show_progress
        ) as progress:
            task = progress.add_task(f"扫描 {pattern} 文件...", total=total)
            
            for file_path in all_files:
                if not file_path.is_file():
                    progress.update(task, advance=1)
                    continue
                
                # 跳过隐藏目录（路径中包含以 . 开头的目录名）
                if any(part.startswith('.') for part in file_path.parts if part not in ('.', '..')):
                    progress.update(task, advance=1)
                    continue
                
                try:
                    content = file_path.read_text(encoding='utf-8')
                    lines = len(content.splitlines())
                    
                    yield CodeFile(
                        path=file_path,
                        language=file_path.suffix[1:] or "unknown",
                        lines=lines,
                        last_modified=file_path.stat().st_mtime
                    )
                    
                    self.stats["total_files"] += 1
                    self.stats["total_lines"] += lines
                    
                except Exception as e:
                    # 结构化：字段可查询（用 bind 传入 extra，非 extra= 参数）
                    self.logger.bind(
                        file_path=str(file_path),
                        error_type=type(e).__name__,
                        error_msg=str(e),
                    ).warning("文件读取失败")
                
                progress.update(task, advance=1)
        
        # 扫描完成，结构化统计（loguru 用 bind 传上下文，不是 extra=）
        self.logger.bind(
            total_files=self.stats["total_files"],
            total_lines=self.stats["total_lines"],
            pattern=pattern,
        ).info("扫描完成")
    
    
       
    @timing
    @log_call
    def generate_report(self, top_n: int = 5, show_progress: bool = True) -> dict:
        """生成分析报告"""
        scan_start = time.perf_counter()
        files = list(self.scan(show_progress=show_progress))
        scan_elapsed = time.perf_counter() - scan_start
        
        # largest_files 按 size_kb 从大到小排序
        largest_files_sorted = sorted(
            files, 
            key=lambda x: x.size_kb, 
            reverse=True
        )[:top_n]
        
        # recent_files 按 last_modified 从新到旧排序
        recent_files_sorted = sorted(
            [f for f in files if f.is_recent],
            key=lambda x: x.last_modified,
            reverse=True
        )[:top_n]
        
        return {
            "summary": {
                **self.stats,
                "scan_time_seconds": round(scan_elapsed, 4)
            },
            "largest_files": [
                asdict(Largest_file(path=str(f.path), lines=f.lines, size_kb=f.size_kb))
                for f in largest_files_sorted
            ],
            "recent_files": [
                str(f.path) for f in recent_files_sorted
            ]
        }
    
    @log_call
    def display_report(self, report: dict):
        """使用 Rich 美化显示报告"""
        console = self.console
        
        # 显示标题
        console.print()
        console.print(Panel.fit(
            "[bold cyan]代码分析报告[/bold cyan]",
            border_style="cyan"
        ))
        console.print()
        
        # 显示统计摘要
        summary_table = Table(title="📊 统计摘要", box=box.ROUNDED, show_header=True, header_style="bold magenta")
        summary_table.add_column("指标", style="cyan", no_wrap=True)
        summary_table.add_column("数值", style="green", justify="right")
        
        summary_table.add_row("总文件数", f"{report['summary']['total_files']:,}")
        summary_table.add_row("总代码行数", f"{report['summary']['total_lines']:,}")
        # 添加扫描时间
        scan_time = report['summary'].get('scan_time_seconds', 0)
        summary_table.add_row("扫描耗时", f"{scan_time:.4f} 秒", style="yellow")
        
        console.print(summary_table)
        console.print()
        
        # 显示最大的文件
        if report['largest_files']:
            largest_table = Table(title="📁 最大的文件 (按大小)", box=box.ROUNDED, show_header=True, header_style="bold yellow")
            largest_table.add_column("排名", style="dim", width=6, justify="center")
            largest_table.add_column("文件路径", style="cyan", no_wrap=False)
            largest_table.add_column("行数", style="green", justify="right", width=10)
            largest_table.add_column("大小 (KB)", style="magenta", justify="right", width=12)
            
            for idx, file_info in enumerate(report['largest_files'], 1):
                largest_table.add_row(
                    str(idx),
                    file_info['path'],
                    f"{file_info['lines']:,}",
                    f"{file_info['size_kb']:.2f}"
                )
            
            console.print(largest_table)
            console.print()
        
        # 显示最近修改的文件
        if report['recent_files']:
            recent_table = Table(title="🕒 最近修改的文件 (7天内)", box=box.ROUNDED, show_header=True, header_style="bold green")
            recent_table.add_column("排名", style="dim", width=6, justify="center")
            recent_table.add_column("文件路径", style="cyan", no_wrap=False)
            
            for idx, file_path in enumerate(report['recent_files'], 1):
                recent_table.add_row(str(idx), file_path)
            
            console.print(recent_table)
            console.print()

# 创建 Typer 应用
app = typer.Typer(help="代码分析器 - 扫描项目并生成统计报告")
console = Console()

@app.command()
@log_call
def analyze(
    root: str = typer.Argument("~/ai-bootcamp", help="要分析的根目录路径"),
    top_n: int = typer.Option(5, "--top", "-n", help="显示前 N 个文件"),
    pattern: str = typer.Option("*.py", "--pattern", "-p", help="文件匹配模式"),
    json_output: bool = typer.Option(False, "--json", "-j", help="输出 JSON 格式"),
    no_progress: bool = typer.Option(False, "--no-progress", help="不显示进度条")
):
    """
    分析代码项目并生成报告
    
    示例:
        python main-challenge.py ~/myproject --top 10
        python main-challenge.py ~/myproject --pattern "*.{py,js}" --json
    """
    try:
        analyzer = CodeAnalyzer(root, console=console)
        report = analyzer.generate_report(top_n=top_n, show_progress=not no_progress)
        
        if json_output:
            # JSON 输出模式
            console.print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            # 美化输出模式
            analyzer.display_report(report)
            
    except Exception as e:
        console.print(f"[bold red]错误:[/bold red] {e}", style="red")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
