# Qwen3-8B TP8 split — COMPUTE die contract v1.1 (2026-10-14 17:30 PT)

Owner decision 06:45 PT 10-14: Qwen is a two-die design (compute/ROM die + KV/system die). This file is the compute
die's contract of record. Generator: `OT_TP8_SPLIT=compute` mode of the tp8b generator (`tools/die_top_lint.py`,
`tools/qwen_rom_fulldie_b3r2.py`, `tools/qwen_kv_die/tp8b_v5.py`) + the spine slot table
`tools/qwen_split/compute_spine.py`. Build driver `tools/qwen_tp8/relay_data_run.py OUT --case` (relays, cuts, reset
tree, pin_align, case, ASSIGNED PIN FILES `OUT/pins/<master>.json`). Log: el1014-qwen-split-compute.log (the ordered
element queue is at its top). v1 (07:27) is superseded by this revision.

| rev | source | what changed |
|---|---|---|
| v1 (C1/C2) | 8627bb585 | outline, spine slot table, trimmed VM, link at the N edge |
| C4..C8 | 6b806fa67 .. e037bd396 | pin-to-pin relay reach (<= 490 um), E-edge band slabs, tile slot 449.28 / pitch 522.288, distributed x slices in the die, per-child clock entries, reference tile ids, 514-b tree words, reach gate + reset tree ON |
| C9 | d986175e0 | link PHY + adapter mirrored (MX): FDI abutted, adapter word faces toward the SU; trimmed-VM `ar` on its N face E end |
| C10 | 53e6df819 + | link words at the real RTL widths + credits; die-name RTL of the link / clock / reset entry; port-bind gate runner |

## 1. Outline and field
- Die 32,413 x 25,937 um = 840.7 mm2 (reticle 33 x 26 mm, 858 mm2; width spare 587 um, height spare 63 um: there is
  no room to widen corridors or add a row band).
- Tile field: 48 columns x 16 rows of `qfd_tile_nk` (RTL `rtl/physical/qfd_tile_nk_slot.sv`), slot **449.28 x 1,442.88**
  (q-tile option (a), 11:42), column pitch 522.288 (corridor 73.008), row pitch 1,486.08. Straps: `tile_id` =
  16 x block + morton(c mod 4, r mod 4) (the reference `ot_qwen_me_array_w12` index; the die tree pairs in Morton order).
- IO band on the S edge: 3 x `qfd_io_serdes`, `qfd_io_collective`, `qfd_io_xfifo`, `qfd_io_ucie` (in-package peer).

## 2. Spine slot table (7.3 mm wide)
- W sub-area, per band b at the band's tile centroid, centred on the port column: `qfd_sp_band_lanes` 777.6 x 1,131.84,
  `qfd_port_tiles_b` 1,036.8 x 2,462.4, `qfd_sp_res_ser` 777.6 x 518.4. E edge: `qfd_port_tiles_b_f1` 1,036.8 x 2,462.4
  at the band centroid (E-field block words land without crossing the spine; one 512-b pfrag word per band crosses).
- E sub-area, N -> S: die link (UCIe x64 PHY `ot_qkvd_ucie_x64_phy` 777.6 x 777.6 on the N edge, **MX**; `qfd_d2d_rom`
  777.6 x 518.4 below it, **MX**, FDI faces abutted across 4.32 um; `qfd_ckbump` + `qfd_rstsync` W of the PHY);
  `qfd_sp_su64_sfu` 3,240 x 3,672 with the constant group E of it (8 `qfd_crom_g`, 8 `qfd_su_cbuf_g`, `qfd_seq_su`) and
  the x tap `qfd_xs_tap` 345.6 x 345.6 E of that at the VM N face; the TRIMMED central VM `qfd_sp_vector_memory`
  4,708.8 x 2,203.2, M7 cap, no M8/M9 wall, SU S face abutted to VM N face (registered seam); `qfd_tt_ctlm`
  777.6 x 1,814.4 + `qfd_tt_up4` 345.6 x 388.8 (5 clock entries ck_pin, ck_l0..3); `qfd_clkrx` + `qfd_rstseq` at the
  die centre.
- Relay channels 86.4 um between spine slots; spine edge channels 108 um.

## 3. Distributed x slices (owner 08:20 PT; builder el1014-qwen-dvm-build.log)
- `qfd_xcol_e` / `qfd_xcol_w` (48): ONE cluster slot **64.8 x 1,313.28** in the column corridor centred on the head row
  (the head segment between station 7 and station 8 is 1,382 um; the corridor carries 3 corridor relays per row segment
  plus E-W tree / block-word crossings, so the slot cannot grow along the corridor without absorbing stations). Inside:
  M2-M7; the die owns M8/M9 over it. Clock entries scalar ck0..ck<n> (head + leaves), straps `tids` (16 x 16-b ids).
  **Decision 16:45:** the slot stays; the slice is re-shaped to it (cluster area <= ~70,000 um2, no 1,130-b hard-child
  face inside the 64.8-um width unless pin fit <= 0.55 on M3/M5/M7; preferred: SRAM storage or a flat dense cluster with
  measured CTS). Fallback B (die change, on request only): xcol 64.8 x ~3,900 absorbing stations 7/8.
- `qfd_xcst_n/s` (768): the station slot 52.68 x 103.66, corridor word 516 b {go, ib 379, xl 128, tag 8} + ready.
- `qfd_xs_tap` (1): 345.6 x 345.6 at the VM N face; inputs sw 2,137 b (SU lane write), aw 553 b (VM attention write),
  xpf 74 b (tt_ctlm), gi 380 b (tree top go / ib); outputs two registered head words hw / he 1,567 b.

## 4. Die-to-die link (boundary with the KV/system die: LINK.md, el1014-qwen-split-kvsys.log)
- KV/system die owns the PLL; core clock + reset forwarded over the D2D bump pair (`qfd_ckbump` model -> `qfd_clkrx`;
  `qfd_rstsync` -> `qfd_rstseq`, which holds every domain FLUSH edges and releases io -> field -> spine -> tree top ->
  sequencer). One frequency both dies.
- `qfd_d2d_rom` = `ot_qfd_split_romlink` (ROM end + level-face codec) + `ot_qkvd_d2d_llr` (CRC-16 / go-back-N),
  RTL `rtl/qwen_split/qfd_link_slots.sv`; verified inside the kvsys full link bench (`rtl/test/qwen_split/run_d2d_rom_link.sh`:
  PASS, ERRP 501 PASS, crossed-tag mutant FAIL 649).
- Die words (bundles LSB first in this order): `x3` 524 = {x3_d 512, x3_tag 11, x3_v} SU `q` -> adapter, credit `x3_cr`
  adapter -> SU `q_cr`; `attn_ret` 520 = {ar_d 519, ar_v} adapter -> VM `ar`, credit `ar_cr` VM -> adapter; `emb` 513 =
  {eq_d 512, eq_v} adapter -> SU; `emb_a` 26 = {ea_addr 24, ea_kind, ea_v} SU -> adapter, `emb_cr` back; `seq_d2d` 56
  (sd levels) seq_su -> adapter; `d2d_seq` 187 (ds) adapter -> seq_su; `o4_pw` 75 adapter -> tt_ctlm; `o4_kvd` 44
  {v, kindk, pos 18, wbase 24} seq_su -> adapter; FDI 1,169 = {tx_up, tx_v, tx_flit 583, rx_v, rx_flit 583} (the
  PHY abstract must be regenerated at the 583-b flit: request to the kvsys lead).
- C_ST (relay stages per face) is reported per face from the build (attention: x3 out and ar back differ).

## 5. Rules every hop / pin / slot obeys
- Every inter-tile signal: register at the pin -> <= 490 um pin-to-pin (reach gate) -> register at the pin; relays are
  die-placed tiles in channels / corridors. Clock at each pin at phi - R; R <= 300 ps one level, else an earlier trunk
  tap (SKEW 150).
- Cuts <= 0.55 (design) / 0.60 (gate) on the fine 2-D scan (every cut line at 50-um steps x 260-um windows,
  `results/arch/qwen_tp8_1012/cuts.py`, CAP_MODE v3).
- Top-down pins: the die generator assigns the pins of every unclosed master (`OUT/pins/<master>.json`); closed views keep
  their pins (re-pin only under die_window).
- NO STUBS (owner 08:05): `tools/qwen_split/port_bind_compute.sh DIE_V OUT` must exit 0 (every die instance binds to real
  RTL under its die name; relays / reset repeaters / clock receiver are generated RTL of the build; the UCIe PHY and the
  forwarded-clock bump are allowed hard-macro models with exactly their die ports; contract straps in `straps.json`;
  every other tied or open input fails). Current table: the log, 17:2x entry.
- PDN in the die chain: r7 (`tools/qwen_split/pdn_regroup.py --skip-prefix rly_`): M8 at 8.64 um (= 4 x the 2.16-um
  origin lattice), M9 at the bump pitch; no macro grid for die relays (pdngen costs ~2 s per instance grid; the core
  lattice runs over the relays either way). Relay M7->M8 vias are a recorded PDN scope item.
