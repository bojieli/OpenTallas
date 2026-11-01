#!/usr/bin/env python3
"""DIE-HEAD-51 plan event l49s (COORD default on DIE-HEAD-49 ASK 08:59): restore the HEAD spine internal stations.

Root cause [DIE-HEAD-49/51]: the plan's internal_stations of hd_spn / hd_spn_end were realized once, by a post-gen
step on a Codex WIP commit (head_realize_spn_source.py -> kit_istations --apply, source_realized1).  gen.py phys
(gen_rtl) does not emit internal stations and head_rekit_current requires published == generated, so every later
regeneration (die-head-33/src25m_cf onward) dropped them, while the plan kept stale sites (be_i y 504 against a
708-1008 window).  This tool makes the realization part of the HEAD source/kit recipe:

  plan    SRC_DIR BASE_DIR CAND_DIR OUT_DIR [--hop UM]
          OUT = SRC plan + the hd_spn_end delta BASE -> CAND (DIE-HEAD-49 l48s items A x_i band, B per-exporter
          reset copies, C status anchors; 3-way, fails when SRC changed a touched field) + the internal stations of
          hd_spn / hd_spn_end re-sited on the current bus windows: per bus the smallest station count whose
          per-bit knee route (kit_istations is_knee_site, worst pin of the window) has every hop <= --hop
          (default 340 um, under the 405 um station reach / 403 um kit_istations knee bound); a bus within --hop
          of its leaf gets no entry.  regs_um = the knee sites of the window-centre bit (G0C hop check).  The
          density clock taps of both types are frozen as explicit taps (freeze_taps): taps, reset tree and every
          START / landing name stay as in SRC.
  realize WRAPPER_IN PLAN TYPE WRAPPER_OUT [--tcl ISTATIONS_TCL]
          kit_istations --apply on a copy of the generated wrapper, then each station's reset (kit_istations writes
          the literal rst_n, which tap-reset wrappers do not have) is rewired to the reset-tree tap rst_n_t<k>
          nearest its planned site; stations add exactly len(regs_um) register stages per bus, nothing else.
  rekit   ROOT SRC_DIR OUT_DIR TYPE
          head_rekit_current.py with the realization applied to the generated wrapper before the published-source
          comparison; istations.tcl is copied into the kit (face_flops.tcl sources /work/istations.tcl).
"""
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DP = HERE.parent / "die_plan"
sys.path[:0] = [str(DP), str(HERE)]
TYPES = ("hd_spn_end", "hd_spn")
KNEE_MAX = 403.0


# ------------------------------------------------------------------------------------------------ plan
def _get(o, path):
    for k in path:
        o = o[k]
    return o


def _walk(a, b, p, out):
    """leaf-level delta a -> b: ('set', path, old, new) / ('append', path, items)"""
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            raise SystemExit(f"plan: key set change at {p} not supported")
        for k in a:
            _walk(a[k], b[k], p + (k,), out)
    elif isinstance(a, list) and isinstance(b, list):
        n = min(len(a), len(b))
        for i in range(n):
            _walk(a[i], b[i], p + (i,), out)
        if len(b) > len(a):
            out.append(("append", p, b[n:], len(a)))
        elif len(a) > len(b):
            raise SystemExit(f"plan: list shrink at {p} not supported")
    elif a != b:
        out.append(("set", p, a, b))


def port_delta(src_t, base_t, cand_t, skip=("note",)):
    d = []
    for k in base_t:
        if k in skip:
            continue
        _walk(base_t[k], cand_t[k], (k,), d)
    t = copy.deepcopy(src_t)
    for op in d:
        if op[0] == "set":
            _, p, old, new = op
            if _get(t, p) != old:
                raise SystemExit(f"plan: {p} changed in SRC ({_get(t, p)!r} != base {old!r}): 3-way conflict")
            _get(t, p[:-1])[p[-1]] = new
        else:
            _, p, items, n0 = op
            lst = _get(t, p)
            if len(lst) != n0:
                raise SystemExit(f"plan: {p} length changed in SRC ({len(lst)} != base {n0})")
            lst.extend(copy.deepcopy(items))
    return t, d


def knee_site(px, py, lx, ly, face, edge, edges, dirn, geom):
    """tools/die_plan/kit_istations.py is_knee_site (same arithmetic)"""
    xmin, ymin, xmax, ymax = geom
    if face in "EW":
        normal = max(abs(xmin - lx), abs(xmax - lx)); along = max(abs(ymin - ly), abs(ymax - ly)); cx, cy = lx, py
    else:
        normal = max(abs(ymin - ly), abs(ymax - ly)); along = max(abs(xmin - lx), abs(xmax - lx)); cx, cy = px, ly
    if dirn == "in":
        first, second, ax, ay, bx, by = normal, along, px, py, lx, ly
    else:
        first, second, ax, ay, bx, by = along, normal, lx, ly, px, py
    if edges == 1:                    # no station: one hop face pin <-> leaf
        return None, first + second
    if first < 1e-8:
        split, worst = 0, second / edges
    elif second < 1e-8:
        split, worst = edges, first / edges
    else:
        split, worst = -1, 1e99
        for j in range(1, edges):
            w = max(first / j, second / (edges - j))
            if w < worst:
                worst, split = w, j
        if split < 0:
            return None, 1e99
    if edge <= split:
        f = edge / split
        return (ax + f * (cx - ax), ay + f * (cy - ay)), worst
    f = (edge - split) / (edges - split)
    return (cx + f * (bx - cx), cy + f * (by - cy)), worst


def resite(t, tn, hop, bt):
    """re-site every bus entry of internal_stations on the current window; returns (entries, report rows)"""
    W, H = t["outline_um"]
    buses = {b["name"]: b for b in t["buses"]}
    leafs = {c["inst"]: c for c in t["contents"]}
    out, rows = [], []
    for e in t.get("internal_stations", []):
        if not e.get("conn", "").startswith("bus:"):
            out.append(e)
            continue
        bus = e["conn"][4:]
        b = buses[bus]
        face, (w0, w1) = b["face"], b["window_um"]
        lx, ly = e["leaf_um"]
        box = leafs[b["leaf"].split(".")[0]].get("outline_um", [0, 0])
        off = max(0.0, min(15.0, box[0 if face in "EW" else 1] / 2.0 - 2.0))
        lxo, lyo = lx + {"W": -off, "E": off}.get(face, 0.0), ly + {"S": -off, "N": off}.get(face, 0.0)
        fx = {"W": 0.0, "E": W}.get(face)
        fy = {"S": 0.0, "N": H}.get(face)
        geom = (fx, w0, fx, w1) if face in "EW" else (w0, fy, w1, fy)
        mid = bt[bus][1]
        n, worst = 0, None
        while True:
            _, worst = knee_site(mid[0], mid[1], lxo, lyo, face, 1, n + 1, b["dir"], geom)
            if worst <= hop:
                break
            n += 1
            if n > 20:
                raise SystemExit(f"{tn} {bus}: no station count reaches hop {hop}")
        old = len(e["regs_um"])
        rows.append(dict(bus=bus, dir=b["dir"], face=face, window_um=[w0, w1], planned_before=old, stations=n,
                         worst_knee_hop_um=round(worst, 1), delta_vs_rtl_cycles=n, delta_vs_old_plan=n - old))
        if n == 0:
            continue
        regs = [knee_site(mid[0], mid[1], lxo, lyo, face, k + 1, n + 1, b["dir"], geom)[0] for k in range(n)]
        regs = [[round(x, 3), round(y, 3)] for x, y in regs]
        if b["dir"] == "in":
            fr, to = [round(mid[0], 3), round(mid[1], 3)], [lx, ly]
        else:
            fr, to = [lx, ly], [round(mid[0], 3), round(mid[1], 3)]
        ne = dict(e, from_um=fr, to_um=to, regs_um=regs,
                  note=f"{e.get('note', '')} [l49s DIE-HEAD-51: re-sited on window {face} {w0:g}-{w1:g}, "
                       f"{n} stations, worst per-bit knee hop {worst:.1f} um <= {hop:g}]".strip())
        out.append(ne)
    return out, rows


def cmd_plan(a):
    src, base, cand, out = (Path(x) for x in a[:4])
    hop = float(a[a.index("--hop") + 1]) if "--hop" in a else 340.0
    import schema as S
    import check as C
    raw = json.loads((src / "source_plan.json").read_text())
    rb = json.loads((base / "source_plan.json").read_text())
    rc = json.loads((cand / "source_plan.json").read_text())
    rep = dict(src=str(src), base=str(base), cand=str(cand), hop_um=hop, station_reach_um=None, types={})
    t, d = port_delta(raw["partition_types"]["hd_spn_end"], rb["partition_types"]["hd_spn_end"],
                      rc["partition_types"]["hd_spn_end"])
    t["note"] = (t.get("note", "") + " | DIE-HEAD-51 l49s: DIE-HEAD-49 l48s items A x_i band flush, B per-exporter "
                 "reset copies, C status anchors (0 data cycles)").strip()
    raw["partition_types"]["hd_spn_end"] = t
    rep["l48s_delta"] = [dict(op=o[0], path="/".join(map(str, o[1])),
                              **({"old": o[2], "new": o[3]} if o[0] == "set" else {"added": len(o[2])})) for o in d]
    P0 = S.Plan(copy.deepcopy(raw))     # SRC + l48s items, stations as in SRC: the reference reset trees / taps
    P = S.Plan(raw)
    rep["station_reach_um"] = C.station_max(P)
    for tn in TYPES:
        tt = raw["partition_types"][tn]
        bt = C._bus_targets(P, tn)
        st, rows = resite(tt, tn, hop, bt)
        tt["internal_stations"] = st
        tt["note"] = (tt.get("note", "") + f" | DIE-HEAD-51 l49s: internal stations re-sited on the current windows and "
                      "realized in RTL (head_spn_l49s.py realize)").strip()
        bad = [e["conn"] for e in st if not C._hops_ok(e["from_um"], e["regs_um"], e["to_um"], rep["station_reach_um"])]
        if bad:
            raise SystemExit(f"{tn}: G0C hop check fails on {bad}")
        rep["types"][tn] = dict(buses=rows, stations=sum(len(e["regs_um"]) for e in st))
    rep["taps"] = freeze_taps(P0, raw, rep)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out, symlinks=True)
    (out / "source_plan.json").write_text(json.dumps(raw, indent=1) + "\n")
    (out / "l49s_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep["types"], indent=1))


def freeze_taps(P0, raw, rep):
    """The stations are FIRM clock sinks (taps.per_bit_station_sites), so in density mode re-siting them would move the
    taps and regenerate the reset relay tree (renamed rst_rl_<n> under every landing / START reference, moved raw
    START export pins).  12.20 freeze, one-block fix: the type's density taps are frozen as explicit taps (same names,
    same xy: make_l48b form), so the clock tap set, the reset tree and every START / landing reference stay exactly as
    in SRC; the explicit-tap check (every sink, stations included, within tap_radius_um, <= tap_max_sinks) must pass."""
    import schema as S
    import reset_tree as RT
    import taps as TP
    out = {}
    f0 = {tn: [(n, x, y) for n, x, y, _, _ in TP.density_taps(P0, tn)] for tn in TYPES}
    rel0 = {tn: [(r["q"], tuple(r["xy"]), r["d"]) for r in RT.for_type(P0, tn)["relays"]] for tn in TYPES}
    for tn in TYPES:
        ck = raw["partition_types"][tn]["clock"]
        if ck.get("tap_mode") != "density":
            raise SystemExit(f"{tn}: expected tap_mode density, got {ck.get('tap_mode')}")
        ck.update(tap_mode="explicit", taps=[dict(name=n, xy=[x, y]) for n, x, y in f0[tn]])
    P = S.Plan(copy.deepcopy(raw))
    for tn in TYPES:
        rel = [(r["q"], tuple(r["xy"]), r["d"]) for r in RT.for_type(P, tn)["relays"]]
        if rel != rel0[tn]:
            raise SystemExit(f"{tn}: reset tree changed under the frozen taps")
        ex = TP.explicit_taps(P, tn)
        out[tn] = dict(taps=len(ex), reset_relays=len(rel), reset_tree_identical=True,
                       tap_loads=[(n, round(l), round(r, 1)) for n, x, y, l, r in ex],
                       max_radius_um=round(max(r for *_, r in ex), 1), max_load=max(l for *_, l, _ in ex))
        print(tn, json.dumps({k: v for k, v in out[tn].items() if k != "tap_loads"}))
    return out


# ------------------------------------------------------------------------------------------------ realize
def realize_text(text, raw, tn, tcl_out=None):
    """generated wrapper text -> realized text (+ istations.tcl text); report dict"""
    import tempfile
    import kit_istations as I
    import schema as S
    import reset_tree as RT
    t = raw["partition_types"][tn]
    mod = t["module"]
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        f = td / f"{mod}.sv"
        f.write_text(text)
        (td / "kit_rtl.json").write_text(json.dumps(dict(files=[str(f)], bound_module=mod)))
        pj = td / "plan.json"
        pj.write_text(json.dumps(raw))
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            I.main([str(pj), tn, str(td), "--apply"])
        txt = f.read_text()
        tcl = (td / "istations.tcl").read_text()
        ist = json.loads((td / "kit_rtl.json").read_text())["kit_istations"]
    rel = RT.for_type(S.Plan(raw), tn)["relays"]
    taps = {r["q"]: r["xy"] for r in rel if str(r["q"]).startswith("rst_n_t")}
    if not taps:
        raise SystemExit(f"{tn}: no rst_n_t<k> reset taps in the reset tree")
    have = set(re.findall(r"\brst_n_t\d+\b", txt))
    taps = {q: xy for q, xy in taps.items() if q in have}   # taps with no consumer are not emitted
    rows = []
    sites = {}
    for e in t["internal_stations"]:
        bus = e["conn"][4:]
        for j, xy in enumerate(e["regs_um"]):
            sites[f"u_ist_{bus}_{j}"] = xy
    def fix(m):
        nm = m.group(1)
        if nm not in sites:
            raise SystemExit(f"{tn}: station {nm} has no planned site")
        x, y = sites[nm]
        q, (tx, ty) = min(taps.items(), key=lambda kv: abs(kv[1][0] - x) + abs(kv[1][1] - y))
        if q not in have:
            raise SystemExit(f"{tn}: nearest reset tap {q} is not a net of the wrapper")
        rows.append(dict(station=nm, site=[x, y], rst=q, rst_xy=[tx, ty], dist_um=round(abs(tx - x) + abs(ty - y), 1)))
        return m.group(0).replace(".rst_n(rst_n)", f".rst_n({q})")
    txt, n = re.subn(r"ot_dp_st #\(\.W\(\d+\)\) (u_ist_\w+?_\d+) \(\.clk\(clk\), \.rst_n\(rst_n\),[^\n]*", fix, txt)
    if n != len(sites) or re.search(r"u_ist_\w+ \([^\n]*\.rst_n\(rst_n\)", txt):
        raise SystemExit(f"{tn}: realized {n} stations, planned {len(sites)}, or a literal rst_n is left")
    if tcl_out:
        Path(tcl_out).write_text(tcl)
    return txt, tcl, dict(type=tn, stations=ist, resets=rows, added_stages=n)


def cmd_realize(a):
    win, plan, tn, wout = a[:4]
    raw = json.loads(Path(plan).read_text())
    tcl = a[a.index("--tcl") + 1] if "--tcl" in a else None
    txt, _, rep = realize_text(Path(win).read_text(), raw, tn, tcl)
    Path(wout).write_text(txt)
    rep.update(before_sha256=hashlib.sha256(Path(win).read_bytes()).hexdigest(),
               after_sha256=hashlib.sha256(txt.encode()).hexdigest())
    print(json.dumps(rep, indent=1))


CLAND_RECT = re.compile(r'^\s*\{(\S*u_cland_\S+)\s+\{([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\}\s+(\S+)\}\s*$', re.M)


def station_cland_guard(kit, tcl, mode):
    """DIE-HEAD-52 spn2 10-31: l49x hd_spn place failed because the u_spr plan-cell station (235.65, 1883.6) filled the
    reserved landing band of u_cland_sin_b_o_b_i_9 before landing_placement.tcl ran ("OT_CLAND no legal nonoverlapping
    row/site in reserved band").  mode "band" (default): reserve every cland_groups band rect as an explicit footprint
    before the station spiral, so ff_put_near steps around it.  mode "after": source istations.tcl after the landing
    rings and reserve the rows they occupied (cland_occ).  Both keep the station plan; only the station grid cell moves."""
    lp = (kit / "landing_placement.tcl").read_text() if (kit / "landing_placement.tcl").exists() else ""
    rects = CLAND_RECT.findall(lp)
    if mode == "after":
        pre = ["# DIE-HEAD-52 spn2 (after): stations run after the landing rings; their occupied rows are explicit footprints",
               "if {[info exists cland_occ]} { dict for {r rs} $cland_occ { foreach xr $rs { lassign $xr a b",
               "  ff_reserve_explicit $a [expr {$ff_y0 + $r * $ff_rh}] [expr {$b - $a}] $ff_rh } } }"]
        ff = kit / "face_flops.tcl"
        t = ff.read_text()
        src = "if {[file exists /work/istations.tcl]} { source /work/istations.tcl }"
        land = "uplevel #0 {source /work/landing_placement.tcl}"
        assert t.count(src) == 1 and t.count(land) == 1, "face_flops.tcl source order anchors"
        t = t.replace(src, "# DIE-HEAD-52 spn2 (after): istations.tcl moved after landing_placement.tcl")
        t = t.replace(land, land + "\nif {[file exists /work/istations.tcl]} { uplevel #0 {source /work/istations.tcl} }")
        ff.write_text(t)
    else:
        pre = [f"# DIE-HEAD-52 spn2 (band): {len(rects)} landing band rects reserved before the station spiral"]
        pre += [f"ff_reserve_explicit [expr {{round({x0}*$ff_dbu)}}] [expr {{round({y0}*$ff_dbu)}}] "
                f"[expr {{round(({x1}-{x0})*$ff_dbu)}}] [expr {{round(({y1}-{y0})*$ff_dbu)}}]"
                for _, x0, y0, x1, y1, _t in rects]
    lines = tcl.splitlines()
    k = next(i for i, l in enumerate(lines) if l.startswith("set is_n 0"))
    return "\n".join(lines[:k] + pre + lines[k:]) + "\n", len(rects)


# ------------------------------------------------------------------------------------------------ rekit
def cmd_rekit(a):
    """head_rekit_current.py (DIE-HEAD-32/46) + realization before the published-source comparison"""
    root, source, out = (Path(x).resolve() for x in a[:3])
    TYPE = a[3]
    sys.path[:0] = [str(root / "tools/die_plan"), str(root / "tools/s81_head")]
    from head_count_strap_sites import apply as count_strap_sites
    from head_start_raw_private import prepare_plan, patch_rtl as private_raw_rtl
    from head_start_reset_aliases import patch_rtl
    out.mkdir(parents=True)
    path, side = source / "source_plan.json", source / "source_sidecar.json"
    plan = json.loads(path.read_text())
    plan, straps = count_strap_sites(plan, path, root, types={TYPE})
    plan, private = prepare_plan(plan, {TYPE})
    cand = out / "source_plan_rekit.json"
    cand.write_text(json.dumps(plan, indent=1) + "\n")
    for f in source.iterdir():
        if f.is_dir():
            (out / f.name).symlink_to(f.resolve())
    gen = out / "gen"
    cmd = [sys.executable, str(root / "tools/die_plan/gen.py"), "phys", str(cand), "--clock-landing", str(side),
           "--types", TYPE, "--out", str(gen), "--rtl-root", str(root), "--trial"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    (out / "gen.log").write_text(r.stdout + r.stderr)
    if r.returncode:
        raise SystemExit(f"gen.py phys exit {r.returncode}: {(r.stdout + r.stderr)[-1500:]}")
    t = plan["partition_types"][TYPE]
    kit = gen / TYPE
    wr = gen / "_rtl" / f"{t['module']}.sv"
    rows = t.get("reset_start_raw_exports", [])
    text = patch_rtl(wr.read_text(), rows)
    real = None
    if any(e.get("conn", "").startswith("bus:") for e in t.get("internal_stations", [])) and TYPE in TYPES:
        (out / "unrealized.sv").write_text(text)     # station-miter reference (generated wrapper, no stations)
        text, tcl, real = realize_text(text, plan, TYPE)
        mode = os.environ.get("OT_L49_IST_MODE", "band")
        tcl, nband = station_cland_guard(kit, tcl, mode)
        real["cland_guard"] = dict(mode=mode, band_rects=nband)
        (kit / "istations.tcl").write_text(tcl)
    published = source / f"{t['module']}.sv"

    def normalize(txt):
        txt = re.sub(r'/\*.*?\*/', '', txt, flags=re.S)
        txt = re.sub(r'//[^\n]*', '', txt)
        return re.sub(r'\s+', '', txt)
    if normalize(text) != normalize(published.read_text()):
        (out / 'before_private.sv').write_text(text)
        raise ValueError('generated (+ realized stations) RTL differs from published current source before private copy')
    text, prr = private_raw_rtl(text, t)
    wr.write_text(text)
    (kit / "rtl" / wr.name).write_text(text)
    rep = dict(type=TYPE, cells=t.get("cells"), raw_reset_exports=len(rows), count_strap_sites=straps,
               private_raw_rtl=prr, gen_cmd=cmd, internal_stations=real and dict(added_stages=real["added_stages"],
                                                                                 resets=real["resets"], cland_guard=real.get("cland_guard")),
               istations_tcl=bool(real), route_qualified=False)
    (out / "rekit_receipt.json").write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps(rep)[:600])


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("plan", "realize", "rekit"):
        raise SystemExit(__doc__)
    dict(plan=cmd_plan, realize=cmd_realize, rekit=cmd_rekit)[sys.argv[1]](sys.argv[2:])
