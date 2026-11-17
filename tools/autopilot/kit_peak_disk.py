#!/usr/bin/env python3
"""kit_peak_disk (FLEET-OPS-R, COORD 11-17 FABLE-FLOW-0300 item 1): the gen disk floor from MEASURED kit disk, not a flat number.
refresh() takes the newest finished attempts of the kit-wave state (status FAIL/CANCELLED/PASS-like, a `work` dir on `gen_host`), du's up to N of them on their hosts
(one ssh per host) and keeps the p90 in GB with the sample size in <ap_dir>/kit_peak_gb.json.  floor() turns it into the admission floor:
    HARD (ot-run refuses below 50 GB) + ceil(1.25 x p90), clamped to [HARD + 10, gen_disk_max_gb (150)]
and falls back to the configured gen_disk_min_gb when there is no fresh measurement (file older than MAX_AGE_H or fewer than MIN_N samples).
Option gen_floor_measured: false turns it off.  Reads only; the one write is the json file."""
import json, math, os, time

HARD = 50
MIN_N = 5
MAX_AGE_H = 72.0
REFRESH_H = 3.0
FILE = "kit_peak_gb.json"
DONE = ("FAIL", "CANCELLED", "PASS", "SIGNED", "DONE")


def pick(state, n=24):
    """-> [(host, work dir)] newest finished attempts with a work dir"""
    rows = [r for r in ((state or {}).get("items") or {}).values()
            if isinstance(r, dict) and r.get("status") in DONE and r.get("work") and r.get("gen_host")]
    rows.sort(key=lambda r: float(r.get("updated") or 0), reverse=True)
    seen, out = set(), []
    for r in rows:
        k = (r["gen_host"], r["work"])
        if k in seen:
            continue
        seen.add(k); out.append(k)
        if len(out) >= n:
            break
    return out


def p90(xs):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(math.ceil(0.9 * len(xs))) - 1)] if xs else None


def measure(state, du, n=24):
    """du(host, [dirs]) -> {dir: bytes}; -> (p90 GB, samples) over the dirs that exist"""
    by = {}
    for h, d in pick(state, n):
        by.setdefault(h, []).append(d)
    gbs = []
    for h, ds in by.items():
        try:
            sizes = du(h, ds) or {}
        except Exception:
            continue
        gbs += [b / 2**30 for b in sizes.values() if b and b > 0]
    return (round(p90(gbs), 2) if gbs else None), len(gbs)


def refresh(ap_dir, state, du, now=None, force=False):
    now = now or time.time()
    p = os.path.join(ap_dir, FILE)
    try:
        if not force and now - os.path.getmtime(p) < REFRESH_H * 3600:
            return None
    except OSError:
        pass
    v, n = measure(state, du)
    if v is None:
        return None
    rec = dict(p90_gb=v, n=n, at=now)
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rec, f)
    os.replace(tmp, p)
    return rec


def load(ap_dir, now=None):
    now = now or time.time()
    try:
        d = json.load(open(os.path.join(ap_dir, FILE)))
        if now - float(d["at"]) <= MAX_AGE_H * 3600 and int(d["n"]) >= MIN_N:
            return float(d["p90_gb"])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def floor(cfg, base=60):
    """the gen disk floor in GB for this tick (cfg['_gen_peak_gb'] is load()'s value)"""
    base = int(cfg.get("gen_disk_min_gb", base))
    peak = cfg.get("_gen_peak_gb")
    if base <= 0 or cfg.get("gen_floor_measured") is False or not isinstance(peak, (int, float)):
        return base
    top = int(cfg.get("gen_disk_max_gb", 150))
    return int(max(HARD + 10, min(top, HARD + math.ceil(1.25 * peak))))
