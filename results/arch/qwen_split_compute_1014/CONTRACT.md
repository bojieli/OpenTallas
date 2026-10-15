# Qwen3-8B TP8 split — COMPUTE die contract v1.3 (2026-10-14 takeover; structural candidate, unqualified)

**Binding owner clarification 2026-10-14 18:59:24 PT:** ROM production is statically cycle scheduled by the compiler.
No runtime credit counters, readiness-driven issue, demand arbitration, or backpressure may schedule normal execution.
The compiler reserves compute, memory ports, link slots, finite-buffer occupancy and write visibility using measured
implemented latencies and phases. Availability/commit checks fault on a missed reservation; they never reschedule it.
The credit-based interfaces below are retained as historical/diagnostic evidence until replaced by real static RTL
and an exact production composition. Arbitrarily stalled safety benches do not qualify production timing or tok/s.


Current source-exact pin contracts supersede older slot-interface descriptions below:

| Native component | Assigned geometry / pins | Qualification and source binding |
|---|---|---|
| Static CDC twelve-leaf composition | `static_cdc/qfd_io_xfifo_static.json`; each leaf233.28x151.2, 2x6 homes in700.248x1563.816,169 real parent ports,24 independent roots | Actual source `b53541400`/`7494a6c90`; record widths ur/dr514,cq517,others546, explicit RTL zero padding to546 SRAM. Collective/seq/cq/calendar producers and root R/phi remain OPEN; metadata does not turn legacy credit graph into production. |
| XS tap | `c15_preflight/qfd_xs_tap.json`; exact216 square,13 real ports including ck, hw/he1567, gi380,xpf72 | Actual candidate TT/FF positive and54.7ps boundary spread; fresh exact-file kit required. The reserved345.6 control-stack envelope stays fixed. |
| Band parent | `c15_preflight/qfd_sp_band_lanes.json`;881.28x1131.84,26 real ports including17 clocks,b0/lnk/reset1 | R0 leaf clocks at actual interior XY, every-second data tracks. Actual parent internal signal/PG capM7; M5 faces do not grant dieM7 through parent. Fresh hybrid parent gate required. |
| Static Q/KVN mux successor | `static_x3/ot_qfd_x3_mux_native.json`;129.6square,12ports/1577bits | Actual candidate063cb47b7, input-to-X3 two edges. Native gate and physical site remain OPEN; original one-edge golden master preserved. |
| VM raw consume observers | `vm_rawcommit/observer_homes39.json` and `qfd_vm_qcommit.json`;39 homes banks24..62,488 total roots | Raw cv/line8/mask16 prove actual write coverage; exact data-at-consume and real macro readback require independent proofs/mutant. Actual raw source24e9aeaf7/fence48ef95d84 and macroproofe10417cf4 adopted: all23 proof source hashes match, positive+8mutants qualified at component scope. New raw leaf51sinks gate setup+275.9/FFhold+26.34, TTboundarymean48.5/spread0.7; route jobraw1-762353d7f accepted QUEUED after final source-matched gate (first raw1-bd49e8a81 refused/source mismatch and preserved unqualified). Old Q-only42sinks/R48ps is not carried forward. |

C15 actual OpenROAD preflight: OT_LEGAL1630/0overlaps/0outside and OT_ASSERTPASS, but OT_PAFAIL DRT0305 on ordinary POWER `one_`. Exit0 does not qualify pin access. Latest no-relay cut0.861 and negative relay cost are diagnostic only; no token price can be derived from a skipped relay plan. C14 full relay source6284141cf remains separately frozen.

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
- W sub-area, per band b at the band's tile centroid, centred on the port column: `qfd_sp_band_lanes` 881.28 x 1,131.84,
  `qfd_port_tiles_b` 1,036.8 x 2,462.4, `qfd_sp_res_ser` 777.6 x 518.4. E edge: `qfd_port_tiles_b_f1` 1,036.8 x 2,462.4
  at the band centroid (E-field block words land without crossing the spine; four full-rate TCUT7 words per band half cross as 2050 bits (2048 data + valid + fault)).
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
  xpf 72 b (real controller lookahead BEFORE producer writes), gi 380 b (one-cycle go / descriptor); outputs two registered head words hw / he 1,568 b. Column faults return inward through fault_i/fault, with the two outermost fault_i ports declared zero-valued termini; the tap consumes hw_f/he_f.

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

## 6. C13 structural candidate and authoritative interface corrections

This revision is a candidate, not a qualified die. C8 real-case placement failed before PDN/GRT/STA due to overlapping
relay frames; the exact source and pair are in `c8_case_failure/overlap.json`. The shared allocator fix removes
unreserved pass-one frames after a failed lifted-chain repair, retains the unrepaired verdict, and permits a fresh
search. C9/C11 builds remain live; their old-source results must be collected before deciding whether to route.

C13 uses `OT_SPLIT_STACK=seam`: the SU/VM registered faces retain the existing 24-nm abutment and zero extra transport
edges. The seam lies 216 um above the head row. The tap sits beside the SU; the controller and tree-top receiver sit
above the tap; the clock receiver sits below the VM. Slab stacks clear the head-row channel. Head words use die M8/M9
over the M7-capped VM. Latency, 2-D cut windows, pin alignment and TT/FF endpoints require measurement on the full plan.

The port-frame slot remains **1,036.8 x 2,462.4**. The earlier claim of eight result groups per frame confused block
words with result groups: TP8 has 48 block words and 24 result groups (eight BW FIFO inputs and four result groups per
half-band frame). The 1,101.6-wide direct-leaf diagnostic option is retained as an environment parameter only and is
not adopted. Every final frame must include its real BW transport and actual result functionality.

The half-band fragment carries **2,050 bits**: four distinct level-TCUT7 words (2,048 data bits, lowest word first),
valid at bit 2,048, fault at bit 2,049. It cannot be represented by the old 512-bit aggregate: production matvec issues
on each active edge, so four-cycle serialization would reduce throughput. The primary consumes this vector on cf1,
and the secondary produces it on cw<band>. Both faces must be registered and the cut/relay plan must be rebuilt.
The band tw/ty vectors are 4,096 bits each, matching qfd_sp_band_lanes; control tc is 341 and tf is 104.

Serializer output rb0..2 is 551 bits and follows the actual qfd_sp_res_ser RTL: data bits 0..511, mask 512..527,
row 528..547, nul 548, end 549, valid 550. A v-at-bit-zero wrapper corrupts this protocol. The serializer me_en inputs
come from one-bit tt_ctlm mer0..2 outputs; serializer sticky faults return on one-bit rf0..2 inputs.

Open native requirements: the real VM Q exporter and arbitration with SU KVN traffic; pre-write XPF compiler/controller
lookahead including resident-X coverage; native no-X VM bundles (full 20-bit row addresses), reset and 448 child-clock
entries; collective and link replay per-child clocks; native half-band reducers and frame transport; block-last
node-less tile binding. No testbench producer, tied functional port, or unqualified native clock path proves these.

### Static production mux pin request (supersedes credit proposal)

The new Q/KVN mux uses compiler-selected `slot_v` and `slot_q`, registered Q/KVN data inputs and registered unified x3
output. It has no production credit/ready ports or counters. Proposed hardened leaf envelope: 129.6 x 129.6 um inside
the existing link adapter rectangle; Q data north, KVN data west, unified x3 east, schedule/reset south, own die clock
entry. Exact RTL port names and physical pin assignments are pending the actual mux implementation; these prose names
must never be inserted as phantom ports. Q exporter/producer adapters must be changed to the same static schedule.

The existing `C13` source-frozen smoke is a geometry diagnostic (61297767d). It is not the compiler scheduled production
die: no relays, old interfaces, incomplete native binding. Actual OpenROAD placement proves only its 1,630-instance
outline/overlap/on-track scope. Full die timing and exact static end-to-end cost remain open.

## Current native qualification gaps (2026-10-14 takeover)

C14 source `6284141cf` is a frozen structural diagnostic: DP tree rehosting preserves the exact ordered AST and exports the physical host manifest. Its full relay allocator is running; neither prere lay center-distance improvements nor pin files qualify the production die. The no-relay C13 case passed placement legality (1630 instances, zero overlaps/outside) but pin access failed on the ordinary POWER net `one_`; proper tie/PG integration remains open.

The native tile wrapper still requires real pin registers and reset; the element owner is implementing them and reporting two extra tile data edges and two edges per node hop. These must enter the compiler schedule and measured cost. The tap candidate has positive TT/FF timing but boundary clock spread86.6ps exceeds80ps: no final pin publication until repaired. VM requires32 separately clocked commit-observer leaves in regions3..6 in addition to448 existing closed leaves.

Static CDC local pins are assigned in `static_cdc/qfd_static_ch546.json`:216x151.2um, R0, exact15 real ports, two independent clock entries. Native kits may use these local pins; twelve absolute die sites await the source-bound producer/consumer map. Legacy monolithic padded IO interfaces do not establish the new native fit.

Latest native qualification evidence: static CDC route `qfd_static_ch546-s2-885fe056c` is CLOSED TT+46.88ps/FF+9.11ps/DRC0, but native launch fails at `o_data[155]`: O667.94958ps minus actual related reader R447.6ps =220.34958ps >220ps. Reader and writer references are separate (TT wckmean270.3ps/rckmean447.6ps); this is not repaired by substituting a global mean or relaxing the limit. Per-clock routed references and actual native repair remain required.

Static slab half-word transport is eight actual BW514 capture stages and four exact ordered FP pair pipelines, not elastic FIFOs or SRAM. All producer and consumer roots must be in the core1.2GHz fixed phase family (833.333ps nominal), each delivered at its own measured phi-R. Actual relay phases and source-to-capture edge padding enter the compiler. An independently drifting clock requires real dual-clock storage and cannot be qualified by the same-family full-rate392-word bench.
