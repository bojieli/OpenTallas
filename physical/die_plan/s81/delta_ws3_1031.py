#!/usr/bin/env python3
"""DIE-S81-45 10-31: serdes__t12 WS3 shore-lot replan on the S81 plan of record (COORD 17:0x: the single S81 plan
exception under 12.20; OWNER 10-29: PMA 129.6 x 2246.4 lies along the shore, fallback = this WS3 lot replan).

Why not compose_ws3_1029.py as is: its un-compose of the 10-29 plan no longer runs (later one-block events made the
landing cohort clones diverge), and a full clock_landing_plan.compose of the plan of record rewrites 198 of 204 types
(the later post-compose one-block fixes: ring_place, band rows, forwarded_clock_only_inputs, ...) with 18 band
placement failures (DIE-S81-45 CHECKED).  This delta therefore splices ONLY what the WS3 geometry changes:

  1. geometry = compose_ws3_1029.apply_geometry + set_stations + site_svc + update_table on a copy of the plan of
     record (lk_WS3 2885.76 x 1226.88 shore lot, PMA pair R90, iqf -> (8760.96, 1330.56), 6 single-instance types
     re-pinned; variant V2 = iqf retagged to the lk_WS3 landing region (981 crossings, every touched lane keeps its
     crossing count), V1 = tags travel (989)); serdes__t12 / iqf__t1 tap tables reset to the R4 grid (their
     grid+explicit added taps were sized for the old outline / pins);
  2. clock_landing_plan.compose (unmodified, default reset monitor, observer seqhost dsdv_hostb_dstat u_u_dst) on
     BASE (= the plan of record + its table) and on NEW (= 1.), the explicit-tap BUDGET validator skipped only for
     the re-tapped types while composing (their taps are rebuilt in step 4 and validated unmodified);
  3. three-way merge plan = POR + (NEW - BASE), sidecar likewise: every value compose does not change keeps the plan
     of record byte for byte (all later one-block fixes); a list whose length changes is taken from NEW (logged);
     then the plan's post-compose conventions on the changed types: every ring band ring_place "ff"
     (delta_ringff_all_1029), the collector_local_sources band copies and the sidecar collector entry mirror the plan
     contract (band copies without ring_place), landing base_type and forwarded_clock_only_inputs as in the plan;
  4. taps: delta_alltap_1030.py on serdes__t12 / iqf__t1 (reach + load, the S81-39 rule), an explicit station tap
     left with no planned sink gets the alltap sink row [x, y, 1] at its own site; delta_alltap_coll_1030.py then
     re-derives the collector trees of the re-tapped types (plan + sidecar, boot budget);
  5. gen.py latency (lane cycles) spliced into the plan.
Only the sections that change are rewritten in the plan text (per type / per top-level key, each in its own original
text style).  Receipt: per-type change list, conflicts, crossings, boot budget, tap results.

usage (repo root):
  delta_ws3_1031.py --variant V2|V1 --out DIR [--base DIR_WITH_BASE_COMPOSE] [--plan P] [--sidecar S]
  -> DIR/plan_h2_2249.json, DIR/landed_sidecar_h2.json, DIR/receipt.json (inputs are never edited)"""
import argparse
import copy
import hashlib
import importlib.util
import json
import multiprocessing as mp
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools/die_plan"))
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402
import taps as TP  # noqa: E402

OBS = dict(module="dsdv_hostb_dstat", instance_suffix="u_u_dst", fault_port="vid_ri", ready_port="alive_i")
OBS_PART = "seqhost"
RETAP = ("serdes__t12", "iqf__t1")
RELAX = set(RETAP) | {"slice_station__t49"}
TOUCHED_TYPES = ("serdes__t12", "iqf__t1", "svc_lo_dsdv_svc_rs_w__t1", "svc_lo_dsdv_svc_rs__t1", "phy__t1",
                 "slice_station__t49")


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def load_mod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


# ------------------------------------------------------------------------------------------------ 1. geometry
def geometry(por, table, variant, log):
    cw = load_mod("compose_ws3_1029", HERE / "compose_ws3_1029.py")
    delta = json.loads((HERE / "delta_ws3_lot_1029.json").read_text())
    raw = copy.deepcopy(por)
    rename, old_all = cw.apply_geometry(raw, delta, log)
    rec = cw.set_stations(raw, log)
    led = cw.site_svc(raw, rec, log)
    tab, per_lane = cw.update_table(raw, table, variant, rename, old_all, log)
    for tn in RETAP:
        ck = raw["partition_types"][tn]["clock"]
        log.append(f"{tn}: tap_mode {ck.get('tap_mode')} ({len(ck.get('added_taps') or [])} added taps) -> grid "
                   "(re-tapped by delta_alltap_1030 after the compose)")
        ck["tap_mode"] = "grid"
        ck.pop("added_taps", None)
        ck.pop("sink_sites_um", None)
    return raw, tab, dict(stations=rec, ft_corridor=led, crossings_per_touched_lane=per_lane)


# ------------------------------------------------------------------------------------------------ 2. compose
def _compose(args):
    plan_p, tab_p, out = args
    _e, _g = TP.explicit_taps, TP.grid_explicit_taps
    TP.explicit_taps = lambda P, tn: ([(n, x, y, 1, 0.0) for n, x, y in TP.explicit_tap_sites(P, tn)]
                                      if tn in RELAX else _e(P, tn))
    TP.grid_explicit_taps = lambda P, tn: ([(n, x, y, 1, 0.0) for n, x, y in TP.grid_explicit_sites(P, tn)]
                                           if tn in RELAX else _g(P, tn))
    import clock_landing_plan as CL
    plan = json.loads(Path(plan_p).read_text())
    tab = {k: v for k, v in json.loads(Path(tab_p).read_text()).items() if k != "collector"}
    t0 = time.time()
    new, sc = CL.compose(plan, tab, plan_path=plan_p, observer_part=OBS_PART, observer=dict(OBS))
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / "plan.json").write_text(json.dumps(new, separators=(",", ":")) + "\n")
    (Path(out) / "sidecar.json").write_text(json.dumps(sc, separators=(",", ":")) + "\n")
    return round(time.time() - t0)


# ------------------------------------------------------------------------------------------------ 3. merge
def merge3(p, b, v, path, log):
    """POR + (NEW - BASE).  Values NEW leaves as BASE keep POR; values only NEW changed take NEW."""
    if v == b:
        return copy.deepcopy(p)
    if p == b:
        return copy.deepcopy(v)
    if isinstance(p, dict) and isinstance(b, dict) and isinstance(v, dict):
        out = {}
        for k in list(p) + [k for k in v if k not in p]:
            if k in p and k in b and k in v:
                out[k] = merge3(p[k], b[k], v[k], f"{path}/{k}", log)
            elif k in v and k not in b:                 # added by NEW (or by both)
                out[k] = copy.deepcopy(v[k]) if k not in p else merge3(p[k], v[k], v[k], f"{path}/{k}", log)
            elif k in b and k not in v:                 # removed by NEW
                if k in p and p[k] != b[k]:
                    log.append(dict(path=f"{path}/{k}", kind="removed_by_new_edited_in_por"))
                continue
            elif k in p:                                # POR-only key (post-compose field): keep
                out[k] = copy.deepcopy(p[k])
        return out
    if isinstance(p, list) and isinstance(b, list) and isinstance(v, list):
        # lists of identified records (collector edges by src/dst/index, sources by name): merged by identity, so a
        # record NEW adds, drops or re-targets never mixes with a POR record that only shares its index
        for key in (lambda e: (e["src"], e["dst"], e["dst_index"]), lambda e: e["name"]):
            try:
                kp, kb, kv = ([key(e) for e in x] for x in (p, b, v))
            except (TypeError, KeyError):
                continue
            if any(len(set(k)) != len(k) for k in (kp, kb, kv)) or (kp == kb == kv):
                continue
            B, V = dict(zip(kb, b)), dict(zip(kv, v))
            out, n = [], dict(removed=0, changed=0, added=0)
            for k, e in zip(kp, p):                    # POR order; removed by NEW dropped, changed by NEW merged
                if k in B and k not in V:
                    n["removed"] += 1
                    continue
                if k in B and k in V:
                    if V[k] != B[k]:
                        n["changed"] += 1
                    out.append(merge3(e, B[k], V[k], f"{path}[{k}]", log))
                else:
                    out.append(copy.deepcopy(e))
            for k, e in zip(kv, v):                    # added by NEW: appended in NEW order
                if k not in B and k not in set(kp):
                    n["added"] += 1
                    out.append(copy.deepcopy(e))
            log.append(dict(path=path, kind="keyed_list_merge", **n))
            return out
    if isinstance(p, list) and isinstance(b, list) and isinstance(v, list) and len(p) == len(b) == len(v):
        return [merge3(x, y, z, f"{path}[{i}]", log) for i, (x, y, z) in enumerate(zip(p, b, v))]
    log.append(dict(path=path, kind="list_len" if isinstance(v, list) else "both_changed",
                    por_vs_base=True, took="NEW"))
    return copy.deepcopy(v)


def post_rules(plan, side, por, changed, log):
    for tn in changed:
        t = plan["partition_types"][tn]
        lc = (t.get("clock") or {}).get("landing_contract")
        plc = (por["partition_types"][tn].get("clock") or {}).get("landing_contract") or {}
        if not lc:
            continue
        for bus, band in lc.get("bands", {}).items():
            if not bus.startswith("monitor_") and band.get("rect_um") and band.get("ring_place") != "ff":
                band["ring_place"] = "ff"
                log.append(f"{tn}/{bus}: ring_place ff (delta_ringff_all_1029 rule)")
        for src in lc.get("collector_local_sources", []):
            if src["name"] in lc["bands"]:
                src["band"] = {k: copy.deepcopy(v) for k, v in lc["bands"][src["name"]].items() if k != "ring_place"}
        for k in ("base_type", "forwarded_clock_only_inputs"):
            if k in plc:
                lc[k] = copy.deepcopy(plc[k])
        st = side["collector"]["types"].get(tn)
        if st is not None:
            st["bands"] = {b: {k: copy.deepcopy(v) for k, v in x.items() if k != "ring_place"} for b, x in lc["bands"].items()}
            st["local_sources"] = copy.deepcopy(lc.get("collector_local_sources", []))
            st["tree"] = copy.deepcopy(lc.get("collector_tree"))
            st["children"] = copy.deepcopy(lc.get("collector_children", []))
            if lc.get("collector_root_node"):
                st["collector_root_node"] = lc["collector_root_node"]


def restation(plan, plan_path, types, log):
    """ft slots whose station count the WS3 geometry changed but whose station form (regs_um / bit_sites_um) is still
    the old path's: a slot that is now LANDED takes the landed form (ring + k stations, no regs / bit sites, as the
    plan's ft6..ft9); an UNLANDED slot takes the station form of delta_station_form_1030 (k -> k+1, out-face register
    per bit, per-bit sites; the type's clock table is NOT touched)."""
    SF = load_mod("delta_station_form_1030", HERE / "delta_station_form_1030.py")
    import check as C
    from gen_phys import type_pins
    from tools.die_trial.legal_sites import RowAllocator
    for tn in types:
        t = plan["partition_types"][tn]
        bad = [s for s in t.get("ft_slots", []) if s.get("regs_um") and len(s["regs_um"]) != int(s.get("stations", 1))]
        if not bad:
            continue
        for s in [s for s in bad if SF.landed(t, s)]:
            log.append(f"{tn}/{s['name']}: landed after the re-pin, {s['stations']} stations; stale {len(s['regs_um'])} "
                       "regs / bit sites dropped (landed form)")
            for k in ("regs_um", "bit_sites_um", "bit_site_cell_um"):
                s.pop(k, None)
        todo = [s for s in bad if not SF.landed(t, s)]
        if not todo:
            continue
        P = S.Plan(copy.deepcopy(plan), plan_path)
        W, H = t["outline_um"]
        pins = {}
        for bus, bit, _l, x, y, face in type_pins(P, tn):
            pins.setdefault(bus, {})[bit] = (x, y, face)
        grow = [(x0 - 4.32, y0 - 4.32, x1 + 4.32, y1 + 4.32) for x0, y0, x1, y1 in S.placed_macro_boxes(t, halo=0.0).values()]
        al = RowAllocator((4.32, 4.32, W - 4.32, H - 4.32), blocked=grow, cell_size=SF.CELL, column_pitch=2.16,
                          row_pitch=.27, origin=(4.32, 4.32))
        for s in t["ft_slots"]:
            if s in todo:
                continue
            for st in s.get("bit_sites_um") or []:
                for x, y in st:
                    al.reserve_rectangle((x, y, x + SF.CELL[0], y + SF.CELL[1]))
        for s in sorted(todo, key=lambda s: (-s["width"], s["name"])):
            name, k = s["name"], int(s["stations"])
            pi, po = pins[name + "_i"], pins[name + "_o"]
            bits = sorted(set(pi) | set(po))
            assert len(bits) == s["width"] + 1, (tn, name)
            geo = {}
            for b in bits:
                A, B = pi.get(b) or po[b], po.get(b) or pi[b]
                ia, ib = SF.inset(A), SF.inset(B)
                r = C.zroute(ia, ib, A[2], B[2])
                geo[b] = (ia, ib, r, C.plen(r))
            last = SF.alloc_bits(al, [geo[b][1] for b in bits], 40.)
            inner = [SF.alloc_bits(al, [C.point_at(geo[b][2], geo[b][3] * j / k) for b in bits], 60.) for j in range(1, k)]
            sites = inner + [last]
            worst, preg = 0.0, []
            for i, b in enumerate(bits):
                ch = [geo[b][0]] + [(st[i][0] + SF.CELL[0] / 2, st[i][1] + SF.CELL[1] / 2) for st in sites]
                worst = max(worst, max(SF.man(u, v) for u, v in zip(ch, ch[1:])))
                preg.append(SF.man(ch[-1], geo[b][1]))
            assert worst <= SF.SMAX, (tn, name, worst)
            regs = [SF.win_centre(t, s, "in_window_um", s["in_face"])]
            for st in sites:
                regs.append([round(float(sum(v[0] for v in st) / len(st) + SF.CELL[0] / 2), 4),
                             round(float(sum(v[1] for v in st) / len(st) + SF.CELL[1] / 2), 4)])
            log.append(f"{tn}/{name}: unlanded {s['in_face']}->{s['out_face']}, stale {len(s['regs_um'])} regs for {k} "
                       f"stations -> station form {k + 1} stations, max hop {worst:.1f}, out pin-reg max {max(preg):.1f}")
            s["stations"] = k + 1
            s["regs_um"] = regs
            s["bit_site_cell_um"] = list(SF.CELL)
            s["bit_sites_um"] = sites


def fill_empty_explicit(plan, plan_path, tn, log):
    """an explicit station tap left with no planned sink: alltap's convention, a sink row [x, y, 1] at its site."""
    ck = plan["partition_types"][tn]["clock"]
    for _ in range(64):
        P = S.Plan(copy.deepcopy(plan), plan_path)
        try:
            TP.explicit_taps(P, tn)
            return True
        except ValueError as ex:
            m = re.search(r"explicit tap (\S+) load=0/\d+, radius=[\d.e+-]+/[\d.e+-]+, empty=True", str(ex))
            if not m:
                log.append(f"{tn}: explicit tap table refused: {str(ex)[:200]}")
                return False
            name = m.group(1)
            x, y = next((x, y) for n, x, y in TP.explicit_tap_sites(P, tn) if n == name)
            ck.setdefault("sink_sites_um", []).append([round(x, 4), round(y, 4), 1])
            log.append(f"{tn}: explicit tap {name} has no planned sink after the re-pin -> sink row [{x}, {y}, 1]")
    return False


# ------------------------------------------------------------------------------------------------ text splice
def _enc_indent(o, ind, compact_keys=(), line_keys=()):
    sp = " " * ind
    if isinstance(o, dict):
        if not o:
            return "{}"
        return "{\n" + ",\n".join(" " * (ind + 1) + json.dumps(k) + ": " + (
            json.dumps(v, separators=(",", ":")) if k in line_keys else
            ("[\n" + ",\n".join(" " * (ind + 2) + json.dumps(x, separators=(",", ":")) for x in v) + "\n" + " " * (ind + 1) + "]")
            if (k in compact_keys and isinstance(v, list) and v) else _enc_indent(v, ind + 1, (), line_keys))
            for k, v in o.items()) + "\n" + sp + "}"
    if isinstance(o, list):
        if not o:
            return "[]"
        return "[\n" + ",\n".join(" " * (ind + 1) + _enc_indent(x, ind + 1, (), line_keys) for x in o) + "\n" + sp + "]"
    return json.dumps(o)


def _encoders(ind, top_type):
    import compact_plan as CP
    out = [lambda o: CP._d(o, ind)]
    if top_type:
        for ck in (("ft_slots", "contents", "hard_cores"), ()):
            for lk in (("pads", "pad_clock"), ()):
                out.append(lambda o, ck=ck, lk=lk: _enc_indent(o, ind, ck, lk))
    out.append(lambda o: _enc_indent(o, ind))
    out.append(lambda o: json.dumps(o, separators=(",", ":")))
    return out


def splice(text, key_re, ind, new_value, top_type, log, label):
    m = re.search(key_re, text, re.M)
    assert m, label
    old, j = json.JSONDecoder().raw_decode(text, m.end())
    seg = text[m.end():j]
    for enc in _encoders(ind, top_type):
        if enc(old) == seg:
            return text[:m.end()] + enc(new_value) + text[j:]
    log.append(f"{label}: no encoder reproduces the original text style; indent form used")
    return text[:m.end()] + _enc_indent(new_value, ind) + text[j:]


def write_plan(por_text, por, plan, log):
    text = por_text
    for tn in plan["partition_types"]:
        if plan["partition_types"][tn] != por["partition_types"].get(tn):
            text = splice(text, r'^  "' + re.escape(tn) + r'": ', 2, plan["partition_types"][tn], True, log, tn)
    for k in plan:
        if k != "partition_types" and plan[k] != por.get(k):
            if isinstance(plan[k], dict):
                for k2 in plan[k]:
                    if plan[k][k2] != por[k].get(k2):
                        assert k2 in por[k], (k, k2)
                        text = splice(text, r'^  "' + re.escape(k2) + r'": ', 2, plan[k][k2], False, log, f"{k}/{k2}")
            else:
                text = splice(text, r'^ "' + re.escape(k) + r'": ', 1, plan[k], False, log, k)
    assert json.loads(text) == plan, "spliced plan text does not equal the merged plan"
    return text


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--variant", choices=("V1", "V2"), required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", help="dir holding a BASE compose (plan.json + sidecar.json) of the SAME plan of record")
    ap.add_argument("--reuse-new", action="store_true", help="keep an existing DIR/NEW compose (same inputs)")
    ap.add_argument("--plan", default=str(HERE / "plan_h2_2249.json"))
    ap.add_argument("--sidecar", default=str(HERE / "h2_2249/landed_sidecar_h2.json"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    por_text = Path(a.plan).read_text()
    side_text = Path(a.sidecar).read_text()
    por, side = json.loads(por_text), json.loads(side_text)
    table = {k: v for k, v in side.items() if k != "collector"}
    log, conflicts = [], []
    geom, tab, grec = geometry(por, table, a.variant, log)
    (out / "geom.json").write_text(json.dumps(geom, separators=(",", ":")) + "\n")
    (out / "table.json").write_text(json.dumps(tab, separators=(",", ":")) + "\n")
    (out / "por_table.json").write_text(json.dumps(table, separators=(",", ":")) + "\n")
    jobs = [(str(out / "geom.json"), str(out / "table.json"), str(out / "NEW"))]
    bdir = Path(a.base) if a.base else out / "BASE"
    if a.reuse_new and (out / "NEW/plan.json").exists():
        jobs = []
    if not (a.base and (bdir / "plan.json").exists()):
        jobs.append((a.plan, str(out / "por_table.json"), str(bdir)))
    secs = []
    if jobs:
        with mp.get_context("fork").Pool(len(jobs)) as pool:
            secs = pool.map(_compose, jobs)
    log.append(f"compose secs {secs}")
    B, Bs = json.loads((bdir / "plan.json").read_text()), json.loads((bdir / "sidecar.json").read_text())
    V, Vs = json.loads((out / "NEW/plan.json").read_text()), json.loads((out / "NEW/sidecar.json").read_text())
    changed = sorted(tn for tn in V["partition_types"] if V["partition_types"][tn] != B["partition_types"].get(tn))
    assert set(V["partition_types"]) == set(B["partition_types"]) == set(por["partition_types"]), "type set changed"
    inst = {}
    for p in V["partitions"]:
        inst.setdefault(p["type"], []).append(p["name"])
    multi = {tn: inst.get(tn) for tn in changed if len(inst.get(tn, [])) != 1}
    assert not multi, ("a changed type is not single-instance", multi)
    plan = merge3(por, B, V, "", conflicts)
    nside = merge3(side, Bs, Vs, "", conflicts)
    post_rules(plan, nside, por, changed, log)
    restation(plan, a.plan, changed, log)
    plan_p = out / "plan_h2_2249.json"
    side_p = out / "landed_sidecar_h2.json"
    plan_p.write_text(write_plan(por_text, por, plan, log))
    side_p.write_text(json.dumps(nside, separators=(",", ":")) + "\n")
    # ---------------------------------------------------------------- 4. taps
    taprep = {}
    ok49 = fill_empty_explicit(plan, str(plan_p), "slice_station__t49", log)
    if plan != json.loads(plan_p.read_text()):
        plan_p.write_text(write_plan(plan_p.read_text(), json.loads(plan_p.read_text()), plan, log))
    taprep["slice_station__t49_explicit_ok"] = ok49
    env = dict(os.environ, TYPES_RE="^(" + "|".join(RETAP) + ")$")
    r = subprocess.run([sys.executable, str(HERE / "delta_alltap_1030.py"), str(plan_p), str(out / "plan_tap.json"),
                        str(out / "alltap_report.json"), "--types", "^(" + "|".join(RETAP) + ")$"],
                       cwd=str(ROOT), capture_output=True, text=True)
    log.append(f"delta_alltap_1030 rc {r.returncode}: {(r.stdout + r.stderr)[-300:]}")
    if r.returncode:
        raise SystemExit("\n".join(map(str, log)))
    os.replace(out / "plan_tap.json", plan_p)
    r = subprocess.run([sys.executable, str(HERE / "delta_alltap_coll_1030.py"), str(plan_p), str(side_p),
                        str(out / "alltap_coll_report.json")], cwd=str(ROOT), capture_output=True, text=True, env=env)
    log.append(f"delta_alltap_coll_1030 rc {r.returncode}: {(r.stdout + r.stderr)[-300:]}")
    if r.returncode:
        raise SystemExit("\n".join(map(str, log)))
    plan = json.loads(plan_p.read_text())
    P = S.Plan(copy.deepcopy(plan), str(plan_p))
    for tn in sorted(set(changed) | RELAX):
        try:
            q = S.tap_grid(P, tn)
            taprep[tn] = dict(mode=plan["partition_types"][tn]["clock"].get("tap_mode", "grid"), taps=len(q), ok=True)
        except ValueError as ex:
            taprep[tn] = dict(ok=False, err=str(ex)[:240])
    # ---------------------------------------------------------------- 5. latency
    lat_copy = out / "lat_plan.json"
    lat_copy.write_text(plan_p.read_text())
    r = subprocess.run([sys.executable, str(ROOT / "tools/die_plan/gen.py"), "latency", str(lat_copy), "--inplace",
                        "--out", str(out / "lat")], cwd=str(ROOT), capture_output=True, text=True)
    log.append(f"gen.py latency rc {r.returncode}: {(r.stdout + r.stderr)[-200:]}")
    if r.returncode:
        raise SystemExit("\n".join(map(str, log)))
    lat = json.loads(lat_copy.read_text())["latency"]
    lat_copy.unlink()
    c0 = {k: v["cycles"] for k, v in por["latency"]["lanes"].items()}
    if lat != plan["latency"]:
        new = copy.deepcopy(plan)
        new["latency"] = lat
        plan_p.write_text(write_plan(plan_p.read_text(), plan, new, log))
        plan = new
    c1 = {k: v["cycles"] for k, v in plan["latency"]["lanes"].items()}
    lane_changes = {k: dict(before=c0.get(k), after=c1.get(k)) for k in sorted(set(c0) | set(c1)) if c0.get(k) != c1.get(k)}
    # ---------------------------------------------------------------- receipt
    final_side = json.loads(side_p.read_text())
    types_changed = sorted(tn for tn in plan["partition_types"] if plan["partition_types"][tn] != por["partition_types"].get(tn))
    col = final_side["collector"]
    rec = dict(kind="S81_WS3_LOT_1031", variant=a.variant, lane="DIE-S81-45",
               inputs=dict(plan=dict(path=a.plan, sha256=sha(por_text)), sidecar=dict(path=a.sidecar, sha256=sha(side_text)),
                           compose_ws3=sha((HERE / "compose_ws3_1029.py").read_bytes()),
                           delta=sha((HERE / "delta_ws3_lot_1029.json").read_bytes())),
               outputs=dict(plan_sha256=sha(plan_p.read_bytes()), sidecar_sha256=sha(side_p.read_bytes())),
               compose_changed_types=changed, plan_changed_types=types_changed,
               other_top_level_changed=[k for k in plan if k != "partition_types" and plan[k] != por[k]],
               merge_conflicts=conflicts, geometry=grec, taps=taprep, lane_cycle_changes=lane_changes,
               lane_sum=dict(before=sum(c0.values()), after=sum(c1.values())),
               crossings=dict(before=side["crossings"], after=final_side["crossings"]),
               parent_changes={pn: dict(before=side["collector"]["parts"][pn]["parent"], after=col["parts"][pn]["parent"])
                               for pn in col["parts"] if col["parts"][pn]["parent"] != side["collector"]["parts"][pn]["parent"]},
               boot=dict(before=side["collector"]["boot_budget"]["ready_at_glue_max_cycles"],
                         after=col["boot_budget"]["ready_at_glue_max_cycles"]),
               placement_failures_new=[f for f in col["placement_failures"] if f["type"] in changed],
               log=log, secs=round(time.time() - t_start))
    (out / "receipt.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("variant", "compose_changed_types", "plan_changed_types", "other_top_level_changed",
                                          "crossings", "boot", "parent_changes", "taps", "lane_sum", "placement_failures_new",
                                          "secs")}, indent=1))
    print("merge conflicts", len(conflicts), "lane cycle changes", len(lane_changes))


if __name__ == "__main__":
    main()
