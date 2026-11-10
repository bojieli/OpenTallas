#!/usr/bin/env python3
"""DIE-HBM-89-N4RF 2026-11-07: n4ext RE-FORM plan candidate (one-block plan delta, DO_NOT_COUNT until a plan event).

  python3 -I mk_plan_n4rf.py BASE_PLAN_DIR OUT_DIR

Outline 216 x 207.36 -> 293.76 x 250.56 (W 34 x 8.64, H 29 x 8.64), origin kept (734.4, 5503.68): the core grows E and N
only.  Slot check (d44v root): nothing in [950.4, 1028.16] x [5503.68, 5754.24]; nearest plan objects are the
L8102x4/mx4 FT regs at die y 5801.9 / 5828.5 (core top 5754.24) and the n4x_*_ne stations at die x 1195.2 (core E
1028.16); W and S faces unchanged.
Pins: W (up_nw/down_nw) and S (job...busy) unchanged; E (up_ne/down_ne) x -> W - 0.096 at the same y; rst_n (N face)
y -> H - 0.096; clk entry -> the centre clock island of the re-centred macro column.
Macros: the same one-column form, re-centred on x = 146.88 with a wider S band and a 28 um clock channel.
"""
import gzip, hashlib, json, shutil, sys
from pathlib import Path

W, H = 293.76, 250.56
OLD_W, OLD_H = 216.0, 207.36
MOD = "ot_hnx_fused_hub_n4ext"
OLD_PINS = "cores/ot_hnx_fused_hub_n4ext__216x207.36__c25b__centry.json"
NEW_PINS = "cores/ot_hnx_fused_hub_n4ext__293.76x250.56__n4rf.json"
ORIGIN = (734.4, 5503.68)
CLK = (146.904, 120.96)                  # M5 track x (0.024 offset as the old 108.024), y on the 4.32 lattice
ISLAND = [142.56, 116.64, 151.2, 125.28]
MACROS = [  # x0, y0 (R0); sizes 94.824 x 41.064 / 31.992 x 17.304
    ("u_fcore.u_native.u_scb", "ot_sram_1r1w_128x256_m1_r2c2", 99.456, 64.8, 94.824, 41.064),
    ("u_fcore.u_native.u_t5.u_pad.u_d", "ot_sram_1r1w_128x256_m1_r2c2", 99.456, 138.24, 94.824, 41.064),
    ("u_fcore.u_native.u_t5.u_pad.u_c", "ot_sram_1r1w2c_32x64_m1", 130.896, 192.24, 31.992, 17.304),
]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(base, out):
    base, out = Path(base), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "cores").mkdir(exist_ok=True)
    pins = json.load(open(base / OLD_PINS))
    moved = dict(E=0, N=0, clk=0)
    for p in pins:
        if abs(p["x"] - (OLD_W - 0.096)) < 1e-6:
            p["x"] = round(W - 0.096, 4); moved["E"] += 1
        elif p["name"] == "rst_n":
            p["y"] = round(H - 0.096, 4); moved["N"] += 1
        elif p["name"] == "clk":
            p["x"], p["y"] = CLK; moved["clk"] += 1
        assert 0 <= p["x"] <= W and 0 <= p["y"] <= H, p
    assert moved == dict(E=444, N=1, clk=1), moved
    (out / NEW_PINS).write_text(json.dumps(pins) + "\n")
    # die plan: root hard core + contents outline / pins, E-face station landings, die clock entry
    plan = json.load(gzip.open(base / "die_plan.json.gz"))
    root = plan["partition_types"]["root"]
    hc = [c for c in root["hard_cores"] if c["inst"] == "u_mu_fused_root"]
    ct = [c for c in root["contents"] if c["inst"] == "u_mu_fused_root"]
    assert len(hc) == 1 and len(ct) == 1
    for c in hc + ct:
        assert c["origin_um"] == list(ORIGIN) and c["outline_um"] == [OLD_W, OLD_H]
        c["outline_um"] = [W, H]
    hc[0]["pins_file"] = NEW_PINS
    hc[0]["note"] += " | DIE-HBM-89-N4RF candidate: RE-FORM 293.76 x 250.56 (E/N growth, util <= 0.40), E pins + rst_n moved, clk entry at the re-centred island"
    nst = 0
    for s in root["internal_stations"]:
        if s["conn"] in ("bus:n4x_up_ne_i", "bus:n4x_dn_ne_o"):
            assert abs(s["to_um"][0] - (ORIGIN[0] + OLD_W)) < 1e-6
            s["to_um"][0] = round(ORIGIN[0] + W, 4); nst += 1
    assert nst == 2
    ntap = 0
    for t in root["clock"]["taps"]:
        if t["name"] == "u_mu_fused_root.clk":
            t["xy"] = [round(ORIGIN[0] + CLK[0] - 0.024, 4), round(ORIGIN[1] + CLK[1], 4)]; ntap += 1
    assert ntap == 1
    (out / "die_plan.json").write_text(json.dumps(plan) + "\n")
    # core_macros.json
    cm = json.load(open(base / "core_macros.json"))
    old = cm["cores"][MOD]
    cm["cores"][MOD] = dict(status="KNOWN", outline_um=[W, H],
                            basis="DIE-HBM-89-N4RF RE-FORM candidate: one centred column re-centred on x 146.88 in the "
                                  "293.76 x 250.56 outline; u_scb below / u_pad.u_d above the clock island "
                                  f"{ISLAND} (32.4 um clock channel with rows: > the 30 um --macro-gap-block bound), u_c above u_d; S band 64.8 um, W/E fields 99.5 um",
                            macros=[dict(name=n, master=m, orient="R0", rect_um=[x, y, round(x + w, 4), round(y + h, 4)])
                                    for n, m, x, y, w, h in MACROS],
                            channel_rule_um=10.8, previous=old)
    (out / "core_macros.json").write_text(json.dumps(cm, indent=1) + "\n")
    # clock entry sidecar (plain json: gen reads PLANDIR/clock_entries.json)
    ce = json.load(gzip.open(base / "clock_entries.json.gz"))
    n = 0
    for blk in ce.values():
        if isinstance(blk, dict) and isinstance(blk.get("u_mu_fused_root"), dict):
            e = blk["u_mu_fused_root"]
            e["xy_um"] = [round(CLK[0] - 0.024, 4), CLK[1]]; e["island_um"] = ISLAND
            e["source"] += " | DIE-HBM-89-N4RF: re-centred island of the 293.76 x 250.56 RE-FORM"
            n += 1
    assert n >= 1, n
    (out / "clock_entries.json").write_text(json.dumps(ce) + "\n")
    views = dict(schema="opentallas.hbm_arch.core_views.v1", plan=str((out / "die_plan.json").resolve()),
                 plan_sha256=sha(out / "die_plan.json"), views=1,
                 view_list=[dict(view=f"{MOD}@{sha(out / NEW_PINS)[:12]}", module=MOD, outline_um=[W, H],
                                 pins_file=NEW_PINS, pins_sha256=sha(out / NEW_PINS), pins=len(pins), family="hnx",
                                 instances=["root.u_mu_fused_root"], placed=1, tables_for_module=1,
                                 canonical_type=None, recipe_keys=[], blockers=[])])
    (out / "views.json").write_text(json.dumps(views, indent=1) + "\n")
    fill = (19906 + 8342) / (W * H)
    print(json.dumps(dict(view=views["view_list"][0]["view"], moved=moved, stations=nst, fill_est=round(fill, 3),
                          clk=CLK, macros=[m[:4] for m in MACROS])))


if __name__ == "__main__":
    main(*sys.argv[1:3])
