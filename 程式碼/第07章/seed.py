"""為第 7 章鐵人商城播種：1,000 位賣家、100,000 件商品、約 300,000 則評價。

資料量刻意做大，好讓「深層分頁」（OFFSET 99980）與「海量讀取」名副其實。
執行前請先以 docker compose 起好 PostgreSQL（見 README）。

    python seed.py
"""
import asyncio
import random

import asyncpg

DSN = "postgresql://postgres:demo@127.0.0.1:55432/shop"
CATEGORIES = ["3C", "服飾", "居家", "食品", "運動", "書籍", "美妝", "玩具"]


async def main():
    conn = await asyncpg.connect(DSN)
    # 全部重建，確保可重複執行
    await conn.execute("""
        DROP TABLE IF EXISTS reviews;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS sellers;
    """)
    await conn.execute("""
        CREATE TABLE sellers (
            id   SERIAL PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE TABLE products (
            id        SERIAL PRIMARY KEY,
            name      TEXT NOT NULL,
            price     INT  NOT NULL,
            category  TEXT NOT NULL,
            seller_id INT  NOT NULL REFERENCES sellers(id),
            sales     INT  NOT NULL          -- 銷量，供「熱門排序」ORDER BY sales DESC
        );
        CREATE TABLE reviews (
            id         SERIAL PRIMARY KEY,
            product_id INT NOT NULL REFERENCES products(id),
            rating     INT NOT NULL,          -- 1~5 星
            comment    TEXT
        );
    """)

    rng = random.Random(42)   # 固定種子，讓每次播種可重現

    # 1,000 位賣家
    await conn.executemany(
        "INSERT INTO sellers(name) VALUES($1)",
        [(f"賣家-{i}",) for i in range(1, 1001)],
    )

    # 100,000 件商品，賣家與分類隨機、銷量隨機
    products = [
        (
            f"商品-{i}",
            rng.randint(50, 5000),                 # price
            rng.choice(CATEGORIES),                # category
            rng.randint(1, 1000),                  # seller_id
            rng.randint(0, 100000),                # sales
        )
        for i in range(1, 100_001)
    ]
    for s in range(0, len(products), 10000):
        await conn.executemany(
            "INSERT INTO products(name, price, category, seller_id, sales) "
            "VALUES($1,$2,$3,$4,$5)",
            products[s:s + 10000],
        )

    # 約 300,000 則評價：每件商品 0~6 則
    reviews = []
    for pid in range(1, 100_001):
        for _ in range(rng.randint(0, 6)):
            reviews.append((pid, rng.randint(1, 5), None))
    for s in range(0, len(reviews), 20000):
        await conn.executemany(
            "INSERT INTO reviews(product_id, rating, comment) VALUES($1,$2,$3)",
            reviews[s:s + 20000],
        )

    # 索引：賣家外鍵、熱門排序、分類篩選
    await conn.execute("CREATE INDEX idx_products_seller   ON products(seller_id);")
    await conn.execute("CREATE INDEX idx_products_sales    ON products(sales DESC);")
    await conn.execute("CREATE INDEX idx_products_category ON products(category);")
    await conn.execute("CREATE INDEX idx_reviews_product   ON reviews(product_id);")
    await conn.execute("ANALYZE;")

    ns = await conn.fetchval("SELECT count(*) FROM sellers")
    np = await conn.fetchval("SELECT count(*) FROM products")
    nr = await conn.fetchval("SELECT count(*) FROM reviews")
    print(f"seeded sellers={ns} products={np} reviews={nr}")
    await conn.close()


asyncio.run(main())
