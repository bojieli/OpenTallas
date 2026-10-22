# HBM-TOK8 (10-20): HBM token-pass layer benches on the current GEN2e4 die + R6 (VEH.2) root cause

## VEH.2 R6 `PROGRAMME_Q1` (qt6011): ROOT CAUSE = fixture bank numbering, not RTL
Isolated bench `r6q/tb_r6q.sv` (only DUT: the die's SU programme producer `ot_hbm_su_programme_pslice_c5`, source
identical at R6 snapshot, die rev 922d803a2 and origin/main), R6 compiler fixture `generated_clockfix/q{0..3}`
(R6 kit `artifacts/hbm-r6-epoch-build-only-1019/kit.tar`), Verilator 5.050, ot-epyc7:
| config | q0 | q1 | q2 | q3 |
|---|---|---|---|---|
| R6 fixture as generated | FAIL 672/672 | FAIL 672/672 | FAIL 672/672 | FAIL 672/672 |
| dictionary banks shifted +3 (`remap_ib4.py`) | PASS 0/672 | PASS | PASS | PASS |
Every produced command is a strict subset of the expected one (dictionary rows never landed). The die leaf
`ot_hbm_su_programme_pgcol` has EDGES 7111 -> IB = 4 index banks (local 0..3), dictionary from local bank 4; the R6
generator lowered each column with the standalone N = 672 image (IB = 1, dictionary from local 1), so its dictionary
writes hit index banks 1..3. Main's `su_programme_compile.lower_columns(resident_edges=7111)` (used by layer_images /
qwen_layer_images) already applies this shift, so the defect is in the R6 private generator only. The unshifted
fixture is the committed fail witness. Successor: regenerate the R6 fixture via main lower_columns (or remap) -- the
same multi-group records are run on the die slice below with main's compiler.

## VEH.1 / TOK.HQ.LAYER: SW slice of the CURRENT die (r11 planA pb5b/die.v, bundle @922d803a2)
- `cut_slice.py --with-relays` (new): GEN2e4 relays every link (rf* stations), so a plain SW cut has 1,239 inputs that
  are relay nets. With the input relay chains pulled in (20,465 stations; clock/reset nets excluded), the boundary is the
  original producer nets again: 100 inputs (92 = the GEN2b sw5e names), 849 outputs (174 of 189 old names).
- Replays (v0 zero init): DS L0/L2/L14 re-emitted by main layer_images (fixtures dsfix/fix, native 10/7 returns = die
  su_SW params; 8/9/10 SU records emitted, other units format_open) + VM-sign mutant; Qwen L0/chain r0/r5 re-emitted
  by main qwen_layer_images (fd6f2a14 = main snap) split to NEV 9873; old GEN2 cqw replays as reference.
- Chain `sw11/chain_sw11.sh` + `sw11/waiter_qe4.sh`; results land in /home/ubuntu/scratch/hbm-tok8/log/summary.log and
  ot-epyc7:/srv/opentallas-scratch/claude/hbm-tok8-1020/sw11/out_<name>/{run.log,acceptance.json}.
- Scope: component slice replays (SU-heavy records), not a full-layer measurement; layer coverage = manifests in emit/.
