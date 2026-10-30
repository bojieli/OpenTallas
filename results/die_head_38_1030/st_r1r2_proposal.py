"""DIE-HEAD-38 R1/R2 plan proposal (no plan edit): stage xy + same-depth reset copies; checks every hop <= 380 um."""
import json, sys
L1 = lambda a, b: abs(a[0]-b[0]) + abs(a[1]-b[1])
LIM = 380.0

def st_like(din, uin, dout, uout, raws, wd_raw, wd_xy):
    # ring ready flop = band low-left corner (measured on src25q3 r2place: d_i (1380.8,247.7), u_i (17.9,25.8))
    src = {din: [1380.8, 247.7], uin: [17.9, 25.8]}
    pins = {f"up_{dout}": [2.144, 354.016], f"up_{uout}": [1440.736, 132.384],
            f"fstart_{dout}": [2.144, 358.368], f"fstart_{uout}": [1440.736, 136.736], "origin": [730.592, 230.56]}
    sin = {"agg": {uin: [[250, 100], [470, 210]], din: [[1035, 250]]},
           dout: {uin: [[250, 120], [485, 215]], din: [[1050, 275]]}}
    anc = {"u_cland_agg_1": [690, 250], "u_cland_agg_2": [900, 220], "u_cland_agg_3": [1110, 190],
           "u_cland_agg_4": [1320, 150],
           f"u_cland_loc_{dout}_1": [720, 300], f"u_cland_loc_{dout}_2": [490, 320], f"u_cland_loc_{dout}_3": [250, 340]}
    chains = {"agg": ["u_cland_agg_1", "u_cland_agg_2", "u_cland_agg_3", "u_cland_agg_4", f"up_{uout}"],
              dout: [f"u_cland_loc_{dout}_1", f"u_cland_loc_{dout}_2", f"u_cland_loc_{dout}_3", f"up_{dout}"]}
    resets = [("w", raws["w"], [360, 160], [f"u_cland_sin_agg_{uin}_0", f"u_cland_sin_agg_{uin}_1",
                                           f"u_cland_sin_{dout}_{uin}_0", f"u_cland_sin_{dout}_{uin}_1"]),
              ("wd", wd_raw, wd_xy, [f"u_cland_loc_{dout}_3", f"u_cland_up_{dout}", f"u_cland_fstart_{dout}"]),
              ("c", raws["c"], [720, 260], ["u_cland_origin", "u_cland_agg_1", "u_cland_agg_2",
                                            f"u_cland_loc_{dout}_1", f"u_cland_loc_{dout}_2"]),
              ("e", raws["e"], [1230, 190], [f"u_cland_sin_agg_{din}_0", f"u_cland_sin_{dout}_{din}_0", "u_cland_agg_3",
                                             "u_cland_agg_4", f"u_cland_up_{uout}", f"u_cland_fstart_{uout}"])]
    return src, pins, sin, anc, chains, resets

def st_m():
    src = {"rx_i": [1333.3, 68.5], "tx_i": [17.9, 26.5]}
    pins = {"up_rx_o": [2.144, 103.008], "up_tx_o": [1440.736, 42.976], "fstart_rx_o": [2.144, 107.36],
            "fstart_tx_o": [1440.736, 47.328], "origin": [730.592, 51.36]}
    sin = {"agg": {"tx_i": [[350, 50]], "rx_i": [[1005, 65]]}, "tx_o": {"tx_i": [[360, 38]], "rx_i": [[1015, 62]]}}
    anc = {"u_cland_agg_1": [680, 65], "u_cland_agg_2": [500, 75], "u_cland_agg_3": [320, 85], "u_cland_agg_4": [150, 95],
           "u_cland_loc_tx_o_1": [700, 55], "u_cland_loc_tx_o_2": [950, 50], "u_cland_loc_tx_o_3": [1200, 47]}
    chains = {"agg": ["u_cland_agg_1", "u_cland_agg_2", "u_cland_agg_3", "u_cland_agg_4", "up_rx_o"],
              "tx_o": ["u_cland_loc_tx_o_1", "u_cland_loc_tx_o_2", "u_cland_loc_tx_o_3", "up_tx_o"]}
    resets = [("w", ["rst_rl_6", [292.3, 51.4], 3], [300, 70], ["u_cland_sin_agg_tx_i_0", "u_cland_sin_tx_o_tx_i_0",
              "u_cland_agg_2", "u_cland_agg_3", "u_cland_agg_4", "u_cland_up_rx_o", "u_cland_fstart_rx_o"]),
              ("c", ["rst_rl_13", [721.4, 51.4], 3], [700, 60], ["u_cland_origin", "u_cland_agg_1", "u_cland_loc_tx_o_1"]),
              ("e", ["rst_rl_15", [1082.2, 51.4], 3], [1200, 50], ["u_cland_sin_agg_rx_i_0", "u_cland_sin_tx_o_rx_i_0",
              "u_cland_loc_tx_o_2", "u_cland_loc_tx_o_3", "u_cland_up_tx_o", "u_cland_fstart_tx_o"])]
    return src, pins, sin, anc, chains, resets

def turn_a():
    src = {"t_i": [17.28, 708.48]}   # band low corner; the ring top (1008.5) is checked too
    pins = {"up_t_o": [91.232, 2.656], "fstart_t_o": [95.52, 2.656], "origin": [88.288, 304.0]}
    anc = {"u_cland_agg_1": [40, 560], "u_cland_agg_2": [60, 380], "u_cland_agg_3": [80, 190]}
    chains = {"agg": ["u_cland_agg_1", "u_cland_agg_2", "u_cland_agg_3", "up_t_o"]}
    resets = [("s", ["rst_rl_1", [21.6, 276.5], 2], [60, 140], ["u_cland_agg_3", "u_cland_up_t_o", "u_cland_fstart_t_o"]),
              ("c", ["rst_rl_3", [86.6, 315.1], 2], [70, 420], ["u_cland_origin", "u_cland_agg_1", "u_cland_agg_2"])]
    return src, pins, {}, anc, chains, resets

R = {"w": ["rst_rl_29", [355.1, 95.0], 4], "c": ["rst_rl_15", [721.4, 230.6], 4], "e": ["rst_rl_23", [1209.6, 181.4], 4]}
R3 = {"w": ["rst_rl_25", [355.1, 95.0], 4], "c": ["rst_rl_14", [721.4, 230.6], 4], "e": ["rst_rl_19", [1209.6, 181.4], 4]}
types = {
    "hd_st_str": (st_like("d_i", "u_i", "d_o", "u_o", R, ["rst_rl_19", [323.6, 230.6], 4], [150, 330]), 5),
    "hd_st_n3_transit": (st_like("d2_i", "u2_i", "d2_o", "u2_o", R3, ["rst_rl_25", [355.1, 95.0], 4], [200, 260]), 5),
    "hd_st_m": (st_m(), 4),
    "hd_turn_a": (turn_a(), 3),
}
out, worst = {}, {}
for tn, ((src, pins, sin, anc, chains, resets), rdepth) in types.items():
    pos = dict(anc); hops = []
    for k, v in pins.items():
        pos["u_cland_" + k] = v
    for tgt, rings in sin.items():
        for ring, st in rings.items():
            for i, xy in enumerate(st):
                pos[f"u_cland_sin_{tgt}_{ring}_{i}"] = xy
    for tgt, ch in chains.items():
        first = ch[0]
        for ring, s in src.items():
            path = [s] + [pos[f"u_cland_sin_{tgt}_{ring}_{i}"] for i in range(len(sin.get(tgt, {}).get(ring, [])))] + [pos[first]]
            for a, b in zip(path, path[1:]):
                hops.append((f"status {ring}->{tgt}", L1(a, b)))
        seq = [pos[c if c.startswith("u_cland_") and c in pos else "u_cland_" + c] for c in ch]
        for a, b in zip(seq, seq[1:]):
            hops.append((f"status chain {tgt}", L1(a, b)))
    for name, (raw, rxy, d), xy, cons in resets:
        hops.append((f"reset {raw}->lrst_{name}", L1(rxy, xy)))
        for c in cons:
            hops.append((f"reset lrst_{name}->{c}", L1(xy, pos[c])))
    bad = [h for h in hops if h[1] > LIM]
    worst[tn] = max(hops, key=lambda h: h[1])
    cyc = {tgt: {ring: len(st) for ring, st in rings.items()} for tgt, rings in sin.items()}
    out[tn] = {"clock": {
        **({"landing_status_input_stages": {tgt: {ring: [{"xy_um": xy} for xy in st] for ring, st in rings.items()}
                                           for tgt, rings in sin.items()}} if sin else {}),
        "landing_status_anchors": anc,
        "landing_local_resets": [dict(name=n, raw=r[0], xy_um=xy, consumers=c) for n, r, xy, c in resets]},
        "_status_cycles_added": cyc, "_reset_copies": len(resets), "_copy_depth": rdepth,
        "_worst_hop_um": [worst[tn][0], round(worst[tn][1], 1)], "_hops_over_380": bad}
    print(tn, "worst", worst[tn], "over", bad, "status cycles", cyc, file=sys.stderr)
print(json.dumps(out, indent=1))
