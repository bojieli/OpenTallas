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
- 01:20 COORD: A5s will R8_STALE like the base; real strict bind = rebase row on A5t (KV-OWN-PV four-table regen, ETA 03:30). Current a5s2 unit (oth-ubuntu-496661) finishes; read its PRE only. A5t rebase: insert ROWS_KV-TAPSPLIT-HGPV after TAPSPLIT-RD, RINS into own fork names, sidecar from own plan, A5t tables read-only.
- 01:4x: OWN pv placed-sink class (COORD). v6n sizing on D28 kit regs: +141 taps -> max 993/1000 (v6n/ dir). Order agreed with KV-PC-TAP: TAPSPLIT-RD -> TAPSPLIT-HGPV -> KV-PC-TAP. bd5bfe850a1e is NOT A5t (dry compose); wait for KV-ALLFIX A5t2 sha. a5s2 (A5s+row) = base 30 R8_STALE, same as ctl.
- NEXT at A5t: (a) rebase row + strict bind; (b) at each pv type's first A5t place, dump placed regs per tap -> tap_split --sinks per type -> row.
- 01:5x: A5t2 a160bc6c5c2c (epyc11, rt 445647cc300c). LIVE epyc10 oth-ubuntu-1190769-1795513914 a5t2.sh (log a5t2.otrun, d_a5t2row, sb3_a5t2row): s10 aa921101a305 + row + rows 11-21; R8 = A5t2 copy 3c0323fcf395 in in_a5t2/ (read-only). Fork == epyc11 tree except R8 (sha over 3425 files). Row docstring "0 cycles" still wrong (RINS +6); fix text in next row cut.
- 02:0x-03:17: a5t2 run1 refused (3 A5t2 rows only on epyc11) -> copied read-only into in_a5t2/rows. a5t2row bind1 = 30 R8_STALE, derived f41eecdfdcf8 = byte-equal KV-ALLFIX gate_A5t2 derived (row adds no R8 change). bind2 a5t2r2 on f41ee: 15/15 emitted, 1 EMIT = ROW DEFECT kv3_hgi_v1__cl42bc8b12 (cland_reset_ft0_i D=rst_rl_203 != literal predecessor rst_rl_199): street_rule.reset_resel nearest-child walk sent fs_ft2_o down sibling 197-199, same old chain as fs_ft0_o. Shared-tool bug, not fixed in tool.
- ROW NOW 6e2fd99765bf (old kept as ROWS_KV-TAPSPLIT-HGPV.py.f2bd37c2e6f9): RESEL-FUNCTION post-pass (branches ending on the same kept terminal -> one old->new map, majority, edges must exist, else REFUSE); docstring +6 cycles + EDGESTRIP cause fixed. 1 repair, idempotent.
- 03:17 ROW-REBASED (DRAFT, 3c146a79): a5t3.sh -> d_a5t3row plan f894d74d1e78, sb3_a5t3row: RC 0, 0 errors, 15/15 RTL, R8 f41eecdfdcf8, own sidecar 591061370a95, asbuilt 87539c2b08f1, pv_col 1976e4314579. PRE 23 RSTREACH, 4 lines vs A5t2 (renames + hgi_v3 15->8). PARTIAL hg_v3 1368, hgi_v8 1351.
- NEXT: FABLE-RC-KV read; LATCHECK +6 ready_at_glue per lane; START depth >= reset depth on 14 resel types; pv placed-sink rows at each pv type's first A5t place (ETA place+90 min).
