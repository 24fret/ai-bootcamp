# ~/ai-bootcamp/day02/src/test_crawler.py
# 用这3个网站测试你的爬虫

import asyncio
from async_crawler import AsyncCrawler, Article

async def test_httpbin():
    """测试HTTPBin"""
    urls = [
        "https://httpbin.org/html",
        "https://httpbin.org/delay/2",
    ]
    
    async with AsyncCrawler(max_concurrent=2, delay=0.5) as crawler:
        articles = await crawler.fetch_many(urls)
        print(f"\n✅ HTTPBin: {len(articles)} 成功")
        for a in articles:
            print(f"  - {a.title[:50]}")

async def test_quotes():
    """测试Quotes网站（前3页）"""
    urls = [
        "http://quotes.toscrape.com/page/1/",
        "http://quotes.toscrape.com/page/2/",
        "http://quotes.toscrape.com/page/3/",
    ]
    
    async with AsyncCrawler(max_concurrent=2, delay=1.0) as crawler:
        articles = await crawler.fetch_many(urls)
        print(f"\n✅ Quotes: {len(articles)} 页成功")
        
        # 解析名言（简单提取）
        for a in articles:
            # 从content中提取第一个<span class="text">
            if 'class="text"' in a.content:
                import re
                quote = re.search(r'<span class="text">(.*?)</span>', a.content)
                if quote:
                    print(f"  - {quote.group(1)[:60]}...")

async def test_jsonplaceholder():
    """测试JSON API"""
    urls = [
        "https://jsonplaceholder.typicode.com/posts/1",
        "https://jsonplaceholder.typicode.com/posts/2",
        "https://jsonplaceholder.typicode.com/posts/3",
    ]
    
    async with AsyncCrawler(max_concurrent=3, delay=0.3) as crawler:
        articles = await crawler.fetch_many(urls)
        print(f"\n✅ JSONPlaceholder: {len(articles)} 成功")
        for a in articles:
            # content是JSON，直接打印
            print(f"  - Post {a.url.split('/')[-1]}: {a.content[:100]}")

async def main():
    print("=== 测试爬虫（3个友好网站）===")
    
    await test_httpbin()
    await test_quotes()
    await test_jsonplaceholder()
    
    print("\n🎉 全部测试完成！")

if __name__ == "__main__":
    asyncio.run(main())