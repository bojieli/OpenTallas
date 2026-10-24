# TOK-DS lane (claude/tok-ds-1024, worktree localhost:~/wt/tok-ds; hosts epyc3 + idle via ot-run)
Goal: DeepSeek ROM (S81) token-pass gate: single-die layer runs on current RTL, per-stage cycles, composed 1-user token latency.
## Current step
0. 07:06 RESUMED by new agent after coordinator restart. epyc3 jobs alive and being collected: builds 0S/0N/7 (verilator pids 85168/85169/85171), compile L0/L2/L14/L20 (pids 86250-86253). Old components sub-agent died at staging (epyc2 ~/wt/tok-ds-comp, nothing run); relaunched as sub-agents COMP + COMPOSE on own branches.
1. fc31 layer vehicles (die fc31 35ba1ef7 = latest GEN die: cap30 + 59 chained-frame reset stations; plan-v4.8 die not assembled yet -> NOT RUNNABLE on v4.8):
   cuts 0S/0N/7/3S_ctl patched with fc31 delta (3S_ctl = a240fb53 = monfc31 binary, reused); 0S/0N/7 split builds + idle 400 on epyc3.
2. compile L0/L2/L14/L20 programmes on tree_fc31 (main compiler, checkpoint fixtures 171/204/217/203 files sha-verified vs committed manifests).
3. sub-agents: (a) composition with plan v4.8 latency table (compose_tok_ds.py), (b) component benches on main RTL (owner fold, dense xs cap, KV VP, rstop).
## Findings
- Old-fleet scratch SURVIVES read-only at /mnt/old-nvme0/claude/ on intel1/intel2: stw-s81d-tok/fc30 (cuts+kits, cut_3S_ctl sim binary on intel1, cut_0N on intel2),
  stw-s81c-cap30/gen-main (cap30 GEN bind/plan/land), intel2 s81-p9-fc-1023/fc31 (fc31 die). S81 lane believes these are LOST.
## Run dirs
- 07:2x epyc3:/srv/opentallas-scratch/claude/tok-ds/fc31/run_ctl/{L0,L2,L14,L20} (cut_3S_ctl replays on compiled fc31 programmes) + mut_m1/{L0,L20} (shift-kind:CTL:1 negative control); logs fc31/logs/
- epyc3:/srv/opentallas-scratch/claude/tok-ds/fc31 (cuts/out_cut_{0S,0N,7} builds pids 85109/85110/85111; compile pid 85681)
- epyc3 inputs: /srv/opentallas-scratch/claude/{stw-s81d-tok (ep5 layers+fc30), s81-p9-fc-1023 (fc31 + monfc31 build), stw-s81c-cap30}
## Results
- 10-24 fc31 compile (main compiler, tree_fc31): L0 65 ops (23 LOWERED/38 PARTIAL/4 GAP, 131 rows), L2 83 (18/47/18), L14 92 (18/54/20), L20 84 (18/49/17).
- fc31 cut_3S_ctl idle 400 (monfc31 build, run before the host loss, log recovered): fault_cycles=0 (fc30: fault from cycle 155). Status fault fixed in idle.
- fc30 layer runs (10-23, recovered): all 16 cut replays FAIL: data cuts 0S/0N/7 have 0 check lines (nothing compared); 3S_ctl faulted from 155 (203 mismatches); check refused by XRT guard (since fixed 8ec7bc8bc).
## OWNER?

## components (sub-agent)
- 2026-10-24 07:03 started: staging ~/wt/tok-ds-comp on epyc2+intel1 (claude/tok-ds-1024 = 8a5d1f3dab). Inputs found: dense vectors intel1:/mnt/old-nvme0/claude/codex-tok-s81-layers/dense_driver/vec_B_kv_landed_current; KV baseline intel2:/mnt/old-nvme0/claude/codex-s81-kv-vp-1021/baseline (its source pins differ on main: ot_reset_sync, ot_s81sl_kv_bank, ot_s81sl_kv_leaf).

## compose (sub-agent)
- 2026-10-24 07:15 started: worktree localhost:~/wt/tok-ds-compose (claude/tok-ds-compose-1024 from claude/tok-ds-1024 978d80201). Latency table of record = physical/die_plan/s81/lat/s81_latency.json (plan_digest b4ac6d49d5198cd0 == digest of current die_plan.json v4.8, 834 lanes); r8/ = BINDER4 v4.6 as-built bind table (digest b8e46d33, 820 lanes, 13 lanes +1..2) + R8 landing pads on v4.7b bus groups -> not of record.
