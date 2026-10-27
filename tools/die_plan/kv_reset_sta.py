#!/usr/bin/env python3
"""Die reset-network STA with the real routed die clock (CLOCK-KV-R15 item c; METHODOLOGY 12.4a pair form).

    kv_reset_sta.py TAPDIR --plan PLAN.json --out OUT [--corner TT --corner FF] [--mem 4g]

TAPDIR holds tap_arrivals_<C>.json + mesh.json (die_clock_mesh proof; R14 or any later clock).

What is timed (reset_tree.py WAVEFRONT mode, the plan's reset.release): every die reset hop is SYNCHRONOUS --
parent relay register rst_o_<k> (interior face site) -> die wire (L route M8 then M9, no die-top relay) -> child
arst_n -> pin register u_rst_in (plain D, no synchroniser).  START hops start_o_<k> -> start_i are the same form.
So the die-level reset checks are setup (the recovery analogue) and hold (the removal analogue) on a plain DFF D pin;
the only asynchronous input is die rst_n -> the ONE root synchroniser (the reset false path, listed, not timed).
Local async recovery/removal at partition flops (delivered rst_n_t<i>) belongs to the partition kit, not the die.

Per hop, two pair sets:
  nearest   launch tap = the parent's tap nearest the rst_o site, capture tap = the child's tap nearest the IN site
            (the relay / pin register sit under those taps: reset_tree 'boundary flops take their nearest tap')
  all_taps  every parent tap x every child tap (conservative bound if the relay sits under another tap)
Block model = declared-budget (12.3 common latency cancels both sides; partition local tree not in the tap arrival),
pin registers DFFHQNx1 characterised by die_sta_related.characterise (OpenSTA, ASAP7 liberty, corner max tap slew).
Kit hold contract (same as die_sta_related, the arst_n / start_i pins are kit IO pins under the plan seam_hold
window W): bound = W - hold damage (capture late - launch early - CPPR); gate corner FF.
Wire: lumped Elmore on the hop's routed L length, M8 H / M9 V ASAP7 setRC values (R in kohm/um, C fF/um):
  setup adds 0.5*R*C (wire) + R*Cpin on top of clk->q characterised with the full wire C as load;
  hold uses NO wire and clk->q at zero load (structural worst case).  UNCHECKED estimate of the wire, labelled.
"""
import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_sta_related as DSR  # noqa: E402

RC = {"M8": (8.44765e-03, 1.03962e-01), "M9": (8.89556e-03, 9.28446e-02)}  # ASAP7 setRC.tcl kohm/um, fF/um
CPIN_FF = 0.6   # DFFHQNx1 D pin cap order of magnitude (ASAP7 ~0.6 fF)


def hops(plan_path):
    import die_infra as DI
    import gen_phys
    import reset_tree as RT
    P = DI.load_plan(plan_path)
    W = RT.wf_plan(P)
    T = W["types"]
    ST = (W.get("start") or {}).get("types", {})
    rp = {n: (x, y) for n, _L, x, y in gen_phys.die_root_pins(P)}
    out = []
    for p, r in W["parts"].items():
        tn = r["type"]
        dst = P.to_die(p, T[tn]["in_um"]) if tn in T else tuple(RT.part_reset_pin(P, p))
        if r["parent"] is None:
            src = rp.get(RT.die_reset_port(P)) or rp.get("rst_n")
            out.append(dict(kind="root_async", net="rst_n", src_part=None, dst_part=p, a=src, b=dst,
                            note=r["source"]))
            if tn in ST and "start" in rp:
                out.append(dict(kind="start_root", net="start", src_part=None, dst_part=p, a=rp["start"],
                                b=P.to_die(p, ST[tn]["in_um"]), note="die start pin -> root START entry"))
            continue
        q = r["parent"]
        k = int(r["source"].rsplit("_", 1)[1])
        o = T[P.parts[q]["type"]]["outs"][k]
        out.append(dict(kind="reset", net="rstw_" + re.sub(r"\W", "_", r["source"]), src_part=q, dst_part=p,
                        a=P.to_die(q, (o[1], o[2])), b=dst, release=r.get("release")))
        if tn in ST and P.parts[q]["type"] in ST:
            so = ST[P.parts[q]["type"]]["outs"]
            if k < len(so):
                s = r["source"].replace(".rst_o_", ".start_o_")
                out.append(dict(kind="start", net="stw_" + re.sub(r"\W", "_", s), src_part=q, dst_part=p,
                                a=P.to_die(q, (so[k][1], so[k][2])), b=P.to_die(p, ST[tn]["in_um"])))
    for h in out:
        h["a"], h["b"] = [round(float(v), 4) for v in h["a"]], [round(float(v), 4) for v in h["b"]]
        h["dx_um"], h["dy_um"] = abs(h["a"][0] - h["b"][0]), abs(h["a"][1] - h["b"][1])
        h["len_um"] = round(h["dx_um"] + h["dy_um"], 2)
    return W, out


def wire(h):
    """lumped Elmore of the L route (M8 dx then M9 dy) driving one D pin: (C_wire fF, delay ps)."""
    r8, c8 = RC["M8"]
    r9, c9 = RC["M9"]
    R1, C1 = r8 * h["dx_um"], c8 * h["dx_um"]
    R2, C2 = r9 * h["dy_um"], c9 * h["dy_um"]
    d = R1 * (C1 / 2 + C2 + CPIN_FF) + R2 * (C2 / 2 + CPIN_FF)   # kohm * fF = ps
    return C1 + C2, d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tapdir")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--corner", action="append")
    ap.add_argument("--period-ps", type=float, default=DSR.PERIOD_PS)
    ap.add_argument("--path", action="append", default=[],
                    help="SRC->DST partition pair to report explicitly (default hub_C->hgi_EN_7)")
    a = ap.parse_args(argv)
    corners = a.corner or ["TT", "FF"]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    d = Path(a.tapdir)
    W, H = hops(a.plan)
    mesh = json.loads((d / "mesh.json").read_text())
    txy = {t["port"]: t["xy"] for t in mesh["taps"]}
    want = a.path or ["hub_C->hgi_EN_7"]
    res = dict(tapdir=str(d.resolve()), plan=str(Path(a.plan).resolve()), period_ps=a.period_ps,
               unc_setup_ps=DSR.UNC_SETUP_PS, unc_hold_ps=DSR.UNC_HOLD_PS, root=W["root"],
               release_mode=W["release"], max_release=W["max_release"],
               hop_counts={k: sum(1 for h in H if h["kind"] == k) for k in sorted({h["kind"] for h in H})},
               max_len_um={k: max(h["len_um"] for h in H if h["kind"] == k) for k in sorted({h["kind"] for h in H})},
               async_false_path=[h for h in H if h["kind"] == "root_async"],
               block_model="declared-budget (12.3 common latency cancels; DFFHQNx1 pin registers; Elmore wire UNCHECKED)",
               corners={})
    timed = [h for h in H if h["kind"] in ("reset", "start")]
    plan = json.loads(Path(a.plan).read_text())
    wseam = DSR.kit_windows(plan.get("clock", {}))["seam"]["ps"]
    res["kit_contract_window_ps"] = wseam
    for c in corners:
        meta, taps = DSR.load_taps(d, c)
        rng = meta["cppr_node_range_ps"]
        slew = max(r["slew_ps"] for r in taps.values())
        cmax = max(wire(h)[0] for h in timed) + CPIN_FF
        reg = DSR.characterise(out / c, c, slew, cmax)
        by_part = defaultdict(list)
        for p, r in taps.items():
            by_part[r["part"]].append(p)

        def near(part, xy):
            return min(by_part[part], key=lambda p: (txy[p][0] - xy[0]) ** 2 + (txy[p][1] - xy[1]) ** 2)

        def pair(A, B, wd):
            la, ea, lc, ec = A["late_ps"], A["early_ps"], B["late_ps"], B["early_ps"]
            node = A["cppr_node"] if A["cppr_node"] == B["cppr_node"] else "h"
            cr = DSR.credit(rng, node, la, ea, lc, ec)
            s = a.period_ps - DSR.UNC_SETUP_PS - (la + reg["clkq_max_wire_ps"] + wd) + (ec - reg["setup_ps"]) + cr
            hh = (ea + reg["clkq_min_nowire_ps"]) - (lc + reg["hold_ps"]) - DSR.UNC_HOLD_PS + cr
            return s, hh, cr, lc - ea - cr

        rows = []
        for h in timed:
            if h["src_part"] not in by_part or h["dst_part"] not in by_part:
                rows.append(dict(h, error="no taps"))
                continue
            cw, wd = wire(h)
            ta, tb = near(h["src_part"], h["a"]), near(h["dst_part"], h["b"])
            s, hh, cr, dmg = pair(taps[ta], taps[tb], wd)
            sa = ha = dmga = None
            for x in by_part[h["src_part"]]:
                for y in by_part[h["dst_part"]]:
                    s2, h2, _, d2 = pair(taps[x], taps[y], wd)
                    sa = s2 if sa is None else min(sa, s2)
                    ha = h2 if ha is None else min(ha, h2)
                    dmga = d2 if dmga is None else max(dmga, d2)
            rows.append(dict(kind=h["kind"], net=h["net"], src=h["src_part"], dst=h["dst_part"], len_um=h["len_um"],
                             wire_ps=round(wd, 2), launch_tap=ta, capture_tap=tb,
                             launch_late_ps=taps[ta]["late_ps"], capture_early_ps=taps[tb]["early_ps"],
                             launch_early_ps=taps[ta]["early_ps"], capture_late_ps=taps[tb]["late_ps"],
                             cppr_ps=round(cr, 2), setup_ps=round(s, 2), hold_ps=round(hh, 2),
                             hold_damage_ps=round(dmg, 2), kit_hold_bound_ps=round(wseam - dmg, 2),
                             kit_hold_bound_all_taps_ps=round(wseam - dmga, 2),
                             setup_all_taps_ps=round(sa, 2), hold_all_taps_ps=round(ha, 2)))
        ok = [r for r in rows if "error" not in r]
        cls = {}
        for k in ("reset", "start"):
            rr = [r for r in ok if r["kind"] == k]
            if not rr:
                continue
            ws, wh = min(rr, key=lambda r: r["setup_ps"]), min(rr, key=lambda r: r["hold_ps"])
            cls[k] = dict(hops=len(rr), worst_setup_ps=ws["setup_ps"], worst_setup=ws["net"],
                          worst_hold_ps=wh["hold_ps"], worst_hold=wh["net"],
                          setup_neg=sum(r["setup_ps"] < 0 for r in rr), hold_neg=sum(r["hold_ps"] < 0 for r in rr),
                          worst_setup_all_taps_ps=min(r["setup_all_taps_ps"] for r in rr),
                          worst_hold_all_taps_ps=min(r["hold_all_taps_ps"] for r in rr),
                          hold_neg_all_taps=sum(r["hold_all_taps_ps"] < 0 for r in rr),
                          worst5_hold=sorted(([r["hold_ps"], r["net"]] for r in rr))[:5],
                          kit_hold_bound_ps=min(r["kit_hold_bound_ps"] for r in rr),
                          kit_hold_neg=sum(r["kit_hold_bound_ps"] < 0 for r in rr),
                          kit_hold_bound_all_taps_ps=min(r["kit_hold_bound_all_taps_ps"] for r in rr))
        named = [r for r in ok if f"{r['src']}->{r['dst']}" in want]
        res["corners"][c] = dict(tap_slew_max_ps=round(slew, 2), register=reg, classes=cls, named=named,
                                 errors=[r for r in rows if "error" in r])
        (out / f"reset_hops_{c}.json").write_text(json.dumps(rows, indent=1) + "\n")
        for k, v in cls.items():
            print(f"{c} {k:6s} hops {v['hops']:4d} setup {v['worst_setup_ps']:8.2f} (neg {v['setup_neg']}) "
                  f"hold {v['worst_hold_ps']:8.2f} (neg {v['hold_neg']}) | all-taps setup {v['worst_setup_all_taps_ps']:8.2f}"
                  f" hold {v['worst_hold_all_taps_ps']:8.2f} (neg {v['hold_neg_all_taps']})  worst hold {v['worst_hold']}"
                  + (f" | kit-contract hold (W {wseam:g}) {v['kit_hold_bound_ps']:.2f} (neg {v['kit_hold_neg']}, all-taps"
                     f" {v['kit_hold_bound_all_taps_ps']:.2f})" if c == "FF" else ""))
        for r in named:
            print(f"{c} NAMED {r['kind']} {r['net']} {r['src']}->{r['dst']} len {r['len_um']} wire {r['wire_ps']} "
                  f"setup {r['setup_ps']} hold {r['hold_ps']} (all-taps {r['setup_all_taps_ps']}/{r['hold_all_taps_ps']})"
                  f" kit-contract hold {r['kit_hold_bound_ps']}")
    res["status"] = "UNCHECKED (NUMBER-CHECK pending)"
    (out / "kv_reset_sta.json").write_text(json.dumps(res, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
