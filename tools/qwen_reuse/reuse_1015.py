#!/usr/bin/env python3
"""Q-REUSE 2026-10-15: Qwen3-8B TP8 split -- unit busy fractions, unit areas, reuse options and compute-die sizing.

Writes results/arch/qwen_reuse_1015/reuse.json.  Every number carries a grade:
  measured  = RTL bench / closed view / committed receipt (path given)
  derived   = arithmetic on the shipped programme shape (word counts, element counts)
  model     = composition / floorplan estimate (formula given)
No new RTL or physical run is made here.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/arch/qwen_reuse_1015/reuse.json"
CLK = 1.2e9

def tok_s(c): return round(CLK / c, 1)
def loss(base, new): return round(100 * (1 - base / new), 3)

# ---------------- bases (cycles / token, AR batch 1, P8191) ----------------
LEDGER = 249431.0     # token_path_20261009/qwen_rom.json = accepted_cost.py qwen_rom composition
A_CENTRAL = 214074.0  # qwen_tp8_1012/tp8.json throughput.A_central (TP8 ROM + KV die, the split)
B4_CENTRAL = 205496.0  # tp8.json B4_central = 5,839.5 tok/s (owner's quoted target)
MEAS_ATTN = 377087.0  # ledger ATTN.NATIVE row: ledger basis with attention at measured 5,362

# ---------------- programme shape (SPEC sec.1, TP8 G=3072, 768 tiles x 64 MAC lanes) ----------------
WORDS = dict(qkv=64, o_proj=48, gate_up=256, down=144)   # stream words / layer / die
LANE_UTIL = dict(qkv=1.0, o_proj=0.889, gate_up=1.0, down=0.889)
HEAD_WORDS, HEAD_UTIL, LAYERS = 1600, 0.989, 36
STREAM = LAYERS * sum(WORDS.values()) + HEAD_WORDS       # 20,032 cycles / token
EFF = LAYERS * sum(WORDS[k] * LANE_UTIL[k] for k in WORDS) + HEAD_WORDS * HEAD_UTIL
ME_WINDOWS_MEASURED = dict(qkv=294, o_proj=278, gate_up=486, down=374)  # go -> last capture, decision.json (actual spctl RTL)
ME_WIN = LAYERS * sum(ME_WINDOWS_MEASURED.values())

# SU (spine) windows per layer from the token path (apportioned from measured RT_OPTRACE), TP8 qknorm x0.5
SU_WIN_LAYER = 15 + 50.5 + 2 + 91 + 246
# SU element-ops / layer (derived): rmsnorm x2 (sumsq + scale on 4096), q/k norm+rope (5 heads x128 x3),
# 2 residual adds (4096), SiLU*up (1536 x2)
SU_ELEM_LAYER = 2 * 2 * 4096 + 5 * 128 * 3 + 2 * 4096 + 2 * 1536
SU_ELEM_PER_CYCLE = 128   # SPEC unit budget: 4,096 FP32 in 32 cycles
SFU_EXP_LAYER = 1536 / 64  # SiLU sigmoid exp over 64 exp units
SFU_RSQ_LAYER = 7          # rmsnorm1 + 4 q heads + 1 k head + rmsnorm2 (scalars)
VMWB_BURSTS_LAYER = 8 + 24 + 8 + 24   # actual captures PC1/12/16/20 (decision.json)
VMWB_CYC_PER_BURST = 8                # 3 parallel band lanes (VMWB successor, accepted 18:50)
AR_WIN_LAYER = 1121 + 979             # measured TP4 collective windows (TP8 central = TP4)
SERDES_PAYLOAD_AR = 8192 / 125.0      # 8 KiB / (150 GB/s / 1.2 GHz)
UCIE_PEER_AR = (16384 + 8192) / 128.0
D2D_FLITS_LAYER = 40
ATTN_PRICE, ATTN_MEAS = 1816.0, 5362.0
QK_END_AGE = 409 - 117                # receipt: LMAX-1 mutant faults at 408 -> LMAX 409 = last QK consume + 117
PV_PAIR_OUT = 590 + 8192 / 2

def busy():
    b = LEDGER
    rows = [
      dict(unit="qfd_tile_nk MAC lanes (768 x 64 = 49,152)", busy_cycles=STREAM, frac_ledger=STREAM / b,
           frac_A_central=STREAM / A_CENTRAL, lane_occupancy=EFF / b, grade="derived",
           basis="every weight read once/token: 36x512 + 1,600 stream words (SPEC sec.1); measured ME windows (actual spctl RTL, "
                 "res_train_decision_1015/decision.json) go->last capture %s = %d cycles/layer, MAC active %d of them (%.0f%%)"
                 % (ME_WINDOWS_MEASURED, sum(ME_WINDOWS_MEASURED.values()), sum(WORDS.values()),
                    100 * sum(WORDS.values()) / sum(ME_WINDOWS_MEASURED.values()))),
      dict(unit="ROM read (per tile: 2 of 10 macros a stream cycle)", busy_cycles=STREAM, frac_ledger=STREAM / b,
           per_macro=STREAM * 2 / 10 / b, grade="derived", basis="1 code word (2 x 266-b reads) / tile / stream cycle"),
      dict(unit="matvec windows (tiles+tree+band+tt, go->last capture)", busy_cycles=ME_WIN + HEAD_WORDS, frac_ledger=(ME_WIN + HEAD_WORDS) / b,
           grade="measured windows + derived head", basis="decision.json per-op windows x36 + head stream"),
      dict(unit="spine SU lanes (qfd_sp_su64_sfu) windows", busy_cycles=LAYERS * SU_WIN_LAYER, frac_ledger=LAYERS * SU_WIN_LAYER / b,
           lane_active=LAYERS * SU_ELEM_LAYER / SU_ELEM_PER_CYCLE / b, grade="model (windows) / derived (lane-active)",
           basis="token-path SU windows (apportioned from measured RT_OPTRACE; qknorm x0.5 at TP8); lane-active = %d elem-ops/layer / 128 per cycle" % SU_ELEM_LAYER),
      dict(unit="SFU exp / rcp (64 each)", busy_cycles=LAYERS * SFU_EXP_LAYER, frac_ledger=LAYERS * SFU_EXP_LAYER / b, grade="derived",
           basis="SiLU on 1,536 gate rows/die/layer over 64 units (softmax exp is on the KV die)"),
      dict(unit="SFU rsqrt (64)", busy_cycles=LAYERS * SFU_RSQ_LAYER, frac_ledger=LAYERS * SFU_RSQ_LAYER / b, grade="derived",
           basis="7 scalar rsqrt / layer on 1 of 64 units"),
      dict(unit="VM write face (result landing, 3 band lanes)", busy_cycles=LAYERS * VMWB_BURSTS_LAYER * VMWB_CYC_PER_BURST,
           frac_ledger=LAYERS * VMWB_BURSTS_LAYER * VMWB_CYC_PER_BURST / b, grade="measured captures + model slots",
           basis="64 bursts/layer (actual PC1/12/16/20 captures) x 8 cycles (VMWB successor); VM read side ~= SU windows"),
      dict(unit="VM total (SU windows + write face)", busy_cycles=LAYERS * (SU_WIN_LAYER + VMWB_BURSTS_LAYER * VMWB_CYC_PER_BURST),
           frac_ledger=LAYERS * (SU_WIN_LAYER + VMWB_BURSTS_LAYER * VMWB_CYC_PER_BURST) / b, grade="model"),
      dict(unit="result serializers qfd_res_train (3, one per band)", busy_cycles=LAYERS * VMWB_BURSTS_LAYER * VMWB_CYC_PER_BURST,
           frac_ledger=LAYERS * VMWB_BURSTS_LAYER * VMWB_CYC_PER_BURST / b, grade="measured captures + model", basis="each band lane busy 8 slots/burst"),
      dict(unit="collective (window: 2 all-reduces/layer)", busy_cycles=LAYERS * AR_WIN_LAYER, frac_ledger=LAYERS * AR_WIN_LAYER / b,
           grade="measured (TP4 path; TP8 central = TP4)", basis="latency-bound: payload occupancy below"),
      dict(unit="board SerDes x3 payload", busy_cycles=LAYERS * 2 * SERDES_PAYLOAD_AR, frac_ledger=LAYERS * 2 * SERDES_PAYLOAD_AR / b,
           grade="derived", basis="8 KiB / all-reduce / link at ~125 B/cycle"),
      dict(unit="UCIe in-package peer payload", busy_cycles=LAYERS * 2 * UCIE_PEER_AR, frac_ledger=LAYERS * 2 * UCIE_PEER_AR / b,
           grade="derived", basis="16+8 KiB / all-reduce at 128 B/cycle"),
      dict(unit="D2D compute<->KV link (UCIe x64, 548-b flit)", busy_cycles=LAYERS * D2D_FLITS_LAYER + 130,
           frac_ledger=(LAYERS * D2D_FLITS_LAYER + 130) / b, grade="derived (LINK.md)", basis="~40 flits each way/layer + 130 EMB flits/token"),
      dict(unit="KV-die attention service (price)", busy_cycles=LAYERS * ATTN_PRICE, frac_ledger=LAYERS * ATTN_PRICE / b, grade="priced"),
      dict(unit="KV-die attention service (measured T=8192)", busy_cycles=LAYERS * ATTN_MEAS, frac_of_measured_token=LAYERS * ATTN_MEAS / MEAS_ATTN,
           grade="measured (qwen_attention_native_calendar_1015/receipt.json)"),
      dict(unit="  inside it: 128 QK row engines (qkd_rhead nativehead_r4)", busy_cycles_per_layer=QK_END_AGE - 34,
           frac_of_service=(QK_END_AGE - 34) / ATTN_MEAS, grade="measured law", basis="QK issue age 34 .. last QK consume ~292 (LMAX 409 - 117)"),
      dict(unit="  inside it: 2 PV pairs (64 pv256 slices, 1 V row/cycle each)", busy_cycles_per_layer=PV_PAIR_OUT,
           frac_of_service=PV_PAIR_OUT / ATTN_MEAS, grade="measured law", basis="pair out = 590 + T/2"),
    ]
    for r in rows:
        for k in list(r):
            if isinstance(r[k], float): r[k] = round(r[k], 4)
    return rows

def other_points():
    # modelled only: no TP8 batch / DFlash composition exists
    b2 = LEDGER + STREAM + LAYERS * ATTN_PRICE
    df5_verify = 5 * STREAM
    return dict(
      batch2=dict(grade="model", step_cycles=b2, per_user_tok_s=tok_s(b2), aggregate_tok_s=round(2 * CLK / b2, 1),
                  mac_busy=round(2 * STREAM / b2, 4), attention_busy=round(2 * LAYERS * ATTN_PRICE / b2, 4),
                  formula="ledger + 1 extra weight stream (1 MAC/lane/cycle) + second user's attention serial on the KV die"),
      dflash_block5=dict(grade="model", mac_busy_cycles_verify=df5_verify,
                  note="verify of 5 tokens reuses each weight 5x: 100,160 MAC-cycles/step, so MAC lanes become the step's largest "
                       "unit; every lane cut multiplies its stream penalty by the block size (no TP8 DFlash composition exists)"))

AREAS = dict(
  tile_slot_um2=449.28 * 1442.88, tile_count=768, rom_macro_um2=7663.95, rom_macros_per_tile=10,
  lsl_um2=9071.2, lsl_per_tile=8, rpair_logic_um2=2870, rpair_per_tile=5, node_um2=9423.5,
  su_slot_mm2=11.897, su_leaves_mm2=2.64, sfu_exp=9683, sfu_rcp=7190, sfu_rsq=9736,
  vm_slot_mm2=10.374, vm_leaves_mm2=2.37, res_ser_slot_mm2=3 * 0.403, res_train_ff_mm2=0.1,
  collective_slot_mm2=5.4, serdes_slot_mm2=12.0, ucie_io_slot_mm2=10.0, port_tiles_mm2=15.32, band_lanes_mm2=2.99,
  kv_die_mm2=265.5, rhead_slot_um2=1079.976 * 492.456, rhead_count=128, rhead_cells_um2=173440,
  ectl_um2=36925, ectl_count=32, ahub_um2=127440, pv_slice_um2=10103, pv_slices_service=64,
  src=dict(tile="CONTRACT.md + closed children rpair/lsl_fp1/node (physical/ref_tile/*/views/*_tt.lib); no closed tile parent",
           su="system_geometry/actual_su_coverage.json + closed su leaves", vm="vm_region_nx_spec_claude.json",
           kv="kvsys_v1_4_2/plan.json + closed KV leaves", census="system_geometry/inputs/current_geometry.json (C17)"))

def area_table():
    a = AREAS; t = a["tile_count"]
    die = 840.7
    rows = [
      ("qfd_tile_nk slots (768)", a["tile_slot_um2"] * t / 1e6, "slot"),
      ("  ROM macros (7,680)", a["rom_macro_um2"] * 10 * t / 1e6, "LEF"),
      ("  MAC lanes: 8 lsl_fp1 / tile", a["lsl_um2"] * 8 * t / 1e6, "closed view"),
      ("  rpair logic + node", (a["rpair_logic_um2"] * 5 + a["node_um2"]) * t / 1e6, "closed views"),
      ("  children fill of tile slot", None, "%.1f %%" % (100 * (a["rom_macro_um2"] * 10 + a["lsl_um2"] * 8 + a["rpair_logic_um2"] * 5 + a["node_um2"]) / a["tile_slot_um2"])),
      ("qfd_sp_su64_sfu slot (leaves 2.64)", a["su_slot_mm2"], "slot"),
      ("  SFUs exp+rcp+rsq x64", 64 * (a["sfu_exp"] + a["sfu_rcp"] + a["sfu_rsq"]) / 1e6, "closed views"),
      ("qfd_sp_vector_memory slot (leaves 2.37)", a["vm_slot_mm2"], "slot"),
      ("qfd_sp_res_ser x3 slots", a["res_ser_slot_mm2"], "slot"),
      ("port_tiles x6 + band_lanes x3", a["port_tiles_mm2"] + a["band_lanes_mm2"], "slot"),
      ("collective + xfifo", a["collective_slot_mm2"] + 1.095, "slot"),
      ("SerDes x3", a["serdes_slot_mm2"], "slot"),
      ("UCIe in-package IO", a["ucie_io_slot_mm2"], "slot"),
    ]
    out = []
    for n, mm2, g in rows:
        out.append(dict(unit=n, mm2=None if mm2 is None else round(mm2, 2),
                        pct_die=None if mm2 is None else round(100 * mm2 / die, 2), grade=g))
    kv = [
      ("qkd_rhead x128 slots", a["rhead_slot_um2"] * 128 / 1e6, "slot"),
      ("  rhead cells", a["rhead_cells_um2"] * 128 / 1e6, "closed leaves"),
      ("qkd_ectl x32", a["ectl_um2"] * 32 / 1e6, "closed views"),
      ("qkd_ahub", a["ahub_um2"] / 1e6, "closed leaves"),
      ("PV slices in the native service (2 pairs x 32)", a["pv_slice_um2"] * 64 / 1e6, "closed leaf"),
    ]
    for n, mm2, g in kv:
        out.append(dict(unit="KV die: " + n, mm2=round(mm2, 2), pct_kv_die=round(100 * mm2 / a["kv_die_mm2"], 2), grade=g))
    return out

# ---------------- compute-die sizing (owner 19:50: S81 treatment) ----------------
DIE_W, DIE_H = 32413.392, 25937.28
TILE_W, TILE_H, ROW_PITCH = 449.28, 1442.88, 1486.08
LSL_ROW = 140.4 + 20.0            # one lsl row + its 20-um channel (tile vertical stack: 5 rpair rows + 4 lsl rows)
PINREG = 2 * (LAYERS * 4 + 1)     # +2 cycles per matvec op (ROM read buffer / pin-register stage at the re-cut lsl band)
KV_DIE = 265.5

def point(name, macs, row_gap, note):
    lsl = macs // 8
    rows_lsl = lsl // 2
    th = TILE_H - (4 - rows_lsl) * LSL_ROW
    pitch = th + row_gap
    dh = DIE_H - 16 * (ROW_PITCH - pitch)
    die = DIE_W * dh / 1e6
    stream = LAYERS * sum(WORDS.values()) * 64 / macs + HEAD_WORDS * 64 / macs
    add = stream - STREAM + (PINREG if macs != 64 else 0)
    cyc_b4 = B4_CENTRAL + add
    cyc_a = A_CENTRAL + add
    children = 10 * AREAS["rom_macro_um2"] + lsl * AREAS["lsl_um2"] + 5 * AREAS["rpair_logic_um2"] + AREAS["node_um2"]
    return dict(point=name, tp=8, macs_per_tile=macs, lsl_per_tile=lsl, rom_read_macros_per_cycle=macs / 32,
                tile_um=[TILE_W, round(th, 2)], tile_mm2=round(TILE_W * th / 1e6, 4),
                tile_children_fill_pct=round(100 * children / (TILE_W * th), 1),
                row_gap_um=row_gap, column_corridor_um=73.008, die_um=[DIE_W, round(dh, 1)], die_mm2=round(die, 1),
                fits_reticle=dh <= 26000 and DIE_W <= 33000, tile_field_share_pct=round(100 * 768 * TILE_W * th / 1e6 / die, 1),
                compute_dies=8, kv_dies=8, total_silicon_mm2=round(8 * die + 8 * KV_DIE, 0),
                stream_cycles_token=round(stream), added_cycles_token=round(add, 0),
                tok_s_vs_B4_central=tok_s(cyc_b4), tok_s_vs_A_central=tok_s(cyc_a),
                ledger_loss_pct=loss(LEDGER, LEDGER + add), note=note, grade="model (floorplan screen + derived stream)")

def sizing():
    pts = [
      point("minimal", 32, 86.4, "4 lsl (2x2) per tile, 1 macro read/cycle; stream x2; over the 5 %/unit ledger limit -> owner exception only"),
      point("recommended", 48, 86.4, "6 lsl (2 cols x 3 rows), 3 macros per 2 cycles (ROM image re-laid by the compiler); row gap doubled 43.2 -> 86.4"),
      point("generous", 48, 172.8, "as recommended, row gap 172.8 (4x today) for relays/tree pads; still under the reticle"),
      point("today", 64, 43.2, "C22 contract: 8 lsl, row gap 43.2 (cannot grow: die height 25.94 of 26.0 mm)"),
    ]
    tp = []
    for n in (10, 12):
        tiles = 768 * 8 / n
        tp.append(dict(point="TP%d (64 MAC/tile)" % n, tp=n, tiles_per_die=round(tiles), grade="model",
                       die_mm2_estimate=round(840.7 - (768 - tiles) * 0.648 * 1.08, 0),
                       compute_dies=n, problems=["32 Q / 8 KV heads do not divide by %d: KV heads replicate or ranks go uneven (KV capacity and HBM traffic grow)" % n,
                                                 "all-reduce over %d ranks: no K4/two-level fold; board topology and collective RTL change" % n,
                                                 "per-die stream words stay 512/layer (G scales with tiles), so tok/s does NOT improve; it pays only for area"],
                       total_silicon_mm2=round(n * (840.7 - (768 - tiles) * 0.648 * 1.08) + n * KV_DIE, 0)))
    return pts, tp

def options():
    led = LEDGER
    o = []
    def add(rank, name, saved_mm2, where, added_cycles, risk, verdict, detail, grade):
        o.append(dict(rank=rank, option=name, area_saved_mm2=saved_mm2, die=where,
                      pct_of_die=round(100 * saved_mm2 / (840.7 if where == "compute" else KV_DIE), 2) if saved_mm2 is not None else None,
                      added_cycles_token=added_cycles,
                      ledger_loss_pct=None if added_cycles is None else loss(led, led + added_cycles),
                      risk=risk, verdict=verdict, detail=detail, grade=grade))
    rec = point("recommended", 48, 43.2, "")
    mn = point("minimal", 32, 43.2, "")
    add(1, "R1 PV on the 128 QK row engines (HBM-SM style): V rows on the K return ports into a 2-SRAM V buffer per rhead, "
           "64-long p.v dot products on the rhead's own multipliers + ktree, partials reduced over the AHUB trees; remove the 2 PV pairs, "
           "vrow and the 4 V ports", -(1.28 - 0.65), "kv", None,
        "medium: rhead operand muxes + V buffer (re-close 128 rheads), PV summation order becomes tree order (golden must adopt it, like the collective fold), p rounded to the q operand format",
        "RECOMMENDED -> Q-ATTN-RATE", "est. service ~860 cycles at T=8192 (QK 292 + LMAX/EXP 132 + 64 dot + ~320 reduce/finalize) vs 5,362 measured: "
        "removes the 33.85 %% proposed ATTN.NATIVE loss (service+link ~1,315 <= 1,816 price). Net cells +0.6 mm2 (+1.28 V buffers/muxes, -0.65 PV slices) "
        "vs +1.9..4.5 mm2 for 4-8x dedicated PV pairs that still miss price (590 fixed + T/8 = 1,614 PV alone).", "model")
    add(2, "R2 compute die 48 MAC/tile (6 lsl, 3 ROM macros per 2 cycles)", round(840.7 - rec["die_mm2"], 1), "compute",
        rec["added_cycles_token"], "medium-high: tile ctl/issue-loop K-split, ROM image re-layout (compiler), lsl band re-cut; tile parent is unclosed so now is the cheapest time",
        "RECOMMENDED sizing", "die height -2.57 mm (one lsl row per tile row); +6,677 stream +290 pin-register cycles/token", "model")
    add(3, "R1b 64 QK row engines (each serves 2 PCs) after R1", round(64 * AREAS["rhead_slot_um2"] / 1e6, 1), "kv", LAYERS * 0,
        "medium: ECTL/PC->rhead map, KV-die floorplan", "CONDITIONAL on R1 measured",
        "QK + V stream 2x (+256 +64 cycles/layer) -> est. ~1,180 + link ~1,635 <= 1,816 price, so 0 ledger loss if R1 lands at its estimate; "
        "cells -11.1 mm2", "model")
    add(4, "R2-min compute die 32 MAC/tile", round(840.7 - mn["die_mm2"], 1), "compute", mn["added_cycles_token"],
        "high", "REJECT unless owner exception (over 5 %/unit)", "stream x2 = +20,032 cycles/token", "model")
    add(5, "SU: share rsqrt 64 -> 4 and exp/rcp 64 -> 32", round((60 * 9736 + 32 * 16873) / 1e6, 2), "compute", LAYERS * (4 + 24),
        "low", "OPTIONAL (cells only; SU slot is 22 %% filled so the die does not shrink)", "rsq busy 0.1 %%, exp/rcp 0.35 %%", "derived")
    add(6, "Attention QK/PV on the compute-die matrix tiles (PC11 VM-sourced-weight mode)", None, "compute", LAYERS * (2 * 1048576 / 64 - ATTN_PRICE),
        "n/a", "REJECT", "K+V 2 MiB/layer would cross the 64 B/cycle D2D link: 32,768 cycles/layer. The HBM design gains because its SMs sit beside HBM; "
        "Qwen's tiles are a die away from the KV.", "derived")
    add(7, "Softmax/reduce on the compute-die SU (merge with ASTK/AHUB)", None, "kv", LAYERS * 2 * (4 * 8192 * 4 / 64),
        "n/a", "REJECT", "scores 128 KiB/layer out + probabilities back over the link = ~4,096 cycles/layer", "derived")
    add(8, "One shared result serializer for 3 bands", round(2 * 0.403, 2), "compute", LAYERS * (1445 - 148), "low",
        "REJECT", "measured: single static face +1,445 vs 148 cycles/layer", "measured")
    add(9, "Fewer SerDes (relay one package)", 4.0, "compute", LAYERS * 2 * 339, "medium", "REJECT", "measured board LAT 339 per relayed all-reduce", "measured")
    add(10, "Collective folds on idle SU lanes", 0.06, "compute", None, "medium", "REJECT (negligible)", "8 fold slices = 0.06 mm2", "closed view")
    o[0]["vs_measured_attention"] = dict(service_cycles_T8192_est=860, measured=ATTN_MEAS, saved_cycles_token=LAYERS * (ATTN_MEAS - 860),
        token_cycles=MEAS_ATTN - LAYERS * (ATTN_MEAS - 860), recovers_proposed_loss_pct=33.853,
        area_note="negative area_saved = net cell ADD (+0.63 mm2 KV die), but avoids +1.9..4.5 mm2 of extra PV pairs")
    return o

def main():
    pts, tp = sizing()
    doc = dict(schema="opentallas.qwen-reuse.v1", date="2026-10-15", owner="Q-REUSE (Claude)", tool="tools/qwen_reuse/reuse_1015.py",
               bases=dict(ledger_qwen_rom=LEDGER, ledger_tok_s=tok_s(LEDGER), tp8_A_central=A_CENTRAL, tp8_B4_central=B4_CENTRAL,
                          b4_tok_s=tok_s(B4_CENTRAL), measured_attention_token=MEAS_ATTN),
               stream_words_token=STREAM, busy_ar_batch1_T8192=busy(), other_points=other_points(), areas=area_table(),
               sizing_points=pts, more_dies_alternative=tp, options=options(),
               verdict=("Tiles are oversized for the rate target (MAC lanes 8 % busy; latency-bound token), so the owner's "
                        "fewer-multipliers branch applies, not TP10/TP12. Recommended: 48 MAC/tile at TP8 plus R1 on the KV die."),
               inputs=["results/arch/token_path_20261009/qwen_rom.json", "results/arch/qwen_tp8_1012/tp8.json", "results/arch/qwen_tp8_1012/SPEC.md",
                       "results/arch/qwen_split_compute_1014/res_train_decision_1015/decision.json",
                       "results/arch/qwen_attention_native_calendar_1015/receipt.json", "results/arch/accepted_cost_ledger_1013.json",
                       "results/arch/qwen_split_1014/LINK.md", "results/arch/qwen_split_compute_1014/CONTRACT.md"])
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps(dict(sizing=pts, tp=tp), indent=1))
    for r in doc["options"]: print(r["rank"], r["option"][:60], r["area_saved_mm2"], r["added_cycles_token"], r["ledger_loss_pct"])
    for r in doc["busy_ar_batch1_T8192"]: print(r["unit"][:60], r.get("frac_ledger"), r.get("frac_of_service"), r.get("lane_active"))

if __name__ == "__main__":
    main()
