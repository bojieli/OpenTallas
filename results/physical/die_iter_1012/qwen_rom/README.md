# Qwen3-8B ROM die (r22ko4): die-level iteration log

Owner decision 2026-10-12: die-level iteration runs in parallel with element closure. Each iteration assembles the die
from the current contract (`results/arch/hier_contract_1011/qwen_rom.json`):

- **real**: the master is bound to a closed, routed element's exported timing view (LEF + TT/FF Liberty from the shared
  exporter, `physical/qwen_die_masters/views/<v>`). Die bits are bound by role or direction (`tools/hier_contract/die_views.py`).
- **budget**: an open element. It has the contract slot outline and pins, and its Liberty takes the contract IO budget:
  setup at each input pin = in_delay_frac x T, clock->out at each output pin = out_delay_frac x T (0.2 T = 166.67 ps).
  FF hold keeps the single-flop minimum view.
- **assumed**: the single-flop constants of `tools/qwen_die_element_lib.py` (iteration 1 only).

The full-die checks are on EPYC3 (`/srv/opentallas-scratch/claude/die-evidence-2/qwen_r22ko4_<e>`): legal real case,
then PDN, then full-die GRT, then die STA (TT setup / FF hold on GRT parasitics with the CTS-measured clock plan), then
rule-H1 hold pads, then IR. Per the academic-validation rule there is no flat full-die DRT. Real-view share counts the
relay stations and the 1,536 cst stations as real: they are bound to closed station ETMs by pin direction.

| It | Run | Contract | Views (real / budget / assumed masters) | Real share inst / area | GRT overflow | TT setup WNS real / all (ps) | FF hold WNS real / all (ps) | IR |
|---|---|---|---|---|---|---|---|---|
| 1 | r22ko4_e6 (src 21fdd3100) | v3 | 156 / 0 / 19 | 87.9% / 7.1% | **154,807** (3D layer assignment: M6 H 111,349 + M8 H 43,425; 2D residual ~50 in 30 gcells, all `n_o4_cb_a/q` constant-buffer words at y ~10,060 um, x 12.3-12.9 mm: floorplan class, option-4 cb word row) | -181.85 (assumed views; `rly_seq_coll` 548-bit WE relay inputs) | -63.36 raw -> **+0.02** with 4,266 rule-H1 pads (clock plan 13,093 sinks bound) | pending |
| 2 | e6 GRT re-timed (`sta_r22k_<c>_it2`) | v4 + it2 views | 159 / 16 / 1 | 88.1% / 7.4% | (same route as it 1) | **-273.07** / TNS -169,070: 787 eps on real `qfd_d2d_rom` (dc 529 @ -273, x3 185, kvd 72, dh, ea) + 547 on `rly_seq_coll` 548-bit WE relay `a` (-181.8). d2d class = clock latency across the hierarchy: the d2d_rom view carries 665.5 ps internal clock insertion, the die plan delivers 47.8 ps to its ck while the feeding relay `rly_seq_d2d_28` is clocked at 420.6 ps; fix = die CTS plan balances the d2d slot to its view insertion (contract clock-entry target), not an element fix | -57.81 raw (30 eps, `qfd_rly_518_NS` a; pads as it 1) | pending |
| 3 | r22ko4_e7 (src 22760e79f) | v4 (+ io_collective M7 straps, 265-region CTS plan) | 156 / 0 / 19 | 87.9% / 7.1% | pending (PDN running) | pending | pending | pending |
| 4 | r22ko4_e8 (src 6974c79ec, EPYC1 die-iter-1012/qwen_r22ko4_e8) | v5 (D5: 509-bit station corridor / tap words, as closed qfd_cst / tile_nk; no clk/rst bundle on the station faces) | assumed + ETM map (it3 = die_views bind on e8) | - | pending (7.57 M nets vs 6.72 M; lint rc 0, audit hops_over 0) | pending | pending | pending |
| 5 | e6 GRT re-timed (`sta_r22k_<c>_it3`, EPYC1 die-iter-1012/qwen_r22ko4_e6 -- moved off EPYC3) | v5 + it2 views | 159 / 16 / 1 | 88.1% / 7.4% | (same route as it 1) | **-194.85** / TNS -204,715: d2d_rom class gone; worst = rly_seq_coll_50 -> _51 (548-bit relay, ~410 um, inside reach: clock class, 51 on clk_r114 with io_xfifo). The it2 STA was wrong in kind: OpenSTA subtracts a macro's ETM clock_tree_path from a pin latency, so every view pin sat one insertion early; it3 writes pin arrival + insertion (sta_tcl -min/-max) and taps clk_d2d (d2d_rom 665.5-767.2 ps tree + ucie_kv + rs_bump) early with a 293 ps TT lift on every other stream tree (clock_plan.py balance, 221860ec6). 196 deep views on shared trees stay late (worst qfd_port_tiles 527 ps) | **-449.92** raw: rs_bump -> d2d_rom (own-tree partner one d2d insertion early), rs_bump -> rly_rst_fwd -311 -> fixed in plan_it3b (own-tree entry pad 716 ps, 2nd commit) -> it3b STA running |
| 5b | e6 GRT re-timed with `plan_it3b` (own-tree entry pad) | v5 + it2 views | 159 / 16 / 1 | 88.1% / 7.4% | (same route as it 1) | -194.85 (rly_seq_coll_50 -> 51, tree-to-tree class; superseded by it 6) | -136.61 raw (io_xfifo -> rly_coll_seq_x_0) | - |
| 6 | e6 GRT re-timed with `plan_it4` (`clock_plan.py balance --sink-target`, 3b30e07c0; EPYC1 die-iter-1012/it4_sta.out) | v5 + it2 views | 159 / 16 / 1 | 88.1% / 7.4% | (same route as it 1) | +8.07 ideal-latency (worst d2d_rom -> rly_d2d_flt_0; rly_rs_3_6 -> sp_vector_memory +16.6) | +18.09 raw (sp_vector_memory -> sp_su64_sfu) | plan: one register instant per clock domain (clk_rx T_D 1,010 ps TT; 1,588 dedicated branches; region delay lines <= 967 ps); FF register-instant spread 87 ps; **added OCV on cross-region pairs up to 102 ps SS (inter budget 150) is not in the ideal-latency STA** -- a TT >= 0 here is not closure until that bound is in the STA |
| 7 | e6 GRT re-timed with `plan_it4` + **clock-path OCV in the STA** (sta_tcl.py b26cbc320+: per-sink non-shared part as -min/-max latency incl. the view ETM insertion; one ideal clock per (domain, region), inter-clock uncertainty base + 5% (R_a + R_b); `sta_tag.sh` tag it5; parity run it5p at OCV 0 = +8.07, mechanism exact) | v5 + it2 views | 159 / 16 / 1 | 88.1% / 7.4% | (same route as it 1) | **-92.83** / TNS -11,982, 294 eps: sp_vector_memory 237, d2d_rom 29, rly_d2d_seq 21 = **deep-ETM-insertion view class** (d2d_rom 665-767 ps, sp_vector_memory own trees: 5% of the view's own tree is non-shared, up to 35.8 ps per side, on top of the region-pair term up to 101 ps TT) | -38.81 raw (sp_vector_memory -> sp_su64_sfu; 12,574 t* tile + 6,144 sp_su64_sfu eps; pads not yet re-run) | worst cross-region pair OCV 132 ps SS (TT) within 150; structural fix = element insertion to the contract clock-entry target (175 ps) or a relay stage after d2d_rom / before sp_vector_memory |


## Where the area is

92.6% of the die area is still on budget views. Almost all of it is one element: `qfd_tile_nk`, 1,536 x 0.345 mm2 =
529.6 mm2. That replicated hardened cluster is open: the h3 route hit DRT-0073 on the lsl leaf's E-face pin access, and
lsl6 is the fix (el1011-q-tile). The die's real-area share moves only when that tile closes. Every other open element is
under 5 mm2.

Bound in iteration 2 (closed and exported, outline matches the slot): `qfd_crom_g` (x8, crom_g_a ff3637ce7),
`qfd_su_cbuf_g` (x8, su_cbuf_g_b d32ba31e7) and `qfd_d2d_rom` (x1, d2d_rom_b).

Some elements have closed but are not bound yet, because their die master is not the closed block:

- `qfd_tt_up4`: the die master has 6 x 513 pw ports. The closed element is one band upper with 768 pw bits.
- `qfd_io_serdes` and `qfd_io_ucie`: the die masters are PHY + adapter composites. Only the adapter has closed.
- `qfd_seq_su` and `qfd_sp_band_lanes`: no exported view in `physical/qwen_die_masters/views` yet.

## Contract v5 (2026-10-12): floorplan fixes from this iteration

- **D5, word width.** The station words were 323 bits: the corridor a/b on `qfd_cst_n`/`_s`, and tap on the cst and
  `qfd_tile_nk`. They are now 509 bits: 508 data plus ready. The closed RTL is 508 + 1: `qfd_cst` (ot_qwen_die_station a_d/b_d/t_d plus
  a_r/b_r/t_r) and the
  tile_nk ports ib 379 + ib_go 1 + xl 128. The die generator still used the b3r2 compressed instruction transport
  (TAP_BITS 325), which no RTL implements. So the die under-counted 186 bits on every station hop. The die generator
  follows in e8.
- **D6, tile_nk layers.** `qfd_tile_nk` signal_max_layer goes from M6 to M7. The die straps on M8, and the tile's M7
  signals run between its M7 PG straps.
- **tile_nk outline held at 266.952 x 1291.656 (about 60% utilisation).** el1011-q-tile asked for a 288.36 um width.
  The 52.68 um column channel beside each tile holds the closed `qfd_cst` stations. Widening the column pitch adds
  64 x 21.4 um = +45 mm2, which takes the die to 866 mm2, over the 858 mm2 reticle.
