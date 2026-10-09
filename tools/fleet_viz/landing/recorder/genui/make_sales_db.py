"""Synthetic but realistic sales database: regions, sales_reps, customers, products, orders (~1M), order_items."""
import sqlite3, random, math, datetime, sys, os
random.seed(20261009)
path = sys.argv[1]
if os.path.exists(path): os.remove(path)
db = sqlite3.connect(path); c = db.cursor()
c.executescript("""
CREATE TABLE regions(region_id INTEGER PRIMARY KEY, name TEXT NOT NULL, country TEXT NOT NULL, timezone TEXT);
CREATE TABLE sales_reps(rep_id INTEGER PRIMARY KEY, name TEXT NOT NULL, region_id INTEGER REFERENCES regions, hired DATE, quota_usd REAL);
CREATE TABLE customers(customer_id INTEGER PRIMARY KEY, name TEXT NOT NULL, segment TEXT CHECK(segment IN ('Consumer','Small Business','Enterprise')),
  region_id INTEGER REFERENCES regions, city TEXT, signup_date DATE, rep_id INTEGER REFERENCES sales_reps);
CREATE TABLE products(product_id INTEGER PRIMARY KEY, sku TEXT UNIQUE, name TEXT NOT NULL, category TEXT, subcategory TEXT, list_price REAL, unit_cost REAL, launched DATE);
CREATE TABLE orders(order_id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers, order_date DATE, channel TEXT, status TEXT, ship_days INTEGER, discount_pct REAL);
CREATE TABLE order_items(order_id INTEGER REFERENCES orders, product_id INTEGER REFERENCES products, quantity INTEGER, unit_price REAL);
""")
regions = [('Pacific Northwest','US','America/Los_Angeles'),('California','US','America/Los_Angeles'),('Mountain','US','America/Denver'),('Texas','US','America/Chicago'),
           ('Midwest','US','America/Chicago'),('Southeast','US','America/New_York'),('Northeast','US','America/New_York'),('Ontario','CA','America/Toronto'),
           ('British Columbia','CA','America/Vancouver'),('UK & Ireland','GB','Europe/London'),('DACH','DE','Europe/Berlin'),('Nordics','SE','Europe/Stockholm')]
rw = [0.07,0.16,0.06,0.10,0.11,0.12,0.15,0.05,0.03,0.07,0.06,0.02]
c.executemany('INSERT INTO regions(name,country,timezone) VALUES (?,?,?)', regions)
cities = {1:['Seattle','Portland','Spokane','Tacoma'],2:['Los Angeles','San Francisco','San Diego','San Jose','Sacramento'],3:['Denver','Salt Lake City','Boise','Phoenix'],
          4:['Austin','Dallas','Houston','San Antonio'],5:['Chicago','Minneapolis','Detroit','Columbus','St. Louis'],6:['Atlanta','Miami','Charlotte','Nashville','Tampa'],
          7:['New York','Boston','Philadelphia','Pittsburgh','Hartford'],8:['Toronto','Ottawa','Hamilton'],9:['Vancouver','Victoria'],10:['London','Manchester','Dublin','Leeds'],
          11:['Berlin','Munich','Zurich','Vienna','Hamburg'],12:['Stockholm','Oslo','Copenhagen','Helsinki']}
first = 'Ava Ben Chloe Dev Elena Farid Grace Hiro Isla Jonas Kemi Liam Maya Noah Olu Priya Quinn Rafael Sofia Tariq Uma Victor Wen Xavi Yara Zane'.split()
last = 'Abara Becker Chen Diaz Eriksen Fischer Garcia Haddad Ito Jensen Kowalski Lopez Murphy Nakamura Okafor Patel Quist Rossi Silva Tanaka Usman Varga Walsh Xu Young Zhou'.split()
reps = []
for r in range(1, 13):
    for k in range(max(2, round(rw[r-1] * 40))):
        hired = datetime.date(2016, 1, 1) + datetime.timedelta(days=random.randint(0, 3000))
        reps.append((f'{random.choice(first)} {random.choice(last)}', r, hired.isoformat(), round(random.choice([600, 750, 900, 1200, 1500]) * 1000.0, 0)))
c.executemany('INSERT INTO sales_reps(name,region_id,hired,quota_usd) VALUES (?,?,?,?)', reps)
reps_by_region = {}
for i, rp in enumerate(reps, 1): reps_by_region.setdefault(rp[1], []).append(i)
cats = {'Laptops':(['Ultrabook','Workstation','Chromebook'],(549,2899)), 'Monitors':(['27-inch','32-inch','Ultrawide'],(179,1299)),
        'Peripherals':(['Keyboards','Mice','Webcams','Headsets'],(19,249)), 'Networking':(['Routers','Switches','Access Points'],(59,899)),
        'Storage':(['SSD','NAS','External HDD'],(49,1199)), 'Software':(['Productivity','Security','Design'],(29,699)),
        'Services':(['Extended Warranty','Setup & Install','Support Plan'],(39,1499)), 'Accessories':(['Cables','Docks','Bags','Stands'],(9,329))}
adj = 'Pro Air Max Lite Flex One Edge Core Prime Nova Zen Studio'.split(); prods = []
for cat, (subs, (lo, hi)) in cats.items():
    for sub in subs:
        for k in range(random.randint(6, 14)):
            price = round(math.exp(random.uniform(math.log(lo), math.log(hi))), -0) - 0.01
            margin = {'Software':0.82,'Services':0.65}.get(cat, random.uniform(0.18, 0.42))
            launched = datetime.date(2019, 1, 1) + datetime.timedelta(days=random.randint(0, 2400))
            prods.append((f'{cat[:3].upper()}-{len(prods)+1001}', f'{sub} {random.choice(adj)} {random.randint(2,9)}{random.choice("0005")}', cat, sub, price, round(price * (1 - margin), 2), launched.isoformat()))
c.executemany('INSERT INTO products(sku,name,category,subcategory,list_price,unit_cost,launched) VALUES (?,?,?,?,?,?,?)', prods)
NP = len(prods); pop = [1.0 / (i + 1) ** 0.9 for i in range(NP)]; random.shuffle(pop)  # Zipf-ish popularity
start, end = datetime.date(2022, 1, 1), datetime.date(2026, 9, 30)
NC = 120000; custs = []
co = 'Acme Northwind Contoso Globex Initech Umbrella Stark Wayne Hooli Vandelay Soylent Tyrell Wonka Cyberdyne Aperture Massive Dynamic Gringotts Oceanic Pied'.split()
for i in range(NC):
    seg = random.choices(['Consumer','Small Business','Enterprise'], [0.62, 0.30, 0.08])[0]
    r = random.choices(range(1, 13), rw)[0]
    name = f'{random.choice(first)} {random.choice(last)}' if seg == 'Consumer' else f'{random.choice(co)} {random.choice(["Labs","Group","Partners","Holdings","Studio","Systems","Logistics","Health"])}'
    sd = start + datetime.timedelta(days=int(random.betavariate(1.3, 1.6) * ((end - start).days - 30)))
    custs.append((name, seg, r, random.choice(cities[r]), sd.isoformat(), random.choice(reps_by_region[r])))
c.executemany('INSERT INTO customers(name,segment,region_id,city,signup_date,rep_id) VALUES (?,?,?,?,?,?)', custs)
# orders: growth ~18%/yr, Q4 + Black Friday peak, back-to-school bump, weekday pattern; customer activity heavy-tailed
days = (end - start).days + 1; w = []
for d in range(days):
    dt = start + datetime.timedelta(days=d); t = d / 365.0
    s = math.exp(0.165 * t) * (1 + 0.35 * math.exp(-((dt.timetuple().tm_yday - 330) / 18) ** 2) + 0.12 * math.exp(-((dt.timetuple().tm_yday - 235) / 14) ** 2))
    s *= [1.08, 1.06, 1.05, 1.04, 1.0, 0.78, 0.72][dt.weekday()]
    if dt.month == 12 and dt.day > 24: s *= 0.6
    w.append(s)
W = sum(w); N = 1_000_000; counts = [int(round(N * x / W)) for x in w]
act = [random.paretovariate(1.6) for _ in range(NC)]
seg_mult = {'Consumer': 1.0, 'Small Business': 2.2, 'Enterprise': 5.0}
act = [a * seg_mult[cu[1]] for a, cu in zip(act, custs)]
signup = [datetime.date.fromisoformat(cu[4]) for cu in custs]
order_rows, item_rows = [], []; oid = 0
idx_sorted = sorted(range(NC), key=lambda i: signup[i]); import bisect
signup_sorted = [signup[i] for i in idx_sorted]
cum = []; s = 0
for i in idx_sorted: s += act[i]; cum.append(s)
chan = ['Web', 'Direct Sales', 'Partner', 'Marketplace']
for d, n in enumerate(counts):
    dt = start + datetime.timedelta(days=d); k = bisect.bisect_right(signup_sorted, dt)
    if k == 0: continue
    for _ in range(n):
        ci = idx_sorted[bisect.bisect_left(cum, random.random() * cum[k - 1])]; cu = custs[ci]; oid += 1
        ch = random.choices(chan, {'Consumer': [0.7, 0.02, 0.08, 0.2], 'Small Business': [0.45, 0.2, 0.25, 0.1], 'Enterprise': [0.1, 0.65, 0.25, 0.0]}[cu[1]])[0]
        st = random.choices(['delivered', 'shipped', 'cancelled', 'returned'], [0.9, 0.02, 0.05, 0.03])[0]
        if (end - dt).days < 7: st = random.choice(['shipped', 'processing', 'delivered'])
        disc = 0.0 if random.random() < 0.6 else round(random.choice([5, 10, 10, 15, 20, 25]) * (1.5 if cu[1] == 'Enterprise' else 1) / 100, 3)
        order_rows.append((oid, ci + 1, dt.isoformat(), ch, st, max(1, int(random.gauss(4 if cu[2] < 10 else 6, 1.6))), disc))
        for _ in range(min(12, 1 + int(random.expovariate(0.9 if cu[1] != 'Enterprise' else 0.35)))):
            p = random.choices(range(NP), pop)[0] if random.random() < 0.3 else int(random.paretovariate(1.1)) % NP
            q = 1 if cu[1] == 'Consumer' else max(1, int(random.expovariate(1 / (3 if cu[1] == 'Small Business' else 12))))
            item_rows.append((oid, p + 1, q, round(prods[p][4] * random.choice([1, 1, 1, 0.95, 0.9]), 2)))
    if len(order_rows) > 200000:
        c.executemany('INSERT INTO orders VALUES (?,?,?,?,?,?,?)', order_rows); c.executemany('INSERT INTO order_items VALUES (?,?,?,?)', item_rows); order_rows, item_rows = [], []
c.executemany('INSERT INTO orders VALUES (?,?,?,?,?,?,?)', order_rows); c.executemany('INSERT INTO order_items VALUES (?,?,?,?)', item_rows)
c.executescript("""CREATE INDEX ix_orders_date ON orders(order_date); CREATE INDEX ix_orders_customer ON orders(customer_id);
CREATE INDEX ix_items_order ON order_items(order_id); CREATE INDEX ix_items_product ON order_items(product_id); CREATE INDEX ix_customers_region ON customers(region_id);""")
db.commit()
for t in ['regions', 'sales_reps', 'customers', 'products', 'orders', 'order_items']: print(t, c.execute(f'select count(*) from {t}').fetchone()[0])
db.execute('VACUUM'); db.close()
