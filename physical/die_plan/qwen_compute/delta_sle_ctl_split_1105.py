#!/usr/bin/env python3
"""QC-SLECTL-B 11-05 (DIE-QC-82, COORD 21:01 vB): sle_ctl split plan event (plan_qc52 delta), the 4 sle_ctl classes.

sle_ctl is 522,340 cells after place (394k movable + 118k tapcells; synth 315,910) [kit-wave efdb36e864 sle_ctl__cl372cea1c
attempt_2], over the 517k OpenROAD cap.  vB hardens the big leaf blocks as children (OWNER safe form: registered faces,
util <= 0.45, <= 150k cells each, short reach):
  * the 10 widest forwarded-clock landing rings (ot_dp_clk_landing_cas #(.W(457..2104), DEPTH 4, WFALL 1, WREG 1,
    DSREP 1)), each on its own plan band (rect unchanged, child outline = the band snapped in to 0.432 um), as named
    wrapper masters sle_cland_w<W>_<face>[_<k>] (param_wrap: kit-only rename of the one paramod instance, proved
    equivalent; no logic, no cycles).  Their faces are registered by construction (d -> fclk-fall writer flops, q -> clk
    flops).  Their reset pin keeps its bound net cland_start (reset_net, not a wavefront target): no RTL change.
  * u_ctl (qfd_dv_s5_ctl_repair4_leaf, 42.7k cells, HARD=1 production shape) as one hard core, reset_net rst_n (the
    leaf tap net it has today): no RTL change.
Children keep their bound paths (physical_inst u_bound.u_cland_<band> / u_bound.u_u_ctl).  Parent faces and pins are
unchanged; the landing bands stay in the contract (ring_input_sdc, pin_reg) with band.hard_core = the child inst.
Clock: core_taps early, one core tap per child clk pin (ck for ctl) at 250 / 202.5 ps ESTIMATE (the DIE-QC-75 target;
re-measure from each child's own kit).  Reset collector tree re-derived if the new obstacles move it.
Pin tables (cores/sle_ctl/): rings from sle_ctl_pins.ring_pins in the parent pin order of their bus; ctl from
sle_ctl_pins.ctl_pins (bound-RTL connectivity, committed table, regenerated with --bound).
usage: delta_sle_ctl_split_1105.py PLAN_IN PLAN_OUT [REPORT.json [SIDECAR_IN SIDECAR_OUT]]"""
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))
sys.path.insert(0, str(HERE / "cores"))
import schema as S  # noqa: E402
import reset_tree as RT  # noqa: E402
import gen_phys as G  # noqa: E402
import sle_ctl_pins as SP  # noqa: E402

ID = "QC-SLECTL-B/SPLIT-1105"
TYPES = ("sle_ctl__cl372cea1c", "sle_ctl__cl503337ff", "sle_ctl__cl67434795", "sle_ctl__cla4f6f12f")
P5 = {"DEPTH": 4, "WFALL": 1, "WREG": 1, "DSREP": 1}
BASE = "ot_dp_clk_landing_cas"
# band, W, face of the d pins (= the face its parent pins enter)
RINGS = [("b_tw_data_i", 2104, "S"), ("x_fw_i", 537, "W"), ("x_fw_p2_i", 537, "E"), ("x_fw_p1_i", 537, "S"),
         ("x_su_l1_i", 457, "S"), ("x_su_l0_i", 457, "E"), ("cws1_i", 517, "N"), ("x_hc1_st_b_i", 517, "N"),
         ("cws2_i", 517, "N"), ("x_st_a_st_b_i", 653, "W")]
CTL = dict(inst="u_ctl", module="qfd_dv_s5_ctl_repair4_leaf", physical_inst="u_bound.u_u_ctl",
           origin_um=[475.2, 336.96], outline_um=[345.6, 259.2], cells=42700,
           cells_basis="sle_ctl a2 synth_stat: u_ctl flattened, ~42.7k cells")
CTL_PINS = "cores/sle_ctl/qfd_dv_s5_ctl_repair4_leaf_pins.json"
TOFF = [0.012, 0.012]
TT, FF = 250.0, 202.5
G4 = 0.432


def snap_in(r):
    x0, y0 = math.ceil(r[0] / G4 - 1e-6) * G4, math.ceil(r[1] / G4 - 1e-6) * G4
    x1, y1 = math.floor(r[2] / G4 + 1e-6) * G4, math.floor(r[3] / G4 + 1e-6) * G4
    return [round(x0, 3), round(y0, 3)], [round(x1 - x0, 3), round(y1 - y0, 3)]


def ring_cells(W):
    import cells as C
    return C.ring_cells(W - 1)


def ring_order(P, tn, band, face):
    pins = [(b, x, y) for n, b, _l, x, y, f in G.type_pins(P, tn) if n == band]
    pins.sort(key=lambda r: (r[2] if face in "WE" else r[1], r[0]))
    return [b for b, _x, _y in pins]


def main():
    pin, pout = sys.argv[1:3]
    rep_p = sys.argv[3] if len(sys.argv) > 3 else None
    text = open(pin).read()
    P0 = json.loads(text)
    seps = next((sp for sp in ((", ", ": "), (",", ":")) if json.dumps(P0, separators=sp) + "\n" == text), None)
    assert seps, "plan text style is not one-line json.dumps"
    P = copy.deepcopy(P0)
    SP0 = S.Plan(P0, pin)
    odir = Path(pout).resolve().parent
    ctl_tbl = json.loads((odir / CTL_PINS).read_text()) if (odir / CTL_PINS).is_file() else \
        json.loads((HERE / "plan_of_record" / CTL_PINS).read_text())
    assert ctl_tbl["outline_um"] == CTL["outline_um"]
    masters, rep = {}, dict(event=ID, types={}, added_cycles=0)
    for tn in TYPES:
        t = P["partition_types"][tn]
        tree0 = RT.for_type(SP0, tn)
        assert not t.get("hard_cores") and t["clock"].get("core_taps") is None, tn
        assert not [x for x in t["clock"]["taps"] if x.get("kind") == "core"], tn
        assert any(c["inst"] == "u_ctl" and c["module"] == CTL["module"] for c in t["contents"]), tn
        bands = t["clock"]["landing_contract"]["bands"]
        hcs, taps = [], []
        for band, W, face in RINGS:
            b = bands[band]
            assert b["instance"] == f"u_cland_{band}" and b.get("ring_place") == "ff", (tn, band)
            org, outl = snap_in(b["rect_um"])
            order = ring_order(SP0, tn, band, face)
            assert len(order) == W, (tn, band, len(order), W)
            key = (W, face, tuple(outl), tuple(order))
            if key not in masters:
                k = sum(1 for m in masters.values() if m["W"] == W and m["face"] == face)
                name = f"sle_cland_w{W}_{face.lower()}" + (f"_{k}" if k else "")
                tbl = SP.ring_pins(name, W, face, outl, order)
                masters[key] = dict(name=name, W=W, face=face, outline=outl, table=tbl,
                                    pins_file=f"cores/sle_ctl/{name}_pins.json")
            m = masters[key]
            inst = f"cl_{band}"
            ck = next(p for p in m["table"]["pins"] if p["name"] == "clk")
            hcs.append(dict(inst=inst, module=m["name"], origin_um=org, outline_um=list(outl), orient="R0",
                            track_offset_um=list(TOFF), pins_file=m["pins_file"], physical_inst=f"u_bound.u_cland_{band}",
                            physical_master=m["name"], param_wrap=dict(base=BASE, params=dict(W=W, **P5)),
                            reset_net="cland_start", cells=ring_cells(W),
                            cells_basis="cells.ring_cells (LAND-KV-1 measured ring model)",
                            note=f"{ID}: landing ring u_cland_{band} as a hard child on its band; registered faces by "
                                 f"construction; 0 added cycles; UNSIGNED until its kit signs off"))
            taps.append(dict(name=f"{inst}.clk", kind="core",
                             xy=[round(org[0] + ck["x"] + TOFF[0], 3), round(org[1] + ck["y"] + TOFF[1], 3)],
                             insertion_ps=TT, insertion_ff_ps=FF,
                             budget_owner=f"{ID}: target 250/202.5 ESTIMATE, re-measure from the child's own kit"))
            b["hard_core"] = inst
        ck = next(p for p in ctl_tbl["pins"] if p["name"] == "ck")
        o = CTL["origin_um"]
        hcs.append(dict(inst=CTL["inst"], module=CTL["module"], origin_um=list(o), outline_um=list(CTL["outline_um"]),
                        orient="R0", track_offset_um=list(TOFF), pins_file=CTL_PINS,
                        physical_inst=CTL["physical_inst"], physical_master=CTL["module"], reset_net="rst_n",
                        cells=CTL["cells"], cells_basis=CTL["cells_basis"],
                        note=f"{ID}: u_ctl as a hard child; 0 added cycles; UNSIGNED until its kit signs off"))
        taps.append(dict(name=f"{CTL['inst']}.ck", kind="core",
                         xy=[round(o[0] + ck["x"] + TOFF[0], 3), round(o[1] + ck["y"] + TOFF[1], 3)],
                         insertion_ps=TT, insertion_ff_ps=FF,
                         budget_owner=f"{ID}: target 250/202.5 ESTIMATE, re-measure from the child's own kit"))
        for h in hcs:
            assert h["origin_um"][0] >= 0 and h["origin_um"][1] >= 0
            assert h["origin_um"][0] + h["outline_um"][0] <= t["outline_um"][0]
            assert h["origin_um"][1] + h["outline_um"][1] <= t["outline_um"][1]
        t["hard_cores"] = hcs
        t["clock"]["core_taps"] = "early"
        t["clock"]["taps"] += taps
        tree1 = RT.for_type(S.Plan(P, pout), tn)
        moved = json.dumps(tree1, sort_keys=True) != json.dumps(tree0, sort_keys=True)
        if moved:
            assert RT.consumer_count(tree1) == RT.consumer_count(tree0), "consumer count moved"
            t["clock"]["landing_contract"]["collector_tree"] = json.loads(json.dumps(tree1))
        rep["types"][tn] = dict(reset_tree_moved=moved, hard_cores=len(hcs))
    for tn in P["partition_types"]:
        if tn not in TYPES:
            assert P["partition_types"][tn] == P0["partition_types"][tn]
    assert {k: v for k, v in P.items() if k != "partition_types"} == {k: v for k, v in P0.items() if k != "partition_types"}
    for m in masters.values():
        f = odir / m["pins_file"]
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(m["table"], indent=1) + "\n")
    if not (odir / CTL_PINS).is_file():
        (odir / CTL_PINS).write_text(json.dumps(ctl_tbl, indent=1) + "\n")
    out = json.dumps(P, separators=seps) + "\n"
    open(pout, "w").write(out)
    rep.update(masters=sorted(m["name"] for m in masters.values()),
               src_sha256=hashlib.sha256(text.encode()).hexdigest(), dst_sha256=hashlib.sha256(out.encode()).hexdigest())
    if len(sys.argv) > 5:
        stext = open(sys.argv[4]).read()
        side = json.loads(stext)
        sst = next((k for k in (1, None) if json.dumps(side, indent=k) + "\n" == stext), 1)
        ch = False
        for tn in TYPES:
            if P["partition_types"][tn].get("hard_cores"):
                import landing_collector as LC
                typ = P["partition_types"][tn]
                by_inst = {h["inst"]: h for h in typ["hard_cores"]}
                bands = typ["clock"]["landing_contract"]["bands"]
                points = {}
                for name, band in bands.items():
                    if not band.get("hard_core"):
                        continue
                    h = by_inst[band["hard_core"]]
                    pins = {q["name"]: q for q in json.loads((odir / h["pins_file"]).read_text())["pins"]}
                    off = h.get("track_offset_um", [0, 0])
                    points[name] = [[h["origin_um"][0]+pins[n]["x"]+off[0],
                                     h["origin_um"][1]+pins[n]["y"]+off[1]] for n in ("ready", "fault")]
                info = side["collector"]["types"][tn]
                rep["types"][tn]["collector_attachments"] = LC.reattach_sources(
                    info, typ["clock"]["landing_contract"]["collector_tree"], status_points=points)
                for source in info["local_sources"]:
                    if source["name"] in points:
                        source["band"] = copy.deepcopy(bands[source["name"]])
                ch = True
        open(sys.argv[5], "w").write(json.dumps(side, indent=sst) + "\n")
        rep["sidecar_changed"] = ch
    if rep_p:
        open(rep_p, "w").write(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(masters=rep["masters"], types=rep["types"])))


if __name__ == "__main__":
    main()
