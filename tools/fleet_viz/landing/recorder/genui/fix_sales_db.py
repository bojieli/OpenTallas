"""Post-process sales.db from make_sales_db.py (owner fixes 2026-10-09): realistic quotas, consistent launch / hire dates,
covering indexes for the BI queries, and nightly-style mart tables. usage: fix_sales_db.py sales.db"""
import sqlite3, random, datetime, sys
db = sqlite3.connect(sys.argv[1]); c = db.cursor()
# quotas: the rep's 2025 book (completed orders, net of discount) x 1.12 growth target x U(0.85, 1.35) -> 2026 YTD attainment ~54-94 % of annual, ~72-125 % prorated
random.seed(42)
rev = dict(c.execute("""SELECT cu.rep_id, SUM(oi.quantity*oi.unit_price*(1-o.discount_pct)) FROM orders o JOIN order_items oi ON oi.order_id=o.order_id
  JOIN customers cu ON cu.customer_id=o.customer_id WHERE o.order_date BETWEEN '2025-01-01' AND '2025-12-31' AND o.status NOT IN ('cancelled','returned') GROUP BY cu.rep_id""").fetchall())
for rep, r in rev.items(): c.execute('UPDATE sales_reps SET quota_usd=? WHERE rep_id=?', (round(r * 1.12 * random.uniform(0.85, 1.35) / 10000) * 10000, rep))
# no product sold before its launch, no rep hired after a customer they own signed up
random.seed(43)
for pid, first in c.execute("select oi.product_id, min(o.order_date) from order_items oi join orders o using(order_id) group by 1").fetchall():
    (l,) = c.execute('select launched from products where product_id=?', (pid,)).fetchone()
    if first < l: c.execute('update products set launched=? where product_id=?', ((datetime.date.fromisoformat(first) - datetime.timedelta(days=random.randint(5, 90))).isoformat(), pid))
for rid, first in c.execute("select rep_id, min(signup_date) from customers group by 1").fetchall():
    (h,) = c.execute('select hired from sales_reps where rep_id=?', (rid,)).fetchone()
    if first < h: c.execute('update sales_reps set hired=? where rep_id=?', ((datetime.date.fromisoformat(first) - datetime.timedelta(days=random.randint(30, 400))).isoformat(), rid))
db.commit()
db.executescript("""
DROP INDEX IF EXISTS ix_orders_date; DROP INDEX IF EXISTS ix_orders_customer; DROP INDEX IF EXISTS ix_items_order;
CREATE INDEX ix_orders_date_cov ON orders(order_date, status, customer_id, discount_pct, channel);
CREATE INDEX ix_orders_customer_date ON orders(customer_id, order_date, status);
CREATE INDEX ix_items_order_cov ON order_items(order_id, product_id, quantity, unit_price);
CREATE INDEX ix_customers_rep ON customers(rep_id, region_id, segment);
CREATE INDEX ix_customers_signup ON customers(signup_date, segment, region_id);
CREATE TABLE mart_daily AS
  SELECT o.order_date AS day, cu.region_id, cu.segment, o.channel, cu.rep_id,
         COUNT(*) AS orders, SUM(x.units) AS units, ROUND(SUM(x.gross * (1 - o.discount_pct)), 2) AS revenue, ROUND(SUM(x.cost), 2) AS cost,
         ROUND(SUM(x.gross * o.discount_pct), 2) AS discount_usd
  FROM orders o JOIN customers cu ON cu.customer_id = o.customer_id
  JOIN (SELECT oi.order_id, SUM(oi.quantity) units, SUM(oi.quantity * oi.unit_price) gross, SUM(oi.quantity * p.unit_cost) cost
        FROM order_items oi JOIN products p ON p.product_id = oi.product_id GROUP BY oi.order_id) x ON x.order_id = o.order_id
  WHERE o.status NOT IN ('cancelled', 'returned') GROUP BY 1, 2, 3, 4, 5;
CREATE TABLE mart_daily_category AS
  SELECT o.order_date AS day, cu.region_id, cu.segment, p.category, p.subcategory,
         COUNT(DISTINCT o.order_id) AS orders, SUM(oi.quantity) AS units, ROUND(SUM(oi.quantity * oi.unit_price * (1 - o.discount_pct)), 2) AS revenue,
         ROUND(SUM(oi.quantity * p.unit_cost), 2) AS cost
  FROM orders o JOIN order_items oi ON oi.order_id = o.order_id JOIN products p ON p.product_id = oi.product_id JOIN customers cu ON cu.customer_id = o.customer_id
  WHERE o.status NOT IN ('cancelled', 'returned') GROUP BY 1, 2, 3, 4, 5;
CREATE TABLE mart_customer AS
  SELECT cu.customer_id, cu.segment, cu.region_id, cu.rep_id, cu.signup_date, MIN(o.order_date) AS first_order, MAX(o.order_date) AS last_order,
         COUNT(*) AS orders, ROUND(SUM(m.gross * (1 - o.discount_pct)), 2) AS revenue
  FROM customers cu JOIN orders o ON o.customer_id = cu.customer_id
  JOIN (SELECT oi.order_id, SUM(oi.quantity * oi.unit_price) gross FROM order_items oi GROUP BY oi.order_id) m ON m.order_id = o.order_id
  WHERE o.status NOT IN ('cancelled', 'returned') GROUP BY cu.customer_id;
CREATE INDEX ix_md_day ON mart_daily(day, region_id, segment, channel, rep_id, orders, revenue, cost);
CREATE INDEX ix_mdc_day ON mart_daily_category(day, category, region_id, segment, revenue, cost, units);
CREATE INDEX ix_mc_first ON mart_customer(first_order, segment, region_id);
CREATE INDEX ix_mc_signup ON mart_customer(signup_date, segment, region_id);
ANALYZE;""")
db.commit(); db.execute('VACUUM'); db.close()
