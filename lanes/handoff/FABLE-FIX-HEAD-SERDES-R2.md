# FABLE-FIX-HEAD-SERDES-R2 handoff (2026-11-20 23:5x PST)

Owner of HEAD hd_serdes until now. Successor: run sdr2d (rows below) and read the final route of sdr2c.

## What was wrong (three separate causes, all measured)

1. Plan defines lost. Live plan (r11b, r13r) had hd_serdes verilog_defines = OT_S81_KP4_ENC_PW16, OT_S81_KP4_SYN_PW8 only.
   The signed sd9he form (11-18, TT -27.16) also had OT_S81_RM_STAGED and OT_S81_KP4_ENC_LA. Without them: unstaged rate
   matcher, rp_g2 -> 4096 mem bits -878 ps at place, one reset net to 624 read-side flops (the 538.8 um a8 verdict).
2. Generator setting. hd_serdes kits carry OT_GPL_SPARSE_OVERFLOW = 0.25 (S81 strip rule): GPL stops at overflow 0.29,
   HPWL 13.36e9. With 0: overflow 0.19, HPWL 5.60e9. Post-CTS TT setup after repair: -1316 (sdr2b) vs +46.69 (sdr2c).
   The kit also lost GLOBAL_ROUTE_ARGS -allow_congestion (GRT-0116 became fatal).
3. Clock tap rows lost. The signed kit had OT_TAP_GROUP_RE / OT_TAP_GROUP_FIXED for the encoder; the r13r kit has none.

## Done

- main 9380343dcbe + db39768f4a6: opt-in OT_S81HD_SERDES_RLEAF (needs OT_S81_RM_STAGED), default unchanged. 1 control
  + 8 slice reset leaves; netlist: max 17 sinks per read-side reset net (was 624). Bench
  tools/s81_link/run_rm_rleaf_bench.sh: rleaf0 / rleaf1 PASS, mut_stale / mut_group FAIL as required.
- Lane clone epyc10 /srv/opentallas-scratch2/claude/fable-fix-head-serdes-r2/repo (clean, pushed).
- Kits, epyc7 /srv/opentallas-scratch2/claude/fable-fix-head-serdes-r2/:
  - sdr2b: r13r NOMCAP kit + 5 defines. FAILED (cause 2). Ended exit 2, keep only as the comparator.
  - sdr2c: sdr2b + OT_GPL_SPARSE_OVERFLOW = 0 + GLOBAL_ROUTE_ARGS = -congestion_report_iter_step 5 -verbose
    -allow_congestion. RUNNING (route), log intel2 ~/fable-fix-head-serdes-r2-logs/sdr2c_route_e7.otrun.log.
    Post-CTS TT +46.69; FF hold gate PASS; pre-GRT hold +4.97 / 0 endpoints; GRT overflow 651;
    GRT-RC TT -373.10 -> -103.37 after repair (TNS -9120). No RSZ-0074 (fix is main 504fcadebf if it appears).
  - epyc10 sdr2 (cancelled first build, define not plumbed): ot-delete skipped it as protected; small, leave.
  - epyc10 sdr2b/gen: pristine copy of the kit (never run). Use it as the source for sdr2d.
- Censuses: epyc7 .../q_cts (sdr2b post-CTS), .../q_grt_c (sdr2c 5_1_grt, GRT RC, max_full.rpt 434 paths).

## sdr2c GRT census: what remains (56 endpoints below -42)

| worst | paths | < -42 | launch-capture skew | family |
|---|---|---|---|---|
| -103 | 27 | 9 | -100 | clk: u_enc.d0 -> u_enc.ch_q |
| -78 | 265 | 30 | -145 | clk: u_enc.ch_q -> u_enc g_pw.pw |
| -70 | 29 | 12 | -381 | clk: u_enc g_pw.pw -> u_enc.wb (launch CK 771.5, capture 390.6) |
| -72 | 45 | 4 | -30 | pma_rck: u_syn.S_q -> u_bm g_pe.thq |
| -63 | 2 | 1 | -82 | clk: u_rm g_staged_rpc rpq -> u_rm.r_m |
| -38..-1 | 66 | 0 | small | pma_rck: u_syn.ldr / S_q -> u_bm (inside the gate) |

51 of the 56 are the ENCODER, and all of it is clock skew between its pipeline ranks (taps clk_t8, t12, t24, t27, t28,
t32 appear on these paths), not logic depth. That is cause 3.

## Ready-to-apply rows for private sdr2d

Source: epyc10 .../sdr2b/gen (pristine). Copy to a new dir sdr2d on a host with memory; patch config.mk by copy + mv.
Start from the sdr2c config.mk (epyc7 .../sdr2c/gen/hd_serdes/config.mk) and add:

1. Encoder on one tap (0 cycles; the signed-kit row, widened from rem_q to every encoder register):
   export OT_TAP_GROUP_RE = (?:^|[/.])(u_enc)[/.]
   export OT_TAP_GROUP_FIXED = u_enc:<tap>
   <tap> = the clk_t<N> nearest the encoder register centroid on the sdr2c placement (the signed kit used clk_t8 on the
   old tap table; r13r has 37 taps, so read it from sdr2c: run/results/.../ot_clock_taps.json + the placed u_enc flops).
   OT_TAP_MAX_SINKS is 1000: count u_enc registers first; if above 1000 raise OT_TAP_MAX_SINKS for this kit or split the
   group in two ADJACENT ranks {d0, ch_q} and {pw, wb, rem_q, sk} on two neighbouring taps (not rank by rank).
   Check after CTS: OT_TAP_INSERTION lines + re-run q2.sh census; pass = no u_enc pair with |skew| > 40.
2. If the encoder still misses after row 1 (logic, not skew): define OT_S81_KP4_ENC_PPCYC (+1 TX ck, pre-approved;
   exists in the kit RTL; signed as sd9pae at -17.46). Post a LATENCY line: TX +1 ck on hd_serdes only.
3. S_q -> u_bm thq (4 endpoints, -72, skew only -30): this is S_q fanout transport, known from sd9h. Structural row =
   kept S_q copies, one per BM unit (g_bm[0..2]) in ot_s81_kp4_dsyn.sv, opt-in define, 0 cycles. NOT WRITTEN. Until it
   exists: OT_S81_RCK_RX_SPCYC (+1 pma_rck, exists; ddly DD 56 fix is in) as the pipeline form. It measured worse
   routed on sd9pb2 (-92), so prefer the copies. With <= 4 endpoints a capture-skew ECO is the allowed near-miss route.
4. rpq -> r_m (1 endpoint, skew -82): add the read-selector copies to their slice tap:
   export OT_TAP_FOLLOW_RE = (?:^|[/.])u_rm[/.]g_staged_rpc[/.]   (verify the key semantics in clock_taps.tcl line 213-231
   before use; if it does not fit, leave it to the capture-skew ECO).
5. Keep from sdr2c unchanged: 5 defines, OT_GPL_SPARSE_OVERFLOW = 0, GLOBAL_ROUTE_ARGS, OT_KEEP_WIRES with rl_s.

Launch as sdr2c was: ot-run --mem 96 --threads 16 --priority die --hosts <host> --dir <kit>/gen -- bash
<kit>/gen/run_kit.sh <kit>/gen/hd_serdes route 96 16. Check the netlist after synth (reset leaves present) as I did.

## Rows owed to the HEAD plan (HEAD-R14), posted, check r16 carries them

- hd_serdes verilog_defines = OT_S81_RM_STAGED, OT_S81_KP4_ENC_LA, OT_S81_KP4_ENC_PW16, OT_S81_KP4_SYN_PW8,
  OT_S81HD_SERDES_RLEAF.
- hd_serdes item env OT_GPL_SPARSE_OVERFLOW = 0 and the GLOBAL_ROUTE_ARGS line.
- Encoder tap group row (row 1 above) once sdr2d proves it.
- Landing reset parents (513.6 um): Codex epyc9 head-crossing-1119/r13/r1_300_codex/serdes_r1_300_trial_v2.json
  (reader on rst_rl_45, writer on rst_rl_118; 233.5 / 176.6 um).

## Reading sdr2c's final route

GRT was 39-91 ps optimistic against routed sign-off on every earlier hd_serdes form, so expect about -140..-190 routed
unless post-route repair recovers it. It is not cancelled: it is the comparator for sdr2d and the DRC proof of the
allow_congestion GRT (overflow 651). If routed TT is inside -42 with internal FF hold >= 0 and DRC 0: export it.
Not verified by me: DRC, routed timing, LEC of the routed netlist (LEC_ASYNC exit 0 was the synth netlist), bind.
The r16 wave hd_serdes item is not mine; whichever signs first counts (COORD).
