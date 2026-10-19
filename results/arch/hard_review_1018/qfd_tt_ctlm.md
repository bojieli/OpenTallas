# HARD-REVIEW 10-18: qfd_tt_ctlm (Qwen compute die tree-top control + ME-side controller)

Read-only post-mortem. Sources: daemon job state `~/.local/state/closure_loop/jobs/qfd_tt_ctlm*.json` (68 records),
`physical/qwen_die_masters/cfg/qfd_tt_ctlm*.env` (origin/main), `results/closure_loop/qfd_tt_ctlm_i-fpbam-150a27450-tc-hm0-cl/verdict.json`,
lanes Q-CTLM / Q-TTH14/15/16 / OWNERS-QWEN / ELEMENT-TABLE, HANDOFF.md, `rtl/qwen_dv/qfd_tt_ctlm_dv.sv`,
`rtl/qwen_sys/static_schedule_20261014/ot_qfd_tt_ctlm_split_static.sv` (origin/main f8be7aafb).

## 0. Is it on the CURRENT die? NO, as a hardened block. Its core logic lives on.

- The die instance `tt_ctlm` on the current Qwen compute die (dv2f14bn / dv2f14bi, Q-DIE14 230b28bd5) binds **`qfd_tt_ctlm_dv`**
  (`rtl/qwen_dv/qfd_tt_ctlm_dv.sv`, Q-CTLM d8f159727, 1,736 pin bits). That replaced `qfd_tt_ctlm_b2` (pre-DV, ~4,594 pin bits),
  which in turn replaced the routed `ot_qfd_tt_ctlm` / `ot_qfd_tt_ctlm_i` / `ot_qfd_tt_ctlm_i_fpm` tile reviewed here.
- What superseded it: the TP4 single die -> TP8 two-die split (owner, 10-14), then the static schedule (no credits), then the DV re-port (10-17).
  - The tree controller and train source were **removed**.
  - The program store, the controller FIFO and the ME controller (`ot_qwen_rom_core_ctrl_static`, which still carries the el1011 fixes
    MEREG/RRG/PCUT/HQ2/PSRAM) moved into the hard child **`ot_qfd_tt_ctlm_static_hr` = "TT head" h16c** (`qfd_tt_ctlm_head_static`).
- OWNERS-QWEN.md: "qfd_tt_ctlm_head, qfd_tt_ctlm_tree, qfd_tt_ctlm_tree_static | not instantiated (dv2f14 uses qfd_tt_ctlm_head_static) | SUPERSEDED".
  The element table (`results/fleet_viz/die_element_table_20261018.json` on claude/elemtable-1018) lists `qfd_tt_ctlm_dv` as a die-level cluster:
  RTL-only, no closure job, iter 4 h. The live risk is therefore **h16c + the qfd_tt_ctlm_dv cluster**, not the old tile.
- The old tile **did close once**: `qfd_tt_ctlm_i-fpbam-150a27450` CLOSED TT +55.31 / FF +10.94 / DRC 0 on 10-12 (auto-merged 71084168c).
  It was then orphaned by the die re-architecture, not by a physical-design dead end.

## 1. Attempt table (61 routes in the qfd_tt_ctlm family: 43 failed incl. 3 refused, 17 cancelled, 1 closed)

| date | job (abridged) | variant | verdict | class | key number |
|---|---|---|---|---|---|
| 10-09 20:02 | ctlm_a/b-618516521 | first ot_qfd_tt_ctlm, 777.6x1814.4 / 1036.8x1555.2 | NEEDS_HUMAN x2 | flow | yosys `modules_.count` assert (parameterised top) |
| 10-09 20:12 | ctlm_a/b-23be324f7 | same, fixed elab | PREROUTE_MARGIN x2 | setup | -1059 / -1179 ps; `r_sbase -> scale_addr[119/959]` (960-b G-sized address) |
| 10-10 03:06 | ctlm_a/b-9632d3f93 | - | CANCELLED x2 | - | superseded by XREG |
| 10-10 04:45 | ctlm_a/b-a639399be | XREG | PREROUTE_MARGIN x2 | setup | -860 / -1201; `u_ctrl_me.d_chase_rows -> hq[400]` (FIFO head enable fanout) |
| 10-10 05:35-20:27 | wide1036/1296 x7 | wider slot variants | NEEDS_RTL x7 | bench | prebuild model / reg_spine / sb_tts_link benches rc!=0 |
| 10-10 11:26-23:43 | ctlm_i_a/b (bfcea35cf, e261d6e89, 955329f22-arf, 6681a9198) | ICUT on ME controller | CANCELLED x8 | - | yosys ~4 h on 65,536-flop program store |
| 10-10 16:22 | ctlm_i_a/b-955329f22 | ICUT | EARLY_FAIL_HOLD x2 | hold | CTS hold stuck -212 / -171 ps, **89,000 endpoints** in margin |
| 10-10 21:43 | i-fpa/fpb-772ccf422 | PSRAM=1 + HQ2 (program store -> 2 SRAMs) | EARLY_FAIL_SETUP x2 | setup | post-CTS -2514 / -1326, 15-17.5 k failing endpoints |
| 10-11 04:46 | i-fpamr-811bd1a67 | MEREG+RRG (reset/enable replication) | EARLY_FAIL_SETUP | setup | -909, 12 k endpoints |
| 10-11 04:48 | i-fpbmr-811bd1a67 | same | PREROUTE_MARGIN | setup | -1346; `h_rd -> kvd_tiles` |
| 10-11 08:05 | i-fp{a,b}mr-34a69f614 | - | NEEDS_RTL x2 | bench | lockstep bench |
| 10-11 08:17-09:48 | mr-ccd87b8f8, au-dace0dae3, au-3d3bde479 | - | CANCELLED x6 | - | rebuilds / bench model missing / p_am pin flop broke argmax loop |
| 10-11 08:36 | i-fp{a,b}au-b312311bd | TEXTBOOK AUDIT | NEEDS_RTL x2 | bench | lockstep s9 |
| 10-11 08:54 | i-fp{a,b}au-f62cd33ac | **AUDIT: -62.7 k dead x_re/x_addr flops, -51.5 k tag flops -> SRAM, 648x648** | EARLY_FAIL_SETUP x2 | setup | -673 / -639, 3.9 k endpoints (5x better) |
| 10-11 09:59 | i-fp{a,b}au-9d6bfc082 | AUDIT + port fix | EARLY_FAIL_SETUP x2 | setup | -1123 / -827 |
| 10-11 14:16 | i-fp{a,b}au-1763e0919 | AUDIT 55 | EARLY_FAIL_SETUP x2 | setup | -533 / -743 |
| 10-11 18:50 | i-fp{a,b}pk-4e9afc303 | PK prefix cuts, **475.2x475.2** (was 8.9 % util) | NEEDS_RTL x2 | hold | routed: FF hold -15 / -21 (TT -152 / -251) |
| 10-11 22:56 | i-fp{a,b}sc-d39a0eefe | SC cuts | REFUSED x2 | lint | 3 of 4 macros off-grid |
| 10-11 23:01 | i-fp{a,b}sc-43229d70e | SC cuts | NEEDS_RTL x2 | hold | FF hold -31.5 / -45.8 (I2R window) |
| 10-12 02:37 | i-fp{a,b}amh-837f0663a | AM + hold kit | NEEDS_HUMAN x2 | flow | `hs_ca` Tcl variable missing |
| 10-12 02:52 | i-fpaam-150a27450 | AM (p_am pinned, +1 argmax cycle) | NEEDS_RTL | bench | cl_ami_s3 |
| **10-12 02:53** | **i-fpbam-150a27450** | **AM, 475.2x475.2** | **CLOSED** | - | **TT +55.31 / FF +10.94 / DRC 0** |
| 10-12 07:10 | i-fp{a,b}amh-f53d1153b | AM+hold | NEEDS_HUMAN x2 | flow | RSZ-3006 buffer insertion |
| 10-12 08:00 | i-fp{a,b}amh2-b51b89bf9 | hm0 | NEEDS_RTL x2 | hold | FF -9.9 / -6.6 |
| 10-12 09:44 | fpbamh2 hm10/hm20 | - | REFUSED / CANCELLED | - | 3-routes-per-commit rule |

Failure classes across the 43 failures:

| class | count | made up of |
|---|---:|---|
| setup | 14 | PREROUTE 5 + post-CTS EARLY_FAIL 9 |
| hold | 8 | CTS storm 2 + routed FF 6 |
| bench / RTL lockstep | 12 | |
| flow / tool crash | 6 | |
| refused | 3 | macro off-grid 2 + routes-per-commit 1 |
Successors, for context (not counted above): `qfd_tt_ctlm_head` closed 10-13 (+17 / +22) and `qfd_tt_ctlm_tree` failed 4x (GRT-0183 maze, hold, TT -102).
The head was then re-done as `qfd_tt_head_static` h0..h16c: about 20 gate revisions on 10-15..18 (h13 -65, h14 -110, h14d -128, h15 -642 spill),
then h16c gate WARN with TT r2r +63.8 and spread 74.2/67.5. h16c route `cd09b7ef0`: TT +66.3 / FF +11.4 / **DRC 5**
(a clock leaf jogs on M4 through the SRAM OBS at the read edge). The fix is the OT_MEG_DEPTH 6.0 guard. Its re-gate died `remote_incomplete` on ot-pve1
(~/scratch/q-tth20/submit.log) and has **not been resubmitted**. A STAGE_ME RTL re-route is also owed (Q-KITS 18:40).

## 2. Structure (old tile, from cfg / RTL / job purposes)

- **Content:** one tile doing four jobs:
  - tree-top control (AMR / SPRE / argmax merge, with G-sized ports: `scale_addr` 960 b, the `t_sel/t_tv` selects);
  - a full copy of the seq_su ME controller (`ot_qwen_rom_core_ctrl_x`, OWN 1);
  - a 64 x 1,024-b program store **in flops** (65,536 flops);
  - the in-tile issue shell, plus the 380/98-b issue/status bus that used to cross 37+37 relays.
  - Totals: about 130.7 k flops before the audit. 62.7 k of those were unobserved per-port `x_re/x_addr` (CSA-row nets with fanout 2-4 k),
    and 51.5 k were tag delay rings.
- **Outline:** 777.6 x 1814.4 (2.3:1 tall), set by the **old die slot** of `sp_tree_top` (777.58 x 3732), not by the tile's content.
  Variant b was 1036.8 x 1555.2. Util was 8.9 %, giving about 414 ps of wire from a pin flop to its consumer (cfg fpb_am comment).
  Final closed outline: 475.2 x 475.2 (1:1), 2x 64x512 + 2x 128x256 SRAMs on a macro grid.
- **Pins:** the predecessor `qfd_sp_tree_top_b` had a 3,084-pin W face (a wall). ctlm spread its pins over 4 faces.
  The submit-lint estimate was W 1.26 / E 0.31 / N 0.02 / S 0.4 b/um, so pin density was **not** the issue.
- **High-fanout nets (the real critical paths):**
  - `load -> hq_fill -> 1,024-b hq enable` (FIFO head; `d_chase_rows -> hq[400]`);
  - `u_rs.rst_q -> 2,372 async clears` (1.27 ns);
  - raw `me_mem_ok -> u_me_cg` clock-gate enable (-1,606);
  - `h_rd -> 32 x ir` copies;
  - `r_sbase -> 960-b scale_addr` (one adder feeding 960 bits).
  - Successor h14d still shows the same class: one `pw_d2` flop drives 16 `wd_in` pins on both SRAMs (-128.7), plus FIFO write enables and the `o_cnt` incrementer.
- **Logic depth:** secondary. There are 25-33 levels on the pretag compare and a 15-MAJ ripple behind `land_cnt`, fixed with exact KS / pipeline cuts at 0 cycles.
- **Clocks:** single domain; ME clock gate pushed down. Clock was not a root cause.

## 3. Root cause

**Wrong partition + memory as flops + an outline inherited from the die slot.** The tile bundled four functions and ~115 k unnecessary or mis-mapped flops
(dead `x_re/x_addr` ports, flop delay rings, a flop program store) into a 2.3:1 slot at 9 % utilisation.
Every wide control word (FIFO head enable, reset, ME enable, scale address) became a high-fanout net spanning mm.
The 89 k-endpoint hold storm and the 12-17 k-endpoint post-CTS setup failures were **symptoms** of that size and spread.

From 10-09 to 10-11 08:00, about 30 attempts chased those symptoms one path at a time: XREG, ICUT, MEREG/RRG reset replication, PSRAM, HQ2, wide slots.
The **TEXTBOOK AUDIT** (10-11) fixed the root: dead flops deleted, delay rings into SRAM, outline shrunk 777x1814 -> 648 -> 475 square.
With that, failing endpoints fell from 15 k to 3.5 k, and the tile closed within ~18 h after the remaining exact KS cuts and one +1-cycle argmax-loop pin register.

The other ~20 failures were overhead, not design: 13 bench/RTL-lockstep failures, 6 tool/flow crashes (yosys parameterised top, Tcl var, RSZ-3006),
and 2 off-grid macro refusals.

## 4. Redesign / verdict

- **Old tile: ABANDONED (already superseded).** It is not on the current die. Nothing to redesign; do not resurrect.
- **Current successor (h16c + qfd_tt_ctlm_dv): CAN CONVERGE.** It already embodies the lesson:
  - tree control removed;
  - program store in SRAM;
  - compact 259.2 x 222.5 head with the SRAM stack W and one L-shaped std-cell band;
  - E/S-face pins;
  - clock at the S L-corner beside the register mass.
  - The density PNG shows a uniform L band with no spill (contrast with h15, where the controller spilled into the W strip).
- **Single change to close h16c:** re-gate and resubmit the OT_MEG_DEPTH 6.0 guard route on the STAGE_ME RTL (geometry 9634bd27 unchanged).
  Then gate the `qfd_tt_ctlm_dv` cluster (spec c1 777.6 x 345.6). That needs the die slot change 777.6 x 1814.4 -> 777.6 x 345.6.
  **Do not keep the old 2.3:1 slot:** that repeats the original mistake. Cost: 0 cycles, area shrinks.
- **Checklist items still open on h16c:**
  - macros at x = 22.464, which is not on the 43.2 um lattice in x;
  - a 0-um macro-macro abut sliver (util_channel WARN);
  - E-face pins on a partial span (~5/um).
- **Risk: MED.** h16c is one DRC fix from closure, but the tt_ctlm_dv cluster gate has never run, and it is on the die critical path
  (element table: tt_ctlm_dv iteration 4 h, no closure job, owner none).

## 5. Lesson

Size and partition a control tile from its **content** (flop census, memories as macros, dead-port audit) before the first route,
never from the slot it inherits. Run the textbook audit at attempt 1, not attempt 30.
When failing endpoints are in the thousands, the fix is structural (delete, re-map, shrink, split), not path cuts.

## PNGs / evidence

- Current successor h16c (viewed):
  - `/home/ubuntu/wt/q-tth15/physical/ref_tile/qfd_tt_head_static_h16c/gate_layout/floorplan.png`
  - `/home/ubuntu/wt/q-tth15/physical/ref_tile/qfd_tt_head_static_h16c/gate_layout/density.png`
- h15 spill (viewed): origin/main `physical/ref_tile/qfd_tt_head_static_h15/gate_layout/density.png` (copied to /tmp/hr_ctlm/h15_density.png).
- h0 head (viewed): origin/main `physical/ref_tile/qfd_tt_head_static/gate_layout/density.png`.
- **No PNGs survive for the old ctlm routes**: run dirs were deep- and bulk-released after the verdicts.
- Closed record: origin/main `results/closure_loop/qfd_tt_ctlm_i-fpbam-150a27450-tc-hm0-cl/verdict.json`.
- Job state: `~/.local/state/closure_loop/jobs/qfd_tt_ctlm*.json`, `qfd_tt_head_static_h16{b,c}-*.json`.
- Configs: origin/main `physical/qwen_die_masters/cfg/qfd_tt_ctlm_i_fpb_am.env` (its comments give the full audit history).
- Lanes: `/home/ubuntu/claude-takeover-20261007/lanes/{Q-CTLM,Q-TTH15,Q-TTH16,OWNERS-QWEN,Q-KITS}.md`; h16c re-gate log `~/scratch/q-tth20/submit.log`.
