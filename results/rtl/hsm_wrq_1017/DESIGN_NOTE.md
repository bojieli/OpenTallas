# ot_hbm_sm_vm_wr_q_t (writer smw_<q>): lane-root re-partition (H-WRQ, 2026-10-17)

## 1. What failed (f4hc 69bfa27a0 routed; re-timed TT/FF with signoff.sdc, `f4hc_path_classes.txt`)

**TT setup -46.5 ps.** One path class. It covers 1,886 of 1,890 negative endpoints:

- Path: `u_wrq.g_sm[k].rp` (core root) -> `o_w` / `ot_prs_*` (clk_out root, E face).
- Shape: 17-21 levels. The rp fanout tree (10/17/24 loads) feeds the fq[rp] 4:1 x 268 mux, the slot 8:1 mux, then the BF16 `rb` increment, then 8 pin_reg_split copies. That is ~600 ps of data.
- Constraint: this is a **cross-entry** path, so signoff.sdc applies inter-entry setup uncertainty **210 ps** (core root > 300 ps) instead of 60.

The u_tgt classes (limit_q/tgt_q, SS -230..-252) are positive at TT. They are SS sensitivity only.

**FF hold -9.6 ps.** Two classes:

- `u_tgt.data_q` (clk_hcfg) -> `tab_w_data` (core).
- `fq` (core) -> `o_sec` (clk_out).

Both are cross-entry pairs, which get **100 ps hold uncertainty**. At CTS the hold repair found **13,705** hold endpoints and inserted **~32k hold buffers**:

- 27,021 + 2,985 + 1,986 buffers; 57.6k cells in total vs 7.7k um2 of logic.
- The source is the wide crossings: rdata_q (clk_in) -> 8,576 fq flops (core); fq/ps/acc (core) -> 456 wq launch flops x 8 copies (clk_out); hcfg -> u_tgt.
- The repair could not finish the endpoints that also carry SS-negative setup cones (tab_w_data, o_sec).

**Clock and outline.**

- Clock: the core root has 9.4k sinks, TT 306-389 ps, spread 83 ps.
- Outline: 142.56 x 388.8, util 0.22.
- Pin pads: inhold/outhold (recipe 3) put pads on every pin.

**Yosys.** fq is inferred as a memory and mapped back to flops: 12,368 flops is the expected count, with no MEMORY_DFF/BMUX2ROM merge of o_*/rp. No ROM inference ate any registers.

**Root cause (structural).** faces4 gives the pin flops their own shallow face roots (native capture <= 190) but keeps the 8.6k-flop FIFO on a deep core root. Every wide data path therefore crosses entries, at 210 ps setup and 100 ps hold. The recipes (ECO, hcfg entry, CTS repeaters) moved the problem between classes and did not remove it.

## 2. Fix: one clock root per SM lane (no wide crossing anywhere)

The writer is 8 independent per-SM serial servers plus one shared descriptor/calendar. Partition the clocks along that seam:

- **8 lane roots, `clk_l0..clk_l7`.** Lane k holds everything for SM k:
  - W pin flops: rv, rrow 12, rdata 256, sm_fault, sm_sched_fault;
  - the DEPTH-4 FIFO (1,072);
  - the server (wp/rp/cnt/ps/acc/flt);
  - the wq lane-k launch flops o_v/o_sec/o_w/o_m and their pin_reg_split copies (E face);
  - a lane copy of the descriptor d_v/d_base/d_stride/d_p/d_mir/d_fmt (same update rule on cv_q).

  That is about 1.7k sinks per root over one ~40 um band. Expected insertion is ~130-160 ps TT, within the native capture/launch and <= 80 ps spread budgets.
- **Core root `clk` (~1.1k sinks).** u_tgt (cmd calendar), the N-face host pin flops, cv_q/cmd_q, quad_q, cmd_fault, busy, fault and rst_q. The root is small, so the N-face pin flops meet native capture without a separate root. **clk_hcfg is deleted**, and with it the hcfg->core hold class.
- **`clk_cal`.** Unchanged: the raw SRAM entry.
- **Remaining crossings are narrow.**
  - Descriptor core -> lanes: 27 bits x 8, quasi-static (changes only while idle).
  - quad_q -> o_sec: 2 bits.
  - Lane -> core: busy/fault/rv OR terms, 4 bits x 8.
  - rst_q async clear, as today.

  About 260 endpoints in all, against ~13.7k now.
- **Unchanged.** Every wide path (rdata -> fq -> o_*) is intra-root at 60/25 ps uncertainty. The failing rp->o_w class loses the 150 ps cross penalty, putting it at about +100 ps TT with the logic unchanged.
- **Pins.** `hold_budget: "die"` (recipe 4): flop-first pins with no inhold/outhold pads, because the boundary hold belongs to the die.

**Behaviour.** Bit-identical and **0 cycles added**: rv(t) -> wq slot 0 at t+3, and the calendar fire edge is unchanged. All entries are the same PLL at phase 0. The SM write-path price does not change.

**Ports.** Per-SM buses replace lo/hi: rv_s<k>, rrow_s<k>[11:0], rdata_s<k>[255:0], smf_s<k>, sms_s<k>, wq_s<k>[280:0], clk_l<k>. Clock ports go from 7 to 10 (clk, clk_cal, clk_l0..7). In the die, all are driven from pll_stream as today; the mapping from the logical ot_hbm_sm_vm_wr_q_t rdata[256k+:256] / wq[281k+:281] is mechanical.

Rejected alternatives:

| Alternative | Why rejected |
|---|---|
| Extra register cycle | Still leaves ~2k-bit padded crossings, and costs a VM calendar edge. |
| Shift-head FIFO | Fixes setup only; the hold crossings stay. |
| FLOW-HOLD alone | Covers boundary pins, not internal entry pairs. It is adopted as the pin recipe. |

## 3. Shape (coordinator 10-17 visual review)

The faces are pin-bound:

- W: 2,152 data pins x 0.096 um = 207 um.
- E: 2,248 pins = 216 um.
- N: about 330 cfg/strap pins = 32 um, plus the clocks.

So any face that carries the W or E pins must be at least ~225 um long. Logic plus macro is 11.6k um2, so util stays about 0.2 for any pin-feasible outline.

- **(a) Square, ~237.6 x 237.6 (preferred if the d4f slot allows).**
  - The W/E faces carry the eight lane pin bands (~26-30 um each).
  - ctl and the SRAM (94.8 x 41.0) sit at the N centre beside the cfg face.
  - The longest crossing (the descriptor to the farthest lane) drops from ~390 um to ~240 um. That is one registered hop, within the 405 um plan reach.
  - Cost: each lane band runs W->E over 240 um instead of 142 um. That is still under one hop.
- **(b) Split into a ctl/SRAM tile (~100 x 100) plus a lane/pass-through tile.** This is the same seam as section 2, with a registered ~31-bit seam.
  - Cost: 2 masters, 2 closures and a die netlist change.
  - The pin-bound pass-through tile cannot be square (it needs ~225 um faces).
  - In-tile lane roots get the same electrical result, so this is a fallback only.
- **Fallback: keep 142.56 x 388.8** if d4f cannot take a new outline. The lane roots alone remove every failing class, and the descriptor hop (<= 390 um) is registered at each lane.

**Decision:** lane roots plus outline (a), subject to the d4f slot check with H-DIE. If d4f rejects (a), keep the current outline; the pin and clock changes are needed either way.

## 4. Gates

- Bench: the existing wrq_t bench, ported to the per-SM ports. Positive plus MUT 1-4, nat2 VM_LAT, and a lane-clock-drop mutant (`LANE_CLOCK_MUT`) must FAIL.
- Pre-route gate with CTS: per-root insertion and spread, and cross-entry endpoint count.
- submit_exact.
- Native audit on CLOSED.
