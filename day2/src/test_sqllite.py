#!/usr/bin/env python3
"""测试数据库功能"""

from ArticleDatabase import ArticleDatabase, ArticleRecord
from datetime import datetime

def test_database():
    # 使用内存数据库测试（:memory:），或文件数据库
    db = ArticleDatabase()  # 默认路径 ~/ai-bootcamp/data/articles.db
    
    print("=== 测试插入 ===")
    
    # 模拟插入爬虫数据
    test_articles = [
        {
            "title": "Herman Melville - Moby Dick",
            "url": "https://httpbin.org/html",
            "content": "Call me Ishmael...",
            "source": "httpbin",
            "fetched_at": datetime.now().isoformat()
        },
        {
            "title": "Quote 1",
            "url": "http://quotes.toscrape.com/page/1/",
            "content": "The world as we have created it...",
            "source": "quotes",
            "fetched_at": datetime.now().isoformat()
        },
        {
            "title": "Post 1",
            "url": "https://jsonplaceholder.typicode.com/posts/1",
            "content": '{"userId": 1, "id": 1, "title": "sunt aut facere"}',
            "source": "jsonplaceholder",
            "fetched_at": datetime.now().isoformat()
        }
    ]
    
    for article in test_articles:
        article_id = db.insert_article(article)
        print(f"插入成功: id={article_id}")
    
    # 测试重复插入（应该更新，而不是报错）
    print("\n=== 测试去重 ===")
    article_id = db.insert_article(test_articles[0])
    print(f"重复插入返回: id={article_id}（应该相同，表示更新）")
    
    print("\n=== 测试查询 ===")
    print("所有文章：")
    for record in db.get_articles(limit=5):
        print(f"  [{record.source}] {record.title[:40]}...")
    
    print(f"\n仅 quotes 来源：")
    for record in db.get_articles(source="quotes", limit=3):
        print(f"  {record.title}")
    
    print("\n=== 测试搜索 ===")
    results = db.search_by_keyword("Moby")
    print(f"搜索 'Moby': {len(results)} 条")
    for r in results:
        print(f"  {r.title}")
    
    print("\n=== 统计 ===")
    stats = db.get_stats()
    print(f"总计: {stats['total_articles']} 条")
    print(f"按来源: {stats['by_source']}")

if __name__ == "__main__":
    test_database()