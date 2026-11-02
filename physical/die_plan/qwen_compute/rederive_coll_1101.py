#!/usr/bin/env python3
"""DIE-QC-62 11-01: re-derive the reset-collector landing data of every landed soft QC type under the CURRENT tools.

Measured failure (DIE-QC-61 bindB, DIE-QC-62 bindM): main tools on the d90 plan_qc52 + sidecar -> strict bind
'EMIT collector rst_n_t21: raw reset parent rst_rl_17 absent' (coll_ftm).  Cause: since d90 the clock-tap rules changed
(taps.py density taps on PG-legal axes / per-bit sink sites, 0ddc1ccd8c8 + 1d753c326cf), so reset_tree.for_type(coll_ftm)
now builds 70 relays (rst_n_t21 <- rst_rl_16) where the stored plan/sidecar tree has 71 (rst_n_t21 <- rst_rl_17 <- rst_rl_16).
The type body is emitted from the current tree, the collector from the stored one -> the stored data are stale.
Delta = for each landed soft type whose stored data differ from the current derivation, rewrite (plan landing_contract
AND sidecar collector.types, kept paired) with the DIE-QC-61 delta_ttctlm_1101 / compose_qc51 rules:
collector_tree = reset_tree.for_type; local source tap = nearest tap relay to the ring pin (band centre if > 405 um);
children node renumbered; forwarded clock-out pins source_clock_tap = nearest clock tap.  Nothing else changes.
usage: rederive_coll_1101.py PLAN_IN SIDECAR_IN PLAN_OUT SIDECAR_OUT [REPORT.json] [--types a,b]"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "die_plan"))
import schema as S  # noqa: E402
import gen_phys as GP  # noqa: E402
import reset_tree as RT  # noqa: E402

L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])  # noqa: E731
J = lambda v: json.dumps(v, sort_keys=True)  # noqa: E731


def derive(P, lc, tn):
    tree = json.loads(json.dumps(RT.for_type(P, tn)))
    n = RT.consumer_count(tree)
    tapxy = {int(r["q"].split("rst_n_t")[1]): r["xy"] for r in tree["relays"] if r["q"].startswith("rst_n_t")}
    srcs = []
    for s in lc.get("collector_local_sources", []):
        pt = s["pin_xy_um"]
        tap = min(range(n), key=lambda i: L1(tapxy[i], pt))
        b = s.get("band") or {}
        if b.get("rect_um") and L1(tapxy[tap], pt) > 405:
            x0, y0, x1, y1 = b["rect_um"]
            c = [round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3)]
            tap = min(range(n), key=lambda i: L1(tapxy[i], c))
        srcs.append(tap)
    # Wavefront re-siting can insert an output BEFORE an existing output. Its
    # ordinal is then different even when the consumer count is unchanged.
    # Children belong to a physical terminal, not an output-list ordinal.
    kids = []
    for c in lc.get("collector_children", []):
        if not c["node"].startswith("rst_n_t"):
            kids.append(c["node"])
            continue
        matches = [i for i, xy in enumerate(tree.get("outs", []))
                   if L1(xy, c["xy_um"]) < 1e-6]
        if len(matches) != 1:
            raise ValueError(f"{tn}: child {c['part']} has {len(matches)} reset outputs at {c['xy_um']}")
        kids.append(f"rst_n_t{n + matches[0]}")
    exp = {}
    outs = [p for p in lc["pins"] if p["kind"] == "clock" and p["dir"] == "out"]
    if outs:
        roots = GP.clock_pins(P, tn)
        exp = {p["name"]: min(roots, key=lambda r: L1((r[1], r[2]), p["xy_um"]))[0] for p in outs}
    return tree, srcs, kids, exp


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--types")]
    only = next((a.split("=", 1)[1].split(",") for a in sys.argv[1:] if a.startswith("--types=")), None)
    pin, sin, pout, sout = args[:4]
    rep_p = args[4] if len(args) > 4 else None
    ptext, stext = open(pin).read(), open(sin).read()
    raw, side = json.loads(ptext), json.loads(stext)
    assert json.dumps(raw) + "\n" == ptext, "plan text style"
    assert json.dumps(side, indent=1) + "\n" == stext, "sidecar text style"
    P = S.Plan(raw, pin)
    sct = side["collector"]["types"]
    rows, errs = [], []
    for tn, t in sorted(raw["partition_types"].items()):
        lc = (t.get("clock") or {}).get("landing_contract")
        if not lc or not lc.get("collector_tree") or t.get("hard") or (only and tn not in only):
            continue
        sc = sct.get(tn)
        assert sc is not None, f"{tn}: no sidecar collector row"
        try:
            tree, srcs, kids, exp = derive(P, lc, tn)
        except Exception as e:  # recorded, the type is left unchanged
            errs.append([tn, repr(e)[:200]]); continue
        ch = []
        if J(tree) != J(lc["collector_tree"]) or J(tree) != J(sc["tree"]):
            ch.append("tree")
        if [s["tap"] for s in lc.get("collector_local_sources", [])] != srcs or \
                [s["tap"] for s in sc.get("local_sources", [])] != srcs:
            ch.append("local_source_taps")
        if [c["node"] for c in lc.get("collector_children", [])] != kids or [c["node"] for c in sc.get("children", [])] != kids:
            ch.append("children")
        if any(p.get("source_clock_tap") != exp[p["name"]] for p in lc["pins"] if p["name"] in exp):
            ch.append("export_taps")
        if not ch:
            continue
        t0 = lc["collector_tree"]
        q0, q1 = {r["q"] for r in t0["relays"]}, {r["q"] for r in tree["relays"]}
        rows.append(dict(type=tn, changed=ch, relays_old=len(q0), relays_new=len(q1), only_old=sorted(q0 - q1)[:8],
                         only_new=sorted(q1 - q0)[:8], depth_old=t0.get("depth"), depth_new=tree.get("depth"),
                         src_taps=[[s["name"], s["tap"], v] for s, v in zip(lc.get("collector_local_sources", []), srcs) if s["tap"] != v],
                         kids=[[c["node"], k] for c, k in zip(lc.get("collector_children", []), kids) if c["node"] != k],
                         export=[[p["name"], p.get("source_clock_tap"), exp[p["name"]]] for p in lc["pins"]
                                 if p["name"] in exp and p.get("source_clock_tap") != exp[p["name"]]]))
        lc["collector_tree"] = tree
        sc["tree"] = json.loads(json.dumps(tree))
        for lst in (lc.get("collector_local_sources", []), sc.get("local_sources", [])):
            assert len(lst) == len(srcs), tn
            for s, v in zip(lst, srcs):
                s["tap"] = v
        for lst in (lc.get("collector_children", []), sc.get("children", [])):
            assert len(lst) == len(kids), tn
            for c, k in zip(lst, kids):
                c["node"] = k
        for p in lc["pins"]:
            if p["name"] in exp:
                p["source_clock_tap"] = exp[p["name"]]
    pt, st = json.dumps(raw) + "\n", json.dumps(side, indent=1) + "\n"
    open(pout, "w").write(pt); open(sout, "w").write(st)
    rep = dict(changed=len(rows), errors=errs, rows=rows,
               plan_in=hashlib.sha256(ptext.encode()).hexdigest(), plan_out=hashlib.sha256(pt.encode()).hexdigest(),
               sidecar_in=hashlib.sha256(stext.encode()).hexdigest(), sidecar_out=hashlib.sha256(st.encode()).hexdigest())
    print("REDERIVE changed", len(rows), "errors", len(errs))
    for r in rows:
        print(" ", r["type"], r["changed"], "relays", r["relays_old"], "->", r["relays_new"], "only_old", r["only_old"][:3],
              "src", len(r["src_taps"]), "kids", r["kids"], "export", len(r["export"]))
    for e in errs:
        print("  ERR", *e)
    if rep_p:
        open(rep_p, "w").write(json.dumps(rep, indent=1) + "\n")


if __name__ == "__main__":
    main()
