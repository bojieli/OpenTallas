#!/usr/bin/env python3
"""loadcap_dryrun.py (FLEET-ADMIT-CAP 11-25): read-only.  On this host, which ot-heavy launchers that are queued NOW would the LOADCAP_FRESH_1125
rule hold?  Prints host load / cap, fresh admits, and per waiter: class, declared threads, old verdict (load1 >= cap) vs new (load1 + fresh + own > cap).
Also counts non-die admits of the last 3 h whose own burst (admits of the prior LOAD_CAP_FRESH_S + own threads) alone exceeded the cap."""
import glob, os, re, sys, time
D = "/var/tmp/ot-heavy"; FRESH = 180
def rd(p):
    try: return open(p, errors="replace").read()
    except OSError: return ""
conf = rd("/etc/ot-heavy.conf")
def cv(k, d):
    m = re.findall(rf"^{k}=([0-9.]+)", conf, re.M); return float(m[-1]) if m else d
n = os.cpu_count(); f = cv("LOAD_CAP_FACTOR", 1.2); sl = cv("DIE_SLICE_CORES", 0); cf = cv("LOAD_CAP_CRIT_FACTOR", 2.0)
cap = f * max(1, n - sl); capc = cf * max(1, n - sl)
l1 = float(rd("/proc/loadavg").split()[0]); now = time.time()
thr = {}
for p in glob.glob(D + "/thr.*"):
    try: thr[p[len(D) + 5:]] = (os.stat(p).st_mtime, int(rd(p).strip() or 0))
    except (OSError, ValueError): pass
fresh = sum(t for m, t in thr.values() if now - m <= FRESH)
held = tot = 0; rows = []
for p in os.listdir("/proc"):
    if not p.isdigit(): continue
    a = rd(f"/proc/{p}/cmdline").split("\0")
    if len(a) < 4 or a[1:2] != ["/usr/local/bin/ot-heavy"] or "--mem" not in a[:8]: continue
    if glob.glob(f"{D}/res.oth-*-{p}-*"): continue          # already admitted
    env = dict(e.split("=", 1) for e in rd(f"/proc/{p}/environ").split("\0") if "=" in e)
    prio = env.get("OT_HEAVY_PRIO", ""); crit = env.get("OT_HEAVY_CPU") == "crit" or env.get("OT_HEAVY_DIRECT") == "1"
    try: own = int(env.get("OT_HEAVY_THREADS", 8))
    except ValueError: own = 8
    die = prio in ("die", "plan"); c = capc if crit else cap
    old = (not crit and not die and l1 >= f * n and f > 0)
    new = (not die and l1 + fresh + own > c and l1 + fresh > 0)
    tot += 1; held += new
    rows.append((own, "die" if die else ("crit" if crit else "kit"), old, new, " ".join(a[a.index("--") + 1:][:3])[:70]))
print(f"{os.uname().nodename}: load1 {l1:.0f} cap {cap:.0f} (crit {capc:.0f}) fresh {fresh} threads; queued {tot}: old rule holds {sum(r[2] for r in rows)}, new rule holds {held}, die/plan pass {sum(r[1]=='die' for r in rows)}")
for r in rows[:4]: print("   ", r)
# replay: recent non-die admits
adm = [(m, t, u) for u, (m, t) in thr.items() if now - m <= 10800]
bad = 0
for m, t, u in adm:
    pr = sum(tt for mm, tt, uu in adm if uu != u and 0 < m - mm <= FRESH)
    bad += (pr + t > cap)
print(f"    last 3h: {len(adm)} admits, {bad} arrived when earlier admits of the prior {FRESH}s + own threads already exceeded the cap")
