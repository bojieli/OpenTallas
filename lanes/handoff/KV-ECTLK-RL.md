# KV-ECTLK-RL handoff (2026-11-15 08:4x PST)
Branch: claude/kv-ectlk-rl-1115 (intel2 /srv/opentallas-scratch2/claude/kv-ectlk-rl), commits 9377570123e (RTL params), 30938205826 (core_sink_census opt-in growth).
RTL: qkd_ectlk_q0..q3, qkd_ectlk_reference, qkd_ectlk_columns(_legacy) take parameters QK_ISSUE_AGE / RESPONSE_LAT (defaults 36 / 25); qkd_ectl3_kiss_st_cols keeps one guard pair CORE_QK/CORE_RL (the values of the signed views) so a bind at other values still fails elaboration. Next change = new -G values + that one pair, no leaf edit.
Miter (bound1834 bench, Verilator 5.032, kv-ectlk-rl-bench/): nom cols 36/25 vs kiss_st #(36,25) RL 25 PASS 0/8580; mut cols 36/25 vs #(34,18) FAIL 8472; base cols 34/18 vs #(34,18) RL 18 PASS 0/8580.
Consumers of 34 (grep rtl/tools/plan): QK = max(34, RL+11) is a FLOOR (kv_regen.py, regen_constants.py); the calendar reads D_QK = QK - 34 (kv_qkh_safe32.calendar_d_qk, kv_bootage, kv_static_programme profile die), so QK 36 is D_QK 2 and nothing fixes 34 as a ceiling. Fixed 34 literals remain only in unrelated native-attention tile/endpoint defaults (split_20261014 qkd_native_attention_endpoint, tb files) that do not sit on hg ECTL. RL 23 limit of the PD note does not apply. Round trip is 25/36 (not 24/35) with krsp +4, rq +3: 8 + 8 + 9.
Core rebuilds (4 kits = copies of the signed quarter kits, run_kit_kv.sh route, ot-run --stage): /srv/opentallas-scratch2/claude/kv-ectlk-rl-cores/q0..q3 (q0 die-kv-56 q0g_hA, q1 die-kv-51 q1r_p2, q2 die-kv-61 q2r_c, q3 kv-q3-2 q3e/kit); only rtl/qkd_ectlk_columns.sv changed (kit-local island-ft edit of q0/q2 kept); q3 needed core_sink_census growth (return_slots[25..31] + c_started re-encode, file core_sink_grow.json).
PLAN ROWS for KV-102 (per hg type, 8 types of 7m; per-type resets unchanged):
 rq (as 7m, +3): bus:o_ectl_Q_N_rq from (170,1322) regs (30,1096.5)(30,731)(30,365.5) to (6,24) capture face:W.
 krsp +4 (replaces the single 3-station row to the row centre 626,1270): shared trunk S1 (306,468) S2 (306,842) from face:W (123,277), then ONE row per core with capture "<core>.rsp_data" and two private stations:
   q0: S3 (306,1216) S4 (30,1300)   hops 374,374,374,360, S4->pin <=223
   q1: S3 (306,1216) S4 (306,1300)  hops 374,374,374,84,  S4->pin <=224
   q2: S3 (520,1010) S4 (605,1300)  hops 374,374,382,375, S4->pin <=244
   q3: NOT FEASIBLE with 4: farthest rsp_data pin (976,1493) is 2069 um (Manhattan) from the window centre = 5.11 hops of 405 (q0 3.16, q1 3.53, q2 4.32). Best 4-station q3 path leaves a 573 um last hop.
 DECISION for KV-102/COORD: krsp +5 on all hg frames (one RL for every core): q3 path (306,468)(605,543)(925,597)(925,971)(925,1300) hops 374x4,329, last <=244; q0..q2 add one station on their branch. Round trip 8+8+10 = 26, QK 37. Cores then rebuild at 37/26 = parameters only (same kits); the 36/25 builds below are the proof of the flow.
 G0 does not check these rsp_data hops (no core_conns sidecar for ectl); hops above are my pin-aware Manhattan, window centre launch (per-bit launch spread y 213..576 not read).
Status of core builds: see COORD-REVIEW-QUEUE lines.

## 11-15 COORD ruling: krsp +5 on all hg frames (RL 26, QK 37) -- ROWS FOR KV-102
rq +3: unchanged from 7m (stations (30,1096.5)(30,731)(30,365.5); from (170,1322) to face:W (6,24)).
krsp +5: shared trunk from face:W (123,277): S1 (306,468), S2 (306,842) [hops 374,374]; then per core, capture "<core>.rsp_data", three private stations:
  q3 (verified): S1 (306,468) S2 (605,543) S3 (925,597) S4 (925,971) S5 (925,1300): hops 374 x4, 329; S5 -> rsp_data pins <= 244 um. (q3 leaves the shared trunk after S1, so its S2 is (605,543), not (306,842).)
  q0: S3 (306,1216) S4 (30,1300)  + one more station on the (306,842)->(306,1216) leg e.g. S3 (306,1029), S4 (306,1216), S5 (30,1300): hops 374,374,187,187,360; S5->pin <=223
  q1: S3 (306,1029) S4 (306,1216) S5 (306,1300): S5->pin <=224
  q2: S3 (520,1010) S4 (605,1300) +1: S3 (450,926), S4 (560,1100)... place 3 stations between (306,842) and (605,1300) at <=405 per hop (794 um total, 4 hops of ~200-380); S5 (605,1300); S5->pin <=254
  (q0..q2 hops all <=405 by construction; positions of the extra station are KV-102's to site on streets; q3 numbers are the binding ones.)
Cores: 37/26 builds launched on 4 kits (kv-ectlk-rl-cores37/q0..q3, ot-run unpinned, route), branch claude/kv-ectlk-rl-1115 @19dac1359b2 (defaults and CORE_QK/CORE_RL = 37/26). 36/25 builds (kv-ectlk-rl-cores) left running as evidence.
Miter 37/26 (kv-ectlk-rl-bench go37.log): nom columns 37/26 vs kiss_st #(37,26) RL 26 PASS 0/8580; mutant columns 37/26 vs #(36,25) FAIL 8096.
