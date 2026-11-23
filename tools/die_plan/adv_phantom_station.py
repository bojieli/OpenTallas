#!/usr/bin/env python3
"""ADV-PHANTOM-STATION (PRECHECK-R2 11-22, static estimator, never a gate): a lane priced +N station cycles with no
register behind them in the bound RTL.

Real case (FABLE-FIX-HEAD-LEP0N 11-22 19:07 RETRACT, COORD 19:2x): HEAD r18m (3dd49f406010) added
partition_types.hd_lep0N.internal_stations {conn bus:o_h2r1_p, launch u_core.h2r1, regs_um 1} / {bus:o_h2r2_p ...} and
lanes L2 / L4 fixed_cycles 1, latency cycles 3.  hd_lep0N is a gen.py-rtl type WITHOUT realize_internal_stations: the gen
wrapper carries no u_ist_ station and the HEAD kit flow inserts none (kit_istations runs only for bound kits via
kit_topology.prepare_stations, or for gen types with realize_internal_stations, gen_rtl.realize_plan_stations).  e1 / e2
kit RTL were byte-identical (0 u_ist_), placed timing identical: plan +1, silicon 0.  LATCHECK (gen_lane_latcheck) PASSED
3 == 3 because lane_asbuilt_latency.side_stages predicts the station as "kit_ist" (kit_depth of the plan row).

How it counts (reuses lane_asbuilt_latency.check, the LATCHECK counter, per plan lane; both ends + ft hops):
  source  u_bout_<o> face + u_bout_<o>_pad<j> + u_ist_<o>_<j> + core pin-face chain + u_lob_ + kit chain
  ft      u_ft_ / u_fx_ (gen: u_ft_<slot>_s<j>) in every ft partition of the lane's port chain
  landing bound clock-landing cycles (bind_clock_landings / gen_clock_landings.json, else latency clock_landing)
  receiver u_bin_<i> face + pads + u_lpad_<i> D + u_ist_ + core chain + kit chain
The difference to LATCHECK: the "kit chain" (stations the kit will insert from plan rows) is credited only where a kit
really inserts them: a BOUND type (strict bind OUT, bind_report.json + rtl/: kit_istations runs on every bound kit), or a
gen type with realize_internal_stations (its stations are already u_ist_ in the gen wrapper).  A plan row on any other gen
type is a phantom.  shortfall = latency table cycles - registers found.

Scope: lanes whose fixed_cycles / latency row / port chain / end-bus station rows / ft slot rows differ from a baseline
(kw baseline=<plan path or dict>, else the plan named by <plan dir>/bind_of_record/provenance_bind.json or the bind OUT's
provenance when it is another plan); a changed lane is flagged when its shortfall grows vs the baseline (same RTL).
Without a baseline every lane is checked (time-capped) and a lane is flagged only when its shortfall exceeds its own
fixed_cycles (s81_head convention --fixed-in-core: fixed cycles may be registers inside the core, e.g. CTL_PRE x_o; those
are counted as "in-core claims, unverified").  A bound bind of ANOTHER plan cannot speak for a changed lane (the re-bind
pads the table at the receiver, bind.lane_pad, so a bound lane always gets its registers): summary line only.

    findings(raw, plan_path, tree=None, baseline=None, bind_out=None, rtl=None, asbuilt=None) -> ["WARN ADV-PHANTOM-STATION ..."]
bind_out: a strict bind OUT dir (bound mode) or a gen.py rtl output dir / its parent with gen/ (gen mode; the plan dir's
published/ kit RTL is read first, as gen_lane_latcheck --rtl published --rtl gen).  rtl: explicit gen RTL dir list.
"""
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

CHECK = "PHANTOM-STATION"
TAG = f"WARN ADV-{CHECK}"
CAP = 20
TIME_CAP_S = 45.0
HERE = Path(__file__).resolve().parent


def _w(obj, msg):
    return f"{TAG} {obj}: {msg}"


def _libs(tree):
    """lane_asbuilt_latency + gen_lane_latcheck of this tools dir, else the tree's (import errors propagate)."""
    for d in [HERE] + ([Path(tree) / "tools" / "die_plan"] if tree else []):
        if (d / "lane_asbuilt_latency.py").is_file():
            if str(d) not in sys.path:
                sys.path.insert(0, str(d))
            import lane_asbuilt_latency as LAL  # noqa: E402
            import gen_lane_latcheck as GL  # noqa: E402
            return LAL, GL
    raise ImportError("lane_asbuilt_latency.py not found beside this module or under tree/tools/die_plan")


def _sha12(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()[:12]


def _parts(plan):
    p = plan.get("partitions") or []
    return {x["name"]: x for x in p} if isinstance(p, list) else dict(p)


def _is_bound(d):
    return bool(d) and os.path.isfile(os.path.join(d, "bind_report.json")) and os.path.isdir(os.path.join(d, "rtl"))


def _has_sv(d):
    try:
        return os.path.isdir(d) and any(n.endswith(".sv") for n in os.listdir(d))
    except OSError:
        return False


def _has_wrappers(d, raw):
    """a gen RTL dir: holds the <module>.sv wrapper of at least one plan type (a bind dir with only lib stubs is not)"""
    if not _has_sv(d):
        return False
    mods = {t.get("module") for t in (raw.get("partition_types") or {}).values() if isinstance(t, dict)}
    return any(m and os.path.isfile(os.path.join(d, m + ".sv")) for m in mods)


def _locate(raw, plan_path, tree, bind_out, rtl):
    """-> (mode 'bound'|'gen', bound dir or list of gen rtl dirs) or (None, reason)"""
    pd = os.path.dirname(os.path.abspath(plan_path)) if plan_path else None

    def gen_dir(d):
        return _has_wrappers(d, raw)
    pub = [os.path.join(pd, "published")] if pd and gen_dir(os.path.join(pd, "published")) else []
    if rtl:
        dirs = [rtl] if isinstance(rtl, str) else list(rtl)
        return "gen", [d for d in dirs if gen_dir(d)]
    if bind_out:
        for c in (bind_out, os.path.join(bind_out, "bind"), os.path.join(bind_out, "out")):
            if _is_bound(c):
                return "bound", c
        for c in (os.path.join(bind_out, "gen"), bind_out):
            if gen_dir(c):
                return "gen", pub + [c]
        why = ("bind not finished: no bind_report.json" + ("; PLAN_GATE_PRE_REFUSED.txt present"
               if os.path.isfile(os.path.join(bind_out, "PLAN_GATE_PRE_REFUSED.txt")) else "")
               if os.path.isdir(bind_out) else "missing")
        return None, (f"bind_out {bind_out}: {why} (neither a strict bind OUT with bind_report.json + rtl/ nor a gen "
                      f"RTL dir with plan wrappers)")
    try:
        import adv_port_pin as PP  # noqa: E402
        b = PP.find_bind_out(raw, plan_path, tree, None)
    except Exception:
        b = None
        cands = ([os.path.join(pd, "bind_of_record")] if pd else []) + (
            [os.path.join(tree, "physical", "die_plan", d, "plan_of_record", x)
             for d in sorted(os.listdir(os.path.join(tree, "physical", "die_plan")))
             for x in ("bind_of_record", os.path.join("native_bind", "out"))]
            if tree and os.path.isdir(os.path.join(tree, "physical", "die_plan")) else [])
        b = next((c for c in cands if _is_bound(c)), None)
    if b:
        return "bound", b
    if pd:
        for c in (os.path.join(pd, "gen"), os.path.join(pd, "bind", "gen")):
            if gen_dir(c):
                return "gen", pub + [c]
    if pub:
        return "gen", pub
    return None, "no bound RTL for this plan (no strict bind OUT, no gen RTL dir); pass bind_out= or rtl="


def _load_plan(x):
    if isinstance(x, dict):
        return x, None
    with open(x) as f:
        return json.load(f), x


def _bind_plan(B, tree):
    """the plan path a strict bind OUT was made from (provenance_bind.json), or None"""
    try:
        with open(os.path.join(B, "provenance_bind.json")) as f:
            pp = (json.load(f).get("provenance") or {}).get("plan")
    except Exception:
        return None
    if not pp:
        return None
    cands = [pp] if os.path.isabs(pp) else [os.path.join(x, pp) for x in (tree, os.path.dirname(B),
                                                                           os.path.join(B, "..", "..", "..", "..", ".."))
                                            if x]
    for c in cands:
        if os.path.isfile(c):
            return os.path.normpath(c)
    return None


# ---- lane signatures (changed-lane scope) ---------------------------------------------------------------------------
def _row_index(types):
    """{(type, bus): sorted station depths of its bus:<bus> rows}"""
    out = {}
    for tn, t in types.items():
        if not isinstance(t, dict):
            continue
        for e in t.get("internal_stations") or []:
            c = str(e.get("conn", ""))
            if c.startswith("bus:"):
                out.setdefault((tn, c[4:]), []).append(len(e.get("regs_um") or []))
    return {k: sorted(v) for k, v in out.items()}


def _ft_sig(t, bus):
    slot = bus[:-2] if bus.endswith("_o") else bus
    for s in (t or {}).get("ft_slots") or []:
        if s.get("name") in (slot, bus):
            return {k: (len(v) if isinstance(v, list) else v) for k, v in sorted(s.items())
                    if ("reg" in k or "station" in k or "site" in k) and not isinstance(v, dict)}
    return None


def lane_info(plan):
    """{lane: dict(src, dst, src_type, dst_type, bus_out, bus_in, fixed, rows_out, rows_in, sig)}"""
    parts, types = _parts(plan), plan.get("partition_types") or {}
    ports = {x["id"]: x for x in plan.get("ports") or [] if isinstance(x, dict) and "id" in x}
    lat = (plan.get("latency") or {}).get("lanes") or {}
    idx = _row_index(types)
    out = {}
    for ln in plan.get("lanes") or []:
        if not isinstance(ln, dict) or "id" not in ln:
            continue
        hp = [ports[q] for q in ln.get("ports") or [] if q in ports]
        if not hp:
            continue
        a, z = hp[0], hp[-1]
        s, d = a["src"]["part"], z["dst"]["part"]
        if s.startswith("@") or d.startswith("@"):
            continue
        st, dt = (parts.get(s) or {}).get("type"), (parts.get(d) or {}).get("type")
        bo, bi = a["src"]["bus"], z["dst"]["bus"]
        ro, ri = idx.get((st, bo), []), idx.get((dt, bi), [])
        hops = []
        for x, y in zip(hp, hp[1:]):
            fp = x["dst"]["part"]
            hops.append((fp, y["src"]["bus"], _ft_sig(types.get((parts.get(fp) or {}).get("type")), y["src"]["bus"])))
        L = {k: v for k, v in (lat.get(ln["id"]) or {}).items() if k not in ("param", "note")}
        sig = json.dumps([ln.get("fixed_cycles"), ln.get("ports"), L, st, dt, ro, ri, hops], sort_keys=True, default=str)
        out[ln["id"]] = dict(src=s, dst=d, src_type=st, dst_type=dt, bus_out=bo, bus_in=bi,
                             fixed=int(ln.get("fixed_cycles") or 0), rows_out=ro, rows_in=ri, hops=hops, sig=sig,
                             table=L)
    return out


# ---- counting ---------------------------------------------------------------------------------------------------------
def _gen_types(plan):
    """plan types as the HEAD gen kit realizes them: a gen type without realize_internal_stations keeps no bus station
    rows (nothing inserts them); declared hard-core cycles (core_latency) stay"""
    out = {}
    for tn, t in (plan.get("partition_types") or {}).items():
        if isinstance(t, dict) and not t.get("realize_internal_stations") and t.get("internal_stations"):
            t = dict(t, internal_stations=[e for e in t["internal_stations"]
                                           if not str(e.get("conn", "")).startswith("bus:")])
        out[tn] = t
    return out


def _gen_landings(dirs):
    for d in dirs:
        f = os.path.join(d, "gen_clock_landings.json")
        if os.path.isfile(f):
            try:
                with open(f) as fh:
                    return {k: int(v) for k, v in (json.load(fh).get("lane_added_cycles") or {}).items()}
            except Exception:
                return None
    return None


def _count_gen_fast(LAL, GL, plan, dirs, lanes, deadline):
    """{lane: LAL.check record} on gen RTL dirs with the kit chain credited per _gen_types -> (recs, landings?, done, n)"""
    gt = _gen_types(plan)
    parts = _parts(plan)
    rows, _ = GL.lane_rows(plan)
    rows = [r for r in rows if r["lane"] in lanes]
    land = _gen_landings(dirs)
    lat = (plan.get("latency") or {}).get("lanes") or {}
    landing_of = (land.get if land is not None else
                  (lambda ln: int((lat.get(ln) or {}).get("clock_landing", 0) or 0)))
    module_of, _ = GL.load_modules(plan, dirs)
    out, done = {}, 0
    for i in range(0, len(rows), 200):
        if time.time() > deadline:
            break
        recs, _ = LAL.check(plan, rows[i:i + 200], module_of, lambda p: (parts.get(p) or {}).get("type"), gt, landing_of)
        for x in recs:
            out[x["lane"]] = x
        done = i + 200
    return out, land is not None, min(done, len(rows)), len(rows)


def _count_bound(LAL, plan, plan_path, B, lanes, deadline):
    """{lane: record} of a same-plan strict bind: the bind's own in-bind LATCHECK records (bind_lane_asbuilt.json,
    lane_asbuilt_latency.bind_check: the module map of the bind itself), else the standalone reader"""
    f = os.path.join(B, "bind_lane_asbuilt.json")
    if os.path.isfile(f):
        with open(f) as fh:
            recs = {r["lane"]: r for r in json.load(fh).get("lanes") or [] if r.get("lane") in lanes}
        return recs, len(recs), len(recs)
    rows, module_of, ptype_of, types, landing_of, _ = LAL.load_bind_dir(B, plan, plan_path)
    rows = [r for r in rows if r.get("lane") in lanes]
    out, done = {}, 0
    for i in range(0, len(rows), 200):
        if time.time() > deadline:
            break
        recs, _ = LAL.check(plan, rows[i:i + 200], module_of, ptype_of, types, landing_of)
        for x in recs:
            out[x["lane"]] = x
        done = i + 200
    return out, min(done, len(rows)), len(rows)


def _short(rec):
    if rec.get("verdict") == "UNOBSERVED" or "delivered" not in rec:
        return None
    return int(rec["table"]) - int(rec["delivered"])


def _found(rec):
    s, d = rec.get("source", {}), rec.get("receiver", {})

    def side(x, io):
        return (f"{io} face {x.get('face', 0)} pads {x.get('pads', 0)} ist {x.get('bound_ist', 0)} "
                f"core {x.get('core_chain', 0)}" + (f" lpad D{x['lpad']}" if x.get("lpad") else "")
                + (f" kit {x['kit_ist']}" if x.get("kit_ist") else "") + (f" lob {x['bound_lob']}" if x.get("bound_lob") else ""))
    return f"{side(s, 'src')}; ft {rec.get('ft', 0)}; landing {rec.get('landing', 0)}; {side(d, 'dst')}"


def findings(raw, plan_path, tree=None, baseline=None, bind_out=None, rtl=None, asbuilt=None, **kw):
    try:
        t0 = time.time()
        deadline = t0 + TIME_CAP_S
        mode, where = _locate(raw, plan_path, tree, bind_out, rtl)
        if mode is None:
            return [_w("not checked", where)]
        if mode == "gen" and not where:
            return [_w("not checked", "gen RTL dir list is empty")]
        LAL, GL = _libs(tree)
        info = lane_info(raw)
        if not info:
            return [_w("not checked", "plan has no partition-to-partition lanes (lanes[] + ports[])")]
        # baseline
        base, bnote = None, ""
        bind_plan = _bind_plan(where, tree) if mode == "bound" else None
        same_bind = None
        if mode == "bound" and bind_plan and plan_path and os.path.isfile(plan_path):
            same_bind = os.path.realpath(bind_plan) == os.path.realpath(plan_path) or _sha12(bind_plan) == _sha12(plan_path)
        if baseline is not None:
            base, bp = _load_plan(baseline)
            bnote = f"baseline {os.path.basename(bp) if bp else 'dict'}"
        else:
            pd = os.path.dirname(os.path.abspath(plan_path)) if plan_path else ""
            bp = _bind_plan(os.path.join(pd, "bind_of_record"), tree or pd) if pd else None
            if not bp and mode == "bound" and same_bind is False:
                bp = bind_plan
            if bp and plan_path and os.path.isfile(bp) and _sha12(bp) != _sha12(plan_path):
                base, _ = _load_plan(bp)
                bnote = f"baseline = bind provenance plan {_sha12(bp)}"
        if base is not None:
            binfo = lane_info(base)
            scope = sorted(k for k, v in info.items() if k not in binfo or binfo[k]["sig"] != v["sig"])
        else:
            binfo = {}
            scope = sorted(info)
            bnote = "no baseline: all lanes, flagged only when shortfall > lane fixed_cycles"
        if not scope:
            return [_w("summary", f"0 lane(s) flagged; 0 lanes changed vs {bnote}; {mode} RTL "
                                  f"{where if mode == 'bound' else ', '.join(where)}; {time.time() - t0:.1f} s")]
        if mode == "bound" and same_bind is not True:
            return [_w("summary", f"0 lane(s) flagged; {len(scope)} lane(s) changed ({bnote or 'no baseline'}) but the bind "
                                  f"OUT {where} is of plan {(_sha12(bind_plan) if bind_plan else '?')} != this plan: a "
                                  f"re-bind pads each bound lane to its table at the receiver (bind.lane_pad) and the kit "
                                  f"inserts every bus row (kit_istations), so a bound lane cannot go phantom; first "
                                  f"changed {', '.join(scope[:6])}; {time.time() - t0:.1f} s")]
        # count
        if mode == "gen":
            recs, has_land, done, nrows = _count_gen_fast(LAL, GL, raw, where, set(scope), deadline)
            brecs = {}
            if base is not None:
                bl = [k for k in scope if k in binfo]
                brecs, _, _, _ = _count_gen_fast(LAL, GL, base, where, set(bl), deadline + 10)
        else:
            # the bind's own plan path (same sha): count-frame / feed files resolve relative to it
            recs, done, nrows = _count_bound(LAL, raw, bind_plan or plan_path, where, set(scope), deadline)
            has_land, brecs = True, {}
        flagged, in_core, unobs, rowsph = [], 0, 0, 0
        gt = raw.get("partition_types") or {}
        for ln in scope:
            r = recs.get(ln)
            if r is None:
                continue
            sh = _short(r)
            if sh is None:
                unobs += 1
                continue
            I = info[ln]
            ph_rows = []
            if mode == "gen":
                for tt, bus, dep, side in ((I["src_type"], I["bus_out"], I["rows_out"], "out"),
                                           (I["dst_type"], I["bus_in"], I["rows_in"], "in")):
                    if dep and not (gt.get(tt) or {}).get("realize_internal_stations"):
                        ph_rows.append((tt, bus, max(dep)))
            if ph_rows:
                rowsph += 1
            if ln in brecs and _short(brecs[ln]) is not None:
                lim, why = max(0, _short(brecs[ln])), f"baseline shortfall {max(0, _short(brecs[ln]))}"
            elif base is not None and ln in binfo:
                lim, why = I["fixed"], f"baseline unobserved; fixed_cycles {I['fixed']} allowed in-core"
            elif base is not None:
                lim, why = I["fixed"] if mode == "gen" else 0, "new lane"
            else:
                lim = I["fixed"] if mode == "gen" else 0
                why = f"fixed_cycles {I['fixed']} allowed in-core" if mode == "gen" else "bound"
            if sh > lim:
                flagged.append((ln, sh, lim, why, r, I, ph_rows))
            elif sh > 0:
                in_core += 1
        out = []
        for ln, sh, lim, why, r, I, ph in flagged[:CAP]:
            tb = I["table"]
            rowtxt = "; ".join(f"{tt}.internal_stations bus:{b} {d} reg(s) on a gen type without "
                               f"realize_internal_stations (no kit inserts it)" for tt, b, d in ph)
            fix = (f"set partition_types.{ph[0][0] if ph else '?'}.realize_internal_stations true (gen_rtl emits the "
                   "u_ist_ chain) or add the stage to the core RTL; else drop the row and the +cycles (lanes.fixed_cycles, "
                   "latency row)"
                   if ph else "land the missing stage(s) (station row the kit realizes, ft register, receiver pad) or "
                              "re-price the lane (fixed_cycles / latency)")
            out.append(_w(f"lane {ln}", f"{I['src']}.{I['bus_out']} -> {I['dst']}.{I['bus_in']}: plan {r['table']} "
                                        f"cycles (fixed {tb.get('fixed', I['fixed'])}, stations {tb.get('stations', '-')}, "
                                        f"boundary {tb.get('boundary', '-')}) vs {r['delivered']} register stage(s) in the "
                                        f"bound RTL ({_found(r)}): {sh} phantom cycle(s) vs {lim} allowed ({why})"
                                        + (f"; {rowtxt}" if rowtxt else "") + f". Fix: {fix}"))
        cov = (f"{done}/{nrows} lane rows counted" + (" (time cap)" if done < nrows else ""))
        out.append(_w("summary", f"{len(flagged)} lane(s) flagged; {len(scope)} lane(s) in scope ({bnote}); {cov}; "
                                 f"{in_core} with shortfall within fixed_cycles/baseline (in-core claims, unverified); "
                                 f"{rowsph} carry station rows no gen kit realizes; {unobs} unobserved; {mode} RTL "
                                 f"{where if mode == 'bound' else ', '.join(where)}"
                                 + ("" if has_land else "; landing cycles from the latency table")
                                 + (f"; first {CAP} shown" if len(flagged) > CAP else "") + f"; {time.time() - t0:.1f} s"))
        return out
    except (Exception, SystemExit) as e:  # never raise (lane_asbuilt_latency exits on a bad bind dir)
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:300]}")]


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--tree")
    ap.add_argument("--baseline")
    ap.add_argument("--bind-out")
    ap.add_argument("--rtl", action="append")
    a = ap.parse_args(argv)
    t0 = time.time()
    with open(a.plan) as f:
        raw = json.load(f)
    t1 = time.time()
    for x in findings(raw, a.plan, a.tree, baseline=a.baseline, bind_out=a.bind_out, rtl=a.rtl):
        print(x)
    print(f"# load {t1 - t0:.1f} s, check {time.time() - t1:.1f} s")


if __name__ == "__main__":
    main()
