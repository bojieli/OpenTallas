# KV-TAPSPLIT-HGPV handoff (split from KV-ALLFIX, 11-23 22:55 PST)
Job: census a (tap load, cap 1200) for hg/hgi/pv on A5. Hubs = KV-HUB-HOLD (do not touch).
Work dir epyc10 /srv/opentallas-scratch2/claude/kv-tapsplit-hgpv (cen.sh census, run_row.sh, comp.sh, sb.sh scoped strict).
- KV-ALLFIX TAPSPLIT-RD 8f1f158a5632 = a5.list line 11 (planned model hg + pv_v1n/v3n/v5n).
- MY ROW: ROWS_KV-TAPSPLIT-HGPV.py f2bd37c2e6f9 (flops snapshot flops_cache_1123.json 4eb26066b1e0; env TS_BRTL TS_DIR TS_FLOPS), inserted after line 11.
  r2 on A5 s11 829a7f50c579 -> r2/plan.json e61cad5d8daf: hg 5 SPLIT +55, hgi 7 SPLIT +134, pv_v1n SPLIT +8; PARTIAL hg_v3 1368 (cap 1800), hgi_v8 1351 (cap 3000).
  BLOCKED pv_v12e/v7e/v2ne/v6n/v5ne: face-register strips in a channel core<->die edge, no legal tap site -> geometry row needed.
- A5ts = r2 + a5.list lines 12-18 + reprice + fill + PRE (comp.sh). Then sb.sh scoped strict on 16 changed types (plan copied to kv-allfix/grow/tree plan_of_record/plan_tshgpv_<tag>.json; epyc10 scratch2 99% so no tree fork).

## 11-23 23:5x CORRECTION (supersedes the 23:38 ROW-REBASED, RETRACTED in a3c84c05)
- sbA5ts bind = R8_FAIL_FAST, rc 1, nothing emitted: NOT a pass. Row f2bd37c2e6f9 is ROW-DRAFT only.
- Cost: RINS ready_at_glue 504 -> 510 (+6). Row docstring "0 cycles" is wrong (fix the text on next cut, sha changes).
- Live: epyc10 oth-ubuntu-2758368-1795506452 (sb2.sh): private fork kv-tapsplit-hgpv/tree, r8_refresh on the fork only, strict rebind -> sb2/, log sb2.otrun. Adopt, do not relaunch.
- Pass = RC_BIND 0, BIND_ERRORS 0, 15 types emitted, SHARED_R8 unchanged.
- My extra file in KV-ALLFIX grow/tree: plan_of_record/plan_tshgpv_sbA5ts.json (removal = ot-delete if KV-ALLFIX asks).
- Edge strips (pv_v12e v7e v2ne v6n v5ne v1n) owner = KV-PV-EDGESTRIP; cause in my posts is inferred, not read from obstacle boxes.
- hg_v3 1368 / hgi_v8 1351: FABLE accepted as PARTIAL (23:21); the brief's "0 taps over 1200" is NOT met.
- 11-24 00:0x: comp.sh OVERWROTE epyc10 grow/tree eW_sidecar_A5.json (668fe4614b79 -> 591061370a95); asbuilt identical. epyc11 has the original; KV-ALLFIX restores. NEVER rerun comp.sh (RINS-WRAP / FWDCLK / EARLYTAP write to their tree). regen.sh not needed, never run.
- FABLE reads after rebind: errors by class, emitted = 15, LATCHECK per lane for +6 ready_at_glue, START depth >= reset depth on 14 resel types.
- 11-24 00:18: LIVE epyc10 ctl oth-ubuntu-3413929-1795508278, row oth-ubuntu-3415406-1795508281 (both.sh -> comp2.sh -> sb3.sh; logs both2_{ctl,row}.otrun). Inputs: pv_col 1976e4314579, sidecar 668fe4614b79 (read-only in fork). rowown arm (own sidecar) = diagnostic, counts for nothing. 00:08 arms + sb2 INVALID. No r8_refresh, no derived-R8 install. Gated only after a rerun on KV-ALLFIX's A5s sha, read by FABLE-RC-KV.
- 00:2x: row-on-668fe unit 3415406 CANCELLED; row2 arm = both_row.sh, log both3_row.otrun (own sidecar 591061370a95, regen check regen2.sh). ctl regen MATCH 668fe. FABLE reads ctl + row2.
- 01:1x: ctl/row2 done: identical 30 R8_STALE (base), derived R8 3c0323fcf395 both; posted d5bef614. A5s 8227d9519faa step9 = my d_ctl/s8 8713e50d2d25 and RINS = d_ctl/s9 682cb2a15ac6, so row2 s9/s10 is the row on A5s. LIVE epyc10 oth-ubuntu-398458-1795511431 a5s.sh (log a5s.otrun): row2 s10 + a5s.list tail (FWDCLK..WIDERAM) on rt 7e079, PRE, scoped strict R8 head; sidecar 591061370a95.
