#!/usr/bin/env python3
"""
爬虫+数据库整合管道 - Day 2 完整实战
┌─────────────────────────────────────────────────────────┐
│              CrawlerPipeline 设计目标                      │
│  1. 端到端自动化：URL输入 → 抓取 → 存储 → 查询展示         │
│  2. 数据流无缝：Article对象 → Record字典 → SQLite持久化    │
│  3. 可观测性：Rich进度条 + 统计报表 + 日志记录              │
│  4. 工具化：Typer CLI，命令行一键操作                      │
└─────────────────────────────────────────────────────────┘

                    数据流架构
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ URL列表 │──→│  爬虫   │──→│  转换   │──→│  数据库  │
│(Typer参)│    │ Article │    │ Record  │    │ SQLite  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
     ↑                                          ↓
     └──────────── 查询/统计/搜索 ←─────────────┘
              (Typer子命令)


              
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import box
import typer

# 导入Day 1和Day 2的模块
sys.path.insert(0, str(Path(__file__).parent))
from async_crawler import AsyncCrawler, Article
from ArticleDatabase import ArticleDatabase, ArticleRecord


class CrawlerPipeline:
    """爬虫+数据库整合管道"""
    
    def __init__(self, db: Optional[ArticleDatabase] = None):
        self.db = db or ArticleDatabase()
        self.console = Console()
    
    def article_to_record(self, article: Article, source: str) -> dict:
        """Article对象 → 数据库字典"""
        return {
            "title": article.title[:200],  # 截断防超长
            "url": article.url,
            "content": article.content[:2000],  # 存摘要，不全存
            "source": source,
            "fetched_at": datetime.fromtimestamp(article.fetched_at).isoformat()
        }
    
    async def crawl_and_store(
        self,
        urls: List[str],
        source: str,
        max_concurrent: int = 2,
        delay: float = 1.0
    ) -> dict:
        """抓取并存储完整流程"""
        stats = {"total": len(urls), "success": 0, "failed": 0, "stored": 0}
        
        # 第1步：抓取
        self.console.print(f"[cyan]开始抓取 {source}: {len(urls)} 个URL[/cyan]")
        
        async with AsyncCrawler(max_concurrent=max_concurrent, delay=delay) as crawler:
            articles = await crawler.fetch_many(urls)
        
        stats["success"] = len([a for a in articles if a and a.status == 200])
        stats["failed"] = stats["total"] - stats["success"]
        
        # 第2步：转换并存储
        self.console.print(f"[green]抓取完成，开始存储...[/green]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("存储到数据库...", total=len(articles))
            
            for article in articles:
                if article and article.status == 200:
                    record = self.article_to_record(article, source)
                    article_id = self.db.insert_article(record)
                    if article_id:
                        stats["stored"] += 1
                progress.advance(task)
        
        return stats
    
    def show_stored_articles(self, source: Optional[str] = None, limit: int = 10):
        """展示已存储的文章"""
        self.console.print(f"\n[bold cyan]已存储的文章[/bold cyan]")
        
        table = Table(
            title=f"来源: {source or '全部'}",
            box=box.ROUNDED,
            show_header=True
        )
        table.add_column("ID", style="dim", width=6)
        table.add_column("标题", style="cyan", max_width=40)
        table.add_column("来源", style="green", width=12)
        table.add_column("采集时间", style="yellow", width=16)
        
        count = 0
        for record in self.db.get_articles(source=source, limit=limit):
            table.add_row(
                str(record.id),
                record.title[:40],
                record.source or "未知",
                record.fetched_at[:16] if record.fetched_at else "-"
            )
            count += 1
        
        self.console.print(table)
        self.console.print(f"[dim]共 {count} 条[/dim]")
    
    def show_stats(self):
        """展示数据库统计"""
        stats = self.db.get_stats()
        
        self.console.print(f"\n[bold green]数据库统计[/bold green]")
        self.console.print(f"总文章数: {stats['total_articles']}")
        
        if stats['by_source']:
            source_table = Table(title="按来源分布", box=box.SIMPLE)
            source_table.add_column("来源", style="cyan")
            source_table.add_column("数量", style="green", justify="right")
            
            for src, cnt in sorted(stats['by_source'].items()):
                source_table.add_row(src, str(cnt))
            
            self.console.print(source_table)


# ========== CLI入口 ==========

app = typer.Typer(help="爬虫+数据库整合工具")
console = Console()

@app.command()
def crawl_quotes(
    pages: int = typer.Option(3, "--pages", "-p", help="抓取页数"),
    max_concurrent: int = typer.Option(2, "--concurrent", "-c", help="并发数"),
    delay: float = typer.Option(1.0, "--delay", "-d", help="延迟(秒)")
):
    """抓取Quotes网站，存入数据库"""
    
    # 生成URL列表
    urls = [
        f"http://quotes.toscrape.com/page/{i}/"
        for i in range(1, pages + 1)
    ]
    
    # 执行管道
    pipeline = CrawlerPipeline()
    
    async def run():
        stats = await pipeline.crawl_and_store(
            urls=urls,
            source="quotes",
            max_concurrent=max_concurrent,
            delay=delay
        )
        
        console.print(f"\n[bold]抓取统计:[/bold]")
        console.print(f"  总计: {stats['total']}")
        console.print(f"  成功: {stats['success']}")
        console.print(f"  失败: {stats['failed']}")
        console.print(f"  存储: {stats['stored']}")
        
        # 展示结果
        pipeline.show_stats()
        pipeline.show_stored_articles(source="quotes", limit=5)
    
    asyncio.run(run())

@app.command()
def crawl_httpbin(
    count: int = typer.Option(2, "--count", "-n", help="测试次数")
):
    """测试HTTPBin，存入数据库"""
    
    urls = ["https://httpbin.org/html"] * count
    
    pipeline = CrawlerPipeline()
    
    async def run():
        stats = await pipeline.crawl_and_store(
            urls=urls,
            source="httpbin",
            max_concurrent=1,
            delay=0.5
        )
        
        console.print(f"\n[bold]HTTPBin测试完成:[/bold]")
        console.print(f"  存储: {stats['stored']}/{stats['total']}")
        
        pipeline.show_stored_articles(source="httpbin")
    
    asyncio.run(run())

@app.command()
def list_articles(
    source: Optional[str] = typer.Option(None, "--source", "-s", help="筛选来源"),
    limit: int = typer.Option(20, "--limit", "-n", help="显示数量")
):
    """查询已存储的文章"""
    pipeline = CrawlerPipeline()
    pipeline.show_stored_articles(source=source, limit=limit)

@app.command()
def stats():
    """查看数据库统计"""
    pipeline = CrawlerPipeline()
    pipeline.show_stats()

@app.command()
def search(
    keyword: str = typer.Argument(..., help="搜索关键词")
):
    """搜索文章标题和内容"""
    pipeline = CrawlerPipeline()
    
    results = pipeline.db.search_by_keyword(keyword, limit=20)
    
    table = Table(title=f"搜索: {keyword}", box=box.ROUNDED)
    table.add_column("ID", style="dim")
    table.add_column("标题", style="cyan")
    table.add_column("来源", style="green")
    
    for record in results:
        table.add_row(
            str(record.id),
            record.title[:50],
            record.source or "-"
        )
    
    console.print(table)
    console.print(f"[dim]找到 {len(results)} 条[/dim]")


if __name__ == "__main__":
    app()