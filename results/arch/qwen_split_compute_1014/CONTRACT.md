# Qwen3-8B TP8 split — COMPUTE die contract v1 (2026-10-14)

Owner decision 06:45 PT 10-14: Qwen is a two-die design (compute/ROM die + KV/system die). This file is the compute
die's contract of record. Generator: `OT_TP8_SPLIT=compute` mode of the tp8b generator (`tools/die_top_lint.py`,
`tools/qwen_rom_fulldie_b3r2.py`, `tools/qwen_kv_die/tp8b_v5.py`) + the spine slot table
`tools/qwen_split/compute_spine.py`. Build driver `tools/qwen_tp8/relay_data_run.py OUT --case` (relays, cuts, reset
tree, pin_align, case, ASSIGNED PIN FILES `OUT/pins/<master>.json`). Log: el1014-qwen-split-compute.log.

## 1. Outline and field
- Die 30,028.8 x 25,937.3 um = 778.9 mm2 (reticle 33 x 26 mm, 858 mm2). Wider than Codex's 718.9-mm2 packing
  candidate on purpose: the spine is 7.3 mm (was 5.2) so every spine master gets a slot sized to its measured need.
- Tile field: 48 columns x 16 rows of `qfd_tile_nk`, slot 399.6 x 1,442.88 um (Codex split candidate; the tile stream
  must fit ctl / cache / node leaves inside this slot — the die cannot grow the row pitch: 16 x 1,486.08 + S IO band =
  26 mm), column pitch 472.608 (station corridor 73 um: `qfd_cst_n/s` 52.68 x 103.66 CLOSED, one per tile row).
- Column heads `qfd_chead_w/e` (CLOSED) on the head row (mid-die, y ~13.92 mm).
- IO band on the S edge: 3 x `qfd_io_serdes`, `qfd_io_collective`, `qfd_io_xfifo`, `qfd_io_ucie` (in-package peer).

## 2. Spine slot table (x 11,364 .. 18,665 um)
- W sub-area, per band b (at the band's tile centroid): `qfd_sp_band_lanes` 777.6 x 1,131.84, `qfd_port_tiles_b`
  1,036.8 x 2,462.4, `qfd_sp_res_ser` 777.6 x 518.4, `qfd_port_tiles_b_f1` 1,036.8 x 2,462.4 (2.553 mm2 each >=
  the measured 2.536 need, blockers G7).
- E sub-area, N -> S: die link (UCIe x64 PHY `ot_qkvd_ucie_x64_phy` 777.6 x 777.6 on the N edge, `qfd_d2d_rom`
  777.6 x 518.4 below it, `qfd_ckbump` + `qfd_rstsync` W of the PHY); `qfd_sp_su64_sfu` 3,240 x 3,672 with the
  constant group E of it (8 `qfd_crom_g`, 8 `qfd_su_cbuf_g`, `qfd_seq_su`); the TRIMMED central VM
  `qfd_sp_vector_memory` 4,708.8 x 2,203.2, M7 cap, NO M8/M9 wall (owner 08:20: distributed x slices); `qfd_tt_ctlm`
  777.6 x 1,814.4 + `qfd_tt_up4` 345.6 x 388.8; `qfd_clkrx` + `qfd_rstseq` at the die centre.
- Relay channels 86.4 um between spine slots; spine edge channels 86.4 um.

## 3. Distributed x slices (owner 08:20 PT 10-14, builder el1014-qwen-dvm-build.log)
- Per tile column, two slice slots in the station corridor beside the column head: N of the head (between head and
  the first `qfd_cst_n`) and S of it (between head and the first `qfd_cst_s`): 64.8 x 604.8 um each
  (0.078 mm2 per column >= 0.043 BF16; FP32 0.085 needs the builder's outline: request a taller slot if FP32).
- Fill bus: head-row broadcast in a reserved die M8 band of 240 um centred on the head row, the whole die width.
- The x-line functional gap of the merged die (one line per root) is closed by this design (each slice holds its
  column's lines); the exact array-equivalence bench belongs to the DVM builder.

## 4. Die-to-die link (boundary with the KV/system die, el1014-qwen-split-kvsys.log)
- KV/system die owns the PLL; core clock + reset forwarded over the D2D bump pair (compute: `qfd_ckbump` ->
  `qfd_clkrx`; `qfd_rstsync` -> `rst_fwd_s` -> `qfd_rstseq`). One frequency both dies.
- Compute link end `qfd_d2d_rom` = `ot_qkvd_rom_end` (native ABI): x3 {512 + tag 11} + v / cr (Q FP32 32 words +
  KVN 4 words per layer; receiver credits 40), ea {kind, addr 24} (RQD 32), dc CTL 528 b -> KV;
  ar RES 519 b (OCR_AR 64), eq embedding 512 b posted, dh HCTL 528 b <- KV. FDI 548 b each way.

## 5. Rules every hop / pin / slot obeys
- Every inter-tile signal: register at the pin -> <= 500 um pin-to-pin -> register at the pin; relays are die-placed
  tiles in channels. Clock at each pin at phi - R; R <= 300 ps one level, R <= ~650 ps earlier trunk tap (SKEW 150).
- Cuts <= 0.55 (design) / 0.60 (gate), including the 2-D window scan.
- Top-down pins: the die generator assigns the pins of every unclosed master (`OUT/pins/<master>.json`, schema
  opentallas.qwen-tp8.assigned-pins.v1); closed views keep their pins (re-pin only under die_window).
- NO STUBS (owner 08:05): every die instance binds to real RTL under its die name, every net on a real port of the
  right width (`tools/qwen_split/die_port_bind.py`). Masters without RTL are release blockers (table in the log).
