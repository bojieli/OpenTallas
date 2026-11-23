# OPUS-FIX-HEAD-LEP0N-R9 (Opus, from 11-22 22:3x PST; successor of FABLE-FIX-HEAD-LEP0N, Fable 429 until 11-29 - do not message it; pairs OPUS-FIX-HEAD-LEP0N-R8)
Goal: hd_lep0N_w (+ hd_st_n4 re-sign) signed off via Row A (LEP-WCHAN-2), Row B (LEP-WCHAN-3) or A+B; first to sign wins.
Read predecessor handoff lanes/handoff/FABLE-FIX-HEAD-LEP0N.md (22:3x section) for all paths/scripts. Hub dir intel2 ~/fable-fix-head-lep0n-1122 (shared with predecessor).
L=/srv/opentallas-scratch2/claude/fable-fix-head-lep0n-1122 (epyc10: r18q_rx base, r18r_wchan2 Row A; epyc7: Row B r18s, A+B r18t).

## ADOPTED 22:3x
- Row A kits (r18r, plan 4a5831b8a9c84826, rt 345ac19b04b3, epyc10, goal route): units fable-lep0n-wa (W sealed, counts), -wap (W probe), -na (nst4 sealed), -nap (nst4 probe); logs ~/fable-fix-head-lep0n-1122/runitem_<x>.log. At kit_rtl 22:31.
- w11 (r18n, no channel fix): real GRT on epyc2 spill (unit fable-lep0n-w11). e1 (r18k, E piece): CTS on intel1 (fable-lep0n-e1); CTS post-hook -179.76 one group wn[1]->rg3 txi = R8 E plan row.
- epyc10 ot-delete of partial fork s81_head_r18s_wchan3.forking-466052: DONE (dir gone 22:3x).
- epyc7: bt_epyc7.sh (intel2 pid 487578) forking r18q->r18s from epyc10, then r18s->r18t local, then chain_bt.sh s|t gates on epyc7 (logs chain_r18s/chain_r18t.otrun.log). Scripts already copied to epyc7 L/tmp.
## NEXT
- On gate PASS r18s / r18t: private-spec hd_lep0N_w + hd_st_n4 each sealed + probe (--host epyc7; see launch_kit.sh), durable waiters.
- epyc10 r18q_rx baseline: delete via ot-delete once epyc7 copy verified (sha d1f98516900c in fork7_r18s.log).
