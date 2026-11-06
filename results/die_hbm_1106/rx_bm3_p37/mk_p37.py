#!/usr/bin/env python3
"""DIE-HBM-81 d44v part 37: adopt the HBM-GAPS-7 RX BM3 vB safe form in the plan (COORD 11:00 (2)).

ot_pdie_serdes_rx (302.4 x 345.6, 5 instances, all R0) becomes, inside the SAME slot (origin and outline kept):
  u_rest  ot_pdie_serdes_rx_bm3_rest   197.856 x 345.6 at rx-frame (104.544, 0)         view @7826e3baf53d (Model-A table)
  u_bm0-2 ot_pdie_serdes_rx_bm_native   95.904 x 106.56 at rx-frame (0, 4.32 + 115.2 i)  view @cefde5fe417d (signed kit table)
Tables = the HBM-GAPS-7 Model-A tables byte for byte (Codex prep_modelA on the current rx table fd611656, 8.64 street).
Every outer rx port moves to the residual (BM pins are seam-only), so all sidecar refs u_lk_X__rx -> u_lk_X__rx__rest;
the BMs get their own hard_cores rows, clock entries, taps and seam core_conns.  physical_inst follows the plan composition
results/die_hbm_1106/rx_bm3_p37/ot_pdie_serdes__p37comp.sv (u_rx = ot_pdie_serdes_rx__p37: u_rest + u_bm0..2).
    mk_p37.py D44V_DIR TABLE_DIR     (in place on the gz plan files of the d44v dir)"""
import copy, gzip, json, re, shutil, sys
from pathlib import Path
D, TD = Path(sys.argv[1]), Path(sys.argv[2])
G = 8.64
REST, BM = "ot_pdie_serdes_rx_bm3_rest", "ot_pdie_serdes_rx_bm_native"
TR, TB = f"{REST}__197.856x345.6__hg7_modelA.json", f"{BM}__95.904x106.56__hg7_modelA.json"
WR, WB = [197.856, 345.6], [95.904, 106.56]
OR_, OB = [104.544, 0.0], [[0.0, 4.32], [0.0, 119.52], [0.0, 234.72]]
r3 = lambda v: round(v + 0.0, 3)


def rd(n):
    return json.loads(gzip.decompress((D / (n + ".gz")).read_bytes()))


def wr(n, o, indent=None):
    b = (json.dumps(o, indent=indent) + "\n").encode()
    with open(D / (n + ".gz"), "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as g:
        g.write(b)


P, CC, CE = rd("die_plan.json"), rd("core_conns.json"), rd("clock_entries.json")
for t in (TR, TB):
    shutil.copyfile(TD / t, D / "cores" / t)
pinsR, pinsB = json.loads((TD / TR).read_text()), json.loads((TD / TB).read_text())
ckR = {p["name"]: (p["x"], p["y"]) for p in pinsR if p["name"] in ("clk", "rck_clk")}
ckB = next((p["x"], p["y"]) for p in pinsB if p["name"] == "clk")
assert set(ckR) == {"clk", "rck_clk"}
RX = re.compile(r"(?<![\w.])(u_lk_[NS]\d)__rx(?![\w])")


def ren(s):
    return RX.sub(r"\1__rx__rest", s) if isinstance(s, str) else s


def deep(o):
    if isinstance(o, dict):
        return {ren(k): deep(v) for k, v in o.items()}
    if isinstance(o, list):
        return [deep(v) for v in o]
    return ren(o)


log = []
for tn, T in P["partition_types"].items():
    hc = T.get("hard_cores") or []
    rows = [h for h in hc if h["module"] == "ot_pdie_serdes_rx"]
    if not rows:
        continue
    for old in rows:
        assert old["outline_um"] == [302.4, 345.6] and old.get("orient", "R0") == "R0", (tn, old["inst"])
        I = old["inst"]
        ox = old["origin_um"][0] + old.get("track_offset_um", [0, 0])[0]
        oy = old["origin_um"][1] + old.get("track_offset_um", [0, 0])[1]

        def row(tag, mod, loc, wh, tab, phys):
            X, Y = ox + loc[0], oy + loc[1]
            gx, gy = round(X / G) * G, round(Y / G) * G
            return dict(inst=f"{I}__{tag}", module=mod, origin_um=[r3(gx), r3(gy)], outline_um=list(wh),
                        track_offset_um=[r3(X - gx), r3(Y - gy)], pins_file=f"cores/{tab}",
                        physical_inst=f"{old['physical_inst']}.{phys}", physical_master=mod, obs_max=old.get("obs_max", "M5"),
                        note=f"DIE-HBM-81 d44v part 37: RX BM3 vB sub-core {phys} of the rx slot {I.removesuffix("__rx")}.u_rx (slot kept; HBM-GAPS-7 form; "
                             f"glue results/die_hbm_1106/rx_bm3_p37/ot_pdie_serdes__p37comp.sv)")
        new = [row("rest", REST, OR_, WR, TR, "u_rest")] + [row(f"bm{i}", BM, OB[i], WB, TB, f"u_bm{i}") for i in range(3)]
        k = hc.index(old)
        hc[k:k + 1] = new
        # clock: taps + entries (residual keeps the rx entry point; BMs at their signed kit clock pin)
        taps = T["clock"]["taps"]
        ti = next(j for j, tp in enumerate(taps) if tp.get("name") == I)
        t0 = taps[ti]
        nt = []
        rt = copy.deepcopy(t0)
        rt["name"] = f"{I}__rest"
        rt["note"] = "DIE-HBM-81 p37: rx tap -> residual (same point) | " + t0.get("note", "")
        nt.append(rt)
        ce_t = CE[tn]
        e0 = ce_t.pop(I)
        er = copy.deepcopy(e0)
        er["xy_um"] = [r3(e0["xy_um"][0] - OR_[0]), r3(e0["xy_um"][1] - OR_[1])]
        er["island_um"] = [r3(v - OR_[i % 2]) for i, v in enumerate(e0["island_um"])]
        er.update(tap=f"{I}__rest", module=REST, native_module=REST,
                  source="DIE-HBM-81 p37: rx entry kept, residual frame (Model-A clk/rck_clk M5 pins inside the island) | " + e0.get("source", ""))
        assert all(er["island_um"][0] <= x <= er["island_um"][2] and er["island_um"][1] <= y <= er["island_um"][3]
                   for x, y in ckR.values()), er
        ce_t[f"{I}__rest"] = er
        for i in range(3):
            bt = copy.deepcopy(t0)
            bt["name"] = f"{I}__bm{i}"
            bt["xy"] = [r3(ox + OB[i][0] + ckB[0]), r3(oy + OB[i][1] + ckB[1])]
            bt["note"] = f"DIE-HBM-81 p37: BM{i} tap at its signed kit clock pin (BM clk = rx rck_clk, merged rx clock)"
            nt.append(bt)
            ce_t[f"{I}__bm{i}"] = dict(
                xy_um=[ckB[0], ckB[1]],
                island_um=[r3(ckB[0] - 4.32), r3(ckB[1] - 4.32), r3(ckB[0] + 4.32), r3(ckB[1] + 4.32)],
                source="DIE-HBM-81 p37: signed BM kit clock pin (ot_pdie_serdes_rx_bm_native_cefde5fe417d-vB)",
                stack=e0.get("stack"), latency_target_tt_ps=e0.get("latency_target_tt_ps"),
                latency_target_ff_ps=e0.get("latency_target_ff_ps"), port=None, merged_clock_ports=["clk"],
                tap=f"{I}__bm{i}", module=BM, native_module=BM)
        taps[ti:ti + 1] = nt
        # conns: residual = the rx conns + its seam ports; BMs = seam only
        C = CC[tn]
        c0 = C.pop(I)
        cr = dict(c0)
        bms = [f"core:{I}__bm{i}" for i in range(3)]
        for p in ("bm_S", "bm_ld", "bm_rs_n", "bm_lam", "bm_om", "bm_L", "bm_any", "bm_done"):
            cr[p] = list(bms)
        C[f"{I}__rest"] = cr
        for i in range(3):
            C[f"{I}__bm{i}"] = {p: [f"core:{I}__rest"] for p in ("S", "ld", "rs_n", "lam", "om", "L", "any", "done")}
            C[f"{I}__bm{i}"]["clk"] = [f"tap:{I}__bm{i}"]
        log.append((tn, I, [(n["inst"], n["origin_um"], n["track_offset_um"]) for n in new]))
    # every other ref of the rx inst (stations, partner conns) -> residual
    if "internal_stations" in T:
        T["internal_stations"] = deep(T["internal_stations"])
    T["clock"]["taps"] = deep(T["clock"]["taps"])
    CC[tn] = deep(CC[tn])
    CE[tn] = deep(CE[tn])
left = [m.group(0) for m in RX.finditer(json.dumps(P) + json.dumps(CC) + json.dumps(CE))]
assert not left, left[:5]
wr("die_plan.json", P)
wr("core_conns.json", CC, indent=1)
wr("clock_entries.json", CE)
cm = json.loads((D / "core_macros.json").read_text())
cm["cores"][REST] = {
    "status": "KNOWN", "outline_um": WR, "macros": [
        {"name": "u_fcore.u_dly.u_dmem", "master": "ot_sram_1r1w2c_64x546_m1", "orient": "R0",
         "rect_um": [9.624, 54.012, r3(9.624 + 178.632), r3(54.012 + 81)]},
        {"name": "u_fcore.u_out.u_cmem", "master": "ot_sram_1r1w_32x546_m1", "orient": "R0",
         "rect_um": [9.624, 205.212, r3(9.624 + 177.768), r3(205.212 + 81)]}],
    "channel_rule_um": 10.8,
    "basis": "DIE-HBM-81 d44v part 37: HBM-GAPS-7 RX BM3 residual; macro homes = its kit macro_placement (gen_hg7/macros_res.json)"}
(D / "core_macros.json").write_text(json.dumps(cm, indent=1) + "\n")
for item in log:
    print("P37", *item)
