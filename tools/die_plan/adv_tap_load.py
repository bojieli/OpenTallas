#!/usr/bin/env python3
"""adv_tap_load.py -- PRECHECK-R2 static advisory ADV-TAP-LOAD (COORD 11-22 18:1x, class TAP-SOFTFLOP; an estimator,
never a gate).

The plan sizes a type's clock taps from its PLANNED sink model (taps.sink_sites: face / ft / station registers,
clock.sink_sites_um, clock.sink_bins_file, soft_reg_banks, control sinks).  Where the model misses the soft-logic flops
the taps are sized for a fraction of the real load (S81 kv_leaf t5: planned 1,099 max per tap vs ~8,000 placed).
Per placed soft type with a clock:

  netlist flops  = DFF cells of the kit's synthesized top (1_2_yosys.v; kit_scan FOLD state netlist_flops; soft logic
                   incl., hard-core internals excluded), exact type else newest kit of the base type (__cl/__pv stripped)
  planned sinks  = taps.sink_sites(P, type) weights (exact, under a time budget), else a cheap count (bus bits + ft bits
                   x stations + station bits x regs + sink_sites_um + sink bins + soft_reg_bank bits), marked '~'
  taps           = clock.taps (explicit), the R4 pitch grid + clock.added_taps (grid+explicit / grid), unlegalised

  WARN when netlist flops > 1.3 x planned sinks, or netlist flops / taps > 1.3 x the planned max tap load (nearest
  tap, as taps.tap_loads), and say whether the taps can hold the netlist at all (flops / taps vs tap_max_sinks).
  PLACED: where a placed register dump of a kit of this logic exists on the same outline (kit_scan placed_raw regs,
  binned), the registers go to the CURRENT taps by nearest tap; any tap over 1,500 is warned (else the kit's own
  per-tap load from its placed scan is quoted, on the kit's taps).

Caches (built by harvest_flops.py on each gen host + merge_flops.py): {flops, placed, placed_bins}.

    findings(raw, plan_path, tree=None, flops_cache=None|path|dict, ratio=1.3, placed_max=1500, budget_s=35)
"""
import contextlib
import io
import json
import math
import os
import re
import sys
import time
from pathlib import Path

CHECK = "TAP-LOAD"
RATIO = 1.3
PLACED_MAX = 1500
BUDGET_S = 25.0
MAX_LINES = 20
SUFFIX = re.compile(r"(?:__(?:cl|pv)[0-9a-f]{6,})+$")
CACHE_ENV = "OT_ADV_FLOPS_CACHE"
CACHE_DEFAULTS = ("adv_cache/flops_cache.json",
                  "/srv/opentallas-scratch2/claude/precheck-cache/flops_cache.json")


def _w(obj, msg):
    return f"WARN ADV-{CHECK} {obj}: {msg}"


def base_type(tn):
    return SUFFIX.sub("", tn)


def load_cache(src):
    if isinstance(src, dict):
        return src, "<dict>"
    cands = [src] if src else []
    if os.environ.get(CACHE_ENV):
        cands.insert(0, os.environ[CACHE_ENV])
    here = Path(__file__).resolve().parent
    cands += [str(here / CACHE_DEFAULTS[0]), CACHE_DEFAULTS[1]]
    for c in cands:
        if c and os.path.isfile(c):
            with open(c) as f:
                return json.load(f), c
    return None, None


def lookup(sec, tn, by_base):
    """(record, basis) from one cache section: exact type, else the newest kit of the same base type."""
    if tn in sec:
        return sec[tn], "kit"
    c = [n for n in by_base.get(base_type(tn), []) if n in sec and n != tn]
    if c:
        n = max(c, key=lambda k: sec[k].get("ts", 0))
        return sec[n], f"base kit {n}"
    return None, None


def tap_pitch(raw, ck):
    p = float(ck.get("tap_pitch_um", (raw.get("budgets") or {}).get("tap_pitch_um", 400.0)))
    if ck.get("tap_grid") is not None and ck.get("tap_mode", "grid") in ("grid", "grid+sinks", "sinks"):
        p = min(p, float(ck["tap_grid"].get("pitch_um", 300.0)))
    return p


def cheap_taps(raw, t):
    """[(name, x, y)] the type's local clock taps without legalisation (schema.tap_grid geometry, cores excluded);
    None for a mode whose taps are solved (density without a stored table)."""
    ck = t.get("clock") or {}
    mode = ck.get("tap_mode")
    table = [(p["name"], float(p["xy"][0]), float(p["xy"][1])) for p in ck.get("taps") or []
             if isinstance(p, dict) and p.get("kind") not in ("core", "glue") and p.get("xy")]
    if mode == "explicit":
        return table or None
    if mode in ("density", "grid+sinks", "sinks"):
        return None                 # solved from the sink inventory (taps.density_taps / sink_taps): not static
    w, h = map(float, t["outline_um"])
    pitch = tap_pitch(raw, ck)
    nx, ny = max(1, math.ceil(w / pitch - 1e-9)), max(1, math.ceil(h / pitch - 1e-9))
    if nx == 1 and ny == 1:
        x, y = ck.get("tap_um") or [w / 2, h / 2]
        out = [("clk", float(x), float(y))]
    else:
        out = []
        for j in range(ny):
            for i in range(nx):
                k = len(out)
                out.append(("clk" if k == 0 else f"clk_t{k}", (i + 0.5) * w / nx, (j + 0.5) * h / ny))
    for p in ck.get("added_taps") or []:
        if isinstance(p, dict) and p.get("xy"):
            out.append((p["name"], float(p["xy"][0]), float(p["xy"][1])))
    return out


def cheap_planned(t):
    """a fast count of the planned sink model (taps.planned_sinks + sink_sites): every bus bit registers at its face,
    an ft slot bit has `stations` registers, an internal station row bits x regs, plus the plan's sink inventory."""
    ck = t.get("clock") or {}
    slots = {s.get("name") for s in t.get("ft_slots") or []}
    n = 0.0
    for b in t.get("buses") or []:
        if b.get("name") not in slots:
            n += float(b.get("width") or 0)
    for s in t.get("ft_slots") or []:
        n += float(s.get("width") or 0) * max(1, int(s.get("stations") or 1))
    for e in t.get("internal_stations") or []:
        n += float(e.get("bits") or 1) * len(e.get("regs_um") or [])
    n += sum(float(r[2]) if len(r) > 2 else 1.0 for r in ck.get("sink_sites_um") or [])
    for bk in ck.get("soft_reg_banks") or []:
        n += len(bk.get("bit_sites_um") or [])
    return n


def nearest_loads(taps, pts):
    """per-tap summed weight under the nearest-tap rule (Manhattan, ties -> lower index, as taps.tap_loads)."""
    load = [0.0] * len(taps)
    T = [(x, y) for _, x, y in taps]
    try:
        import numpy as np          # optional (taps.py needs it anyway); same argmin tie rule
        if pts:
            A = np.asarray(pts, dtype=float)
            TX, TY = np.asarray([p[0] for p in T]), np.asarray([p[1] for p in T])
            for i in range(0, len(A), 4096):
                B = A[i:i + 4096]
                j = (np.abs(B[:, :1] - TX[None, :]) + np.abs(B[:, 1:2] - TY[None, :])).argmin(axis=1)
                acc = np.bincount(j, weights=B[:, 2], minlength=len(T))
                for k in range(len(T)):
                    load[k] += float(acc[k])
        return load
    except ImportError:
        pass
    if len(pts) * len(T) > 2_000_000:
        pts = binned(pts, 20.0)
    rng = range(len(T))
    for x, y, wt in pts:
        j = min(rng, key=lambda i: (abs(x - T[i][0]) + abs(y - T[i][1]), i))
        load[j] += wt
    return load


def binned(pts, b=5.0):
    """pts [(x, y, w)] merged onto a b-um lattice (bin centres): the nearest-tap split changes only at bin edges."""
    acc = {}
    for x, y, wt in pts:
        k = (int(x // b), int(y // b))
        acc[k] = acc.get(k, 0.0) + wt
    return [((i + 0.5) * b, (j + 0.5) * b, v) for (i, j), v in acc.items()]


class Exact:
    """taps.sink_sites on the plan, with the tools of the tree (or the module's own dir), lazily."""

    def __init__(self, raw, plan_path, tree):
        self.ok, self.why, self.P, self.T = False, "", None, None
        dirs = []
        if tree:
            dirs.append(str(Path(tree) / "tools" / "die_plan"))
        dirs.append(str(Path(__file__).resolve().parent))
        for d in dirs:
            if (Path(d) / "taps.py").is_file() and (Path(d) / "schema.py").is_file():
                try:
                    sys.path.insert(0, d)
                    import schema as S  # noqa: E402
                    import taps as T  # noqa: E402
                    self.P, self.T, self.dir = S.Plan(raw, str(plan_path)), T, d
                    self.ok = True
                    return
                except Exception as e:  # noqa: BLE001
                    self.why = f"{type(e).__name__}: {str(e)[:80]}"
                finally:
                    if sys.path and sys.path[0] == d:
                        sys.path.pop(0)
        self.why = self.why or "no tools/die_plan (schema.py, taps.py)"

    def sinks(self, tn):
        sys.path.insert(0, self.dir)          # taps.py imports gen_phys / ft_full_stage / reset_tree lazily
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return self.T.sink_sites(self.P, tn)
        finally:
            if sys.path and sys.path[0] == self.dir:
                sys.path.pop(0)


def _fmt(v):
    return f"{v:,.0f}"


def _findings(raw, plan_path, tree=None, flops_cache=None, ratio=RATIO, placed_max=PLACED_MAX, budget_s=BUDGET_S,
              exact=True, dump=None, planned_sinks=None, **_kw):
    t_start = time.time()
    P = raw.get("partition_types") or {}
    if not P:
        return [_w("not checked", "plan has no partition_types")]
    cache, src = load_cache(flops_cache)
    if cache is None:
        return [_w("not checked", f"no netlist flop cache (set {CACHE_ENV} or run harvest_flops.py + merge_flops.py)")]
    fl, pl, pb = cache.get("flops") or {}, cache.get("placed") or {}, cache.get("placed_bins") or {}
    by_base = {}
    for n in set(fl) | set(pl) | set(pb):
        by_base.setdefault(base_type(n), []).append(n)
    placed = {p.get("type") for p in raw.get("partitions") or [] if isinstance(p, dict)}
    rows, n_cmp, n_unmeas, n_notap = [], 0, 0, 0
    for tn in sorted(P):
        t = P[tn]
        if (placed and tn not in placed) or t.get("hard") or not t.get("outline_um") or not t.get("clock"):
            continue
        frec, fbasis = lookup(fl, tn, by_base)
        prec_b, pbasis = lookup(pb, tn, by_base)
        if not frec and not prec_b:
            n_unmeas += 1
            continue
        taps = cheap_taps(raw, t)
        if not taps:
            n_notap += 1
            if not (t.get("clock") or {}).get("sink_bins_file"):
                continue
            taps = []
        rows.append(dict(tn=tn, t=t, frec=frec, fbasis=fbasis, prec_b=prec_b, pbasis=pbasis, taps=taps,
                         cheap=cheap_planned(t), flops=(frec or {}).get("flops") or (prec_b or {}).get("n_regs")))
    # exact planned sinks (sink coordinates for the per-tap rule) under the time budget, highest netlist flops/tap first
    ex = Exact(raw, plan_path, tree) if exact and rows and not (planned_sinks and len(planned_sinks) >= len(rows)) else None

    def prio(r):     # the per-tap rule can only fire where the netlist load per tap is high: those first
        return -(r["flops"] or 0) / max(1, len(r["taps"]))
    n_exact = 0
    for r in rows:              # caller-supplied planned sinks {type: [(x, y, w)]} (precheck ctx, tests) win
        if planned_sinks and r["tn"] in planned_sinks:
            s = planned_sinks[r["tn"]]
            r["sinks"], r["planned"] = binned(s), sum(w for *_, w in s)
            n_exact += 1
    for r in sorted((r for r in rows if "planned" not in r), key=prio):
        if not ex or not ex.ok or time.time() - t_start > budget_s:
            break
        try:
            s = ex.sinks(r["tn"])
        except Exception as e:  # noqa: BLE001
            r["exact_err"] = f"{type(e).__name__}: {str(e)[:80]}"
            continue
        r["sinks"] = binned(s)
        r["planned"] = sum(w for *_, w in s)
        n_exact += 1
    hits, n_total = [], 0
    nr = {'inventory': 0, 'per-tap': 0, 'cap': 0, 'placed': 0}
    for r in rows:
        tn, t, taps = r["tn"], r["t"], r["taps"]
        ck = t.get("clock") or {}
        cap = int(ck.get("tap_max_sinks") or 1500)
        radius = float(ck.get("tap_radius_um") or 200.0)
        flops = r["flops"] or 0
        planned = r.get("planned", r["cheap"])
        mark = "" if "planned" in r else "~"
        n_cmp += 1
        why, score = [], 0.0
        tot = bool(flops and planned > 0 and flops > ratio * planned)
        n_total += tot
        avg = flops / len(taps) if flops and taps else 0.0
        inventory = bool(ck.get("sink_bins_file"))     # the plan model IS the placed register inventory (bins)
        r["pmax"] = None
        if inventory and tot:
            why.append(f"sink bins {mark}{_fmt(planned)} planned vs {_fmt(flops)} netlist flops ({r['fbasis'] or r['pbasis']}) "
                       f"= x{flops / planned:.2f} > {ratio}: the bins ({ck.get('sink_bins_file')}) miss flops, the "
                       f"{'density ' if not taps else ''}taps are sized short")
            score = max(score, flops / planned)
            nr['inventory'] += 1
        if r.get("sinks") and taps:
            ld = nearest_loads(taps, r["sinks"])
            j = max(range(len(ld)), key=ld.__getitem__)
            r["pmax"], pname = ld[j], taps[j][0]
            if r["pmax"] > 0 and avg > ratio * r["pmax"]:
                why.append(f"{_fmt(avg)} netlist flops/tap ({_fmt(flops)} flops, {r['fbasis'] or r['pbasis']}, over {len(taps)} "
                           f"taps) vs planned max {_fmt(r['pmax'])} ({pname}) = x{avg / r['pmax']:.2f} > {ratio}")
                score = max(score, avg / r["pmax"])
                nr['per-tap'] += 1
        if flops and taps and avg > cap:
            nr['cap'] += 1
            why.append(f"{len(taps)} taps x cap {cap} = {_fmt(len(taps) * cap)} < {_fmt(flops)} netlist flops "
                       f"(needs >= {math.ceil(flops / cap)} taps)")
            score = max(score, avg / cap)
        placed_note = ""
        pr = r["prec_b"]
        r["placed_cur"], r["placed_kit"] = None, None
        try:
            ow, oh = map(float, t["outline_um"])
            same = bool(pr and pr.get("die_um") and abs(float(pr["die_um"][0]) - ow) < 0.05
                        and abs(float(pr["die_um"][1]) - oh) < 0.05)
        except (TypeError, ValueError, IndexError):
            same = False
        if same and taps:
            pts = [(float(x), float(y), float(n)) for x, y, n in pr["bins"]]
            how = "nearest"
            ld = None
            if ex and ex.ok and hasattr(ex.T, "assign"):
                try:     # the kit's split (clock_taps.tcl mirror): nearest, then re-home over-cap sinks within the radius
                    ld = list(ex.T.assign(taps, pts, cap, radius)[0])
                    how = f"kit split cap {cap} r{radius:g}"
                except Exception:  # noqa: BLE001
                    ld = None
            if ld is None:
                ld = nearest_loads(taps, pts)
            r["placed_cur"] = max(ld) if ld else None
            over = sorted(((ld[i], taps[i][0]) for i in range(len(taps)) if ld[i] > placed_max), reverse=True)
            if over:
                placed_note = (f"placed regs of kit {pr['kit'].split(':')[-1][:56]} ({_fmt(pr['n_regs'])}) on the current "
                               f"{len(taps)} taps ({how}): {len(over)} over {placed_max}: "
                               + ", ".join(f"{n} {_fmt(v)}" for v, n in over[:5]))
                score = max(score, over[0][0] / placed_max)
                nr['placed'] += 1
        elif not same:
            prk, _ = lookup(pl, tn, by_base)
            r["placed_kit"] = (prk or {}).get("max_load")
            if prk and prk.get("over1500"):
                o = prk["over1500"]
                placed_note = (f"kit {prk['kit'].split(':')[-1][:56]} placed scan (its own taps; outline differs): "
                               f"{len(o)} taps over 1500: " + ", ".join(f"{n} {_fmt(v)}" for n, v in o[:4]))
                score = max(score, o[0][1] / placed_max)
                nr['placed'] += 1
        if not why and not placed_note:
            continue
        if not why and not _kw.get("list_placed", os.environ.get("OT_ADV_TAPLOAD_PLACED_LIST", "0") == "1"):
            continue        # PRECHECK-R2: placed > 1,500 alone fires on 326/328 S81 types (signed incl.): counted in the summary only
        if tot and not inventory:
            why.append(f"plan sink model {mark}{_fmt(planned)} vs {_fmt(flops)} netlist flops (x{flops / planned:.1f})")
        msg = "; ".join(why + ([placed_note] if placed_note else []))
        msg += ("; fix: size the taps on the netlist register inventory (clock.sink_bins_file from the placed kit, "
                "taps.py bins) and re-run tap_split (TAP-SOFTFLOP, TAP-GRID-R5)")
        hits.append((score, _w(tn, msg)))
    hits.sort(key=lambda h: -h[0])
    if dump:
        with open(dump, "w") as f:
            f.write("type\tflops\tbasis\tcheap\tplanned\texact_err\ttaps\tcap\tplanned_max_tap\tplaced_cur_max\tplaced_kit_max\n")
            for r in rows:
                f.write("\t".join(str(x) for x in (r["tn"], r["flops"], r["fbasis"] or r["pbasis"], round(r["cheap"]),
                        round(r["planned"]) if "planned" in r else "", r.get("exact_err", ""), len(r["taps"]),
                        (r["t"].get("clock") or {}).get("tap_max_sinks"), round(r["pmax"]) if r.get("pmax") else "",
                        round(r["placed_cur"]) if r.get("placed_cur") else "", r.get("placed_kit") or "")) + "\n")
    out = [m for _, m in hits[:int(_kw.get('max_lines') or MAX_LINES)]]
    left = sorted((r["flops"] or 0) / len(r["taps"]) for r in rows if "planned" not in r)
    out.append(_w("summary", f"{len(hits)} of {n_cmp} types with netlist data flagged (per-tap x{ratio}, taps x cap, placed "
                             f"tap > {placed_max} after the kit split; by rule {nr}); total-sink rule (netlist > {ratio} x planned) alone: "
                             f"{n_total} types (listed only where the plan model is a sink_bins_file inventory; otherwise it is boundary/station "
                             f"registers by design); planned "
                             f"sinks exact on {n_exact}, cheap count (~) on {n_cmp - n_exact}"
                             f"{f' (their flops/tap <= {left[-1]:,.0f})' if left else ''}"
                             f"{'' if not ex or ex.ok else ' (exact off: ' + ex.why + ')'}; {n_unmeas} types without a kit "
                             f"netlist, {n_notap} without a static tap table (density/sink taps: inventory rule only); cache {Path(src).name if src else '-'} "
                             f"{cache.get('made', '')}; {time.time() - t_start:.0f} s"))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001 -- an estimator reports, never stops
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    t0 = time.time()
    with open(sys.argv[1]) as f:
        _raw = json.load(f)
    t1 = time.time()
    for ln in findings(_raw, sys.argv[1], sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None,
                       flops_cache=sys.argv[3] if len(sys.argv) > 3 else None,
                       dump=os.environ.get("OT_ADV_TAPLOAD_DUMP"),
                       budget_s=float(os.environ.get("OT_ADV_TAPLOAD_BUDGET_S", BUDGET_S)),
                       max_lines=int(os.environ.get("OT_ADV_MAX_LINES", MAX_LINES))):
        print(ln)
    print(f"# ADV-{CHECK} load {t1 - t0:.1f} s, check {time.time() - t1:.1f} s")
