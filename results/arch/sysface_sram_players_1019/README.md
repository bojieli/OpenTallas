# SYSFACE T/L/E native SRAM table players

Opt-in component `ot_qwen_d2d_cal_sram` replaces runtime flop tables with two
`ot_sram_1r1w_64x16_m1` macros per player. Nothing instantiates it by default;
legacy `ot_qwen_d2d_cal`, image files, FACE and shared OVL format are unchanged.
KV-OVL-CLOSURE owns subsequent FACE integration, pin-register replication and kit.

## Model and fixed schedule

`model.json` was committed before fleet simulation. T is NE64/AW6, L32/AW5,
E16/AW4. Each uses 2048 physical SRAM bits (six macros total, 6144 bits,
2290.2264 um2 raw SRAM); shallow logical L/E retain the same fixed macro.
A table entry is 32 bits, split low/high into native instances `lo` and `hi`.
One 32-bit read and write port gives 4 B/edge each; events are 13 bits/edge.
No ECC is added under the academic SRAM policy.

Four idle head reads cache rows 0/1 and SEG1/SEG1+1, followed by a 32-bit
lookahead word. Exactly four stopped edges after the final config/base write
are required before start. On the next edge start may use the last SRAM output
as its second SEG1 head; this removes an extra warmup edge. Earlier starts fault,
without a wait, drop, credit or rescheduling mechanism. Actual release admission
has more than 1032 program replay edges after table boot, as confirmed by the
FACE owner; this remains an explicit integration obligation.

At start the native read requests base+2. At an entry transition it requests
ptr+2 while the cached next word becomes current and previous SRAM output
becomes next. Between transitions it requests ptr+1. This sustains dt=1 and
consecutive bursts at II=1 without adding an external event edge. Last-row
logical wrapping and overrun retain the legacy pointer width/check.
Native SRAM has a rising-edge read, read-before-write semantics and active-high
16-bit masks. Reads are disabled on config writes, writes are stopped-only;
runtime config faults and does not write memory. No collision behavior is used.

## Evidence

Source RTL `850456dae`, source/model snapshot `61f7a0a34`. R2 witness receipt is
`results/rtl/sysface_sram_players_1019/receipt.json`; all simulations ran with
Verilator 5.050 on ot-epyc6 unit oth-ubuntu-81676-1792427333.

* T actual CALPIPE be5612758 combined49/base46: 252493 edge checks/193 events PASS.
* L exact legacy component fixture: 473 edge checks/229 events PASS.
* E actual combined8/base4: 1239 edge checks/306 events PASS.
* Coverage includes both segments, cold restart/halt, consecutive entries/bursts,
  every logical row, near-wrap SEG1, base reload with exactly four idle edges,
  reset/runtime-write overlap, and starts after only 0..3 idle edges.
* Five committed fail witnesses reject swapped 16-bit banks, wrong head,
  wrong segment, stale lookahead and missing prefetch-ready fault.

T/E arrays are byte-bound to the copied immutable manifest in this directory.
L is a component fixture, not the unbound production Q-slot/L calendar. These
results do not establish the absolute epoch, native launch phase, LEVEL/identity,
embedding production join, full token, native timing or physical closure.
Earlier R1 witnesses are preserved. Initial build preflight failed because the
runner omitted its output directory; no RTL ran until that runner was corrected.

## Safe-design checklist before any composed gate

1. Pins: PENDING parent pin registers and two-stage face reset landing. Three
   equal-depth kept local reset copies add one initialization release edge only.
2. Reach: PENDING parent placement; candidate outline302.4x172.8 has no required
   single-cycle reach beyond405um, but actual endpoints still need measurement.
3. Fanout: generic Yosys0.68 census retains three reset-copy instances. T reset
   loads are8/31/19; L8/30/19; E8/29/19. Internal register-Q max fanout14.
   Parent start/start_seg expressions still have generic87/70 loads at T and
   require measured upstream replication to<=32 before gate.
4. Depth: shallow fixed head selection replaces the table mux; PENDING actual
   technology mapping, native cone depths and TT/FF checks. No combinational
   external input-to-output data path.
5. Storage: PASS two hard SRAMs/player, no inferred runtime memories in generic
   netlists; only128-bit head cache and32-bit lookahead, no deep flop delay lines.
6. Floorplan: PENDING final ROOT review. Proposed nine-macro parent grows9.375%,
   six SRAMs on43.2 lattice, minimum channels24.84/22.41um; native SRAM W32/E31
   pins over20.79um=1.539/1.491 pins/um. External pin/PG/via access and actual
   full-width band utilisation remain unmeasured. No area/DRC waiver claimed.
7. Clock: PENDING native hard-child refs, regional parent topology, TT/FF spread,
   and io_hold_margin>=.03. Generic census is not technology area or CTS proof.
8. Schedule: component start/event delta0, II1; four stopped preload edges and
   one extra initialization reset-release edge are explicit. Production calendar
   and parent-phase closure remain open. No physical gate was launched.
