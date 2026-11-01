#!/usr/bin/env python3
"""DIE-QC-58M (11-01, adopted by DIE-QC-59): st_a class (+ slw_st_b_v2) macro-channel delta on plan_qc52 (one-block class fix, plan freeze 12.22).

KIT-WAVE-12 preflight FAIL PLAN macro_channels on all four sle_st_a types (sle_st_a_v2 + its three v1 clones):
  macro column 1 x[267.84,343.008]: E vertical channel 2.592 um < 10.8
  macro column 2 x[345.6,386.208]:  W vertical channel 2.592 um < 10.8
Root cause (plan, not the kit generator): the physical-only hard_cores[] sites written by Codex's one-off
results/qc_codex_kits_2249/add_macro_sites.py.  Its region lattice puts the 32x64 SRAMs of every region u_r<k> on
x = 267.84 / 311.04 / 354.24 (43.2 um pitch -> 11.232 um channels), but in region u_r0 its displacement search slid
u_hb / u_skn / u_sks one lattice step west of the 354.24 column to x = 345.6 (no channel rule in that search).  That
leaves a 2.592 um sliver between the 311.04 column (r1..r3, 343.008 east edge) and the 345.6 column.

Fix: smallest-displacement class-uniform re-site of the three u_r0 SRAMs (8.64-um lattice, generator metric
|dx|+|dy| steps, total 15), with every macro column clear by >= 10.8 um and no macro bridging columns 1 and 2:
  u_hb  (345.6, 138.24) -> (354.24, 138.24)   back on the class lattice column x = 354.24 (u_scale_wait column)
  u_sks (345.6, 198.72) -> (354.24, 224.64)   same column, north of the x_fw_ctl_i landing band
  u_skn (345.6, 172.8)  -> (397.44, 138.24)   new single-macro column x[397.44,429.408]
Column 2 becomes x[354.24,386.208] (channel to column 1 = 11.232 um), the new column leaves 11.232 um W and 19.872 um E
(btab column 449.28).  Why not all three at x = 354.24: on the three v1 clones the landing band x_fw_ctl_i
[385.728,168.48,478.496,218.16] reaches 0.48 um into x[354.24,386.208] at y 168-218, and the x_ctl_fw / x_fw_ctl
station rows (y 250-290) and collector relays (y 293-320) leave only one free 4.32-um-halo slot (y 224.64-241.92) in
that column inside the u_r0 quarter (y < 334.8); x <= 311.04 (joining column 1) is blocked by the b_hw_ctl_hc0
station-1 reserve (x < 340.75, y < 277.5).  Same sites on all eight st_a types: the four sle_st_a types of the
KIT-WAVE-12 failure and the four slw_st_a types (slw_st_a_v1__clb036e152, slw_st_a_v1__clfc5867a6,
slw_st_a_v2__cl9f076a5c, slw_st_a_v2__clf4365a62), which carry the identical u_r0 sites and the identical 2.592-um
sliver (not yet in a wave).  Same rule, other class: slw_st_b_v2 u_r5.u_skn (233.28, 509.76) -> (224.64, 509.76), one
lattice step west, so its column x[224.64,256.608] clears the x = 267.84 column by 11.232 um (was 2.592).  orient, track_offset_um, pins_file,
outline, ports, pins, type outline: unchanged.  No RTL, cell or cycle change (physical-only macro sites).  The script re-checks on the edited plan: the kit macro_channels
rule (same clustering as tools/die_plan/kit_contract.py on the kit CORE_AREA = outline inset 4.32), halo-vs-halo
overlap of all hard cores, and the generator's own reserve set (landing bands, clock taps/tap_um, collector relays,
ft-slot regs / bit sites / implicit station groups) against the moved halo boxes.

usage: python3 -I delta_mch_1101.py PLAN [--receipt R.json] [--dry-run]     (edits PLAN in place, single-line json)
"""
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))

# class st_a = every E / W slice st_a type (sle_st_a*, slw_st_a*): all eight carry the identical u_r0 sites (the
# generator placed both from the sle_st_a_v2 exact map); slw_st_b_v2 carries its own 2.592-um sliver (u_r5.u_skn)
ST_A = ("sle_st_a", "slw_st_a")
MOVES = {"u_bound.u_u_r0.u_hb.u_m.g_bank[0].u_m": ((345.6, 138.24), (354.24, 138.24)),
         "u_bound.u_u_r0.u_skn.u_m.g_bank[0].u_m": ((345.6, 172.8), (397.44, 138.24)),
         "u_bound.u_u_r0.u_sks.u_m.g_bank[0].u_m": ((345.6, 198.72), (354.24, 224.64))}
MOVES_B = {"slw_st_b_v2": {"u_bound.u_u_r5.u_skn.u_m.g_bank[0].u_m": ((233.28, 509.76), (224.64, 509.76))}}


def moves_for(tn):
    return MOVES if tn.startswith(ST_A) else MOVES_B.get(tn)
MIN_CH = 10.8           # tools/die_plan/kit_contract.py MIN_CHANNEL_UM
CORE_INSET = 4.32       # kit CORE_AREA = DIE_AREA inset 4.32 (gen config.mk)
EPS = 1e-6


def rect_hit(a, b):
    return a[0] < b[2] - 1e-8 and b[0] < a[2] - 1e-8 and a[1] < b[3] - 1e-8 and b[1] < a[3] - 1e-8


def box(hc, halo=0.0):
    x, y = hc["origin_um"][0] + hc["track_offset_um"][0], hc["origin_um"][1] + hc["track_offset_um"][1]
    w, h = hc["outline_um"]
    if hc.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
        w, h = h, w
    return [x - halo, y - halo, x + w + halo, y + h + halo]


def channel_errors(t):
    """kit_contract.macro_channels on the plan rects (x-overlap clusters = columns; W/E channel and interior gap)."""
    W, H = t["outline_um"]
    core = [CORE_INSET, CORE_INSET, W - CORE_INSET, H - CORE_INSET]
    bs = sorted(([hc["inst"]] + box(hc) for hc in t.get("hard_cores", [])), key=lambda b: b[1])
    cols = []
    for b in bs:
        if cols and b[1] < max(x[3] for x in cols[-1]) - EPS:
            cols[-1].append(b)
        else:
            cols.append([b])
    edges = [core[0]] + [v for c in cols for v in (min(b[1] for b in c), max(b[3] for b in c))] + [core[2]]
    err = []
    for i, c in enumerate(cols):
        lo, hi = min(b[1] for b in c), max(b[3] for b in c)
        for side, g in (("W", lo - edges[2 * i]), ("E", edges[2 * i + 3] - hi)):
            if g < MIN_CH - EPS:
                err.append(f"macro column {i} x[{lo:g},{hi:g}]: {side} vertical channel {g:.3f} um < {MIN_CH:g}")
        st = sorted(c, key=lambda b: b[2])
        if len(st) > 1 and max(st[k + 1][2] - st[k][4] for k in range(len(st) - 1)) < MIN_CH - EPS:
            err.append(f"macro column {i}: {len(st)} stacked macros with no interior horizontal channel >= {MIN_CH:g}")
    return err, [(round(min(b[1] for b in c), 3), round(max(b[3] for b in c), 3), len(c)) for c in cols]


def reserves(P, t, tn):
    """the reserve set of results/qc_codex_kits_2249/add_macro_sites.py obs() (same geometry, same tools)."""
    import check as C
    import gen_phys as GP

    def ptbox(p, h=2.0):
        return [p[0] - h, p[1] - h, p[0] + h, p[1] + h]
    o = []
    ck = t.get("clock", {})
    lc = ck.get("landing_contract", {})
    o += [("band " + k, b["rect_um"]) for k, b in lc.get("bands", {}).items()]
    o += [("tap " + z.get("name", "?"), ptbox(z["xy"])) for z in ck.get("taps", []) if "xy" in z]
    if ck.get("tap_um"):
        o.append(("tap_um", ptbox(ck["tap_um"])))
    o += [("relay", ptbox(r["xy"], 1)) for r in lc.get("collector_tree", {}).get("relays", [])]
    for key in ("ft_slots", "internal_stations"):
        for f in t.get(key, []):
            o += [(f"{key} {f['name']} reg", ptbox(p, 1.5)) for p in f.get("regs_um", [])]
            for row in f.get("bit_sites_um", []):
                o += [(f"{key} {f['name']} bit", [p[0], p[1], p[0] + 1.404, p[1] + .27]) for p in row]
    pins = defaultdict(dict)
    for bus, bit, layer, x, y, face in GP.type_pins(P, tn):
        pins[bus][bit] = (x, y, face)
    for f in t.get("ft_slots", []):
        groups = defaultdict(list)
        pi, po, st = pins[f["name"] + "_i"], pins[f["name"] + "_o"], int(f.get("stations", 1))
        for bit in sorted(set(pi) | set(po)):
            ap, bp = pi.get(bit) or po[bit], po.get(bit) or pi[bit]

            def inset(q):
                x, y, face = q
                return {"E": (x - 1, y), "W": (x + 1, y), "N": (x, y - 1), "S": (x, y + 1)}[face]
            a, b = inset(ap), inset(bp)
            rt = C.zroute(a, b, ap[2], bp[2])
            ln = C.plen(rt)
            for ii in range(st):
                if f.get("bit_sites_um") and ii > 0:
                    x, y = f["bit_sites_um"][ii - 1][bit]
                else:
                    x, y = a if f.get("bit_sites_um") else (tuple(f["regs_um"][ii]) if f.get("regs_um")
                                                            else C.point_at(rt, ln * ii / st))
                groups[ii].append((x, y))
        for ii, a in groups.items():
            o.append((f"station {f['name']}[{ii}]", [min(q[0] for q in a) - 1, min(q[1] for q in a) - 1,
                                                     max(q[0] for q in a) + 1, max(q[1] for q in a) + 1]))
    return o


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    plan_path = Path(args[0])
    receipt = Path(argv[argv.index("--receipt") + 1]) if "--receipt" in argv else None
    dry = "--dry-run" in argv
    src = plan_path.read_bytes()
    raw = json.loads(src)
    if json.dumps(raw).encode() != src.rstrip(b"\n"):
        raise SystemExit("plan does not round-trip through json.dumps byte-exactly; refusing to rewrite")
    pts = raw["partition_types"]
    cls = sorted(tn for tn, t in pts.items() if moves_for(tn) and t.get("hard_cores"))
    rec = dict(schema="opentallas.plan_delta.v1", lane="DIE-QC-58M", event="st_a (sle+slw) + slw_st_b_v2 macro_channels fix",
               plan=str(plan_path.name), sha256_before=hashlib.sha256(src).hexdigest(), types={})
    for tn in cls:
        t = pts[tn]
        before, cols_b = channel_errors(t)
        by = {hc["inst"]: hc for hc in t["hard_cores"]}
        moved = []
        for inst, (o0, o1) in moves_for(tn).items():
            hc = by[inst]
            if max(abs(a - b) for a, b in zip(hc["origin_um"], o0)) > EPS:
                raise SystemExit(f"{tn} {inst}: origin {hc['origin_um']} != expected {list(o0)}")
            hc["origin_um"] = list(o1)
            moved.append(dict(inst=inst, origin_from=list(o0), origin_to=list(o1)))
        after, cols_a = channel_errors(t)
        halos = [(hc["inst"], box(hc, hc.get("halo_um", 4.32))) for hc in t["hard_cores"]]
        W, H = t["outline_um"]
        ov = [(a[0], b[0]) for i, a in enumerate(halos) for b in halos[i + 1:] if rect_hit(a[1], b[1])]
        out = [n for n, b in halos if b[0] < 8.64 - EPS or b[1] < 8.64 - EPS or b[2] > W - 8.64 + EPS
               or b[3] > H - 8.64 + EPS]
        rec["types"][tn] = dict(moved=moved, macro_channels_before=before, macro_channels_after=after,
                                columns_before=cols_b, columns_after=cols_a, halo_overlaps=ov, halo_outside=out)
    # generator reserve set needs the Plan view (ports / parts); built once on the edited plan
    import schema as S
    P = S.Plan(raw, path=plan_path)
    bad = False
    for tn in cls:
        t = pts[tn]
        res = reserves(P, t, tn)
        hits = []
        for m in rec["types"][tn]["moved"]:
            hb = box(next(hc for hc in t["hard_cores"] if hc["inst"] == m["inst"]), 4.32)
            hits += [(m["inst"], nm, [round(v, 3) for v in r]) for nm, r in res if rect_hit(hb, r)]
        r = rec["types"][tn]
        r["reserve_hits"] = hits
        r["reserves_checked"] = len(res)
        ok = not (r["macro_channels_after"] or r["halo_overlaps"] or r["halo_outside"] or hits)
        r["verdict"] = "PASS" if ok else "FAIL"
        bad |= not ok
        print(f"{tn}: before {len(r['macro_channels_before'])} after {len(r['macro_channels_after'])} "
              f"cols {r['columns_after']} overlaps {len(r['halo_overlaps'])} reserve_hits {len(hits)}/{len(res)} "
              f"-> {r['verdict']}")
    out = (json.dumps(raw) + ("\n" if src.endswith(b"\n") else "")).encode()
    rec["sha256_after"] = hashlib.sha256(out).hexdigest()
    rec["verdict"] = "FAIL" if bad else "PASS"
    if receipt:
        receipt.write_text(json.dumps(rec, indent=1) + "\n")
    if bad:
        raise SystemExit("delta check FAIL; plan not written")
    if not dry:
        plan_path.write_bytes(out)
    print("PASS", "dry-run" if dry else f"written {plan_path}", rec["sha256_after"][:12])


if __name__ == "__main__":
    main(sys.argv[1:])
