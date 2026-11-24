# KV-TAPSPLIT-HGPV handoff (split from KV-ALLFIX, 11-23 22:55 PST)
Job: census a (tap load, cap 1200) for hg/hgi/pv on A5. Hubs = KV-HUB-HOLD (do not touch).
Work dir epyc10 /srv/opentallas-scratch2/claude/kv-tapsplit-hgpv (cen.sh census, run_row.sh, comp.sh, sb.sh scoped strict).
- KV-ALLFIX TAPSPLIT-RD 8f1f158a5632 = a5.list line 11 (planned model hg + pv_v1n/v3n/v5n).
- MY ROW: ROWS_KV-TAPSPLIT-HGPV.py f2bd37c2e6f9 (flops snapshot flops_cache_1123.json 4eb26066b1e0; env TS_BRTL TS_DIR TS_FLOPS), inserted after line 11.
  r2 on A5 s11 829a7f50c579 -> r2/plan.json e61cad5d8daf: hg 5 SPLIT +55, hgi 7 SPLIT +134, pv_v1n SPLIT +8; PARTIAL hg_v3 1368 (cap 1800), hgi_v8 1351 (cap 3000).
  BLOCKED pv_v12e/v7e/v2ne/v6n/v5ne: face-register strips in a channel core<->die edge, no legal tap site -> geometry row needed.
- A5ts = r2 + a5.list lines 12-18 + reprice + fill + PRE (comp.sh). Then sb.sh scoped strict on 16 changed types (plan copied to kv-allfix/grow/tree plan_of_record/plan_tshgpv_<tag>.json; epyc10 scratch2 99% so no tree fork).
