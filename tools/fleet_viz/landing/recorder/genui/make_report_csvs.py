"""CSV inputs of the report-editing case (run inside edit/data): web_analytics.csv, project_hours.csv, inventory.csv."""
import random, datetime, math, csv
random.seed(11)
pages = ['/', '/pricing', '/blog/what-is-rag', '/docs/quickstart', '/docs/api', '/careers', '/blog/benchmarks-2026', '/signup', '/contact', '/changelog']
pw = [0.24, 0.12, 0.10, 0.14, 0.11, 0.04, 0.09, 0.08, 0.03, 0.05]
with open('web_analytics.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['date', 'page', 'device', 'country', 'visits', 'bounces', 'avg_seconds', 'signups'])
    d = datetime.date(2026, 1, 1)
    while d <= datetime.date(2026, 9, 30):
        base = 5200 * math.exp(0.004 * (d - datetime.date(2026, 1, 1)).days) * (0.7 if d.weekday() >= 5 else 1) * (2.4 if d == datetime.date(2026, 6, 17) else 1)
        for p, x in zip(pages, pw):
            for dev, dx in (('mobile', 0.46), ('desktop', 0.49), ('tablet', 0.05)):
                for c, cx in (('US', 0.52), ('DE', 0.12), ('IN', 0.14), ('GB', 0.10), ('BR', 0.12)):
                    v = max(0, int(random.gauss(base * x * dx * cx, base * x * dx * cx * 0.15)))
                    b = int(v * min(0.95, max(0.1, random.gauss(0.62 if dev == 'mobile' else 0.44, 0.05))))
                    s = sum(random.random() < (0.031 if p == '/signup' else 0.004) for _ in range(v)) if v < 400 else int(v * (0.031 if p == '/signup' else 0.004))
                    w.writerow([d.isoformat(), p, dev, c, v, b, round(random.gauss(48 if dev == 'mobile' else 95, 12), 1), s])
        d += datetime.timedelta(days=1)
people = ['Ana Ruiz', 'Ben Cho', 'Dara Singh', 'Eli Novak', 'Fatima Zahra', 'Gus Moreau', 'Hana Kim', 'Ivo Petrov']
projects = ['Atlas migration', 'Billing v2', 'Mobile app', 'Data platform', 'Support rotation']
with open('project_hours.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['week_start', 'person', 'project', 'hours'])
    d = datetime.date(2026, 1, 5)
    while d <= datetime.date(2026, 9, 28):
        for p in people:
            tot = random.gauss(40, 4) + (9 if p == 'Gus Moreau' and d.month in (7, 8, 9) else 0) + (-40 if random.random() < 0.06 else 0)
            mix = [random.random() ** 2 for _ in projects]; s = sum(mix)
            for pr, m in zip(projects, mix):
                h = round(max(0, tot) * m / s, 1)
                if h >= 0.5: w.writerow([d.isoformat(), p, pr, h])
        d += datetime.timedelta(days=7)
cats = ['Fasteners', 'Electrical', 'Plumbing', 'Tools', 'Safety', 'Paint']
with open('inventory.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['sku', 'item', 'category', 'warehouse', 'on_hand', 'reorder_point', 'avg_daily_use', 'unit_cost', 'supplier', 'lead_time_days'])
    for i in range(140):
        cat = random.choice(cats); use = round(random.lognormvariate(1.2, 0.9), 1)
        rp = int(use * random.choice([10, 14, 21])); oh = max(0, int(random.gauss(rp * 1.6, rp * 0.9)))
        w.writerow([f'{cat[:2].upper()}-{4000 + i}', f'{cat} item {random.choice(["A","B","C","D"])}{random.randint(10,99)}', cat, random.choice(['Reno NV', 'Columbus OH', 'Allentown PA']),
                    oh, rp, use, round(random.lognormvariate(2, 1), 2), random.choice(['Grainger', 'Fastenal', 'Uline', 'McMaster', 'HD Supply']), random.choice([3, 5, 7, 10, 14, 21])])
