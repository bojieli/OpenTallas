# TOKSIM-S81D/MTPW (10-20): MTP verify wave (wave.busy) and MTP block charges (mc.*) on the release p4l-MU die

## DAG definitions (results/arch/token_path_20261009/ds_rom_mtp.json, composer claude/toksim-s81b-1019@c26aef028)
- `wave.busy` = nodes wave.p2..p6 (group W, 5 x 32,309.2 = 161,546): per verify position 2..6, the slowest stage's busy
  (old r8 26.8149 us = **the sum of group V.S029 nodes L19.ffn.hc_pre .. L20.attn.hc_post = 32,177.5**, i.e. V.S029 minus
  its stage hop V.L20.substage_hop0) x (1 + WFC handoff 46/11,271). The hop out (wave.h2..h6, 1,011.2) is separate.
- `mc.*` (tools/mtp_step_charges.py, 30,631.7 total): MC.draft p2.selected_path 15,357 / markov.floor 562.5 /
  mtp_seq.draft_chain 48; MC.verify wfc_kit.ar_pass 13,560 / wfc_kit.intervals 1,077.8; MC.accept mtp_seq.seed_release
  22.4 / wfc_tok.edges 3 / mtp_commit 1.

## Vehicle: S029-class 6-position occupancy on the release issuer (run_mtpw.sh)
The positions of a verify step are separate jobs on each stage die's issuer: real `dsdv_seq_host` + `ot_dsdv_fixed_issue`
(two job contexts). Every RTL file is byte-identical to release GEN mu4c 19bf4121e (`rtl_blobs_release_19bf4121e.txt`).
The bench is MU-S81/TOK `tb_dv_prog_seqhost.sv +mu` with check_mu.py. The programmes are the compiled L2 programme
(index stage S002, the same class as S029: 2 copies, full scan) and the L0 MTP-calendar programme. One user gets six positions,
pos 5000..5005, each with its own context, issued every S edges. Verilator 5.050 on ot-epyc6 (oth-ubuntu-1684100 / 1684136).
Golden = the single-position run of the same programme (its PROG trace equals the committed check_seqhost-PASS runs
MU-S81 L2_A_single / HEADMU L0_single line for line, except the pos context bits). PASS means: position 0 is
line-identical; positions 1..5 are position 0's trace moved by k x S with their own context, nothing missing or extra; no
issuer fault; 6 jobs.

| leg | S (edges) | L2 (S002 class) | L0 MTP prog |
|---|---|---|---|
| p6_w: stage window = composed S029 busy | 47,136 | PASS, KS 360 + k x 47,136 exactly | PASS, same |
| at control span (82 / 80, 4-grid) | 84 / 80 | PASS | PASS |
| 2 contexts overlapping (span/2) | 44 / 40 | multiset exact, no fault (check (a) assumes no overlap) | fault code 9 (same engine same edge) |
| 3+ contexts | 4..32 | fault code 5 | fault code 5 |
| mutant off the 4-edge phase grid | 47,138 | FAIL fault code 5 | FAIL fault code 5 |

**Measured: the release issuer adds 0 edges between verify positions** (KS_k - KS_0 = k x S exactly). There is no WFC
handoff; the old 46/11,271 (= 131.7 a position) is not on the release die. The only constraint is the 4-edge start phase,
which costs at most 3 a position. The issuer's control floor is the 80..84-edge programme span, so the datapath
occupancy sets the wave. Two positions can overlap at the control level, but only where their engines do not issue
on the same edge, and the compiler must check that (a compile fault, never a stall).

## wave.busy composed from the release-RTL per-op records already in the composer (compose_wave.py, s029_position_compose.json)
Per position = sum of the V.S029 nodes (excluding the hop) at the composer's current node cycles, + 0 handoff (measured):
**47,136.2 a position** (old 32,309.2). Grade split per position: release-RTL 25,973 / newest-element 3,648 / current-RTL
1,323 / old-RTL 12,114.2 (a_proj 1,859.2, idx.q 93, idx.score 5,937, idx.topk_local 4,225) / modelled-PHY 3,624 /
priced 454. x 5 = 235,681 vs 161,546 (+74,135 cycles on the MTP step). The schedule assumption is the release single-user
programme: one context in the datapath at a time, so the stage is held for its span, and each position does its own
index read. This is the conservative ctx=1 case of the stage model.
Not folded as a single measured grade: about 34% is old-RTL, PHY or priced. The composer needs a hook that composes wave.busy
from the V.S029 nodes with their own grades (see MTPW.json).

## mc.* on the release die
The release die.v (ot-epyc7 s81-bind-mu4c/bind_main/bind/die.v, sha256 ce6b7913...) has **0** matches for wfc, mtp_seq,
mtp_commit, wfc_tok, markov, p2_, mtp, head and draft. None of the mc.* blocks has executing release RTL, so every old
number is kept and marked "unmeasured: no release RTL".
For wfc_kit.*, the release replacement (the static calendar issuer) is measured above at 0 edges a position.
