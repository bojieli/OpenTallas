#!/usr/bin/env python3
"""DIE-QC-67/HC3 11-04: slw_hc3 RE-FORM, split form A (COORD 11-03 23:3x; plan_qc52 delta, ESTIMATE-FIRST).

Measured failure: flat type 295,330 cells / 69,481 FF on 4 taps (d90 kit wave attempt_3), hold -252 at the post-CTS gate.
Split: the eight ot_qfd_xs_leaf #(FILL_PIPE 1, NCH 4, READ_PIN_PIPE 1) instances (~31k cells, 6,972 FF each, 53,148 FF
total, one register on every input and output pin) become one hard master placed 8x as two write chains of 4; u_xh3 and
u_pstn stay flat (~55k cells, ~16.3k FF).  No RTL, port or cycle change: same bound netlist with the leaf as a black box;
the type outline, buses and lanes are unchanged.  Tile clock: density taps on the measured flat sinks, plus one early
core tap per leaf.  Reset tree / landing data are re-derived with the composer rules (delta_ttctlm_1101).
Leaf 198.72 x 60.48: write chain S (in) -> N (out) on the same M5 column, 17.28-um channels for seam hold repair;
read pins on the E face (M4), clk / rst_n at the S-face centre.  Hard views bind later (lef/lib) from the signed leaf.
usage: delta_hc3_split_1104.py PLAN_IN PLAN_OUT [REPORT.json]    (writes the pin table beside this script: cores/hc3/)"""
import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))
import delta_ttctlm_1101 as DT  # noqa: E402
import schema as S  # noqa: E402

TYPES = ("slw_hc3__clccfc3e6b", "slw_hc3__cld86a7ad4")
BINS = "physical/die_plan/qwen_compute/plan_of_record/sink_bins/hc3a_{}.json"
MOD = "ot_qfd_xs_leaf"
PINS = "cores/hc3/ot_qfd_xs_leaf_pins.json"
W, H = 198.72, 60.48
X0, Y0, DX, DY = (103.68, 319.68), 216.0, None, 77.76     # column origins; 8.64 lattice; channels 17.28
TOFF = [0.012, 0.012]
RH = 0.042     # half pin rect depth (gen_core_kit_qc RECT M5 h / M4 w)


def m5_slots():
    """M5 tracks 0.012 + 0.048 k, every second track, core margin clear, off the core PDN stripe pairs (2.064 + 4.32 k)"""
    out = []
    k = 0
    while True:
        x = round(0.012 + 0.096 * k, 4)
        k += 1
        if x > W - 4.4:
            return out
        if x < 4.4:
            continue
        d = (x - 2.064) % 4.32
        if d < 0.40 or d > 4.32 - 0.25:
            continue
        out.append(x)


def pin_table():
    slots = m5_slots()
    # write word in position order: {w_m[p], w_d[16 p +: 16]}; the 82 control bits at the centre, around clk / rst_n
    data = []
    for p in range(64):
        data.append(("m", p))
        data += [("d", 16 * p + b) for b in range(16)]
    ctl = [("v", None), ("ep", None), ("c_v", None), ("c_ep", None)] + [("off", i) for i in range(6)] + \
          [("ctl", i) for i in range(72)]
    n = len(data) + len(ctl)
    assert n == 1170 and len(slots) >= n + 8, (n, len(slots))
    mid = len(slots) // 2
    gap = 4                                  # clk / rst_n slots: 4 free tracks of 0.096 each side at the centre
    lo, hi = slots[:mid - gap], slots[mid + gap:]
    half = len(data) // 2
    # spread evenly over each half face: data outside, controls next to the centre
    nlo, nhi = half + len(ctl) // 2, len(data) - half + len(ctl) - len(ctl) // 2
    seq_lo, seq_hi = data[:half] + ctl[:len(ctl) // 2], ctl[len(ctl) // 2:] + data[half:]
    pick = lambda s, m: [s[int(i * len(s) / m)] for i in range(m)]  # noqa: E731
    xs = dict(zip(seq_lo, pick(lo, nlo)))
    xs.update(zip(seq_hi, pick(hi, nhi)))
    assert len(xs) == n
    NM = {"m": ("w_m", "wo_m"), "d": ("w_d", "wo_d"), "ctl": ("w_ctl", "wo_ctl"), "off": ("w_off", "wo_off"),
          "v": ("w_v", "wo_v"), "ep": ("w_ep", "wo_ep"), "c_v": ("c_v", "co_v"), "c_ep": ("c_ep", "co_ep")}
    pins = []
    for key, x in xs.items():
        kind, b = key
        i, o = NM[kind]
        s = "" if b is None else f"[{b}]"
        pins.append(dict(name=i + s, layer="M5", x=x, y=RH, dir="in"))
        pins.append(dict(name=o + s, layer="M5", x=x, y=round(H - RH, 4), dir="out"))
    pins.append(dict(name="clk", layer="M5", x=slots[mid - 1], y=RH, dir="in"))
    pins.append(dict(name="rst_n", layer="M5", x=slots[mid + 1], y=RH, dir="in"))
    # read port, E face M4
    rd = [("r_v", 0), ("r_t", 0), ("r_ep", 0)] + [("r_p", i) for i in range(28)]
    qq = [("q", i) for i in range(64)] + [("q_v", 0), ("q_bad", 0)]
    seq = [(n_, b, "in") for n_, b in rd] + [(n_, b, "out") for n_, b in qq]
    y0, y1 = 5.0, H - 5.0
    for j, (n_, b, d) in enumerate(seq):
        y = y0 + (y1 - y0) * j / (len(seq) - 1)
        y = round(0.012 + 0.048 * round((y - 0.012) / 0.048), 4)
        nm = n_ if n_ in ("r_v", "r_t", "r_ep", "q_v", "q_bad") else f"{n_}[{b}]"
        pins.append(dict(name=nm, layer="M4", x=round(W - RH, 4), y=y, dir=d))
    assert len({(q["layer"], q["x"], q["y"]) for q in pins}) == len(pins)
    return dict(schema="opentallas.core_pins.v1", core=MOD, module=MOD, frame=f"core R0, origin (0,0), outline {W} x {H}",
                source="DIE-QC-67/HC3 11-04 delta_hc3_split_1104.py: planned pin table, write chain S->N same column, "
                       "read E, clk/rst_n S centre; kit tracks (0.012 + 0.048 k); NOT SIGNED", pins=pins)


def main():
    pin, pout = sys.argv[1:3]
    rep_p = sys.argv[3] if len(sys.argv) > 3 else None
    text = open(pin).read()
    P0 = json.loads(text)
    seps = next((sp for sp in ((", ", ": "), (",", ":")) if json.dumps(P0, separators=sp) + "\n" == text), None)
    assert seps, "plan text style is not one-line json.dumps"
    table = pin_table()
    pf = HERE / "plan_of_record" / PINS
    pf.parent.mkdir(exist_ok=True)
    pf.write_text(json.dumps(table, indent=0) + "\n")
    ckp = next(q for q in table["pins"] if q["name"] == "clk")
    P = copy.deepcopy(P0)
    rep = dict(event="DIE-QC-67/HC3 split form A", types={}, src_sha256=hashlib.sha256(text.encode()).hexdigest(),
               pins=len(table["pins"]), leaf=dict(outline_um=[W, H], clk_pin=[ckp["x"], ckp["y"]]))
    for t in TYPES:
        ty = P["partition_types"][t]
        ck = ty["clock"]
        assert not ty.get("hard_cores"), t
        taps0 = S.tap_grid(S.Plan(P, pin), t)
        lc0 = copy.deepcopy(ck["landing_contract"])
        ck.update(DT.KNOBS)
        ck["sink_bins_file"] = BINS.format(t)
        ck["core_taps"] = "early"
        hcs, core = [], []
        for k in range(8):
            ox, oy = X0[k // 4], round(Y0 + (k % 4) * DY, 3)
            inst = f"u_xl3_{k}"
            c = next(c for c in ty["contents"] if c["inst"] == inst)
            c.update(outline_um=[W, H], origin_um=[ox, oy],
                     note=f"DIE-QC-67/HC3 11-04: hard core, chain {k // 4} depth {k % 4}")
            hcs.append(dict(inst=inst, module=MOD, origin_um=[ox, oy], outline_um=[W, H], orient="R0",
                            track_offset_um=TOFF, pins_file=PINS, physical_inst=f"u_bound.u_{inst}",
                            physical_master=MOD,
                            note="DIE-QC-67/HC3 11-04: ot_qfd_xs_leaf #(FILL_PIPE 1, NCH 4, READ_PIN_PIPE 1); view binds "
                                 "when the leaf kit signs off"))
            core.append(dict(name=inst + ".clk", kind="core",
                             xy=[round(ox + TOFF[0] + ckp["x"], 3), round(oy + TOFF[1] + ckp["y"], 3)], orient="R0",
                             insertion_ps=250, insertion_tol_ps=40, insertion_ff_ps=202.5,
                             budget_owner="DIE-QC-67/HC3 11-04: plan frame; re-measure on the signed leaf view"))
        ty["hard_cores"] = hcs
        ck["taps"] = list(ck.get("taps", [])) + core
        DT.T = t
        if lc0.get("collector_tree") is None:
            assert not lc0.get("collector_local_sources") and not lc0.get("collector_children"), t
            roots = DT.GP.clock_pins(S.Plan(P, pout), t)
            for pn in ck["landing_contract"]["pins"]:
                if pn["kind"] == "clock" and pn["dir"] == "out":
                    pn["source_clock_tap"] = min(roots, key=lambda r: DT.L1((r[1], r[2]), pn["xy_um"]))[0]
        else:
            DT.apply(P, DT.derive(S.Plan(P, pout), P))
        taps1 = S.tap_grid(S.Plan(P, pout), t)
        lc = ck["landing_contract"]
        rep["types"][t] = dict(taps_old=len(taps0), taps_new=len(taps1), core_taps=8,
                               collector_tree=dict(old=len((lc0["collector_tree"] or {}).get("relays", [])),
                                                   new=len((lc["collector_tree"] or {}).get("relays", []))))
        print(t, rep["types"][t])
    out = json.dumps(P, separators=seps) + "\n"
    open(pout, "w").write(out)
    rep["dst_sha256"] = hashlib.sha256(out.encode()).hexdigest()
    if rep_p:
        open(rep_p, "w").write(json.dumps(rep, indent=1) + "\n")


if __name__ == "__main__":
    main()
