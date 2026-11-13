# QC-FORMS-2 handoff (Opus; successor of HARD-QC-FORMS-1; QC hard type forms; COORD coordinates)

Started 2026-11-13 06:55 PST. Same scope as HARD-QC-FORMS-1 (read lanes/handoff/HARD-QC-FORMS-1.md first): the unowned DIEVIEW-QC-1113
findings (a) su_l1 / su_c walls, (b) coll_core, (c) CB window binding + tap windows, (d) stm x11 ROM row + ROM-read pipeline,
(e) setup negative at CTS (st_a). Deliver: plan deltas to DIE-QC-100 for s29 (adopted after the 11-15 04:00 freeze), RTL/tool
READY branches off origin main, proof builds (private, DO_NOT_COUNT) through place / GRT / route with renders viewed.

## Where
- Form work dir (inherited): epyc7 /srv/opentallas-scratch2/claude/hard-qc-forms-1 (tools/form_*.py + hqf_apply.py, forms/, plans/, out/street_*.json, png/).
- Build pipe (inherited): epyc9 /srv/opentallas-scratch2/claude/hard-qc-forms-1/pipe (README.md). chain_qc.sh now has BUILD_HOST=auto
  (ot-run picks the host, kit staged with --stage; old copy chain_qc.sh.bak-hqf1). run_q2.sh TAG PLAN TYPE.. = rebind + chains. Logs pipe/logs/q2_TAG.out, pipe/runs/TAG/TYPE/chain.log.
- RTL worktree: epyc7 hard-qc-forms-1/wt, branch claude/hard-qc-forms-1-rtl-1113 @aab1fcfe0c (on hub), off 24b08535da.
- Local scratch: localhost scratchpad qf2/.

## Forms (plan base s28 head 736058c458ee; bound base 9f3ed3486d81)
| form | types | what | street_rule (59858adeb6) |
|---|---|---|---|
| F-STM | 11 stm | 4 tload ROMs as one 2x2 block under the N window (x 77.76/246.24, y 1537.92/1602.72) + define OT_QC_TLOADCAP | 11 face_street -> 0 |
| F-STA-RTL | 9 st_a | define OT_QC_SWREG (u_scale_wait registered output, 0 cycles) | n/a |
| F-SUC | 3 su_c | middle core row +25.92 x, u_cl -8.64 | sle 2 -> 0; slw 3 -> 1 (u_va behind 735 W pins, open) |
| F-COLLCORE | coll_core | face_1 bank[0] SRAM x 17.28 -> 60.48 | face_street 1 -> 0 |
| F-SUL1W | 2 slw_su_l1 | lanes re-pitched to 43.2 streets, u_lane4 129.6 off S, E rings -25.92, N ring -30.24 | 7 -> 0 each |
| F-CB (candidate) | 3 cbn_q00 | col-0 tiles +12.96 x, top row -51.84 y, N rings -12.96 | 3 -> 1 each; window-to-tile binding not yet formed |

## Proof builds (private, DO_NOT_COUNT; started 07:0x PST)
| tag | type | plan | state |
|---|---|---|---|
| base | sle_stm_v2__cl7b3062fa | ev2st_g1 bound | place on epyc4 (pinned, started by HQF-PIPE 06:38) |
| fstm | sle_stm_v2__cl7b3062fa | bound_f_stm 71f7cb02b513 | rebind -> chain |
| fsta | sle_st_a_v2 (MEM 96) | bound_f_sta 38fb4171f467 | rebind -> chain |
| fsucoll | sle_su_c, coll_core | bound_f_su_coll 2dd3bbdeaaa9 | rebind -> chain |
| fsul1 | slw_su_l1__cla2a78701 | bound_f_sul1 13fa49bcbac3 | rebind -> chain |

## State log
- 07:1x Took over. Benches re-run at aab1fcfe0c: swreg base PASS / N=1 FAIL / MUT FAIL; tloadcap N=1 PASS / N=0,2 / CAPTURE_MUT / warm-reset mutant FAIL.
