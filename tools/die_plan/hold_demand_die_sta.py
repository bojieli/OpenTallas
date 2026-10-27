#!/usr/bin/env python3
"""CLOCK-KV-R21 (a): clock.hold_demand source "die_sta" -- the per-port-bit FF hold demand that the SHARED die gate
(tools/die_plan/die_sta_related.py, main) measured on the assembled die, handed to the partition kits as a hold
obligation (12.4a a1: data-path hold delay, clock untouched).  RULING CLOCK-KV-R20 (a).

Source "plan" (hold_demand.py) derives D per seam pair from the plan's declared clock arrival model.  Source "die_sta"
takes D per seam BIT from a gate run: for every seam bit (die_clock.seam_pairs geometry: the pin point on the sender
face, the nearest launch / capture taps), the endpoint path of the gate's seam class (launch model x capture model:
the hard core whose die-frame outline holds the pin when that core has a real view whose pins_file is the plan's,
else budget) gives the FF hold slack h; D = -h, k = ceil(D / HB4.ff_early_ps).  Type-hardened: one value per
(partition type, port, bit) = the worst instance (max D).  Provenance = sha256 of the gate JSON, of the capture
records and of the gate tool file; a plan fragment names the demand file and its sha256 (gen_phys refuses a mismatch).

Placement (who pads): the RECEIVING partition's input (set_input_delay -min tightened by D on that bit) by default.
A receiver type listed in --sender-side (a hard macro with no P&R kit, e.g. kv3_phy_v1) cannot pad inside: its
demand goes to the SENDING partition's output stage (set_output_delay -min tightened by D on the sender's output bit).
When the sender is ALSO a --sender-side type (e.g. a PHY->PHY feedthrough), no kit can pad it: the bit is listed under
"unplaced" (a landing island in front of the receiving macro is needed; gen_phys never emits it).
The die gate is indifferent to the side: the HB4 model adds the same min delay to the same launch->capture data path.
Bits that are not partition->partition seams (die edge, channels) are not covered (listed in uncovered).
usage: hold_demand_die_sta.py CAPTURE.pkl GATE.json PLAN.json PROOF_DIR --tool die_sta_related.py --out DIR
       [--core-view MODULE=VIEWDIR ...] [--sender-side TYPE ...] [--types T1,T2 (first files)]"""
import argparse
import gzip
import hashlib
import json
import math
import pickle
import sys
from collections import defaultdict
from pathlib import Path

SCHEMA = "opentallas.hold_demand.die_sta.v1"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _pins_match(view_meta, pins, plan_dir, outline_um=None, extra=()):
    import die_sta_related as R
    return R.pins_match(view_meta, pins, plan_dir, outline_um, extra) is None


def demand_rows(P, ff, tt, M, real_pins, hb, tol_um=1.0, plan_dir=None):
    """[row] one per seam bit: pid, bit, src/dst part+type+bus, launch/capture tap, model, ff_hold_ps, D, k."""
    import schema as S
    gtaps = set(x[0] for x in ff) | set(x[1] for x in ff)
    plan_pins = sorted({h["pins_file"] for t in P.types.values() for h in t.get("hard_cores", []) or []
                        if h.get("pins_file")})
    tb = defaultdict(list)
    for t in M["taps"]:
        if t["port"] in gtaps:
            tb[t["part"]].append((t["port"], t["xy"]))
    crect = defaultdict(list)
    for n, p in P.parts.items():
        for h in P.types[p["type"]].get("hard_cores", []) or []:
            ox, oy = map(float, h["origin_um"]); w, hh = map(float, h["outline_um"])
            xs, ys = zip(*[P.to_die(n, q) for q in ((ox, oy), (ox + w, oy + hh))])
            # CLOCK-KV-R24 content match, GATE-PINS-2 canonical + exact-mirror form, as die_sta_related
            real = h.get("module") in real_pins and (real_pins[h["module"]] is None or
                                                     _pins_match(real_pins[h["module"]], h.get("pins_file"), plan_dir,
                                                                 h.get("outline_um"), plan_pins))
            crect[n].append((min(xs), min(ys), max(xs), max(ys), h["inst"], h["module"], real))

    def owner(part, pt):
        for x0, y0, x1, y1, inst, mod, real in crect.get(part, []):
            if x0 - tol_um <= pt[0] <= x1 + tol_um and y0 - tol_um <= pt[1] <= y1 + tol_um:
                return inst, mod, real
        return "GLUE", None, False
    rows, unc = [], defaultdict(int)
    for pid, pr in P.ports.items():
        sa, sb = pr["src"]["part"], pr["dst"]["part"]
        if S.DIE_PART in (sa, sb) or sa not in tb or sb not in tb:
            unc["die edge / untapped part"] += 1
            continue
        ra = P.rect(sa); f = pr["face"]
        for bit, lay, c in P.port_pins(pid):
            pt = ((ra[2] if f == "E" else ra[0]), c) if f in "EW" else (c, (ra[3] if f == "N" else ra[1]))
            ta = min(tb[sa], key=lambda t: abs(t[1][0] - pt[0]) + abs(t[1][1] - pt[1]))[0]
            tc = min(tb[sb], key=lambda t: abs(t[1][0] - pt[0]) + abs(t[1][1] - pt[1]))[0]
            si, sm, sr = owner(sa, pt); di, dm, dr = owner(sb, pt)
            key = (ta, tc, f"{sa}->{sb}", f"core:{sm}" if sr else "budget", f"core:{dm}" if dr else "budget")
            if key not in ff:
                unc["no gate record for the endpoint path"] += 1
                continue
            h = float(ff[key][1])
            D = max(0.0, -h)
            k = math.ceil(D / hb["ff_early_ps"] - 1e-9) if D > 0 else 0
            rows.append(dict(pid=pid, bit=int(bit), src_part=sa, src_type=P.parts[sa]["type"], src_bus=pr["src"]["bus"],
                             src_core=si, dst_part=sb, dst_type=P.parts[sb]["type"], dst_bus=pr["dst"]["bus"],
                             dst_core=di, launch_tap=ta, capture_tap=tc, model=f"{key[3]}>{key[4]}",
                             ff_hold_ps=round(h, 3), tt_setup_ps=round(float(tt[key][0]), 3) if key in tt else None,
                             demand_ps=round(D, 3), k=k))
    return rows, dict(unc)


def harden(rows, sender_side):
    """type-hardened demand: {'inputs'|'outputs': {type: {sv_bus: {bit: [k, D_ps]}}}} worst instance per template bit."""
    import gen_rtl
    out = dict(inputs=defaultdict(dict), outputs=defaultdict(dict), unplaced=defaultdict(dict))
    inst = dict(inputs=defaultdict(set), outputs=defaultdict(set), unplaced=defaultdict(set))
    for r in rows:
        if not r["k"]:
            continue
        side = "outputs" if r["dst_type"] in sender_side else "inputs"
        if side == "outputs" and r["src_type"] in sender_side:
            side = "unplaced"      # neither side has a P&R kit: needs a landing island (not padded by any kit)
        t, bus, part = ((r["src_type"], r["src_bus"], r["src_part"]) if side in ("outputs", "unplaced")
                        else (r["dst_type"], r["dst_bus"], r["dst_part"]))
        b = out[side][t].setdefault(gen_rtl.sv_id(bus), {})
        cur = b.get(str(r["bit"]), [0, 0.0])
        b[str(r["bit"])] = [max(cur[0], r["k"]), round(max(cur[1], r["demand_ps"]), 3)]
        inst[side][t].add(part)
    return ({s: {t: dict(sorted(v.items())) for t, v in sorted(out[s].items())} for s in out},
            {s: {t: len(v) for t, v in inst[s].items()} for s in inst})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("capture"); ap.add_argument("gate_json"); ap.add_argument("plan"); ap.add_argument("proof")
    ap.add_argument("--tool", required=True, help="the die_sta_related.py that produced GATE.json (main)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--core-view", action="append", default=[], help="MODULE=VIEWDIR (same as the gate)")
    ap.add_argument("--match-pins", action=argparse.BooleanOptionalAction, default=True,
                    help="a core is real only when its plan pins_file is the view's own; default ON = the gate default "
                         "(--core-view-match-pins, CLOCK-KV-R22); --no-match-pins for a gate run with "
                         "--no-core-view-match-pins")
    ap.add_argument("--sender-side", action="append", default=[], help="receiver TYPE without a P&R kit: pad at sender")
    ap.add_argument("--types", default="", help="comma list: also write per-type files for these first")
    a = ap.parse_args(argv)
    import schema as S
    import die_sta_related as R
    P = S.Plan(S.load(a.plan))
    d = pickle.load(open(a.capture, "rb"))
    tt, ff = dict(zip(d["classes"], d["recs"]))["seam"]
    real_pins = {}
    for kv in a.core_view:
        m, vd = kv.split("=", 1)
        prov = json.loads((Path(vd) / "provenance.json").read_text())
        k = prov["kit"]
        real_pins[m] = dict(pins_sha256=k.get("pins_sha256"), pins_file=k.get("pins_file"),
                            pins_canon_sha256=k.get("pins_canon_sha256"), outline_um=k.get("outline_um"),
                            view_dir=str(vd), module=m) if a.match_pins else None
    M = json.loads((Path(a.proof) / "mesh.json").read_text())
    gate = json.loads(Path(a.gate_json).read_text())
    rows, unc = demand_rows(P, ff, tt, M, real_pins, R.HB4, plan_dir=Path(a.plan).resolve().parent)
    dem, ninst = harden(rows, set(a.sender_side))
    cells = lambda side: sum(v[0] * ninst[side][t] for t, buses in dem[side].items() for b in buses.values()
                             for v in b.values())
    rec = dict(schema=SCHEMA, status="UNCHECKED until NUMBER-CHECK",
               provenance=dict(gate_json=str(Path(a.gate_json).resolve()), gate_json_sha256=sha(a.gate_json),
                               capture_sha256=sha(a.capture), tool="tools/die_plan/die_sta_related.py",
                               tool_sha256=sha(a.tool), plan_sha256=sha(a.plan),
                               gate_summary_seam_hb4=gate["summary"]["seam"].get("hb4"),
                               core_views={m: p for m, p in real_pins.items()}, match_pins=a.match_pins,
                               hb=R.HB4),
               placement=dict(default="receiver input (set_input_delay -min tightened by demand_ps on the bit)",
                              sender_side=sorted(a.sender_side),
                              sender_rule="receiver is a hard macro without a P&R kit: the sender's output bit "
                                          "(set_output_delay -min tightened by demand_ps)"),
               totals=dict(seam_bits=len(rows), bits_with_demand=sum(1 for r in rows if r["k"]),
                           cells_per_endpoint=sum(r["k"] for r in rows),
                           cells_type_hardened=dict(inputs=cells("inputs"), outputs=cells("outputs"),
                                                    unplaced=cells("unplaced")),
                           template_bits=dict(inputs=sum(len(b) for bb in dem["inputs"].values() for b in bb.values()),
                                              outputs=sum(len(b) for bb in dem["outputs"].values() for b in bb.values())),
                           area_mm2_type_hardened=round((cells("inputs") + cells("outputs") + cells("unplaced")) * R.HB4["area_um2"] / 1e6, 4),
                           uncovered=unc),
               instances=ninst, inputs=dem["inputs"], outputs=dem["outputs"], unplaced=dem["unplaced"])
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    body = json.dumps(rec, indent=0, sort_keys=False) + "\n"
    (out / "hold_demand_die_sta.json").write_text(body)
    hsha = hashlib.sha256(body.encode()).hexdigest()
    frag = dict(clock=dict(hold_demand=dict(source="die_sta", file="hold_demand_die_sta.json", sha256=hsha,
                                            gate_json_sha256=rec["provenance"]["gate_json_sha256"],
                                            tool_sha256=rec["provenance"]["tool_sha256"])))
    (out / "plan_hold_demand_fragment.json").write_text(json.dumps(frag, indent=1) + "\n")
    with gzip.open(out / "hold_demand_bits.tsv.gz", "wt") as g:
        cols = list(rows[0])
        g.write("\t".join(cols) + "\n")
        for r in rows:
            g.write("\t".join(str(r[c]) for c in cols) + "\n")
    per = {}
    for t in [x for x in a.types.split(",") if x]:
        sub = dict(rec, inputs={t: dem["inputs"].get(t, {})} if t in dem["inputs"] else {},
                   outputs={t: dem["outputs"].get(t, {})} if t in dem["outputs"] else {}, scope=f"type {t} only")
        (out / f"hold_demand_die_sta_{t}.json").write_text(json.dumps(sub, indent=0) + "\n")
        per[t] = dict(in_bits=sum(len(b) for b in dem["inputs"].get(t, {}).values()),
                      out_bits=sum(len(b) for b in dem["outputs"].get(t, {}).values()),
                      in_cells_per_inst=sum(v[0] for b in dem["inputs"].get(t, {}).values() for v in b.values()),
                      out_cells_per_inst=sum(v[0] for b in dem["outputs"].get(t, {}).values() for v in b.values()),
                      instances_in=ninst["inputs"].get(t, 0), instances_out=ninst["outputs"].get(t, 0))
    print(json.dumps(dict(sha256=hsha, totals=rec["totals"], first_types=per), indent=1))


if __name__ == "__main__":
    sys.exit(main())
