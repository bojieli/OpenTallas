# CALPIPE SRAM calendar recovery, 2026-10-19

Vehicle: main-lineage qfd_dv_cmd_cal_mu at NU=1/4; controller base
claude/mu-die-qw2-1019 05a8c8fe3. The paused lane's uncommitted delta-timer,
registered-head, per-playhead relocation and registered programme writes were
preserved. The runtime-indexed eight-entry flop FIFOs are replaced by SRAM.

One existing ot_sram_1r1w_64x512_m1_r2c2 per user holds two four-entry rows;
NU4 adds four macros (g_fifo[0..3].u_fifo), each 171.288 by 77.784 um.
Storage payload is 8 x 128 x NU bits. A 512-bit write register per macro
captures the programme read output; a 128-bit collision-forward register
handles the macro's read-before-write semantics. The next command/time delta
captures directly into the existing registered head. Pending writes forward
before the SRAM write edge too. Read lookahead respects a refused start's
frozen playhead. Macro depth64 is the smallest available 512-bit write ABI;
only rows0/1 are live. No runtime-indexed flop storage array remains.

Analytical price: four extra macros = 53,293.86 um2 raw macro area (NU4).
Write staging2048 bits + collision staging512 bits replaces4096 FIFO flops;
head/time registers remain. No command, TLOAD, start, completion or external
transport edge changes. Read/write capacity is four commands per fetch,
one issue per edge per user; shared programme read-port policy is unchanged.
The dense production-width test plays23 consecutive commands, crossing both
row boundaries, a ring wrap, and a partial final batch, for NU1 and each NU4
playhead. It also puts a refused start on a dense pop edge.

Evidence: fleet Verilator5.050, ot-epyc6,
/srv/opentallas-scratch/claude/mu-dq-calpipe-sram/src_w128.
seq_w128: positive PASS, NU1 zero lockstep mismatches, MU4 288 schedule events,
1536 landed words,235 dense events. MUT33 wrong next head FAIL; MUT2 swapped
entry halves FAIL. The witnesses below include committed failing logs.
OPSEG production full/red +ctx_part and drift/collision/context negatives PASS: red845548 edges/3677 fires, full4057900 edges/22146 fires (opseg_m0.out).

Safe-design checklist for the successor parent kit:
1. External pin registers/reset landing: parent kit responsibility (ABI unchanged).
2. Reach: parent places four new macros and their staging/head registers locally;
   no claim of physical closure before that gate.
3. Fanout: FIXED for SRAM head field selects:48 hierarchy-kept selector
   modules/48 parameter identities at NU4, separate replicas per32-bit chunk
   and WD/read/collision source; pending/bypass flags replicated too. Fleet
   Yosys0.68 synth -flatten -noabc inventory confirms48 instances retained,
   max selector output load32. check_calpipe_selectors.py checks the JSON.
   Other parent critical cones still require their normal synthesis review.
4. Depth: old rp->eight-entry word/time mux->compare->issue cone removed;
   registered fire and per-user relocated heads replace it. Physical timing owed.
5. Storage: FIXED, SRAM rings; only one-edge interface/collision registers outside.
6. Floorplan: parent must place all six SRAMs on43.2um lattice with full pin-face
   channels and size the outline from synthesized area; macro geometry above.
7. Clock: parent regional CTS/landing gate owed. No clock/mask constraints relaxed.
8. Schedule: unchanged, zero added issue/transport edges demonstrated by lockstep
   and dense expected event comparisons; no credits or backpressure added.

Not a tile gate or sign-off record. The CTLM structural kit re-cut consumes this
RTL alongside ctx_x/hu changes and must finish items1-4,6-7 before its gate.

Selector follow-up: command/TLOAD edges unchanged; seq_sel positive+dense
lockstep PASS, calendarMUT33 FAIL. Source qfd_calpipe_selector is in the same
SV file; no source-list addition. keep_hierarchy deliberately preserves the
per-source/per-chunk select registers through flatten/opt_merge. Placement
must treat these small internal modules as soft logic in the core region.

Strict CE/mask follow-up: qfd_calpipe_readvalid keeps sixteen local read-valid
copies per user, each enabling32 WD register bits, with the original
clear/freeze/read-pipeline semantics. qfd_calpipe_mask keeps two copies per
programme mask bit so each drives32 macro pins. Yosys inventory confirms64
CE modules/64 identities (maximum direct output load1, followed by local
32-bit write-enable logic),32 mask modules/32 identities (maximum32loads),
and48 selectors retained. seq_ce lockstep+dense PASS; MUT33 FAIL. All helpers
live in the existing SV source. Selector-only fullOPSEG repeated PASS is
selector_opseg_m0.out; CE/mask fullOPSEG harvest pending in lane log.
