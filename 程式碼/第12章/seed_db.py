"""建立反哺實驗用的 SQLite 資料庫：20 個分類、2000 件商品。"""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "shop.db"
DB.unlink(missing_ok=True)
conn = sqlite3.connect(DB)
conn.execute("CREATE TABLE categories (id INTEGER PRIMARY KEY, name TEXT)")
conn.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, category_id INTEGER)")
conn.executemany("INSERT INTO categories VALUES (?, ?)",
                 [(i, f"鐵人分類 {i:02d}") for i in range(1, 21)])
conn.executemany("INSERT INTO products VALUES (?, ?, ?)",
                 [(i, f"鐵人商城商品 {i:04d}", (i % 20) + 1) for i in range(1, 2001)])
conn.commit(); conn.close()
print(f"資料庫建立完成：20 個分類、2000 件商品 → {DB.name}")
