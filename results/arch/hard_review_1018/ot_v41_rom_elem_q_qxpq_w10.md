# HARD-REVIEW 10-18: ot_v41_rom_elem_q_qxpq_w10 (DeepSeek S81 ROM q-element)

This is a read-only post-mortem. Nothing was submitted, edited or launched.

## Summary

- **On the current die: YES, but only as a leaf inside a stand-in parent.**
  - There are 12 instances in each of `rtl/dsrom_sys/s81_dv/frame/col_h9.sv` and `col_h10.sv`, plus `col_h9_MX`.
  - The c5 real-view die netlist has 1,280 instances (`physical/s81_die_views/q_elem_qs5f_efs/die_pins.json`). S81-A quotes x1898 for an older plan.
  - S81-DIE8 (lanes/S81-DIE8.md:21) lists it as "inside stand-in parents; binds when the parent/frame hardens (not a die-level binding)".
- **Root cause:** one hard tile does two jobs. It holds two NB macro pairs at the far W and E ends, plus a shared x-FIFO and walker in the middle. Everything hangs on one 53k-sink clock root (TT R 510 ps), and all 739 pins sit on about 11% of the S and N faces (10.4 pins/um, M5 only). Every retry chased hold, I2R windows, x1 pin moves and CTS hooks, which are symptoms of this layout.
- **Verdict: CAN CONVERGE.** Bind the already-CLOSED RSTP=1 view. Do NOT re-route the tile. A redesign (split into two lane tiles) only if frame STA or GRT names it.
- **Risk: MED.** The leaf is closed, but the boundary-match at the frame parent (510 ps against 80-240 ps siblings) is unproven and is the real bind risk.

## Why the closed view is not die-bindable

There are five separate reasons.

| # | Kind | Fact | Structural? |
|---|---|---|---|
| 1 | **Pin timing (native audit)** | The closed view `dsrom-qelem-qs5f-efs-7fb23b7ff-tc-hm10-cl` fails the native pin audit on exactly one pin: **rst_n capture 239.2 ps > 190**. The data pins pass (launch 212.4 on bank_free vs a 220 budget, so 7.6 ps margin; FF hold need -16.3). Cause: the rst_n pin fans straight into the asynchronous clears of the boundary registers across the 510.84 um width. Evidence: `results/rtl/dsrom_qelem_pq_20261006/qxpq_rst_1017/native_audit_closed.json`. | Partly. The single rst_n fanout is an RTL defect. The fix (RSTP=1 sync relay flop at the pin, 0 data cycles, +1 reset edge) is APPROVED (HANDOFF 0co) and its route is **CLOSED**: `dsrom-qelem-qs5f-rstp-f9192e143-tc-hm10-cl-2bded98f0`, TT +68.11 / FF +6.39 / DRC 0, finished 10-18 09:26, auto-merged into main 20f4cdcaa. Gate estimate for native rst_n capture: about 35 ps. |
| 2 | **No published view for the RSTP route (abstract/kit)** | `physical/s81_die_views/` on origin/main has only `q_elem_qs5f`, `q_elem_qs5f_efs` and `q_elem_qs5f_x1b_stub`. No RSTP view directory exists (no LEF, tt/ff/ss lib, insertion.json, die_pins, slot_fit or child_lint). The RSTP view's native audit is **owed** (pending_results.txt:497). The closed record is only `qxpq_rst_1017/closed/{view/q_elem.lef, corner_sta.json}`. | No. This is bookkeeping: export the view with view_export, then audit it. |
| 3 | **Port/param mismatch in the parent RTL** | `col_h9.sv` and `col_h10.sv` instantiate the element with no `.RSTP(1)` (grep count 0), so they bind the RSTP=0 netlist. That is the one that fails the native audit. The die also has to release this element's rst_n one cycle earlier (0co); that is not done yet. | No. Re-emit the frames with RSTP=1 and fix the reset calendar. |
| 4 | **Parent does not exist (hierarchy)** | The element binds only into the col_h9_l4 / col_h10_l4 / col_h9_MX_l4 frames, and those are stand-ins. No frame kit or flow exists. Before any frame gate, the frame needs: a frame_lp emitter with 3 landed regions, the crs4 view, the bf_col decision and the qxpq RSTP view (lanes/S81-DIE7_logs/frame.md "Missing before any gate (a)-(d)"). | Yes, but at the parent level, not in this tile. |
| 5 | **Clock boundary / contract (clock + pins)** | View insertion TT boundary mean is **510.3 ps** (lib max 598, all-sink 456-552) over **53,105 sinks** on one root. Frame siblings are 82-241 ps (cfg7_seq_bfp 93, su_t_sm* 146-241; `lanes/S81-A_logs/native_audit_s81a_1017.json`). The mismatch at each linked child pair is **~270-430 ps**, far above the 80 ps boundary-match rule and the ">~100 ps difference => landed regions" rule. The frame must either compensate (deliver qxpq's clock ~300-400 ps early, or delay its neighbours) or land every qxpq crossing. On the pins: slot_fit.json says "slot clock_entry ck/N/M4 vs view clock pin clk on S (M5): the die lead must fix the entry", and the slot lists no pins. The router chose the pin placement: N-face outputs sit at x 151-163 in the efs view but x 228-240 in the RSTP view, so every re-route moves the frame-facing pins. child_lint WARNs: 6,682 M7 pockets (legacy view; needs `abstract_pin_stub.py` or a `--strict-pockets` parent lint). | **Yes.** This one is structural. One huge tree with high insertion sitting next to small tiles is exactly what the 10-18 landed-regions standard exists to handle. |

## (a) Route attempts (44 daemon jobs, `~/.local/state/closure_loop/jobs/dsrom-qelem-*.json`)

Before 10-07 there were also RTL timing rungs QM2..QM7 and QS2..QS5 (quick exact gates, `results/rtl/dsrom_qelem_pq_20261006/qx10q*.json`). Those added the QPIPE, QZ, QY, QX, PQ, QM and QS knobs: ten wrapper generations, each one "zero added cycles".

| Date | Job (suffix) | Variant | Verdict | Class | Key number |
|---|---|---|---|---|---|
| 10-07 | qs3-48d02e7af | QS3 | NEEDS_HUMAN | flow | calibrate synth/place crash |
| 10-07 | qs3-cb92bce64 | QS3 | CANCELLED | - | - |
| 10-07 | qs4-cc7e9b2a9 | QS4 | NEEDS_HUMAN | flow | route crashed x2 |
| 10-07 | qs5-5a2b2209f | QS5 | NEEDS_HUMAN | flow | calibrate crash |
| 10-07 | qs5-1b89b1b6d | QS5 | CANCELLED | - | - |
| 10-07 | qs4r-cc7e9b2a9 | QS4 retry | EARLY_FAIL_DRC | DRC/congestion | DRT iter 43: 16,453 violations, not converging |
| 10-07 | qs5r-1b89b1b6d | QS5 retry | NEEDS_RTL | hold + DRC | SS +22.7 / FF -23.3 / DRC 99 |
| 10-07 | qs5f-e1fbc25c1 | QS5f | CANCELLED (stale) | hold | TT +87.5 / FF -26.7 |
| 10-07 | qs3/qs4/qs4r/qs5/qs5f/qs5r -tt (x6) | TT corner reruns | NEEDS_HUMAN | flow/fanout | RSZ-0060 buffer cap in CTS repair (IO SDC budget or extreme fanout) |
| 10-08 | qs5f-hm10-fa27bd608-tc | hold margin 10 | EARLY_FAIL_HOLD | hold | CTS hold WNS -111.3, 12,429 buffers, 14,061 endpoints |
| 10-08 | qs5f-hm25-4ea1fb1d0-tc | hold margin 25 | EARLY_FAIL_HOLD | hold | WNS -114.9, 27,676 endpoints |
| 10-09 | qs5f-h1min-2c681ce7f-tc | H1 input min | NEEDS_HUMAN | flow | calibrate crash x2 |
| 10-09 | qs5f-hm10-...-f5-hm0 | hm0 | NEEDS_RTL | hold (I2R) | FF -51.2; window I2R=590@-82.7/-108.2 (all input pins) |
| 10-09 | qs5f-h1hook-17765b771-tc | H1 input SDC hook | EARLY_FAIL_HOLD | hold | WNS -23.3 (from -106), 13,498 endpoints |
| 10-09 | h1hook-...-hm25-cl | same, hm25 | CANCELLED | - | superseded by efs |
| 10-09 | efs-8da652050 hm10 / hm25 | E/F pins south | NEEDS_HUMAN x2 | flow | route crashed x2 |
| 10-09 | efs-dadce97fb hm10 / hm25 | same | NEEDS_RTL x2 | bench | bench_qs5_source_bound rc=1 |
| **10-09 to 10-10** | **efs-7fb23b7ff-tc-hm10-cl** | **H1 hook + E/F south, hm10** | **CLOSED** | - | **TT +98.72 / FF +12.04 / DRC 0; SS -187.6; hold ECO +59,153 cells on 40,185 endpoints** |
| 10-09 | efs-7fb23b7ff-tc-hm25-cl | same, hm25 | EARLY_FAIL_HOLD | hold | WNS -18.9, 27,159 endpoints |
| 10-10 | x1b-e82a88082 hm10 | xs_q1 pins moved to S 400-505 (near E pair) | EARLY_FAIL_HOLD | hold | WNS -103.8, 13,285 endpoints |
| 10-10 | x1b-e82a88082 hm25 | same | EARLY_FAIL_HOLD | hold | WNS -85.5, 26,483 endpoints |
| 10-10 | x1e-e82a88082 hm10 | xs_q1 pins on the E face | FLOORPLAN_MARGIN | floorplan | E ROM abuts the pin edge, 266 pins behind it |
| 10-10 | x1bcg-a685e7d34 hm25 | x1b + CTS clock-gate hook | EARLY_FAIL_HOLD | hold | WNS -215.2, 26,446 endpoints |
| 10-10 | x1bcg-ebb8dba8b hm10 | same | EARLY_FAIL_HOLD | hold | WNS -31.0, 13,187 endpoints |
| 10-10 | x1bg16-6ef1e18cc hm10 | x1b + CTS group 16 | EARLY_FAIL_HOLD | hold | WNS -149.2, 12,781 endpoints |
| 10-10 | x1bg64-68b86b02d hm10 | x1b + CTS group 64 | EARLY_FAIL_HOLD | hold | WNS -16.0, 12,867 endpoints |
| 10-10 | x1bp-5b1b09465 / fc696d1ca | x1b + pin regs | CANCELLED x2 | - | - |
| 10-10 | x1bp-0b034d61d hm25 | same | EARLY_FAIL_HOLD | hold | WNS -97.8, 27,070 endpoints |
| 10-10 | x1bp-116a5261f hm10 | same | EARLY_FAIL_HOLD | hold | WNS -57.8, 13,666 endpoints |
| 10-17 | rstp-35152e3e1 | RSTP=1 | INVALID | flow/spec | retired hosts pinned, no pass/fail bench |
| 10-17 | rstp-f9192e143 | RSTP=1 | REFUSED | lint | STRUCTURE_REPEAT (18 terminal fails since the last CLOSED) |
| 10-17 | rstp-...-43d221ec6 | RSTP=1 | REFUSED | lint | CLOSED_STANDS (needs reroute_reason/source) |
| 10-17 | rstp-...-e0f932882 / 76d52c946 | RSTP=1 | REFUSED x2 | lint | fail-witness not in commit (daemon fetch race) |
| 10-17 | rstp-...-07c6fb363 | RSTP=1 | NEEDS_RTL | bench | vacuous min_count regex |
| **10-17 to 10-18** | **rstp-...-2bded98f0** | **RSTP=1** | **CLOSED** | - | **TT +68.11 / FF +6.39 / DRC 0; SS -208.9 (5,756 viol, sensitivity only); hold ECO +59,131 cells on 39,964 endpoints** |

Tally by failure class:

| Class | Jobs |
|---|---|
| Hold | 17 (13 of them at CTS repair, before route) |
| Flow crash | 9 |
| Cancelled | 7 |
| Lint/spec | 6 |
| Bench | 3 |
| DRC | 1 |
| Floorplan | 1 |
| CLOSED | 2 |

**Not a single setup failure at TT.** The element always had setup margin. Its trouble is hold, the clock, and boundary pins.

## (b) Physical and RTL facts

PNGs (viewed):
- `/home/ubuntu/OpenTallas` origin/main `results/rtl/dsrom_qelem_pq_20261006/qxpq_rst_1017/gate/floorplan.png`
- the same directory's `density.png` and `cts_density.png`
- local copies: `/tmp/qxpq_rev/gate_floorplan.png`, `/tmp/qxpq_rev/gate_density.png`, `/tmp/qxpq_rev/gate_cts_density.png`

According to gate_receipt.json, the layout is identical to the closed efs view. No GRT congestion PNG exists for either closed route; the DRT metrics are in `closed_qs5f/5_2_route.json`.

- **Outline:** 510.84 x 221.4 um, aspect **2.31:1** (long and thin), 113.1k um2. Std-cell fill is 0.56 after CTS, and the density PNG is even and green; CTS hot spots are mildly brown in the centre.
- **Macros:** 4 x `ot_rom_4096x274_m8`, stacked two at the far W end and two at the far E end (g_mac[0] W, g_mac[1] E). They hug the W/E faces and leave a ~10 um sliver row (orange) below each stack.
- **Pins:** 739 signal pins, all M5:
  - **S: 610 pins in x 226.1-284.6 (58.5 um of a 510.8 um face = 11%) = 10.4 pins/um.**
  - **N: 129 pins in a 12.3 um window = 10.5 pins/um.** That window is x 151-163 in efs and x 228-240 in RSTP.
  - W and E faces: none.
  - The kit allowed `--pin-region ... bottom:136.08-374.76` (238 um), but the placer packed the pins into a quarter of that.
  - This breaks the checklist rule (full faces, <=6/um) and the 10-17 "partial-face pin cluster" defect list. The 10-17 coordinator REVIEW.json passed it as "pin_spread: unchanged from the closed view".
- **Macros far from pins:** all inputs enter at S-centre. The 512-bit x vector (xs_q0 + xs_q1, plus e0/e1) goes into one shared x-FIFO (`f_q0/f_q1`, XF=4) and the walker. Inside **each** pair, x0 feeds rom0's lane and x1 feeds rom1's lane (`ot_v41_rom_elem_w10.sv` g_mac, l0/l1 bterm). So two 512-bit x copies travel ~150-250 um from the centre to both ends, and 4 x 274-bit ROM read words come back toward the centre outputs. That is why the x1b and x1e trials (moving xs_q1 next to the E pair) could not help: both pairs need xs_q1.
- **Clock:** one `clk` pin on the S face at x 231. The tree feeds 53,105 sinks, including 4 macro clocks behind ICGs (`u_e.g_cg.u_cg.gclk` plus a clone). Measured TT: R 510.3, all-sink 456-552, spread 75 ps (passes <=80). FF boundary is 402. The clock enters at the pin cluster, while the register mass is spread across the full width plus the two macro ends.
- **Size and fanout:** 230,536 routed nets and 1.26 m of wire.
  - Both hold ECOs added **~59k cells (~26% more instances) on ~40k endpoints below the hold margin**. These are short R2R paths: shift/delay chains (`ot_hdc_delay`, `chain3/4`, QPIPE/QZ stages) under a 510 ps tree, with a +-50 ps local skew.
  - The I2R hold window (590 input pins at -83/-108 ps) comes from input min-delay (0.36 ns) against 510 ps capture insertion. The H1 input-SDC hook fixed it by re-referencing, not by changing the geometry.
  - Before CTS, the -tt reruns hit the RSZ-0060 buffer cap, which points to extreme fanout on the IO or broadcast nets.
- **Logic depth:** not the limiter. TT R2R margin is +68 to +99 ps after QTIMING_FIX/QPIPE. SS is -188 / -209 (sensitivity only).
- **CDC:** none. There is one clock; rst_n was the only async boundary item, and RSTP fixes it.

## (c) Root cause

**Root cause: wrong partition and shape.** One 2.3:1 tile packs two independent macro-pair lanes at opposite ends and puts a shared x-stream FIFO and walker between them. All I/O sits on one narrow S/N window and one clock root covers 53k sinks. The consequences:

1. The insertion is large (510 ps), so short R2R and I2R paths need ~40k hold fixes. This is why all 17 hold failures happened, why the hm10-vs-hm25 coin flips happened (hm25 never closed), and why ~59k ECO buffers were needed.
2. The boundary insertion is ~300-400 ps above every sibling, so the parent cannot bind it without compensation or landing. That is the bind problem.
3. The pin windows are 10.4 pins/um, which gave the DRC/route crashes in the QS4/QS5 era.

The retries chased symptoms: hold margins (hm0/10/25), the H1 input-SDC hook, E/F pin moves, x1 pin moves (x1b/x1e), CTS clock-gate/group hooks (cg/g16/g64), pin regs (x1bp), and then the rst_n relay. None of these changed the partition or the clock structure. The closure that finally happened used a lower hold margin (10 ps) plus a 59k-cell ECO.

This is the "good physical design, no masking" anti-pattern: the closure is legitimate under the rules (closed tiles stand), but it was reached by masking, not by fixing the geometry.

## (d) Structural options

**Recommended now (closure first, CONVERGE).** Keep the closed tile. Bind the RSTP=1 view:

1. Export `physical/s81_die_views/q_elem_qs5f_rstp` with view_export: LEF, tt/ff/ss lib, insertion.json, die_pins, slot_fit, and a child_lint after abstract_pin_stub (pockets).
2. Run `native_pin_audit --relative-to` on the RSTP view. Expected: rst_n ~35 ps, data pins unchanged (watch bank_free launch 212.4 against 220).
3. Re-emit col_h9, col_h10 and col_h9_MX with `.RSTP(1)`, and release qxpq rst_n one cycle earlier in the frame reset calendar.
4. In the frame_lp emitter, put each qxpq pair in its **own landed region, or give it an explicit parent compensation tap** of about -300 ps relative to its neighbours. Then judge it per linked child pair at the child flops (TT+FF <=80). The frame floorplan must follow the view's router-chosen pin windows (S x 226-285, N x 228-240) and clock entry S/M5, and the slot contract (N/M4) must be corrected.

Cost: 0 data cycles. The +3 edges per landing are already in the frame plan if qxpq crossings fall on landed cuts. Otherwise there are no extra cycles, but the frame CTS needs ~300-400 ps of compensation delay on sibling taps (buffers only).

**Only if frame STA, GRT or the boundary check names qxpq (do not start it now):** split it into **two lane tiles**, one per macro pair: ~255 x 221 um each, close to square.
- Each lane tile gets its own x-FIFO copy, pins spread over a full face facing the x-stream producer (<=6/um), and its clock entry beside its own register mass.
- Expected insertion is ~250-300 ps per tile, with about half the sinks.
- Cost: duplicate x-FIFO, walker and config, about +4-6k flops per element (~+3-5% area), 0-1 cycle (pin registers already exist under QP_XS), and a new RTL boundary that needs a lock-step bench against the current element.
- Given the ~1,300-1,900 instances, this is a large re-verification and should be done only if forced.

**Verdict: CAN CONVERGE.** The single change that gets there is: bind the closed RSTP=1 view (view export, native audit, frames RSTP=1), and land or compensate its clock boundary in the frame. **Do not ABANDON**, and **do not re-route the leaf** (STRUCTURE_REPEAT is correct: 18 or more failed routes since the last CLOSED).

**Risk: MED.** The leaf is closed. The open risk is the frame-level boundary match (510 vs 80-240 ps) and the frame hardening that does not exist yet.

## Evidence paths

- Daemon job records: `~/.local/state/closure_loop/jobs/dsrom-qelem-*.json` (44 jobs)
- Closed efs view: `/home/ubuntu/OpenTallas/results/rtl/dsrom_qelem_pq_20261006/closed_qs5f/{receipt.json, corner_sta.json, 5_2_route.json, view/q_elem.lef}`
- Published die view: origin/main `physical/s81_die_views/q_elem_qs5f_efs/{SOURCE.txt, slot_fit.json, child_lint.json, insertion.json, die_pins.json}`
- RSTP: origin/main `results/rtl/dsrom_qelem_pq_20261006/qxpq_rst_1017/{native_audit_closed.json, gate/gate_receipt.json, gate/REVIEW.json, closed/corner_sta.json, closed/view/q_elem.lef}`
- RTL:
  - `rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv` (RSTP), `rtl/v41rom/ot_v41_rom_elem_w10.sv` (g_mac, x FIFO)
  - `rtl/dsrom_sys/s81_dv/frame/col_h9.sv:3613-`, `col_h10.sv:4022-` (RSTP not set)
- Lanes and logs:
  - `/home/ubuntu/claude-takeover-20261007/lanes/S81-A.md:11`, `lanes/S81-DIE8.md:21`, `lanes/S81-DIE7_logs/frame.md`
  - `lanes/S81-A_logs/native_audit_s81a_1017.json`
  - `HANDOFF.md` lines 3274, 3367-3373, 4021
  - `pending_results.txt:497`
