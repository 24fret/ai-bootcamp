"""
测试 main-challenge.py 中的代码分析器

运行方式（二选一）:
    cd day1/src
    pytest test_main_challenge.py -v
    或
    python test_main_challenge.py

依赖:
    需先安装 main-challenge.py 的依赖:
        pip install typer rich loguru
    使用 pytest 时:
        pip install pytest
"""

import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

# 从 main-challenge.py 加载模块（文件名含连字符，需用 importlib）
_src_dir = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "main_challenge",
    _src_dir / "main-challenge.py",
)
_main = importlib.util.module_from_spec(_spec)
sys.modules["main_challenge"] = _main
try:
    _spec.loader.exec_module(_main)
except ModuleNotFoundError as e:
    print("加载 main-challenge.py 失败，请先安装依赖:")
    print("  pip install typer rich loguru")
    print(f"  错误: {e}")
    sys.exit(1)

CodeAnalyzer = _main.CodeAnalyzer
CodeFile = _main.CodeFile
Largest_file = _main.Largest_file
asdict = _main.asdict


# ---------------------------------------------------------------------------
# 数据类与报告结构
# ---------------------------------------------------------------------------

class TestLargestFile(unittest.TestCase):
    """测试 Largest_file 数据类"""

    def test_create_and_asdict(self):
        obj = Largest_file(path="/tmp/foo.py", lines=100, size_kb=2.5)
        d = asdict(obj)
        self.assertEqual(d["path"], "/tmp/foo.py")
        self.assertEqual(d["lines"], 100)
        self.assertEqual(d["size_kb"], 2.5)


class TestCodeFile(unittest.TestCase):
    """测试 CodeFile 数据类（需要真实路径）"""

    def test_size_kb_and_is_recent(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.py"
            p.write_text("line1\nline2\n")
            mtime = time.time() - 86400
            os.utime(str(p), (mtime, mtime))  # 使用 os.utime，需要传入字符串路径
            cf = CodeFile(path=p, language="py", lines=2, last_modified=mtime)
            self.assertGreaterEqual(cf.size_kb, 0)
            self.assertTrue(cf.is_recent)


class TestCodeAnalyzer(unittest.TestCase):
    """测试 CodeAnalyzer 扫描与报告"""

    def test_scan_skips_hidden_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.py").write_text("x")
            (root / ".hidden").mkdir()
            (root / ".hidden" / "b.py").write_text("y")
            (root / "normal").mkdir()
            (root / "normal" / "c.py").write_text("z")
            analyzer = CodeAnalyzer(root)
            files = list(analyzer.scan(show_progress=False))
            paths = [str(f.path) for f in files]
            self.assertTrue(any("a.py" in p for p in paths))
            self.assertTrue(any("normal" in p and "c.py" in p for p in paths))
            self.assertFalse(any(".hidden" in p for p in paths))
            self.assertEqual(analyzer.stats["total_files"], 2)
            self.assertEqual(analyzer.stats["total_lines"], 2)

    def test_generate_report_structure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "small.py").write_text("a\nb\n")
            (root / "big.py").write_text("x\n" * 20)
            analyzer = CodeAnalyzer(root)
            report = analyzer.generate_report(top_n=5, show_progress=False)
            self.assertIn("summary", report)
            self.assertIn("largest_files", report)
            self.assertIn("recent_files", report)
            self.assertEqual(report["summary"]["total_files"], 2)
            self.assertEqual(report["summary"]["total_lines"], 22)
            self.assertLessEqual(len(report["largest_files"]), 5)
            for item in report["largest_files"]:
                self.assertIn("path", item)
                self.assertIn("lines", item)
                self.assertIn("size_kb", item)

    def test_largest_files_sorted_by_size_kb(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "tiny.py").write_text("1")
            (root / "large.py").write_text("x\n" * 100)
            analyzer = CodeAnalyzer(root)
            report = analyzer.generate_report(top_n=5, show_progress=False)
            sizes = [x["size_kb"] for x in report["largest_files"]]
            self.assertEqual(sizes, sorted(sizes, reverse=True))

    def test_recent_files_sorted_by_time(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "old.py").write_text("a")
            (root / "new.py").write_text("b")
            old_f = root / "old.py"
            new_f = root / "new.py"
            t_old = time.time() - 86400 * 2
            t_new = time.time() - 86400 * 0.5
            os.utime(str(old_f), (t_old, t_old))  # 使用 os.utime，需要传入字符串路径
            os.utime(str(new_f), (t_new, t_new))
            analyzer = CodeAnalyzer(root)
            report = analyzer.generate_report(top_n=5, show_progress=False)
            paths = report["recent_files"]
            if len(paths) >= 2:
                idx_new = next(i for i, p in enumerate(paths) if "new.py" in p)
                idx_old = next(i for i, p in enumerate(paths) if "old.py" in p)
                self.assertLessEqual(idx_new, idx_old)

    def test_report_json_serializable(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "one.py").write_text("1")
            analyzer = CodeAnalyzer(root)
            report = analyzer.generate_report(top_n=5, show_progress=False)
            s = json.dumps(report, indent=2, ensure_ascii=False)
            self.assertIn("summary", s)
            self.assertIn("largest_files", s)


def run_pytest():
    """若已安装 pytest，用 pytest 运行（支持 -v 等参数）"""
    try:
        import pytest
        return pytest.main([__file__, "-v"])
    except ImportError:
        return None


if __name__ == "__main__":
    # 优先用 pytest（若已安装），否则用 unittest
    exit_code = run_pytest()
    if exit_code is not None:
        sys.exit(exit_code)
    unittest.main(verbosity=2)
