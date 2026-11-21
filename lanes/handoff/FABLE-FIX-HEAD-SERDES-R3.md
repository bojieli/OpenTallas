# FABLE-FIX-HEAD-SERDES-R3 handoff (successor of FABLE-FIX-HEAD-SERDES-R2; started 2026-11-20 23:55 PST)

Owner of HEAD hd_serdes (last unsigned HEAD type with hd_lep0N, which OPUS-FIX-HEAD-LEP0N-R2 owns).
Logs: intel2 ~/fable-fix-head-serdes-r3-logs/. Lane dirs /srv/opentallas-scratch2/claude/fable-fix-head-serdes-r3 on
epyc9 (kit sdr2d), epyc7 (census q_enc, an.py, an2.py), epyc10 (lane clone repo), epyc8 (bench copy brepo, bench_scopy2).

## 1. r16 wave row check (done 00:1x): NOT cancelled, it carries the R2 fixes
Row s81_head_hd_serdes_b908d01a2956b a1, kit epyc9 kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r16/items/hd_serdes.
- defines: all five (RM_STAGED, ENC_LA, ENC_PW16, SYN_PW8, HD_SERDES_RLEAF); 8 rl_s reset leaves present in the netlist.
- sparse exit off: no OT_GPL_SPARSE_OVERFLOW; GPL overflow 0.194 at the 2nd timing pass, HPWL 5.36e9; -allow_congestion present.
- landing reset parents: reader start rst_rl_45, writer start rst_rl_118 (Codex trial sites).
- It has no encoder tap group, so expect sdr2c-like timing (GRT TT about -103), not -1316. Placed, AUTO-GEOM PASS-COND 23:56.

## 2. sdr2c (epyc7, R2 kit): GRT TT -103.37 / TNS -9120 after repair, in detailed route since 23:55. Read its final route
(client log intel2 ~/fable-fix-head-serdes-r2-logs/sdr2c_route_e7.otrun.log; gates DRC 0, TT >= -42, FF hold >= 0, LEC).

## 3. Cause of the encoder skew (measured on sdr2c 5_1_grt.odb, epyc7 .../q_enc: flops.tsv = every register, x, y, tap, TT clock arrival)
- The r13r/r16 kit has 37 clk taps; the signed sd9he view had 22. The 15 new taps clk_t22..t36 all sit in the encoder
  (x 1241-1466, y 141-236) and all carry the default 94-ps tap window (pre_cts.tcl: set_clock_latency -source -early -94).
  The encoder has 11,321 registers over ~25 taps (pw 4800 over 8+ taps, ch_q 520 over 8 taps): every rank-to-rank path is
  cross-tap and pays 50-94 ps of window, with no CRPR.
- GRT tails inside single taps, next to their reserved tap sites: clk_t25 arrivals 500..772 (102 pw + 15 ch_q late),
  t23 ..628, t24 ..550, t26 ..633, t5 471..858 and t6 496..797 (u_ptx.l/q), t4 mean 588. Branch nets beside the site are routed
  160-250 um for a 25-um cluster (OT_CLK_LEAF_REPEAT grt pass); the GRT repeater adds 190-270 ps to that branch only.
  Other taps are tight (+-15 ps). pma_rck tree 823..1046.

## 4. sdr2d (epyc9 .../fable-fix-head-serdes-r3/sdr2d/gen, unit oth-ubuntu-3041869-1795249148, client log sdr2d_route_e9.otrun.log,
kit log sdr2d/gen/hd_serdes/run_route.log) = pristine copy of the r16 wave kit inputs (so it has the reset parents) + in config.mk:
- export OT_TAP_GROUP_RE = (?:^|[/.])(u_enc)[/.]   and   export OT_TAP_GROUP_FIXED = u_enc:clk_t20
  (clk_t20 at (1337,123): 50-ps window, 40 um from the encoder centroid (1341,159); pinned group, exempt from the 1000 cap)
- -DOT_S81_KP4_SYN_SCOPY and OT_KEEP_WIRES + ot_s81_kp4_dsyn:S_u; rtl/ot_s81_kp4_dsyn.sv = first lane text.
Launched 00:39 PST, synth done 00:5x: 900 S_u flops, 0 S_q (yosys folded the non-kept S_q into one kept copy, so one unit
shares its copy with the recurrence), registers 37166, reg_fanout PASS.
Checks owed: after CTS the OT_CLOCK_TAPS GROUPS line and OT_TAP_INSERTION of clk_t20 (insertion must stay near the 450
target with ~11.3k sinks) and the q_enc census again (q12.sh + tail.tcl + an.py / an2.py in the epyc7 lane dir; copy to the host).
Fallbacks: tap tree too deep -> two ADJACENT rank groups on two 50-ps taps; encoder still missing on logic ->
OT_S81_KP4_ENC_PPCYC (+1 TX ck, LATENCY line owed); S_u unit that shares the recurrence still missing -> add
ot_s81_kp4_dsyn:S_q to OT_KEEP_WIRES (4 separate registers; not tested).

## 5. RTL: main 31a73b93741 (pushed via ot-push-main 00:5x)
OT_S81_KP4_SYN_SCOPY in rtl/dsrom_sys/s81_link/ot_s81_kp4_dsyn.sv (base form only): 3 kept copies S_u of the syndrome
register, same next-state as S_q, one per RiBM unit; +0 cycles; default unchanged. S_q stays as the accumulator in RTL.
Bench tools/s81_link/run_kp4_scopy_bench.sh: KP4_SCOPY_BENCH PASS (epyc8 .../bench_scopy2.log): off / hd / scopy_only /
hd_scopy PASS; DMUT 2, DMUT 3, SCOPY_MUT_STALE, SCOPY_MUT_BIT FAIL as required. (A copy without the chunk-0 restart is
not a mutant: copies are read only in the S-final cycle; the first bench run showed it invisible, mutant replaced.)
The sdr2d kit RTL is the first lane text (mutant SCOPY_MUT_RESTART + older comment); with no mutant define it elaborates
to the same logic as main 31a73b93741.

## 6. Plan rows for the next HEAD event (once sdr2d proves them)
- partition_types.hd_serdes.clock.tap_group = {"re": "(?:^|[/.])(u_enc)[/.]", "fixed_taps": {"u_enc": "clk_t20"}}
  (gen_phys.tap_group_exports writes OT_TAP_GROUP_RE / OT_TAP_GROUP_FIXED).
- hd_serdes verilog_defines += OT_S81_KP4_SYN_SCOPY (tools >= main 31a73b93741); OT_KEEP_WIRES += ot_s81_kp4_dsyn:S_u.
- clock.tap_window per_port_ps for clk_t22..t36: measured values instead of the 94 default.

## Note
An earlier commit of this file (9f6334c42b) carried FLOW-FIX-0100 text by mistake (shared scratchpad file name); this version replaces it.
