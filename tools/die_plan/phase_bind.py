#!/usr/bin/env python3
"""phase_bind.py -- C-DIECLOCK-PHASE-BIND (HEAD-SERDES-R2 / FABLE-RC-HEAD 11-26): re-derive the plan's clock-phase choices
from a die STA run on the ROUTED die clock, and check a plan against them.

Why: the W10 HEAD die clock is phase-distributed by design (routed tap arrivals 947..7006 ps TT at T = 833 ps).  Seams are
closed by per-instance phase choices in the plan (partitions[].reset_entry_phase + id_straps strap_rst_ph, the START
tree's edge_fall per region / stage, count-align J / K).  Those choices were derived on a cell-delay die tree and were never
re-derived when the die clock was routed: on the routed W10 tree sp5->host_nstrip arst_n moved from -1.4 to +400 ps and
host_w->sst5 from -50 to -28 ps.  This tool re-derives them from the routed timing and emits plan rows.

    phase_bind.py derive --plan PLAN.json --sta DIE_STA.json [--sidecar SC.json] [--run-entry-rows ROWS.json]
                         [--start-stages start_stages.json] [--arr TT=arr_TT.txt --arr FF=arr_FF.txt]
                         [--period 833] [--guard 60] --out phase_bind.json [--rows plan_rows.json]
                         [--sidecar-rows sidecar_rows.json] [--ca-rows count_align_rows.json]
    phase_bind.py check  --plan PLAN.json --bind phase_bind.json [--sidecar SC.json] [--guard 60]   (report only, exit 0)

DIE_STA.json is die_sta.py run (TT + FF) with --spine-tree on the routed die clock (ctree.v + ctree.spef from
dieclock_route_step / combo GRT) and real peer views; its spine_tree dir and ctree.spef sha key the bind.

Model (one seam = one die_sta seam group src->dst/bus; per corner the max (setup) and min (hold) record).  The STA reports
the slack against the capture edge Es that run used (Es = ideal setup capture edge in the launch clock's frame, the hold
edge is Es - T).  The data window in that frame is edge independent:
        W_hi = Es - setup_slack            (latest data arrival + setup + uncertainty - capture clock arrival)
        W_lo = hold_slack + (Es - T)       (earliest data arrival - hold - uncertainty - capture clock arrival)
so for any other capture edge E:  setup' = E - W_hi,  hold' = W_lo - (E - T).  Library setup / hold of the rising and
falling capture flops are taken equal (a few ps), everything else (routed clock RC, peer views, data RC) is measured.
  * reset / START pin entry (types with reset.pin_entry_phase, pin_entry_phase.py): E(h) = T - h T/2, h in -8..8; one h per
    instance covers u_rst_in and u_run_in (arst_n / start_i groups ending in u_rst_in|u_run_in/cap_r|cap_f).  The edge the
    run used: --run-entry-rows (die_sta --entry-phase rows of that run) else the default of the endpoint flop (cap_r T,
    cap_f T/2).
  * START tree captures (ot_dp_landing_origin stages, *tstart* part captures): E(f, n) = (T/2 if f else T) - n T; f is the
    region / stage edge_fall, n the whole-cycle offset the count-align origin (J) absorbs.  Edge the run used: from the
    endpoint flop polarity ($_DFF_N_ / ot_st_origin_f1 = fall).
  A START capture with no edge clearing the guard in both corners is AMBIGUOUS (count_align_plan's term: J differs between
  corners; the TT / FF clock skew of a long routed branch moves the window by up to ~170 ps): count-align must budget it.
  score(choice) = min over both corners of (setup', hold').  The derived choice maximises score (ties: the plan's value,
  then the smaller |value|).  Status per seam owner:
        OK          plan choice scores >= guard
        MISBOUND    plan choice < guard and the derived choice >= guard           -> plan row emitted
        NO-WINDOW   no choice reaches the guard (data window too wide)            -> structural row (HB4 / lockup / retime)
        UNMEASURED  instance opted in but no group of the STA run ends in its entry cells (old view, missing peer)
Count-align ring ports (K / DEPTH) are NOT derived here: the START d rows (--ca-rows, landed_phase_ocv row form, d = capture
clock - launch clock arrival per corner) feed count_align_plan.py; ring crossings need landed_phase_ocv.py on the same
routed die clock run.  `check` reports a sidecar with no routed-clock provenance as COUNT-ALIGN-UNBOUND.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA = "opentallas.phase_bind.v1"
H_RANGE = range(-8, 9)
N_RANGE = range(-8, 9)
RESET_BUSES = ("arst_n", "start_i")      # the two die reset / START relay inputs of a pin_entry_phase instance
ENTRY_RE = re.compile(r"(?:^|/)(u_rst_in|u_run_in)[/.](cap_[rf])")
FALL_RE = re.compile(r"\$_S?DFF[A-Z]*_N|_DFFN|negedge|\$_DFF_N", re.I)
RISE_RE = re.compile(r"\$_S?DFF[A-Z]*_P|\$_DFFE_P|\$_DFF_P", re.I)


def sha12(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]
    except OSError:
        return None


def load_arrivals(path):
    """OT_EDGES v1 lines: KIND port late early slew -> {port: late}; T/N rise, F/M fall source (late)."""
    out = {}
    for ln in Path(path).read_text().splitlines():
        x = ln.split()
        if len(x) >= 3 and x[0] in ("T", "N", "F", "M"):
            try:
                out[x[1]] = float(x[2])
            except ValueError:
                pass
    return out


def split_group(g):
    src, rest = g.split("->", 1)
    dst, bus = rest.split("/", 1)
    return src, dst, bus


def entry_of(end):
    m = ENTRY_RE.search(end or "")
    return (m.group(1), m.group(2)) if m else (None, None)


def reset_edge(h, T):
    return T - h * T / 2.0


def start_edge(f, n, T):
    return (T / 2.0 if f else T) - n * T


def polarity(end, module=""):
    if FALL_RE.search(end or ""):
        return True
    if RISE_RE.search(end or ""):
        return False
    if module.endswith("_f1"):
        return True
    return False


def windows(corners, group, edge_used, T):
    """[(corner, 'max'|'min', value)] of the edge-independent window: W_hi for max, W_lo for min.
    edge_used(rec) -> the capture edge Es that run used for this record."""
    out = []
    for c, seams in corners.items():
        g = seams.get(group) or {}
        for kind in ("max", "min"):
            r = g.get(kind)
            if not r or r.get("worst") is None:
                continue
            es = edge_used(r)
            w = float(r["worst"])
            out.append((c, kind, es - w if kind == "max" else w + es - T))
    return out


def score_at(ws, E, T):
    s = None
    for _c, kind, v in ws:
        x = (E - v) if kind == "max" else (v - (E - T))
        s = x if s is None else min(s, x)
    return s


def pick(scores, plan_val):
    """scores {choice: score}; best score, ties -> plan value, then smaller |choice|."""
    best = max(scores.values())
    cands = [k for k, v in scores.items() if v >= best - 1e-6]
    if plan_val in cands:
        return plan_val
    return sorted(cands, key=lambda k: (abs(k) if isinstance(k, int) else abs(k[1]), str(k)))[0]


def status_of(plan_score, best_score, guard, measured=True):
    if not measured:
        return "UNMEASURED"
    if plan_score is not None and plan_score >= guard:
        return "OK"
    if best_score >= guard:
        return "MISBOUND"
    return "NO-WINDOW"


def enabled(t):
    return ((t or {}).get("reset") or {}).get("pin_entry_phase") is True


def derive(plan, sta, sidecar=None, run_rows=None, stages=None, arr=None, T=833.0, guard=60.0):
    corners = {c: v.get("seams") or {} for c, v in (sta.get("corners") or {}).items()}
    insts = sta.get("instances") or {}
    types = plan.get("partition_types") or {}
    parts = {p["name"]: p for p in plan.get("partitions", [])}
    run_h = {}
    for r in (run_rows or {}).get("rows", []):
        run_h[r["part"]] = int(r["half_cycles"])
    groups = sorted(set().union(*[set(s) for s in corners.values()])) if corners else []

    # ---- reset / START pin entry
    by_part, proxy = {}, {}
    for g in groups:
        src, dst, bus = split_group(g)
        if dst not in parts or not enabled(types.get(parts[dst].get("type"))):
            continue
        ends = [((corners[c].get(g) or {}).get(k) or {}).get("end") for c in corners for k in ("max", "min")]
        if any(entry_of(e)[0] for e in ends if e):
            by_part.setdefault(dst, []).append(g)
        elif bus in RESET_BUSES:
            proxy.setdefault(dst, []).append(g)
    reset = {}
    for name, p in sorted(parts.items()):
        if not enabled(types.get(p.get("type"))):
            continue
        plan_h = int(p.get("reset_entry_phase", 0))
        gs, measured_on = by_part.get(name, []), "entry_cell"
        if not gs and proxy.get(name):
            gs, measured_on = proxy[name], "proxy_first_flop"
        ws = []
        for g in gs:
            def used(r, _n=name, _m=measured_on):
                if _m != "entry_cell":
                    return start_edge(polarity(r.get("end")), 0, T)
                ent, cap = entry_of(r.get("end"))
                if _n in run_h:
                    return reset_edge(run_h[_n], T)
                return T if cap != "cap_f" else T / 2.0
            ws += windows(corners, g, used, T)
        if not ws:
            reset[name] = dict(type=p.get("type"), plan_h=plan_h, status="UNMEASURED", groups=gs)
            continue
        sc = {h: round(score_at(ws, reset_edge(h, T), T), 3) for h in H_RANGE}
        h = pick(sc, plan_h)
        st = status_of(sc.get(plan_h), sc[h], guard)
        reset[name] = dict(type=p.get("type"), plan_h=plan_h, derived_h=h if st != "OK" else plan_h, best_h=h,
                           strap=(h if st != "OK" else plan_h) % 2, plan_score=sc.get(plan_h), best_score=sc[h],
                           status=st, groups=gs, scores={str(k): v for k, v in sc.items()},
                           run_h=run_h.get(name), measured_on=measured_on, plan_has_h="reset_entry_phase" in p,
                           plan_strap=(p.get("id_straps") or {}).get("strap_rst_ph"))

    # ---- START tree captures
    sregion = {}
    for s in (stages or {}).get("stages", []):
        sregion["st_" + s["id"]] = (s.get("region"), bool(s.get("edge_fall")))
    regions = ((sidecar or {}).get("count_aligned") or {}).get("regions") or {}
    start = {}
    ca_rows = {c: [] for c in corners}
    for g in groups:
        src, dst, bus = split_group(g)
        if not src.startswith("st_"):
            continue
        if not (dst.startswith("st_") or "tstart" in bus):
            continue
        if dst in sregion:
            region, plan_f = sregion[dst]
        elif dst in regions:
            region, plan_f = dst, bool(regions[dst].get("edge_fall"))
        else:
            region, plan_f = dst, None

        def used(r, _d=dst):
            f = polarity(r.get("end"), insts.get(_d, ""))
            return start_edge(f, 0, T)
        ws = windows(corners, g, used, T)
        if not ws:
            continue
        sc = {}
        for f in (False, True):
            for n in N_RANGE:
                sc[(f, n)] = round(score_at(ws, start_edge(f, n, T), T), 3)
        best = max(sc, key=lambda k: (sc[k], -abs(k[1])))
        plan_best = max((sc[k] for k in sc if k[0] == plan_f), default=None) if plan_f is not None else None
        st = status_of(plan_best, sc[best], guard) if plan_f is not None else ("UNBOUND" if sc[best] >= guard else "NO-WINDOW")
        if st == "NO-WINDOW":
            st = "AMBIGUOUS"         # count_align_plan term: J takes 2 values across corners -> count-align must budget it
        if st == "OK":
            best = max((k for k in sc if k[0] == plan_f), key=lambda k: (sc[k], -abs(k[1])))
        start[g] = dict(region=region, src_region=sregion.get(src, (src, None))[0], plan_edge_fall=plan_f,
                        derived_edge_fall=best[0], derived_cycles=best[1], plan_score=plan_best, best_score=sc[best],
                        status=st)
        for c in corners:
            r = ((corners[c].get(g) or {}).get("max") or (corners[c].get(g) or {}).get("min") or {})
            if r.get("launch") is not None and r.get("capture") is not None:
                d = float(r["capture"]) - float(r["launch"])
                ca_rows[c].append(dict(port=f"start:{start[g]['src_region']}->{region}", d_ps=round(d, 3), p_dn_ps=0.0,
                                       p_up_ps=0.0, margin_ps=0.0, unshared_a_ps=0.0, unshared_b_ps=0.0, group=g))

    def count(dct):
        out = {}
        for v in dct.values():
            out[v["status"]] = out.get(v["status"], 0) + 1
        return out
    spine = sta.get("spine_tree") or {}
    sdir = spine.get("dir") if isinstance(spine, dict) else None
    key = dict(plan_sha12=None, sta_spine_dir=sdir,
               ctree_spef_sha12=sha12(Path(sdir) / "ctree.spef") if sdir else None,
               arr_sha12={c: sha12(p) for c, p in (arr or {}).items()})
    arr_info = {}
    for c, p in (arr or {}).items():
        a = load_arrivals(p)
        if a:
            arr_info[c] = dict(ports=len(a), min_ps=round(min(a.values()), 2), max_ps=round(max(a.values()), 2))
    return dict(schema=SCHEMA, period_ps=T, guard_ps=guard, key=key, arrivals=arr_info,
                reset_entry=reset, start=start, summary=dict(reset_entry=count(reset), start=count(start)),
                count_align="ring ports K/DEPTH not derived here: landed_phase_ocv.py + count_align_plan.py on the same routed "
                            "die clock run; START d rows in --ca-rows"), ca_rows


def _op(present, old, new):
    return dict(op="replace", old=old, value=new) if present else dict(op="set", value=new)


def plan_rows(bind, plan_sha12, lane="HEAD-SERDES-R2"):
    rows = []
    for name, r in sorted(bind["reset_entry"].items()):
        if r["status"] != "MISBOUND":
            continue
        h = r["derived_h"]
        common = dict(type=r["type"], measured=f"plan h={r['plan_h']} score {r['plan_score']} ps < guard; h={h} score "
                                               f"{r['best_score']} ps (routed die clock, phase_bind)")
        rows.append(dict(id=f"PHASE-BIND-{name}-H", path=["partitions", {"name": name}, "reset_entry_phase"],
                         **_op(r.get("plan_has_h", True), r["plan_h"], h), **common))
        if r.get("plan_strap") != h % 2:
            rows.append(dict(id=f"PHASE-BIND-{name}-STRAP", path=["partitions", {"name": name}, "id_straps", "strap_rst_ph"],
                             **_op(r.get("plan_strap") is not None, r.get("plan_strap"), h % 2), **common))
    return dict(schema="opentallas.plan_rows.v1", class_id="C-DIECLOCK-PHASE-BIND", lane=lane,
                base_plan_sha256_12=plan_sha12, source=f"phase_bind {bind['key']}", rows=rows)


def sidecar_rows(bind, sidecar_sha12, sidecar, lane="HEAD-SERDES-R2"):
    regions = ((sidecar or {}).get("count_aligned") or {}).get("regions") or {}
    rows, seen = [], set()
    for g, r in sorted(bind["start"].items()):
        if r["status"] != "MISBOUND" or r["region"] not in regions or r["region"] in seen:
            continue
        seen.add(r["region"])
        rows.append(dict(id=f"PHASE-BIND-START-{g}", path=["count_aligned", "regions", r["region"], "edge_fall"], op="replace",
                         old=r["plan_edge_fall"], value=r["derived_edge_fall"],
                         measured=f"{g}: plan edge_fall {r['plan_edge_fall']} score {r['plan_score']} ps; derived "
                                  f"{r['derived_edge_fall']} n={r['derived_cycles']} score {r['best_score']} ps",
                         note="count-align J / K must be re-derived (count_align_plan.py) after this row"))
    return dict(schema="opentallas.plan_rows.v1", target="sidecar", class_id="C-DIECLOCK-PHASE-BIND", lane=lane,
                base_sidecar_sha256_12=sidecar_sha12, rows=rows)


def check_lines(plan, bind, sidecar=None, guard=None, max_list=8):
    """report-only lines (no prefix): plan phases vs a phase_bind.json."""
    guard = bind.get("guard_ps", 60.0) if guard is None else guard
    types = plan.get("partition_types") or {}
    parts = {p["name"]: p for p in plan.get("partitions", [])}
    out, mis, nowin, unmeas, ok = [], [], [], [], 0
    for name, p in sorted(parts.items()):
        if not enabled(types.get(p.get("type"))):
            continue
        b = (bind.get("reset_entry") or {}).get(name)
        h = int(p.get("reset_entry_phase", 0))
        if not b or b.get("status") == "UNMEASURED":
            unmeas.append(name)
            continue
        sc = (b.get("scores") or {}).get(str(h))
        best = b.get("best_score")
        if sc is not None and sc >= guard:
            ok += 1
        elif best is not None and best >= guard:
            mis.append((sc, name, h, b.get("best_h"), best))
        else:
            nowin.append((best, name, h))
    mis.sort(key=lambda x: (x[0] if x[0] is not None else -1e9))
    for sc, name, h, bh, best in mis[:max_list]:
        out.append(f"RESET-ENTRY MISBOUND {name} reset_entry_phase {h} scores {sc} ps < {guard}; routed clock wants {bh} ({best} ps)")
    for best, name, h in sorted(nowin)[:max_list]:
        out.append(f"RESET-ENTRY NO-WINDOW {name} h={h}: best {best} ps < {guard} for every h (structural seam fix)")
    regions = ((sidecar or {}).get("count_aligned") or {}).get("regions") or {}
    smis = []
    for g, r in sorted((bind.get("start") or {}).items()):
        plan_f = bool(regions[r["region"]].get("edge_fall")) if r.get("region") in regions else r.get("plan_edge_fall")
        if plan_f is None:
            continue
        if plan_f != r.get("derived_edge_fall") and r.get("status") in ("MISBOUND",):
            smis.append(g)
    out.append(f"SUMMARY reset_entry ok {ok} misbound {len(mis)} no_window {len(nowin)} unmeasured {len(unmeas)}; "
               f"start edge_fall misbound {len(smis)} (bind {bind.get('key', {}).get('ctree_spef_sha12')})")
    if smis:
        out.append(f"START-EDGE MISBOUND {len(smis)} group(s), e.g. {', '.join(smis[:4])}")
    if sidecar is not None and not ((sidecar.get("count_aligned") or {}).get("clock_provenance")):
        out.append("COUNT-ALIGN-UNBOUND sidecar count_aligned has no clock_provenance (die clock run / ctree.spef sha it was "
                   "derived from): K / DEPTH / J are not tied to the routed die clock")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="phase_bind", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("derive")
    d.add_argument("--plan", required=True)
    d.add_argument("--sta", required=True)
    d.add_argument("--sidecar")
    d.add_argument("--run-entry-rows")
    d.add_argument("--start-stages")
    d.add_argument("--arr", action="append", default=[], metavar="CORNER=FILE")
    d.add_argument("--period", type=float, default=833.0)
    d.add_argument("--guard", type=float, default=60.0)
    d.add_argument("--out", required=True)
    d.add_argument("--rows")
    d.add_argument("--sidecar-rows")
    d.add_argument("--ca-rows")
    d.add_argument("--lane", default="HEAD-SERDES-R2")
    c = sub.add_parser("check")
    c.add_argument("--plan", required=True)
    c.add_argument("--bind", required=True)
    c.add_argument("--sidecar")
    c.add_argument("--guard", type=float)
    a = ap.parse_args(argv)
    if a.cmd == "check":
        sc = json.loads(Path(a.sidecar).read_text()) if a.sidecar else None
        for x in check_lines(json.loads(Path(a.plan).read_text()), json.loads(Path(a.bind).read_text()), sc, a.guard, 10 ** 6):
            print("PHASE-BIND " + x)
        return 0
    plan = json.loads(Path(a.plan).read_text())
    sta = json.loads(Path(a.sta).read_text())
    sidecar = json.loads(Path(a.sidecar).read_text()) if a.sidecar else None
    rr = json.loads(Path(a.run_entry_rows).read_text()) if a.run_entry_rows else None
    stg = json.loads(Path(a.start_stages).read_text()) if a.start_stages else None
    arr = dict(x.split("=", 1) for x in a.arr)
    bind, ca = derive(plan, sta, sidecar, rr, stg, arr, a.period, a.guard)
    bind["key"].update(plan_sha12=sha12(a.plan), sidecar_sha12=sha12(a.sidecar) if a.sidecar else None, sta_sha12=sha12(a.sta),
                       run_entry_rows_sha12=sha12(a.run_entry_rows) if a.run_entry_rows else None)
    Path(a.out).write_text(json.dumps(bind, indent=1) + "\n")
    if a.rows:
        Path(a.rows).write_text(json.dumps(plan_rows(bind, bind["key"]["plan_sha12"], a.lane), indent=1) + "\n")
    if a.sidecar_rows and sidecar is not None:
        Path(a.sidecar_rows).write_text(json.dumps(sidecar_rows(bind, bind["key"]["sidecar_sha12"], sidecar, a.lane), indent=1) + "\n")
    if a.ca_rows:
        Path(a.ca_rows).write_text(json.dumps(dict(schema="opentallas.phase_bind_ca_rows.v1", note="landed_phase_ocv row form; "
                                                   "d = capture - launch clock arrival of the START group (routed die clock)",
                                                   corners={c: dict(all=v) for c, v in ca.items()}), indent=1) + "\n")
    print(f"{a.out}: reset_entry {bind['summary']['reset_entry']} start {bind['summary']['start']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
