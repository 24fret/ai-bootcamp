#!/usr/bin/env python3
"""
异步爬虫 - Day 2 上午核心
8GB内存优化：限制并发 + 流式处理

┌─────────────────────────────────────────────────────────┐
│                    AsyncCrawler 设计目标                   │
│  1. 高性能：异步IO同时处理多个请求，不阻塞等待             │
│  2. 资源安全：8GB内存限制下，控制并发数+数据大小            │
│  3. 健壮性：超时、异常、错误状态码都有处理                   │
│  4. 可观测：日志记录全过程，统计成功失败                    │
└─────────────────────────────────────────────────────────┘

                    核心设计模式
┌─────────────────────────────────────────────────────────┐
│  异步上下文管理器（async with）                           │
│  ├─ __aenter__: 自动创建HTTP session                     │
│  ├─ 业务逻辑: 执行抓取任务                                │
│  └─ __aexit__: 自动关闭连接，释放资源                     │
│                                                          │
│  信号量控制（Semaphore）                                  │
│  └─ 像"通行证"，只有3个，用完等别人归还才能继续           │
└─────────────────────────────────────────────────────────┘

关键设计决策表
| 决策                       | 选择      | 原因              |
| ------------------------ | ------- | --------------- |
| `aiohttp` vs `requests`  | aiohttp | 支持异步，性能高10倍     |
| `Semaphore(3)` vs 无限制    | 3       | 8GB内存安全，防目标网站封禁 |
| `delay=1s` vs 立即请求       | 1秒      | 礼貌爬虫，防被封IP      |
| `timeout=30s` vs 默认      | 30秒     | 防止死等，快速失败       |
| 截断1MB/10KB内容             | 是       | 防内存爆炸，存精华       |
| `return_exceptions=True` | 是       | 单个失败不影响整体       |

数据流全景图
输入: URL列表 ["url1", "url2", "url3", ...]
    ↓
async with AsyncCrawler() as crawler  ← 创建session，准备资源
    ↓
fetch_many(urls)
    ├── 创建任务: [fetch_one(url1), fetch_one(url2), ...]
    ├── gather并发执行（受semaphore=3限制）
    │       ├── 任务1: sleep(1s) → HTTP请求 → 解析 → Article
    │       ├── 任务2: sleep(1s) → HTTP请求 → 解析 → Article
    │       ├── 任务3: sleep(1s) → HTTP请求 → 解析 → Article
    │       ├── 任务4: 等待semaphore ─→ 获取 → HTTP请求...
    │       └── ...
    └── 收集所有结果
        ├── 成功: Article对象
        ├── 失败: None或异常
        └── 统计: success/failed/total_time
    ↓
返回: List[Article]
    ↓
__aexit__ 自动关闭session，释放资源


推荐可以爬取的网站
| 网站                   | URL                                    | 允许爬虫     | 特点              | 适合练习       |
| -------------------- | -------------------------------------- | -------- | --------------- | ---------- |
| **HTTPBin**          | `https://httpbin.org`                  | ✅ 专门用于测试 | 模拟各种HTTP场景      | 基础请求、错误处理  |
| **Quotes to Scrape** | `http://quotes.toscrape.com`           | ✅ 教学专用   | 经典爬虫练习站，结构简单    | 分页、解析、存储   |
| **JSONPlaceholder**  | `https://jsonplaceholder.typicode.com` | ✅ 假数据API | REST API，返回JSON | API调用、数据处理 |

"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Optional, Dict
import time
from loguru import logger
from pathlib import Path


@dataclass
class Article:
    """文章数据类"""
    title: str
    url: str
    content: str
    fetched_at: float
    status: int = 200  # HTTP状态码
    
    def to_dict(self) -> Dict:
        """转字典，方便存储"""
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content[:500],  # 摘要
            "fetched_at": self.fetched_at,
            "status": self.status
        }


class AsyncCrawler:
    """异步爬虫：M2 8GB优化版"""
    
    def __init__(
        self,
        max_concurrent: int = 3,      # 8GB内存：3并发安全
        delay: float = 1.0,           # 礼貌延迟1秒
        timeout: int = 30             # 30秒超时
    ):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.delay = delay
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
        self.stats = {
            "success": 0,
            "failed": 0,
            "total_time": 0.0
        }
    
    async def __aenter__(self):
        """异步上下文管理器：进入时创建session"""
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            #伪装浏览器，防被拒绝
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
        )
        logger.info(f"爬虫启动：并发={self.semaphore._value}, 延迟={self.delay}s")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出时关闭session"""
        if self.session:
            await self.session.close()
            logger.info(f"爬虫关闭：成功={self.stats['success']}, 失败={self.stats['failed']}")
    
    async def fetch_one(self, url: str) -> Optional[Article]:
        """抓取单个URL"""
        async with self.semaphore:  # 限制并发数
            await asyncio.sleep(self.delay)  # 礼貌延迟
            
            start_time = time.time()
            
            try:
                logger.debug(f"开始抓取: {url}")
                
                async with self.session.get(url) as response:
                    elapsed = time.time() - start_time
                    
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status}: {url}")
                        self.stats["failed"] += 1
                        return Article(
                            title="",
                            url=url,
                            content="",
                            fetched_at=time.time(),
                            status=response.status
                        )
                    
                    # 读取内容（限制大小防内存爆炸）
                    html = await response.text()
                    if len(html) > 1_000_000:  # 1MB限制
                        logger.warning(f"页面过大，截断: {url}")
                        html = html[:1_000_000]
                    
                    # 解析
                    soup = BeautifulSoup(html, 'lxml')
                    
                    title = self._extract_title(soup)
                    content = self._extract_content(soup)
                    
                    self.stats["success"] += 1
                    self.stats["total_time"] += elapsed
                    
                    logger.success(f"抓取成功 ({elapsed:.2f}s): {title[:50]}...")
                    
                    return Article(
                        title=title,
                        url=url,
                        content=content,
                        fetched_at=time.time(),
                        status=200
                    )
                    
            except asyncio.TimeoutError:
                logger.error(f"超时: {url}")
                self.stats["failed"] += 1
                return None
                
            except Exception as e:
                logger.error(f"抓取失败 {url}: {e}")
                self.stats["failed"] += 1
                return None
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """智能提取标题"""
        # 尝试多种选择器
        selectors = [
            'h1.article-title',
            'h1.entry-title',
            'h1.post-title',
            'h1',
            'title',
            '.article-header h1'
        ]
        
        for selector in selectors:
            tag = soup.select_one(selector)
            if tag:
                return tag.get_text(strip=True)[:200]
        
        return "无标题"
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """智能提取正文"""
        # 移除噪声元素
        for noise in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            noise.decompose()
        
        # 尝试正文容器
        selectors = [
            'article',
            'main',
            '.article-content',
            '.post-content',
            '.entry-content',
            '[role="main"]'
        ]
        
        for selector in selectors:
            container = soup.select_one(selector)
            if container:
                return container.get_text(separator='\n', strip=True)[:10000]
        
        # 兜底：取最长段落
        paragraphs = soup.find_all('p')
        if paragraphs:
            longest = max(paragraphs, key=lambda p: len(p.get_text()))
            return longest.get_text(strip=True)[:10000]
        
        return soup.get_text(separator='\n', strip=True)[:5000]
    
    async def fetch_many(self, urls: List[str]) -> List[Article]:
        """批量抓取"""
        start_time = time.time()
        
        # 创建所有任务
        tasks = [self.fetch_one(url) for url in urls]
        
        # 并发执行，等待全部完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # 过滤结果
        articles = []
        for r in results:
            if isinstance(r, Article) and r.status == 200:
                articles.append(r)
            elif isinstance(r, Exception):
                logger.error(f"任务异常: {r}")
        
        logger.info(f"批量完成: {len(articles)}/{len(urls)} 成功, 总耗时 {total_time:.2f}s")
        
        return articles


# ========== 测试代码 ==========

async def test_crawler():
    """测试异步爬虫"""
    
    # 测试URL列表（用可靠站点）
    test_urls = [
        "https://httpbin.org/html",           # 测试HTML页面
        "https://httpbin.org/delay/2",        # 测试延迟处理
        "http://quotes.toscrape.com",     # 经典爬虫测试网站
        "https://jsonplaceholder.typicode.com",  #假数据网站
        "http://localhost:3000" # 本地测试URL（请确保服务已启动）
    ]
    
    # 添加更多真实URL（如果有）
    # test_urls.extend([
    #     "https://news.ycombinator.com",
    #     "https://github.com/trending",
    # ])
    
    async with AsyncCrawler(max_concurrent=2, delay=0.5) as crawler:
        articles = await crawler.fetch_many(test_urls)
        
        print(f"\n{'='*50}")
        print(f"抓取结果: {len(articles)} 篇成功")
        print(f"{'='*50}")
        
        for art in articles:
            print(f"\n标题: {art.title}")
            print(f"URL: {art.url}")
            print(f"内容预览: {art.content[:100]}...")
            print(f"耗时: {art.fetched_at - time.time():.2f}s 前")


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level="INFO")
    
    # 运行测试
    asyncio.run(test_crawler())