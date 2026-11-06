#!/usr/bin/env python3
"""QC CBN conservative form B (QC-CBN-RF1 11-06): harden the five forwarded-clock landing rings of the two failing
cbn_q00 classes as registered-face hard children at their parent pins; keep the four NK children.

Why: cbn_q00__cl622f65d2 failed GRT (overflow 1,170,056, M6/M4 horizontal, capacity-0 boxes over the NK macros);
the soft rsf_i / na_i00 rings (11,606 cells each) were placed in the 82-um left strip far from their top-face pins and
carry most sampled overflow nets. Each ring becomes one child in the top (north rings) / bottom (south rings) strip
directly under its pins. Soft cells drop 172,914 -> ~114,838 (<=150k, OWNER safe form B). 0 data cycles.

Masters are keyed by (W, face, outline, parent pin order). The na_i00 key equals the AP-signed HC0 master
sle_cland_w515_n (byte-identical pin table, same RTL) and is reused. Other orders need their own master:
nb_i00 / rsf_i (W515 N) and bc_i00 / bc_i10 (W517 S) all have different parent pin orders.
Not solved here: the collector/reset re-solve (native event) and the FF hold class of zero-logic shift chains
(u_d*_u_t_*_n_y, u_r8b_*, u_lpad_*, u_ft_rsf_o_*), which this event does not touch.
Usage: delta_cbn_ring_split_1106.py PLAN_IN PLAN_OUT REPORT
"""
import copy, hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "tools" / "die_plan"))
sys.path.insert(0, str(REPO / "physical" / "die_plan" / "qwen_compute" / "cores"))
import schema as S  # noqa: E402
import reset_tree as RT  # noqa: E402
import gen_phys as G  # noqa: E402
import sle_ctl_pins as SP  # noqa: E402

ID = "QC-CBN-RF1/RING-SPLIT-1106"
TYPES = ("cbn_q00__cl622f65d2", "cbn_q00__cldbcda913")
P5 = {"DEPTH": 4, "WFALL": 1, "WREG": 1, "DSREP": 1}
BASE = "ot_dp_clk_landing_cas"
TOFF = [0.012, 0.012]
# band -> (origin, outline, face); north strip y 2462.4..2527.2, south strip y 4.32..77.76 (NK macro edges)
PLACE = {"na_i00": ([17.28, 2466.72], [88.56, 51.84], "N"),
         "rsf_i": ([187.92, 2466.72], [88.56, 51.84], "N"),
         "nb_i00": ([1129.68, 2466.72], [88.56, 51.84], "N"),
         "bc_i00": ([436.32, 17.28], [89.184, 51.84], "S"),
         "bc_i10": ([643.68, 17.28], [89.184, 51.84], "S")}
# measured synth cells of the soft rings (cbn_q00__cl622f65d2 attempt_7 1_synth_odb.v)
CELLS = {515: 11606, 517: 11652}
SIGNED = {"sle_cland_w515_n": dict(pins_sha256="37dc78dc7a12570794ae81ce84b8591f77b23f4ada8b4406d5810f8a58383c44",
                                   tt=90.19, ff=72.02,
                                   views="epyc4:/srv/opentallas-scratch2/claude/codex-qc-hc0-parent2-1106/views_ap/sle_cland_w515_n")}


def ring_order(P, tn, band, face):
    pins = [(b, x, y) for n, b, _l, x, y, f in G.type_pins(P, tn) if n == band]
    pins.sort(key=lambda r: (r[2] if face in "WE" else r[1], r[0]))
    return [b for b, _x, _y in pins]


def table_sha(tbl):
    return hashlib.sha256((json.dumps(tbl, indent=1) + "\n").encode()).hexdigest()


def main():
    pin, pout, rep_p = sys.argv[1:4]
    text = open(pin).read()
    P0 = json.loads(text)
    seps = next((sp for sp in ((", ", ": "), (",", ":")) if json.dumps(P0, separators=sp) + "\n" == text), None)
    assert seps, "plan text style is not one-line json.dumps"
    P = copy.deepcopy(P0)
    SP0 = S.Plan(P0, pin)
    odir = Path(pout).resolve().parent
    masters, rep = {}, dict(event=ID, types={}, added_cycles=0)
    for tn in TYPES:
        t = P["partition_types"][tn]
        tree0 = RT.for_type(SP0, tn)
        assert len(t["hard_cores"]) == 4 and all(h["module"] == "qfd_tile_nk_a0c" for h in t["hard_cores"]), tn
        assert t["clock"]["core_taps"] == "early", tn
        bands = t["clock"]["landing_contract"]["bands"]
        assert sorted(t["clock"]["landing_ring_wreg"]["buses"]) == sorted(PLACE), tn
        hcs, taps, rows = [], [], []
        for band, (org, outl, face) in PLACE.items():
            pins = [(bit, f) for name, bit, _l, _x, _y, f in G.type_pins(SP0, tn) if name == band]
            W = len(pins)
            assert {f for _, f in pins} == {face}, (tn, band)
            b = bands[band]
            assert b["instance"] == f"u_cland_{band}" and b.get("ring_place") == "ff", (tn, band)
            order = ring_order(SP0, tn, band, face)
            key = (W, face, tuple(outl), tuple(order))
            if key not in masters:
                cand = SP.ring_pins(f"sle_cland_w{W}_{face.lower()}", W, face, outl, order)
                if table_sha(cand) == SIGNED.get(cand["core"], {}).get("pins_sha256"):
                    name, reuse = cand["core"], True
                else:
                    k = sum(1 for m in masters.values() if m["W"] == W and m["face"] == face and not m["reuse"])
                    name, reuse = f"sle_cland_w{W}_{face.lower()}_{300 + k}", False
                tbl = SP.ring_pins(name, W, face, outl, order)
                masters[key] = dict(name=name, W=W, face=face, outline=outl, table=tbl, reuse=reuse,
                                    pins_file=f"cores/cbn_ring/{name}_pins.json", bands=[])
            m = masters[key]
            m["bands"].append(f"{tn}:{band}")
            inst = f"cl_{band}"
            ck = next(p for p in m["table"]["pins"] if p["name"] == "clk")
            sg = SIGNED.get(m["name"]) if m["reuse"] else None
            hcs.append(dict(inst=inst, module=m["name"], origin_um=list(org), outline_um=list(outl), orient="R0",
                            track_offset_um=list(TOFF), pins_file=m["pins_file"], physical_inst=f"u_bound.u_cland_{band}",
                            physical_master=m["name"], param_wrap=dict(base=BASE, params=dict(W=W, **P5)),
                            reset_net="cland_start", cells=CELLS[W],
                            cells_basis="measured soft-ring synth cells (cl622f65d2 attempt_7 1_synth_odb.v)",
                            note=f"{ID}: landing ring u_cland_{band} as a hard child under its {face}-face pins; "
                                 f"registered faces by construction; 0 added cycles; "
                                 + (f"REUSES AP-signed {m['name']} ({sg['views']})" if sg else
                                    "UNSIGNED until its own kit signs off")))
            taps.append(dict(name=f"{inst}.clk", kind="core",
                             xy=[round(org[0] + ck["x"] + TOFF[0], 3), round(org[1] + ck["y"] + TOFF[1], 3)],
                             insertion_ps=sg["tt"] if sg else 250.0, insertion_ff_ps=sg["ff"] if sg else 202.5,
                             budget_owner=(f"{ID}: measured AP-signed child" if sg else
                                           f"{ID}: target 250/202.5 ESTIMATE, re-measure from the child's own kit")))
            b["hard_core"] = inst
            b["rect_um"] = [org[0], org[1], round(org[0] + outl[0], 3), round(org[1] + outl[1], 3)]
            rows.append(dict(band=band, master=m["name"], reuse=m["reuse"], W=W, face=face, origin=org, outline=outl))
        allh = t["hard_cores"] + hcs
        X, Y = t["outline_um"]
        for i, a in enumerate(allh):
            ax, ay = a["origin_um"]; aw, ah = a["outline_um"]
            assert ax >= 4.32 and ay >= 4.32 and ax + aw <= X - 4.32 and ay + ah <= Y - 4.32, (tn, a["inst"])
            for c in allh[i + 1:]:
                cx, cy = c["origin_um"]; cw, chh = c["outline_um"]
                assert min(ax + aw, cx + cw) <= max(ax, cx) or min(ay + ah, cy + chh) <= max(ay, cy), (tn, a["inst"], c["inst"])
        for k, v in bands.items():   # soft bands left (monitors) must not overlap a new child
            if v.get("hard_core") or "rect_um" not in v:
                continue
            r = v["rect_um"]
            for h in hcs:
                hx, hy = h["origin_um"]; hw, hh = h["outline_um"]
                assert min(r[2], hx + hw) <= max(r[0], hx) or min(r[3], hy + hh) <= max(r[1], hy), (tn, k, h["inst"])
        t["hard_cores"] = allh
        t["clock"]["taps"] += taps
        tree1 = RT.for_type(S.Plan(P, pout), tn)
        moved = json.dumps(tree1, sort_keys=True) != json.dumps(tree0, sort_keys=True)
        rep["types"][tn] = dict(rings=rows, reset_tree_moved=moved, reset_depth_before=tree0.get("depth"),
                                reset_depth_after=tree1.get("depth"))
    for tn in P["partition_types"]:
        if tn not in TYPES:
            assert P["partition_types"][tn] == P0["partition_types"][tn]
    assert {k: v for k, v in P.items() if k != "partition_types"} == {k: v for k, v in P0.items() if k != "partition_types"}
    for m in masters.values():
        f = odir / m["pins_file"]
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(m["table"], indent=1) + "\n")
    out = json.dumps(P, separators=seps) + "\n"
    open(pout, "w").write(out)
    rep["masters"] = [dict(name=m["name"], W=m["W"], face=m["face"], outline=m["outline"], reuse_signed=m["reuse"],
                           pins_sha256=table_sha(m["table"]), bands=m["bands"]) for m in masters.values()]
    rep.update(src_sha256=hashlib.sha256(text.encode()).hexdigest(), dst_sha256=hashlib.sha256(out.encode()).hexdigest())
    open(rep_p, "w").write(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(masters=[(m["name"], m["reuse_signed"], m["bands"]) for m in rep["masters"]],
                          reset={k: (v["reset_tree_moved"], v["reset_depth_before"], v["reset_depth_after"])
                                 for k, v in rep["types"].items()})))


if __name__ == "__main__":
    main()
