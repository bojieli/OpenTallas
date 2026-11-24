"""adv_stale_keepout.py -- PRECHECK ADV-STALE-KEEPOUT (COORD 11-23, FABLE-RC-KV; advisory WARN, never a hold).

(1) KEEPOUT: clock.keepouts_um rectangles that are copies of landing bands from before the bands moved (KV pv_v2ne / pv_v5ne:
    stale keepouts blocked tap sites; the fourth derived section a re-floor leaves behind, after reset names, reset branches and
    early / forwarded-export taps).  A keepout carries no source link, so three static signals per type that has landing_contract.bands:
      EXACT   keepouts equal (<= 0.05 um) to a CURRENT band rect_um: current copies (fine)
      MOVED   a keepout that overlaps a current band with 0.3 <= IoU < 0.995: a displaced / resized copy (stale suspect)
      ALL-DISPLACED  as many keepouts as bands and NOT ONE equals a current band (pv_v2ne 16/16, pv_v5ne 49/49): the whole set is old geometry
    with a baseline plan (baseline= kw): STALE = a keepout equal to the BASELINE rect of a band that moved since, matching no current band.
(2) BINS: clock.sink_bins_file (the derived sink inventory) whose `n` differs by more than 10 % from the latest placed DB's register
    count in the PRECHECK flops cache (FABLE-RC-KV: pv bins 50k vs 139k placed on pv_v6n).  Needs the bins file under the tree and a
    placed kit in the cache; types without either are not judged.
findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
"""
import json
import sys
from pathlib import Path

CHECK = "ADV-STALE-KEEPOUT"
MAX_LINES = 20
TOL = 0.05
BINS_PCT = 0.10


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def eq(a, b, tol=TOL):
    return len(a) == 4 and len(b) == 4 and max(abs(x - y) for x, y in zip(a, b)) <= tol


def iou(a, b):
    w = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    h = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = w * h
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def bands_of(t):
    lc = ((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}
    return {k: v["rect_um"] for k, v in lc.items() if isinstance(v, dict) and isinstance(v.get("rect_um"), list) and len(v["rect_um"]) == 4}


def judge_keepouts(ko, bands, base_bands=None):
    """-> dict(exact, moved=[(keepout, band, iou)], all_displaced, stale=[(keepout, band)]) for one type"""
    exact = [k for k in ko if any(eq(k, r) for r in bands.values())]
    moved = []
    for k in ko:
        if k in exact or not bands:
            continue
        n, b = max(((n, iou(k, r)) for n, r in bands.items()), key=lambda x: x[1])
        if 0.3 <= b < 0.995:
            moved.append((k, n, b))
    stale = []
    if base_bands:
        gone = {n: r for n, r in base_bands.items() if n in bands and not eq(r, bands[n])}
        for k in ko:
            if k in exact:
                continue
            for n, r in gone.items():
                if eq(k, r):
                    stale.append((k, n))
                    break
    return dict(exact=len(exact), moved=moved, all_displaced=bool(ko) and len(ko) == len(bands) and not exact, stale=stale)


def judge_bins(n_bins, placed, pct=BINS_PCT):
    """-> None or the relative difference when the bins count is off the placed count by more than pct"""
    if not n_bins or not placed:
        return None
    d = abs(n_bins - placed) / placed
    return d if d > pct else None


def _placed_count(cache, tn, by_base, AT):
    """(count, how): newest placed kit register count of the type (flops cache entry from a place kit, else placed_bins)"""
    best = None
    for sec, key in (("flops", "flops"), ("placed_bins", "n_regs")):
        rec, basis = AT.lookup((cache.get(sec) or {}), tn, by_base)
        if rec and rec.get(key):
            if sec == "flops" and "place" not in str(rec.get("kit", "")) and "route" not in str(rec.get("kit", "")):
                continue
            c = (int(rec["ts"]) if str(rec.get("ts", "")).isdigit() else 0, int(rec[key]), f"{sec} {basis} {rec.get('kit', '')}")
            best = max(best, c) if best else c
    return (best[1], best[2]) if best else (None, None)


def _findings(raw, plan_path, tree=None, **kw):
    types = raw.get("partition_types") or {}
    used = {p.get("type") for p in raw.get("partitions") or [] if isinstance(p, dict)}
    base = kw.get("baseline")
    bt = {}
    if base:
        try:
            bt = (json.loads(Path(base).read_text()).get("partition_types") or {}) if not isinstance(base, dict) else (base.get("partition_types") or {})
        except (OSError, ValueError):
            bt = {}
    hits, nt, nflag, nweak = [], 0, 0, 0
    for tn, t in sorted(types.items()):
        if not isinstance(t, dict) or t.get("hard") is True or (used and tn not in used):
            continue
        ko = (t.get("clock") or {}).get("keepouts_um") or []
        bands = bands_of(t)
        if not ko or not bands:
            continue
        nt += 1
        r = judge_keepouts(ko, bands, bands_of(bt[tn]) if tn in bt else None)
        msg = []
        if r["stale"]:
            msg.append(f"STALE {len(r['stale'])} keepout(s) equal the BASELINE rect of a band that moved since ({', '.join(sorted({n for _, n in r['stale']})[:5])}): "
                       f"first {r['stale'][0][0]}")
        if r["all_displaced"]:
            msg.append(f"ALL-DISPLACED {len(ko)} keepouts for {len(bands)} bands and none equals a current band rect: the set is old band geometry")
        if r["moved"]:
            k, n, b = r["moved"][0]
            msg.append(f"MOVED {len(r['moved'])} keepout(s) overlap a current band without matching it (e.g. {k} vs band {n}, IoU {b:.2f})")
        if msg:
            strong = bool(r["stale"] or r["all_displaced"])
            nflag += strong
            nweak += not strong
            hits.append((0 if strong else 1, _w(f"{tn}: {'stale keepouts' if strong else 'INFO weak signal (MOVED only; unconfirmed vs KV-PV-EDGESTRIP, 2 true / 2 clean types known)'} ({r['exact']} of {len(ko)} keepouts match a current band): " + "; ".join(msg) +
                           "; they block tap sites; fix: regenerate clock.keepouts_um from the current bands")))
    nb = 0
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import adv_tap_load as AT
        cache, _src = AT.load_cache(kw.get("flops_cache"))
    except Exception:  # noqa: BLE001
        AT, cache = None, None
    if cache and tree:
        by_base = {}
        for n in set(cache.get("flops") or {}) | set(cache.get("placed_bins") or {}):
            by_base.setdefault(AT.base_type(n), []).append(n)
        for tn, t in sorted(types.items()):
            if not isinstance(t, dict) or t.get("hard") is True or (used and tn not in used):
                continue
            f = (t.get("clock") or {}).get("sink_bins_file")
            if not f:
                continue
            p = Path(f) if Path(f).is_absolute() else Path(tree) / f
            try:
                n_bins = int(json.loads(p.read_text()).get("n") or 0)
            except (OSError, ValueError):
                continue
            placed, how = _placed_count(cache, tn, by_base, AT)
            d = judge_bins(n_bins, placed)
            if d is not None:
                nb += 1
                hits.append(_w(f"{tn}: BINS sink bins count {n_bins:,} vs latest placed {placed:,} ({how}) = {d * 100:.0f}% off (> {BINS_PCT * 100:.0f}%): "
                               f"density taps are sized on the wrong inventory; fix: re-derive {Path(f).name} from the placed kit (taps.py sink bins)"))
    hits = [h if isinstance(h, str) else h for h in hits]
    hits.sort(key=lambda h: h[0] if isinstance(h, tuple) else 2)
    hits = [h[1] if isinstance(h, tuple) else h for h in hits]
    out = hits[:MAX_LINES]
    out.append(_w("summary", f"{nflag} of {nt} types with band-derived keepouts flagged strong (ALL-DISPLACED / STALE), {nweak} MOVED-only INFO; {nb} types with sink bins >{BINS_PCT * 100:.0f}% off the placed count"
                             f"{'' if base else ' (no baseline given: STALE-vs-baseline not run)'}"))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None,
                       baseline=sys.argv[3] if len(sys.argv) > 3 else None):
        print(ln)
