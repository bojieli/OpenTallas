#!/usr/bin/env python3
"""PATH-HBM/ROOTPACK option R3 (2026-10-25): root re-pack, NO outline change, on top of the B2p delta.

    python3 physical/die_plan/hbm_arch/path_hbm_b2p_r3.py --src B2p_base_ids --out B2p_r3 --chain B2p_inputs

Layout (root type frame 1382.4 x 5356.8, 8.64 lattice):
  * idx/host/hc cluster packed into a bottom band y 34.56..1157.76 (3 rows: link+selector / rxs+ctl+argmax+xqr+col /
    7 hc cores), directly W/E of the low W+E idx windows (L80/L12/L74/L48/L53/L64, y 399-1740).
  * TKM snake 3 columns x 11 rows (x 207.36 / 535.68 / 864.0; col0 R0 up = root + tile0..9, col1 MX down = tile10..20,
    col2 R0 up = tile21..31), chain pins face-to-face; root at col0 bottom faces the W L74 window (993-1412).
  * W edge 0..207.36 and E edge 1183.68..1382.4 = vertical corridors (L13/L62/L89 down to the cluster, L9/L63 up to N).
  * horizontal corridors between rows: L4 (+L96) gap r4/r5 and L150 gap r7/r8 (sizes printed; NOT the bit-sized
    widths: the outline has no room, see report 'shortfall').
Then path_hbm_b2p.step_a (pins, chain conns, conv relay, taps, hop table) with this placement, R3-INTERNAL stations
re-derived for every non-TKM root core link (b2o.internal_stations), FT slots re-sited (hbm_bit_stations.repair root).
"""
import argparse, copy, json, math, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "tools/die_plan"))
import path_hbm_b2p as PB  # noqa: E402

LAT, W_T, H_T = 8.64, 319.68, 345.6
COLS = [207.36, 535.68, 864.0]
Y0 = 1192.32
GAP = [8.64] * 10
GAP[4] = 164.16      # r4/r5: L4x1+L4mx1+L96 corridor (needs 5676 b / 20.05 b/um = 283 um)
GAP[7] = 69.12       # r7/r8: L150 corridor (1120 b -> 56 um)
CLUSTER = {          # hard cores (origin, keeps orient)
    "u_hb_idx__link": (34.56, 34.56), "u_hb_idx__selector": (699.84, 34.56),
    "u_host_cp_rxs": (34.56, 544.32), "u_hb_idx__ctl": (483.84, 544.32), "u_hb_argmax": (483.84, 812.16),
    "u_col_idx": (967.68, 768.96),
    "u_hc_eng_tail0_sk_steady": (34.56, 984.96), "u_hc_eng_tail0_sk_step0": (198.72, 984.96),
    "u_hc_eng_tail0_rest": (362.88, 984.96), "u_hc_eng_tail1_rest": (527.04, 984.96),
    "u_hc_eng_tail1_sk_step0": (691.2, 984.96), "u_hc_eng_tail1_sk_steady": (855.36, 984.96),
    "u_hc_eng_hcp_sys1": (1019.52, 984.96)}
SOFT = {"u_hb_idx__xqr": (967.68, 544.32), "u_hb_idx__xq_N": (1235.52, 544.32), "u_hb_idx__xq_S": (1235.52, 682.56),
        "u_su_prog": (1192.32, 820.8), "u_col_su": (1287.36, 820.8), "u_str_C": (1192.32, 924.48),
        "u_host_cp_ingress": (1244.16, 924.48), "u_hb_router_ids": (1287.36, 924.48), "u_obs_C": (1322.88, 924.48),
        "u_host_status": (1192.32, 984.96), "u_vm_status4": (1227.6, 984.96)}
BITS_PER_UM = (1 / 0.048 + 1 / 0.064) * 0.55     # M5+M7 (= M4+M6) tracks at 0.55 utilisation = 20.05 b/um


def rows():
    y, out = Y0, []
    for i in range(11):
        out.append(round(y, 3))
        if i < 10:
            y += H_T + GAP[i]
    return out


def placement():
    R = rows()
    t = []
    for k in range(10):
        t.append(dict(inst=f"u_tkm_SW_tile{k}", tile_tid=k, origin_um=[COLS[0], R[k + 1]], orient="R0"))
    for j in range(11):
        t.append(dict(inst=f"u_tkm_SW_tile{10 + j}", tile_tid=10 + j, origin_um=[COLS[1], R[10 - j]], orient="MX"))
    for j in range(11):
        t.append(dict(inst=f"u_tkm_SW_tile{21 + j}", tile_tid=21 + j, origin_um=[COLS[2], R[j]], orient="R0"))
    return dict(root=dict(inst="u_tkm_SW_root", origin_um=[COLS[0], R[0]], orient="R0"), tiles=t,
                note="PATH-HBM/ROOTPACK R3: 3x11 column snake")


def snake_blocks(R):
    """contiguous snake row groups (split at the corridor gaps) as single routing blockages."""
    out, start = [], 0
    for i in range(11):
        if i == 10 or GAP[i] > LAT + 1e-6:
            y0, y1 = R[start], R[i] + H_T
            out.append((COLS[0], y0, COLS[2] + W_T - COLS[0], round(y1 - y0, 3)))
            start = i + 1
    return out


def conv_path(plan_pins_root, plan_pins_term, R):
    """root conv pin (root N face, col0) -> gap -> W edge -> top band -> tile31 conv pin (col2 r10, N face = top)."""
    rx = COLS[0] + plan_pins_root["x"]
    ry = R[0] + H_T
    tx = COLS[2] + plan_pins_term["x"]
    ty = R[10] + H_T
    top = ty + 30.24
    return [[rx, ry], [rx, ry + 4.32], [103.68, ry + 4.32], [103.68, top], [tx, top], [tx, ty]]


def place_cluster(T, log):
    HC = {c["inst"]: c for c in T["hard_cores"]}
    CT = {c["inst"]: c for c in T["contents"]}
    for n, xy in CLUSTER.items():
        HC[n]["origin_um"] = list(xy)
        if n in CT:
            CT[n]["origin_um"] = list(xy)
        log.append(dict(inst=n, to=list(xy)))
    for n, xy in SOFT.items():
        CT[n]["origin_um"] = list(xy)
        log.append(dict(inst=n, to=list(xy), soft=True))
    hc = [HC[n] for n in HC if n.startswith("u_hc_eng_")]
    x0 = min(c["origin_um"][0] for c in hc); y0 = min(c["origin_um"][1] for c in hc)
    x1 = max(c["origin_um"][0] + c["outline_um"][0] for c in hc); y1 = max(c["origin_um"][1] + c["outline_um"][1] for c in hc)
    CT["u_hc_eng"]["origin_um"] = [x0, y0]; CT["u_hc_eng"]["outline_um"] = [round(x1 - x0, 3), round(y1 - y0, 3)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True); ap.add_argument("--out", required=True); ap.add_argument("--chain", required=True)
    ap.add_argument("--no-ft-repair", action="store_true")
    a = ap.parse_args(argv)
    src, out, chain = Path(a.src), Path(a.out), Path(a.chain)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out)
    # chain dir for step_a: B2p chain inputs + the R3 placement + conv path
    cdir = out / "inputs" / "r3_chain"
    cdir.mkdir(parents=True, exist_ok=True)
    for f in chain.iterdir():
        if f.is_file():
            shutil.copyfile(f, cdir / f.name)
    pl = placement()
    json.dump(pl, open(cdir / "tkm_chain_placement.json", "w"), indent=1)
    rp = {q["name"]: q for q in json.load(open(chain / f"{PB.ROOT_M}__repin.json"))}
    tp = {q["name"]: q for q in json.load(open(chain / f"{PB.TERM_M}__repin.json"))}
    R = rows()
    cv = json.load(open(chain / "tkm_conv_tree.json"))
    cv["path"] = conv_path(rp["x_u_u_g_tiles_0_e86_u_tile_conv"], tp["tile_conv"], R)
    cv["note"] = "PATH-HBM/ROOTPACK R3 conv relay: root N gap -> W edge corridor -> top band -> tile31 N conv pin"
    json.dump(cv, open(cdir / "tkm_conv_tree.json", "w"), indent=1)

    plan = json.load(open(out / "die_plan.json"))
    T = plan["partition_types"]["root"]
    log = dict(src=str(src), src_plan_sha256=PB.sha(src / "die_plan.json"), pin_files={}, moved=[], soft_moved=[],
               r3=dict(rows=R, cols=COLS, gaps=GAP, cluster=[]))
    place_cluster(T, log["r3"]["cluster"])
    # partition clock tap: centre of the L4 corridor (B2p tap 691.2,2656.8 would sit inside a col1 tile)
    T["clock"]["tap_um"] = [691.2, round(R[4] + H_T + GAP[4] / 2, 3)]
    PB.step_a(plan, out, cdir, log)
    # u_tkm_SW soft bbox = snake bbox
    HC = {c["inst"]: c for c in T["hard_cores"]}
    tkc = [c for n, c in HC.items() if n.startswith("u_tkm_SW_")]
    CT = {c["inst"]: c for c in T["contents"]}
    x0 = min(c["origin_um"][0] for c in tkc); y0 = min(c["origin_um"][1] for c in tkc)
    x1 = max(c["origin_um"][0] + c["outline_um"][0] for c in tkc); y1 = max(c["origin_um"][1] + c["outline_um"][1] for c in tkc)
    CT["u_tkm_SW"]["origin_um"] = [x0, y0]; CT["u_tkm_SW"]["outline_um"] = [round(x1 - x0, 3), round(y1 - y0, 3)]
    # conv relay re-stationed at <= 360 um pitch (step_a uses 400; 'well under 405')
    for s in T["internal_stations"]:
        if s["conn"].startswith("u_tkm_SW_root.x_u_u_g_tiles_0_e86_u_tile_conv"):
            regs, L, pitch = PB.stations_along(cv["path"], 360.0)
            s["regs_um"] = regs
            s["note"] = (f"B2p_r3 PATH-HBM conv relay root -> tile31 (TOKEN CB21): {L:.1f} um, {len(regs)} stations, "
                         f"pitch {pitch:.1f} um <= 360 (W edge corridor + top band)")
            hops = [abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip([s["from_um"]] + regs, regs + [s["to_um"]])]
            log["stations"].update(conv_stations=len(regs), conv_worst_hop_um=round(max(hops), 1))
    # R3-INTERNAL stations for every root core link on the new geometry (TKM conv relay from step_a kept)
    import b2o  # noqa: E402
    import cores_b2 as CB  # noqa: E402
    # route non-TKM links in the corridors only: each contiguous snake row group is ONE blockage (the 8.64-um
    # inter-tile gaps carry ~173 b and are not corridors), so the relay router must use the W/E edges and the
    # L4/L150 row gaps
    blk = snake_blocks(R)
    _RR, _FP = CB.RelayRouter, CB.free_point

    class RR(_RR):
        def __init__(self, boxes, *a_, **k_):
            super().__init__(list(boxes) + blk, *a_, **k_)
    CB.RelayRouter = RR
    CB.free_point = lambda p, boxes, *a_, **k_: _FP(p, list(boxes) + blk, *a_, **k_)
    keep = [s for s in T["internal_stations"] if s["conn"].startswith("u_tkm_SW_root.x_u_u_g_tiles_0_e86_u_tile_conv")]
    ilog = []
    fails = b2o.internal_stations(plan, out, ["root"], ilog)
    T = plan["partition_types"]["root"]
    T["internal_stations"] = [s for s in T.get("internal_stations", [])
                              if not s["conn"].startswith("u_tkm_SW_root.x_u_u_g_tiles_0_e86_u_tile_conv")] + keep
    CB.RelayRouter, CB.free_point = _RR, _FP
    log["r3"]["internal_stations"] = dict(log=ilog, unroutable=fails, conns=len(T["internal_stations"]),
                                          sites=sum(len(s["regs_um"]) for s in T["internal_stations"]))
    if not a.no_ft_repair:
        import hbm_bit_stations as HBS  # noqa: E402
        try:
            fr = HBS.repair(plan, log=lambda m: None, only_types=["root"])
        except HBS.RepairFailure as e:
            fr = e.report
        log["r3"]["ft_repair"] = dict(checked=fr.get("checked"), added=len(fr.get("added", [])),
                                      type_failures=fr.get("type_failures"), unfixed=len(fr.get("unfixed", [])))
    # lane latency table = the plan's lanes after the FT re-siting (b2o rule); deltas recorded
    import schema as S  # noqa: E402
    P = S.Plan(plan)
    c0 = plan["latency"]["lanes"]
    newl = {lid: P.lane_latency(lid) for lid in P.lanes}
    log["r3"]["lane_cycle_delta"] = {k: v["cycles"] - c0[k]["cycles"] for k, v in newl.items()
                                     if k in c0 and v["cycles"] != c0[k]["cycles"]}
    plan["latency"]["lanes"] = newl
    # corridor budget (bits that must cross the snake horizontally / climb the edges) vs geometry
    W, H = T["outline_um"]
    need_h = dict(L4x1=2816, L4mx1=2816, L150x2=560, L150mx2=560, L96=44, L139_140=8)
    gaps_um = sum(GAP)
    log["r3"]["corridors"] = dict(
        bits_per_um=round(BITS_PER_UM, 2),
        horizontal_cross_bits=sum(need_h.values()), horizontal_gap_um=round(gaps_um, 2),
        horizontal_capacity_bits=round(gaps_um * BITS_PER_UM),
        top_band_um=round(H - (R[10] + H_T), 2), top_band_capacity_bits=round((H - (R[10] + H_T)) * BITS_PER_UM),
        top_band_need_bits=3297, w_edge_um=COLS[0], e_edge_um=round(W - COLS[2] - W_T, 2),
        edge_need_bits_each=3625, edge_capacity_bits_each=round(min(COLS[0], W - COLS[2] - W_T) * BITS_PER_UM),
        bottom_turn_um=round(R[0] - max(c["origin_um"][1] + c["outline_um"][1] for n, c in HC.items()
                                         if not n.startswith("u_tkm_SW_")), 2))
    json.dump(plan, open(out / "die_plan.json", "w"), indent=1)
    log["out_plan_sha256"] = PB.sha(out / "die_plan.json")
    json.dump(log, open(out / "b2p_r3_report.json", "w"), indent=1)
    print(json.dumps(dict(lane_cycle_delta=log["r3"]["lane_cycle_delta"], stations=log["stations"], ist=log["r3"]["internal_stations"]["log"], unroutable=fails[:5],
                          ft=log["r3"].get("ft_repair"), corridors=log["r3"]["corridors"],
                          worst_tap_dist=log["cts_hop_table"]["worst_tap_dist_um"],
                          worst_root_delta=log["cts_hop_table"]["worst_root_delta_um"], soft_moved=log["soft_moved"],
                          plan=log["out_plan_sha256"][:8]), indent=0))


if __name__ == "__main__":
    main()
