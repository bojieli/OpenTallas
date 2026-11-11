#!/usr/bin/env python3
"""DIE-S81-85 LATETAP-PAD-1111: designed landed delay (METHODOLOGY 12.8d2 residual tap pads) on the E-early die taps of
the S81 types whose measured kit tap window exceeds the T/4 cap (one plan event, re-basable).

COORD ruling (11-11, via DIE-S81-85): 27 S81 types / 153 ports need a kit tap window above T/4 = 208 ps (T = 833 ps) on
DIE-RECHECK-1's routed recheck of plan 66466e86ebcd (kitwin_auto_66466e86ebcd.json).  A window cannot fix them; give
them a structural fix, the SMALLER of (A) a designed delay in the die clock tree or (B) pin cycles.

Measure (die_sta_related.kit_port_needs, nominal 12.24b: early := late, CPPR 0): the window of kit port p of a
partition is max over the partition's other taps q of E(q) - E(p), E = routed tap arrival + declared early-core-tap
earliness (the kit SDC source latency -early of a clk_c<k> core tap).  It is a property of the clock arrivals of the
partition's taps only: no logic path enters it.  Cause on 66466e86ebcd (TT binding; 259 instance taps over 208):
  COL   22 col_h9/col_h10 ROM-column types, 232 instance taps in 80 partitions: capture = an early core tap clk_c<k>
        (declared earliness 250 TT / 202.5 FF; region DME 'merge' early sink) whose E sits 128-210 ps (median 179) above
        the plain-tap median (the DME delivers ~70 of the 250 ps declared earliness), launch = the earliest plain grid
        taps (median 49 ps below the plain median, up to 117).  Every region is in the DME list; same region root on
        both sides (feed depth cancels); stage count difference -4..+4.
  BKSEL bk_sel__t2, 20 taps: capture clk_c4 (earliness 579 TT) E 202 ps above the plain median.
  LEAF  ot_s81sl_leaf__t8 / __t22, 1 tap each: one plain tap 70-112 ps below the median (10-12 fewer stages than the
        capture), capture early core tap E 105-140 above.
  SVCRS svc_hi_dsdv_svc_rs__t6 / __t2: plain clk_t1..t3 74-109 ps below the median vs core taps c40/c60.
(B) pin cycles cannot change this number (it has no path term) -> (A) for every group.

(A) form = the S81 residual tap-pad form already in use (DIE-S81-43 / S81-REGTREE-3, CLOCK-RESIDUAL ledger): n
BUFx24 cells in series on the last leg of each E-early tap (die_trial --tap-pad / ot_clk residual.tap_pad), n =
ceil((need_c - (CAP - MARGIN)) / PAD_PS_c) maxed over TT/FF, on every instance tap of a blocked type whose need exceeds
CAP - MARGIN.  A padded tap stays below the partition's latest E (asserted), so no other port's window grows and
every launch stays inside the kit's [-W, 0] window (no setup cost against the kit contract).

The plan records the table as clock.cohort.tap_pad (clock.cohort is the authoritative die-clock cohort record; no kit
or build consumer reads it, so every partition type stays byte-identical and no kit input changes); the die clock
recipe takes the sidecar events/latetap_pad_1111/tap_pad.json with residual.tap_pad (same bytes, asserted).

usage: delta_latetap_pad_1111.py derive PROOF_DIR PLAN OUT_PAD.json         (fit the table on a routed recheck proof)
       delta_latetap_pad_1111.py apply PLAN_IN PLAN_OUT [REPORT.json]        (record events/.../tap_pad.json in the plan)
       delta_latetap_pad_1111.py --check PLAN_IN PLAN_OUT                    (re-apply, assert byte-identical output)
       delta_latetap_pad_1111.py delta FIT.json PADS_DELTA.json                (tap-keyed, base-agnostic delta from a fit)
       delta_latetap_pad_1111.py apply-delta PLAN_IN PLAN_OUT PADS_DELTA.json [REPORT.json]
                                    (any base: asserts every tap's partition/type and that only clock.cohort.tap_pad moves)
Re-basing onto another plan (e.g. the SVCPROV-V5 combined plan): derive on that plan's routed recheck proof, replace the
sidecar + BASE_SHA, apply.  derive needs tools/die_plan (die_sta_related, schema, gen_phys) and git on PATH.
Optional events/latetap_pad_1111/kitwin_after.json (die_sta_related --kit-window-out on the PADDED tree of the fit plan):
apply also raises the per-port windows of the padded types to the padded measurement (max(current, measured), <= CAP).

FORM PROOF on 66466e86ebcd (events/latetap_pad_1111/verify_66466e_pad1.json): fit tap_pad_fit_66466e.json (450 taps,
593 BUFx24, 1/2/3/4/5 pads on 339/86/19/5/1 taps; COL 419 taps / 543 pads, BKSEL 23/42, LEAF 2/2, SVCRS 6/6) built
with the DIE-RECHECK-1 recipe + residual.tap_pad: the 153 ports of the 27 types are <= 200 ps (were 209-296), 0 die
types over 208 (were 27), the 10553 ports of the other types unchanged to the ps (unpadded tap arrivals move <= 0.5
ps), TT intra setup 386.41 -> 466.41, intra skew TT 295 -> 206 / FF 241 -> 170, landed class unchanged.  Measured
per-pad delay TT 21.4-32.5 (median 25.3) / FF 16.5-25.9 (median 19.6): the PAD_PS lower bound holds on every tap.
STATUS: BASE_SHA = the combined plan 99f40d35071d; its routed recheck (the fit input) cannot be built yet: the 14 svc_rs
types carry hard_cores physical_master without physical_inst (gen_phys.content_physical_identity ValueError, the
SVCPROV-V5 defect, also in 5d1555dc7d74).  After that fix: recheck -> derive -> tap_pad.json -> apply."""
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "tools" / "die_plan")]

EVENT = "LATETAP-PAD-1111"
EV = HERE / "events" / "latetap_pad_1111"
BASE_SHA = "99f40d35071d66bf2edd2b81f4d7046598f297bbf0b1b3884006252e85172eb9"   # FEED-BAL-2-1111 on SVCPROV-V5 (ca10ae6afbab)
CAP_PS = 208.0          # T/4, T = 833 ps (gen_phys tap window bound)
MARGIN_PS = 8.0         # re-route perturbation of a padded tree (neighbour legs move with the pad placement)
PAD_PS = {"TT": 20.0, "FF": 16.0}   # lower bound per BUFx24 tap pad (S81-REGTREE-3: +18..27 FF; DIE-S81-43 dE 20/dL 25)
MAX_PADS = 6
CORE_RE = re.compile(r"__clk_c\d+$")


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def plan_types(plan):
    return {p["name"]: p["type"] for p in plan["partitions"]}


def effective(proof, plan, plan_path):
    """{corner: {port: (part, E)}} with E = nominal routed late arrival + kit earliness offset (kit_port_needs)."""
    import die_sta_related as D
    out, ecm = {}, None
    for c in ("TT", "FF"):
        meta, taps = D.load_taps(Path(proof), c)
        meta, taps = D.single_arrival(meta, taps, D.NOMINAL_ARRIVAL_DEFAULT)
        rng = D.clock_cppr_ranges(meta)
        if ecm is None:
            ecm = D.early_core_map(plan, taps, plan_path=plan_path)
        ko = {p: m[0]["early_ps"][c] for p, m in ecm.items()}
        e = {}
        for p, r in taps.items():
            if r.get("part") is None:
                continue
            e[p] = (r["part"], r["late_ps"] + ko.get(p, 0.0))
        out[c] = (e, rng, taps, ko)
    return out


def needs(E):
    """{port: (need, worst capture port)} per partition: max over the partition's other taps of E(q) - E(p)."""
    by = defaultdict(list)
    for p, (part, v) in E.items():
        by[part].append((v, p))
    out = {}
    for part, rows in by.items():
        rows.sort()
        top, top_p = rows[-1]
        sec = rows[-2] if len(rows) > 1 else rows[-1]
        for v, p in rows:
            q, qp = (top, top_p) if p != top_p else sec
            out[p] = (q - v if len(rows) > 1 else 0.0, qp)
    return out


def derive(proof, plan_path, out_path):
    plan = json.loads(Path(plan_path).read_text())
    ptype = plan_types(plan)
    ev = effective(proof, plan, plan_path)
    import die_sta_related as D
    # exactness: the closed form above == kit_port_needs (same-root pairs, nominal => credit 0)
    for c in ("TT", "FF"):
        E, rng, taps, ko = ev[c]
        assert all(abs(v) < 1e-9 for v in rng.values()), "nominal arrivals expected (CPPR range 0)"
    nd = {c: needs(ev[c][0]) for c in ("TT", "FF")}
    tmax = defaultdict(float)
    for c in nd:
        for p, (v, _) in nd[c].items():
            tmax[ptype[ev[c][0][p][0]]] = max(tmax[ptype[ev[c][0][p][0]]], math.ceil(v - 1e-9))
    blocked = sorted(t for t, v in tmax.items() if v > CAP_PS)
    bparts = sorted(p for p, t in ptype.items() if t in blocked)
    pads, rows = {}, []
    for p in sorted(nd["TT"]):
        part = ev["TT"][0][p][0]
        if ptype[part] not in blocked:
            continue
        n = 0
        for c in ("TT", "FF"):
            over = nd[c][p][0] - (CAP_PS - MARGIN_PS)
            if over > 0:
                n = max(n, math.ceil(over / PAD_PS[c] - 1e-9))
        if n:
            if n > MAX_PADS:
                raise SystemExit(f"{p}: {n} pads > {MAX_PADS}")
            pads[p] = n
            rows.append(dict(port=p, part=part, type=ptype[part], pads=n,
                             need_tt=round(nd["TT"][p][0], 2), need_ff=round(nd["FF"][p][0], 2),
                             capture_tt=nd["TT"][p][1], core_tap=bool(CORE_RE.search(p))))
    # predicted after-state with the lower-bound pad model: every padded tap stays below its partition's latest E,
    # and every port of the blocked types is <= CAP - MARGIN
    pred = {}
    for c in ("TT", "FF"):
        E = {p: (part, v + PAD_PS[c] * pads.get(p, 0)) for p, (part, v) in ev[c][0].items()
             if ptype[part] in blocked}
        n2 = needs(E)
        pred[c] = max(v for v, _ in n2.values())
        for p in pads:
            part = E[p][0]
            top = max(v for q, (pt, v) in E.items() if pt == part and q != p)
            assert E[p][1] < top, f"{p}: padded tap would become the latest of {part}"
        before = nd[c]
        grown = [p for p in n2 if n2[p][0] > before[p][0] + 1e-6]
        assert not grown, f"{c}: pads raise the window of {grown[:5]}"
    assert max(pred.values()) <= CAP_PS - MARGIN_PS + 1e-6, pred
    hist = defaultdict(int)
    for v in pads.values():
        hist[v] += 1
    grp = defaultdict(lambda: dict(taps=0, pads=0, parts=set(), types=set()))
    for r in rows:
        g = ("COL" if r["type"].startswith("col_") else "BKSEL" if r["type"].startswith("bk_sel")
             else "LEAF" if "leaf" in r["type"] else "SVCRS")
        grp[g]["taps"] += 1
        grp[g]["pads"] += r["pads"]
        grp[g]["parts"].add(r["part"])
        grp[g]["types"].add(r["type"])
    rec = dict(
        event=EVENT, cell="BUFx24_ASAP7_75t_R", form="die_trial --tap-pad (METHODOLOGY 12.8d2 residual tap pad)",
        plan_sha256=sha256(plan_path),
        proof=dict(dir=str(proof), **{f"tap_arrivals_{c}.json": sha256(Path(proof) / f"tap_arrivals_{c}.json")
                                      for c in ("TT", "FF")}),
        rule=dict(cap_ps=CAP_PS, margin_ps=MARGIN_PS, pad_ps=PAD_PS, max_pads=MAX_PADS,
                  n="ceil((need_c - (cap - margin)) / pad_ps_c), max over TT/FF, every instance tap of a type "
                    "whose measured window > cap"),
        blocked_types=blocked, blocked_type_max_ps={t: tmax[t] for t in blocked}, blocked_partitions=len(bparts),
        taps=len(pads), cells=sum(pads.values()), pads_per_tap_hist=dict(sorted(hist.items())),
        groups={g: dict(taps=v["taps"], pads=v["pads"], partitions=len(v["parts"]), types=len(v["types"]))
                for g, v in sorted(grp.items())},
        predicted_max_need_ps={c: round(v, 2) for c, v in pred.items()},
        pad=dict(sorted(pads.items())), rows=rows)
    Path(out_path).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("taps", "cells", "pads_per_tap_hist", "groups", "predicted_max_need_ps")}))


def cohort_record(side):
    s = json.loads(side.read_text())
    return dict(id="s81_latetap_pad_1111", authority="COORD 11-11 ruling via DIE-S81-85: 27 types / 153 ports above "
                "T/4 get the smaller structural fix; (A) designed tap delay chosen for all groups (pin cycles do not "
                "enter the measured window)", event=EVENT, cell=s["cell"], form=s["form"],
                sidecar="physical/die_plan/s81/events/latetap_pad_1111/tap_pad.json",
                sidecar_sha256=sha256(side), fit_plan_sha256=s["plan_sha256"], fit_proof=s["proof"], rule=s["rule"],
                blocked_types=s["blocked_types"], taps=s["taps"], cells=s["cells"], pad=s["pad"])


def apply(plan_in, plan_out, report=None, check=False):
    raw = Path(plan_in).read_bytes()
    base = hashlib.sha256(raw).hexdigest()
    if base != BASE_SHA:
        raise SystemExit(f"base plan sha {base[:12]} != {BASE_SHA[:12]}")
    side = EV / "tap_pad.json"
    plan = json.loads(raw)
    if json.dumps(plan, indent=1).encode() + (b"\n" if raw.endswith(b"\n") else b"") != raw:
        raise SystemExit("plan is not in the canonical indent-1 form; text edit needed")
    taps_of = {f"t_{p['name']}__" for p in plan["partitions"]}
    rec = cohort_record(side)
    bad = [p for p in rec["pad"] if not any(p.startswith(x) for x in taps_of)]
    if bad:
        raise SystemExit(f"pad ports of no partition: {bad[:5]}")
    ptype = plan_types(plan)
    for t in rec["blocked_types"]:
        if t not in plan["partition_types"]:
            raise SystemExit(f"blocked type {t} not in plan")
    kwp = EV / "kitwin_after.json"
    raised = {}
    if kwp.is_file():
        # padded-tree measurement: a port of a padded type whose measured window exceeds its plan window is raised to
        # it (FEED-BAL rule max(current, measured), ceil 1 ps); every value must be <= CAP (the point of the event)
        kw = json.loads(kwp.read_text())
        if kw["plan_sha256"] != rec["fit_plan_sha256"]:
            raise SystemExit("kitwin_after.json was not measured on the fit plan")
        tw = plan["clock"]["tap_window"]
        pp = tw.setdefault("per_port_ps", {})
        for t in sorted({ptype[p[2:].split("__")[0]] for p in rec["pad"]}):
            for port, v in sorted(kw["per_port_ps"][t].items()):
                if v > CAP_PS:
                    raise SystemExit(f"{t}.{port}: measured {v} > cap {CAP_PS} on the padded tree")
                cur = pp.get(t, {}).get(port, (tw.get("per_type_ps") or {}).get(t, tw["window_ps"]))
                if v > cur:
                    raised.setdefault(t, {})[port] = [cur, v]
        for t, d in raised.items():
            if t not in pp:
                raise SystemExit(f"{t}: no per-port table to raise")
            for port, (_, v) in d.items():
                pp[t][port] = int(v) if float(v).is_integer() else v
        rec["window_raise"] = dict(source="events/latetap_pad_1111/kitwin_after.json", sha256=sha256(kwp),
                                   types=len(raised), ports=sum(len(d) for d in raised.values()))
    if "tap_pad" in plan["clock"]["cohort"]:
        raise SystemExit("clock.cohort.tap_pad already present")
    base_plan = json.loads(raw)
    plan["clock"]["cohort"]["tap_pad"] = rec
    assert json.dumps(plan["partition_types"], sort_keys=True) == json.dumps(base_plan["partition_types"], sort_keys=True)
    assert all(plan[k] == base_plan[k] for k in plan if k != "clock")
    assert all(plan["clock"][k] == base_plan["clock"][k] for k in plan["clock"] if k not in ("cohort", "tap_window"))
    tw0, tw1 = base_plan["clock"]["tap_window"], plan["clock"]["tap_window"]
    assert {k: v for k, v in tw0.items() if k != "per_port_ps"} == {k: v for k, v in tw1.items() if k != "per_port_ps"}
    assert {t for t in tw1.get("per_port_ps", {}) if tw1["per_port_ps"][t] != tw0.get("per_port_ps", {}).get(t)} \
        == set(raised)
    out = json.dumps(plan, indent=1).encode() + (b"\n" if raw.endswith(b"\n") else b"")
    osha = hashlib.sha256(out).hexdigest()
    if check:
        cur = Path(plan_out).read_bytes()
        if cur != out:
            raise SystemExit(f"--check: {plan_out} differs from the re-derived output ({osha[:12]})")
        print(json.dumps(dict(check="PASS", output_plan_sha256=osha)))
        return
    Path(plan_out).write_bytes(out)
    by_t = defaultdict(int)
    for p in rec["pad"]:
        by_t[ptype[p[2:].split("__")[0]]] += 1
    rep = dict(event=EVENT, base_plan_sha256=base, output_plan_sha256=osha, sidecar_sha256=rec["sidecar_sha256"],
               changed_keys=["clock.cohort.tap_pad"] + (["clock.tap_window.per_port_ps"] if raised else []),
               partition_types_changed=0, window_raised=raised, relaunch_types=sorted(by_t),
               padded_taps=rec["taps"], pad_cells=rec["cells"], padded_taps_by_type=dict(sorted(by_t.items())))
    if report:
        Path(report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("base_plan_sha256", "output_plan_sha256", "padded_taps", "pad_cells")}))


def make_delta(fit, out):
    """tap-keyed, base-agnostic pad delta from a derive fit: {type: {die tap port: pads}} (COORD 02:0x freeze: delivered
    for DIE-S81-85's combined event, re-applies onto any plan whose partitions / types carry these taps)."""
    s = json.loads(Path(fit).read_text())
    types = defaultdict(dict)
    for r in s["rows"]:
        types[r["type"]][r["port"]] = r["pads"]
    d = dict(event=EVENT, keyed_by="die tap port t_<partition>__<kit clock port>, grouped by partition type",
             changes="adds clock.cohort.tap_pad only (die-clock record read by the die clock recipe as residual.tap_pad); "
                     "no partition type, partition, port, window or latency key moves",
             cell=s["cell"], form=s["form"], rule=s["rule"], fit_plan_sha256=s["plan_sha256"], fit_proof=s["proof"],
             fit_sha256=sha256(fit), taps=s["taps"], cells=s["cells"],
             types={t: dict(sorted(v.items())) for t, v in sorted(types.items())})
    Path(out).write_text(json.dumps(d, indent=1) + "\n")
    print(json.dumps(dict(types=len(d["types"]), taps=d["taps"], cells=d["cells"])))


def apply_delta(plan_in, plan_out, delta, report=None):
    """base-agnostic apply: every pad tap must name a partition of the delta's type in PLAN_IN; adds clock.cohort.
    tap_pad (+ the residual.tap_pad sidecar {pad: ...} next to PLAN_OUT); asserts nothing else in the plan moves."""
    raw = Path(plan_in).read_bytes()
    plan = json.loads(raw)
    nl = b"\n" if raw.endswith(b"\n") else b""
    fmt = next((kw for kw in (dict(indent=1), dict()) if json.dumps(plan, **kw).encode() + nl == raw), None)
    if fmt is None:
        raise SystemExit("plan is in neither canonical json.dumps form (indent=1 / default)")
    d = json.loads(Path(delta).read_text())
    ptype = plan_types(plan)
    miss = []
    pad = {}
    for t, taps in d["types"].items():
        if t not in plan["partition_types"]:
            miss.append(f"type {t}")
            continue
        for port, n in taps.items():
            part = port[2:].split("__")[0]
            if ptype.get(part) != t:
                miss.append(f"{port}: partition {part} is {ptype.get(part)}, not {t}")
            pad[port] = int(n)
    if miss:
        raise SystemExit("delta does not fit this plan: " + "; ".join(miss[:10]) + f" ({len(miss)} total)")
    cohort = plan["clock"].setdefault("cohort", None)
    if cohort is None or "tap_pad" in cohort:
        raise SystemExit("clock.cohort missing or already has tap_pad")
    base = json.loads(raw)
    cohort["tap_pad"] = dict(id="s81_latetap_pad_1111", event=EVENT, cell=d["cell"], form=d["form"], rule=d["rule"],
                             delta_sha256=sha256(delta), fit_plan_sha256=d["fit_plan_sha256"], taps=len(pad),
                             cells=sum(pad.values()), pad=dict(sorted(pad.items())))
    assert all(plan[k] == base[k] for k in base if k != "clock") and set(plan) == set(base)
    assert all(plan["clock"][k] == base["clock"][k] for k in base["clock"] if k != "cohort")
    assert {k: v for k, v in plan["clock"]["cohort"].items() if k != "tap_pad"} == base["clock"]["cohort"]
    out = json.dumps(plan, **fmt).encode() + nl
    Path(plan_out).write_bytes(out)
    side = Path(plan_out).with_name("tap_pad_residual.json")
    side.write_text(json.dumps(dict(pad=dict(sorted(pad.items()))), indent=1) + "\n")
    rep = dict(event=EVENT, base_plan_sha256=hashlib.sha256(raw).hexdigest(),
               output_plan_sha256=hashlib.sha256(out).hexdigest(), changed_keys=["clock.cohort.tap_pad"],
               partition_types_changed=0, taps=len(pad), cells=sum(pad.values()), residual_sidecar=str(side),
               residual_sidecar_sha256=sha256(side))
    if report:
        Path(report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["derive"] and len(a) == 4:
        derive(*a[1:])
    elif a[:1] == ["apply"] and len(a) in (3, 4):
        apply(*a[1:])
    elif a[:1] == ["delta"] and len(a) == 3:
        make_delta(*a[1:])
    elif a[:1] == ["apply-delta"] and len(a) in (4, 5):
        apply_delta(*a[1:])
    elif a[:1] == ["--check"] and len(a) == 3:
        apply(a[1], a[2], check=True)
    else:
        raise SystemExit(__doc__)
