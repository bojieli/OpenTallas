"""S81 release head die (S81.HEAD): top-down microarchitecture sizing (AGENTS.md design method step 1).

Lane S81-HEAD, 2026-10-24.  The head die holds the DeepSeek-V4.1 LM head (vocab 129,280 x 5,120 BF16, ROM-resident),
the argmax and the MTP sequencer of the S81 72-frame release array, and the host link (S81.HOST: host on head dies
only).  This module states, for every block of the die, the numbers the design method asks for: MACs / cycle, bytes /
cycle at every memory port, bits / cycle across every boundary, routing against channel capacity, replica count,
area / floorplan slot fit and the latency contribution to the single-user token.  The die plan
(physical/die_plan/s81_head/gen_plan.py) reads `model()["floorplan"]`; nothing in the plan is sized elsewhere.

Sources (all committed):
  - head bundle RTL rtl/v41rom/ot_dsrom_head_bundle.sv: 5 logical elements = 10 x ot_rom_4096x274_m8, 128 vocab rows,
    `go` at G, x slice m at G + 5 + m (m < 8192 + 7 SK); tile README physical/ref_tile/s81hd_tile_m (go -> result
    8,359 with IOREG 1 / SAFE 1; mini array spo -> 2 tiles -> spr 8,375, token 21946 exact) at CUT 0x17b; the tile is
    rebased (10-24) on the CLOSED element views' CUT 0x1ff / SPLIT9 1 (SK 11): +54 cycles (mini array 8,429, exact),
    ot_s81hd_elem == closed RTL proven by tools/s81_head/hd_elem_eq.sh.
  - OWNER 2026-10-24: 4 head dies (one TP4 group), no HBM on head dies.
  - CLOSED element views (SS sign-off): dshead-elemA-ss-f11f3cc47 (317.672 x 317.672, SS +133.67 / FF +10.81 ps) and
    dshead-elemB-ss-a318fdf47 (277.652 x 277.652, SS +91.75 / FF +19.13 ps), physical/dsrom_fh_safe/closed/elem{A,B}.
    elemB 163,817 cells (results/rtl/dsrom_fh_redesign_20261006/elemB_final/history/original_physical.json).
  - rack: docs/RELEASE_RACK.md 2.1 + results/arch/release_rack_1021/connections_s81.csv (12 head dies = H0..H2 x TP4,
    head die macros WS0/1 ES0/1 EN0/1 (TP4 mesh), WN0/1 (out: head hop / token return), WN2/3 (in: S240 or previous
    head group), HOST0/1 (host NIC)); one circuit = 2 macros, 939 Gb/s usable a direction; D = 251-258 cycles.
  - calendar results/token_pass/calendar_landing_pipeline_s81_1021/land0/calendar_rel241_G4_{ar,mtp}.json
    (AR 952.8 tok/s/user, 47,642 aggregate; MTP 2,963.4 / 17,780; head windows 10,357 cycles a position).
  - layer-die cell density: physical/die_plan/s81/cells_est.json (lep LP frames 192k-365k cells in 1442.88 x 1226.88).
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
F_HZ = 1.2e9
GRID = 8.64

# ----------------------------------------------------------------------------------------------- model constants
VOCAB, D_MODEL = 129_280, 5_120
TP = 4                                   # head ranks a group (rack: H<g> x rank 0..3)
ROWS_PER_BUNDLE = 128
BUNDLES = VOCAB // ROWS_PER_BUNDLE       # 1010
ELEMS = dict(A=4, B=1)                   # A: 32 rows x K 0..4095 (LV 8); B: 128 rows x K 4096..5119 (LV 6, PAD 2)
ROM = dict(macro="ot_rom_4096x274_m8", words=4096, bits=274, per_bundle=10, area_um2=7881.4,
           src="results/uarch/v41_rom_depth_study.json")
BUNDLE_GO_TO_RESULT = 8_359 + 54         # IOREG 1 / SAFE 1 (tile README, SAFE point 8) at CUT 0x17b; +54 at the CLOSED
                                         # element views' CUT 0x1ff / SPLIT9 1 (S81-HEAD 10-24: mini array 8,375 -> 8,429)
X_BEATS = D_MODEL * 16 // 512            # 160 beats of 512 b on the stage circuit (XB in)
ELEM_VIEW = dict(A=dict(job="dshead-elemA-ss-f11f3cc47", um=317.672, ss_ps=133.67, ff_ps=10.81,
                        cells=None, cells_basis="ASSUMED: elemB cells x area ratio (no elemA count committed)"),
                 B=dict(job="dshead-elemB-ss-a318fdf47", um=277.652, ss_ps=91.75, ff_ps=19.13, cells=163_817,
                        cells_basis="measured (elemB_final original_physical.json)"))
ELEM_VIEW["A"]["cells"] = int(round(ELEM_VIEW["B"]["cells"] * (ELEM_VIEW["A"]["um"] / ELEM_VIEW["B"]["um"]) ** 2))
TILE_GLUE_CELLS = 50_000                 # ASSUMED: BST 2 x 512 b + skew lines 14.3 kb + 2-stage x pass + chain merge
CIRCUIT_USABLE_GBPS = 939.0
HOP_D = dict(tp_mesh=251, head_hop=257, token_return=251, host=258)      # rack hop_latency (OPTION D)
CAL = dict(ar_tok_s_user=952.8, ar_tok_s=47_642, mtp_tok_s_user=2_963.4, mtp_tok_s=17_780, tau=3.649, positions=6,
           head_window=10_357, mtp_head_gaps=[23_239, 42_662, 47_832, 47_832, 47_832],
           ar_T=1_259_399.6, src="results/token_pass/calendar_landing_pipeline_s81_1021/land0/calendar_rel241_G4_*.json")
REACH_M47 = 405.0 * 0.9                  # PLAN-TOOL5 reach: M4-M7 owner local plan x reach_margin

# floorplan lattice (all multiples of 8.64)
SERDES_SLOT = (2885.76, 1226.88)         # = layer-die serdes partitions (same PHY abstract and bump field)
FRAME = (1442.88, 1226.88)               # = layer-die frame (lep LP / station partitions)
SEAL = 103.68
ELEM_SLOT = 345.6                        # 40 x 8.64: elemA 317.672 + ~19-um channel; 2 x 3 slots a tile
TURN_W = 172.8                          # 566 chain pins on the U-turn N/S faces at <= 3.5 / um
TILE_W_EXTRA = 17.28                     # 10-24 G3 floorplan review (S81-HEAD): edge strips 17.28 / 19.29 um + a
                                         # 36.6-um centre column for the elements' W-face x pins and E-face controls
                                         # (the 691.2 tile left 8.64-um slivers); paid by the spine column, not the die


def _lat(x):
    return round(x / GRID) * GRID


def tile():
    cells = ELEMS["A"] * ELEM_VIEW["A"]["cells"] + ELEMS["B"] * ELEM_VIEW["B"]["cells"] + TILE_GLUE_CELLS
    w, h = round(2 * ELEM_SLOT + TILE_W_EXTRA, 4), round(3 * ELEM_SLOT, 4)
    core_um2 = ELEMS["A"] * ELEM_VIEW["A"]["um"] ** 2 + ELEMS["B"] * ELEM_VIEW["B"]["um"] ** 2
    macs = ROWS_PER_BUNDLE * D_MODEL / 8192.0           # one 16-lane BF16 word a cycle per element
    return dict(
        content="ot_s81hd_tile = 1 bundle (4 A + 1 B elements as CLOSED hard cores) + chain glue",
        outline_um=[w, h], area_mm2=round(w * h / 1e6, 4), core_fill=round(core_um2 / (w * h), 3),
        cells=cells, cells_basis=f"4 x elemA {ELEM_VIEW['A']['cells']} ({ELEM_VIEW['A']['cells_basis']}) + elemB "
                                 f"{ELEM_VIEW['B']['cells']} + glue {TILE_GLUE_CELLS} ASSUMED",
        hard_cores="5 (each < 400k cells): the tile is over the 400k CORE-KS cap, so the elements are its cores",
        macs_per_cycle=macs, rom_bits_per_cycle=ELEMS["A"] * ROM["bits"] + ELEMS["B"] * ROM["bits"],
        x_in_bits_per_cycle=512, chain_bus_bits=565,
        chain_bus="bus B: x 512 (xa K0..4095 / xb K4096..5119) + go + xv + rv + row17 + bits32 (FP32 logit) + flt",
        go_to_result=BUNDLE_GO_TO_RESULT, x_stream_cycles=8192 + 7 * 11,
        face_pins=dict(i=565 + 1, o=565 + 1, note="+1 epoch bit; on a 345.6-um window with M4+M6 = 1.6 pins/um"))


def floorplan(tiles_needed):
    """Die geometry from the rack's link count and the tile slot (no other input)."""
    serdes_per_edge = 6
    W = serdes_per_edge * SERDES_SLOT[0] + 2 * SEAL
    inner = W - 2 * SEAL
    t = tile()
    tw, th = t["outline_um"]
    per_half = int((inner - 2 * TURN_W - 1000.0) // (2 * tw))         # keep >= 1 mm for the spine column
    spine_w = inner - 2 * (per_half * tw + TURN_W)
    per_rowpair = 2 * 2 * per_half                                     # W + E chain, out + back rows
    rowpairs = math.ceil(tiles_needed / per_rowpair)
    slots = rowpairs * per_rowpair
    H = 2 * (SEAL + SERDES_SLOT[1] + FRAME[1]) + rowpairs * 2 * th
    return dict(
        outline_um=[round(W, 4), round(H, 4)], area_mm2=round(W * H / 1e6, 1), reticle_mm2=858,
        serdes=dict(per_edge=serdes_per_edge, slot_um=list(SERDES_SLOT),
                    N=["WN2", "WN1", "WN0", "WN3", "EN0", "EN1"], S=["WS1", "WS0", "HOST0", "HOST1", "ES0", "ES1"],
                    note="same slot, PHY abstract and bump field as the S81 layer die (cross-die die_io pairing)"),
        link_row=dict(frames_per_row=int(round(inner / FRAME[0])), frame_um=list(FRAME),
                      note="one row of layer-die frames inside each SerDes row: link endpoints, ctl, ft stations"),
        tiles=dict(per_half_row=per_half, rowpairs=rowpairs, chains=2 * rowpairs, tiles_per_chain=2 * per_half,
                   slots=slots, used=tiles_needed, dark=slots - tiles_needed, tile_um=[tw, th]),
        spine=dict(width_um=round(spine_w, 4), node_um=[round(spine_w, 4), round(2 * th, 4)], levels=rowpairs,
                   note="one spine node a row-pair: x/go down, best up, W/E chain heads (upper row) and tails (lower)"),
        turn_um=[TURN_W, th])


def latency(fp):
    """Single-user head path a position (cycles), from the plan's station counts (reach 364.5 um on M4-M7)."""
    sw, sh = fp["spine"]["node_um"]
    tw = fp["tiles"]["tile_um"][0]
    node_st = math.ceil((sw / 2 + sh / 2) / REACH_M47)                # x: N face -> W/E chain head (internal)
    level_st = math.ceil(sh / REACH_M47)                             # x / best: N face -> S face (internal)
    L = fp["spine"]["levels"]
    chain = fp["tiles"]["tiles_per_chain"]
    x_fill = L * (2 + level_st) + node_st + 2 * chain // 2           # down the spine, into the farthest chain head
    ret = 2 * chain // 2 + (2 + 4) + L * (2 + level_st) + node_st          # out row + turn + back row, up the spine
    rows = dict(xb_ingress=X_BEATS + 2, x_fill_and_return=x_fill + ret, bundle=BUNDLE_GO_TO_RESULT,
                spine_merge_fire=2 * L, rank_merge=HOP_D["tp_mesh"] + 49 + 51 + 10,
                mtp_seq_token_former=6, out_hop_issue=4)   # rank_merge: actual-bit reach repair: M0S_TX49/RX51; return turn4FT+2face stages
    tot = sum(rows.values())
    return dict(rows=rows, total=tot, calendar_head_window=CAL["head_window"],
                vs_calendar=tot - CAL["head_window"],
                ar_share=round(tot / CAL["ar_T"], 5),
                note="x fill / return counts 2 edges a tile (registered faces) + the spine stations at 364.5 um")


def throughput():
    pos_ar = CAL["ar_tok_s"]
    pos_mtp = CAL["mtp_tok_s"] / CAL["tau"] * CAL["positions"]
    occ = BUNDLE_GO_TO_RESULT + X_BEATS + 300
    out = {}
    for groups in (1, 3):
        out[f"groups_{groups}"] = dict(
            ar_occupancy=round(pos_ar / groups * occ / F_HZ, 3), mtp_occupancy=round(pos_mtp / groups * occ / F_HZ, 3))
    return dict(positions_per_s=dict(ar=pos_ar, mtp=round(pos_mtp)), occupancy_cycles_a_position=occ, **out,
                single_user_positions_never_overlap=min(CAL["mtp_head_gaps"]) > occ,
                verdict="ONE TP4 group (4 dies) sustains the saturated AR and MTP head rate (<= 35% busy); the "
                        "single-user MTP positions arrive >= 23,239 cycles apart > 8,819 occupancy, so a group never "
                        "holds two positions. 12 dies (3 groups) is the 10-06 rack record: OWNER decision.")


def links():
    x_bits = D_MODEL * 16
    return dict(
        per_die_macros=12, circuits=6,
        stage_in=dict(macros="WN2+WN3", bits_a_position=x_bits, beats=X_BEATS,
                      occupancy_ar=round(CAL["ar_tok_s"] / 3 * x_bits / (CIRCUIT_USABLE_GBPS * 1e9), 5)),
        stage_out=dict(macros="WN0+WN1", payload="token (+ in-band host frames to the stage dies)"),
        tp_mesh=dict(macros="WS0/1 ES0/1 (ring) + EN0/1 (d+2)", bits_a_position=64,
                     note="rank argmax all-gather: 50 b best + tag; 64-b core-side lanes"),
        host=dict(macros="HOST0+HOST1", core_bits=276,
                  note="host plane: token out a user, prompt / config / KV ingest; stage dies get it in-band via "
                       "WN0/1 (S81.HOST). 276-b core-side lanes = 331 Gb/s a direction (MODEL; the stage circuits "
                       "carry 20-30x headroom)"),
        draft_fanout="SPEC v1 had 5 draft fan-out SerDes; the rack wires none (RELEASE_RACK 'placeholders'). Not "
                     "planned: OWNER decision (MTP draft runs on the copy-B wave, TOK.DS.RATE)")


def blocks(fp):
    t = tile()
    n = fp["tiles"]["slots"]
    return dict(
        tiles=dict(replicas=n, active=fp["tiles"]["used"], macs_per_cycle=n * t["macs_per_cycle"],
                   rom_bytes_per_cycle=n * t["rom_bits_per_cycle"] / 8, rom_macros=n * ROM["per_bundle"],
                   area_mm2=round(n * t["area_mm2"], 1),
                   fanout="none: x enters a chain head once and is forwarded tile to tile (registered); best is "
                          "merged forward; no mux/demux beyond the 3-way spine node copy"),
        spine=dict(replicas=fp["spine"]["levels"], bits_per_cycle=dict(x_down=565, best_up=565, ft_up_down=2 * 404),
                   content="spo (x/go 3-way registered forward) + spr (capture-all-then-fire argmax) per level"),
        ctl=dict(replicas=1, cells=300_000, cells_basis="ASSUMED (SPEC ctl ~1.5 x 1.5 mm; x store 80 kb SRAM)",
                 x_store_bits=D_MODEL * 16, x_store_read_bits_per_cycle=512,
                 content="x store + stream issue + spine root + final compare + rank merge + dsfd_mtp_seq + token "
                         "former + host frame mux + fault/status"),
        lep_0N=dict(content="dsdv_slice_lepw_mu.LP (the layer die's s_0N_LP: identical stage-circuit protocol)",
                    cells=365_489, cells_basis="layer die cells_est s_0N_LP (measured lep + lanes, flattened)"),
        mesh_ep=dict(replicas=3, content="2 x dsfd_coll_lane_w_safe8_ntf + 64-b static adapter",
                     cells=140_000, cells_basis="ASSUMED (layer die 2-lane lep LP 192k incl. MU land)"),
        host_ep=dict(replicas=1, content="2 x dsfd_coll_lane_w_safe8_ntf + dsdv_hostb_stage_hbc frame endpoint",
                     cells=200_000, cells_basis="ASSUMED"),
        hbm="none: the LM head is ROM-resident and argmax/MTP state is small; the rack's 4 stacks a head die (10-06 "
            "record) is not needed by this die: OWNER decision (saves 48 stacks)")


def model():
    fp = floorplan(BUNDLES // TP + (1 if BUNDLES % TP else 0))
    t = tile()
    blk = blocks(fp)
    lat = latency(fp)
    die_macs = blk["tiles"]["macs_per_cycle"]
    return dict(
        schema="opentallas.s81.head_die_model.v1", lane="S81-HEAD 2026-10-24",
        status="MODEL (top-down sizing; no P&R)",
        workload=dict(vocab=VOCAB, d_model=D_MODEL, weights="BF16 ROM", tp=TP,
                      bundles=BUNDLES, bundles_per_rank=[253, 253, 252, 252],
                      rows_per_rank=[253 * 128, 253 * 128, 252 * 128, 252 * 128]),
        tile=t, floorplan=fp, blocks=blk, links=links(), latency=lat, throughput=throughput(),
        intensity=dict(macs_per_cycle=die_macs, rom_bytes_per_cycle=blk["tiles"]["rom_bytes_per_cycle"],
                       compute_intensity_macs_per_rom_byte=round(die_macs / blk["tiles"]["rom_bytes_per_cycle"], 3),
                       comm_bits_per_mac=round((512 + 64) / die_macs, 5)),
        routing=dict(
            tile_face=dict(bits=566, tracks=int(ELEM_SLOT / 0.048 * 0.6 + ELEM_SLOT / 0.064 * 0.6), ratio=None),
            spine_ns_face=dict(bits=2 * 566 + 2 * (276 + 2 * 64 + 1) + 2 * 2,
                               tracks=int(fp["spine"]["width_um"] / 0.048 * 0.6 + fp["spine"]["width_um"] / 0.064 * 0.6)),
            note="per-face G0 numbers are recomputed by tools/die_plan/check.py on the generated plan"),
        levers=dict(
            vocab_over_12_dies=dict(saving_cycles=round(BUNDLE_GO_TO_RESULT * (1 - 4 / 12)),
                                    ar_rate_gain=round(BUNDLE_GO_TO_RESULT * (2 / 3) / CAL["ar_T"], 5),
                                    verdict="split the vocabulary over all 12 dies (1/12 each): ~5.6k cycles a "
                                            "position = 0.44% AR, below the 1% adoption rule: NOT a lever"),
            one_reticle_head=dict(note="1,010 tiles x 0.717 mm2 = 724 mm2 of tiles: one 790-mm2 frame-class die could "
                                       "hold the whole head (no TP4 mesh); recorded, not planned (rack is TP4)")),
        owner=["head-die count 12 (3 TP4 groups) vs 4 (1 group): 1 group meets AR + MTP rate (throughput row)",
               "HBM on head dies: none needed (blocks.hbm)",
               "draft fan-out SerDes: none planned (links.draft_fanout)",
               f"{fp['tiles']['dark']} dark tile slots (ten = 0) keep the chains regular; alternative: shorter last "
               "chain + empty slots (same outline)"])


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "results/uarch/s81_head_die.json"))
    a = ap.parse_args(argv)
    payload = json.dumps(model(), indent=2, allow_nan=False) + "\n"
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(payload)
    print(payload)


if __name__ == "__main__":
    sys.exit(main())
