#!/usr/bin/env python3
"""
SQLite数据库模块 - Day 2 下午
8GB内存优化：连接池复用、上下文管理器

┌─────────────────────────────────────────────────────────┐
│                    ArticleDatabase 设计目标                │
│  1. 数据持久化：内存中的Article → 磁盘SQLite              │
│  2. 自动去重：相同URL自动更新，不重复存储                  │
│  3. 流式查询：大数据量不爆内存，用yield惰性返回            │
│  4. 上下文安全：连接自动管理，异常自动回滚                 │
│  5. 可观测：操作日志记录，方便调试                        │
└─────────────────────────────────────────────────────────┘

                    核心设计模式
┌─────────────────────────────────────────────────────────┐
│  上下文管理器（@contextmanager）                           │
│  ├─ 自动获取连接                                          │
│  ├─ 成功自动提交（commit）                                │
│  ├─ 异常自动回滚（rollback）                               │
│  └─ 最终自动关闭（close）                                 │
│                                                          │
│  ON CONFLICT UPSERT（插入或更新）                          │
│  └─ URL唯一键冲突时，自动更新而非报错                      │
└─────────────────────────────────────────────────────────┘


| 模块                   | 核心设计     | 价值              |
| -------------------- | -------- | --------------- |
| `ArticleRecord`      | 数据库专用数据类 | 边界清晰，类型安全       |
| `@contextmanager`    | 连接自动管理   | 不泄露，异常安全        |
| `ON CONFLICT UPSERT` | 原子插入或更新  | 简洁去重，不报错        |
| `yield` 流式查询         | 惰性返回     | 大数据不爆内存         |
| `INDEX`              | 查询加速     | O(n) → O(log n) |



"""

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from typing import List, Optional, Iterator, Dict, Any
from datetime import datetime
from pathlib import Path
import json
from loguru import logger


@dataclass
class ArticleRecord:
    """数据库记录结构（与Article区分，避免混淆）"""
    id: Optional[int] = None
    title: str = ""
    url: str = ""
    content: str = ""
    source: str = ""           # 来源：httpbin/quotes/jsonplaceholder
    category: Optional[str] = None
    fetched_at: Optional[str] = None
    created_at: Optional[str] = None


class ArticleDatabase:
    """文章数据库管理器"""
    
    def __init__(self, db_path: Optional[Path] = None):
        # 默认路径：项目目录下的data文件夹
        if db_path is None:
            db_path = Path("~/ai-bootcamp/data/articles.db").expanduser()
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化表结构
        self._init_tables()
        logger.info(f"数据库初始化: {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """上下文管理器：自动提交/回滚"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 让查询结果可用字典方式访问
        
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库事务回滚: {e}")
            raise
        finally:
            conn.close()
    
    def _init_tables(self):
        """创建表结构（如果不存在）"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,      -- UNIQUE防止重复插入
                    content TEXT,
                    source TEXT,                    -- 来源标识
                    category TEXT,
                    fetched_at TIMESTAMP,           -- 抓取时间
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引，加速查询
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_source 
                ON articles(source)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_fetched_at 
                ON articles(fetched_at)
            """)
            
            logger.debug("表结构初始化完成")
    
    def insert_article(self, article: Dict[str, Any]) -> Optional[int]:
        """
        插入文章，自动去重（基于URL）
        返回：插入的ID，或None（如果失败）
        """
        with self._get_connection() as conn:
            try:
                cursor = conn.execute("""
                    INSERT INTO articles 
                    (title, url, content, source, fetched_at)
                    VALUES (:title, :url, :content, :source, :fetched_at)
                    ON CONFLICT(url) DO UPDATE SET
                        title=excluded.title,
                        content=excluded.content,
                        fetched_at=excluded.fetched_at
                    RETURNING id
                """, article)
                
                article_id = cursor.fetchone()[0]
                logger.success(f"插入/更新文章: id={article_id}, url={article['url'][:50]}...")
                return article_id
                
            except sqlite3.Error as e:
                logger.error(f"数据库插入失败: {e}")
                return None
    
    def get_articles(
        self,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Iterator[ArticleRecord]:
        """
        流式查询文章（内存友好）
        可筛选来源，支持分页
        """
        with self._get_connection() as conn:
            if source:
                cursor = conn.execute("""
                    SELECT * FROM articles 
                    WHERE source = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (source, limit, offset))
            else:
                cursor = conn.execute("""
                    SELECT * FROM articles 
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            # 使用yield，流式返回，不一次性加载全部
            for row in cursor:
                yield ArticleRecord(**dict(row))
    
    def search_by_keyword(self, keyword: str, limit: int = 50) -> List[ArticleRecord]:
        """全文搜索（简单版：标题和内容匹配）"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM articles 
                WHERE title LIKE ? OR content LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (f'%{keyword}%', f'%{keyword}%', limit))
            
            return [ArticleRecord(**dict(row)) for row in cursor]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._get_connection() as conn:
            # 总数量
            total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            
            # 按来源分组
            cursor = conn.execute("""
                SELECT source, COUNT(*) as count 
                FROM articles 
                GROUP BY source
            """)
            by_source = {row['source']: row['count'] for row in cursor}
            
            return {
                "total_articles": total,
                "by_source": by_source,
                "database_path": str(self.db_path)
            }
    
    def delete_old_articles(self, days: int = 30) -> int:
        """清理旧数据（维护用）"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM articles 
                WHERE fetched_at < datetime('now', ?)
            """, (f'-{days} days',))
            
            deleted = cursor.rowcount
            logger.info(f"清理旧数据: {deleted} 条")
            return deleted