# PVM distributed source (H.STA.BLK.14.3.1) -- reviewed, fixed, benched (L2H-SMATT/PVMD 2026-10-19)

Successor of the SAFE2 single-source ev / tag_d[14] input-pin capture (input-fanout waiver rejected). Start: Codex private
draft fae1ece6e (never compiled). Branch claude/hbm-pvm-dist-1019.

## Review of fae1ece6e (what was wrong, what changed)
Draft compiled and was cycle-exact at first try (candidate == SAFE2 reference one edge later), but the fleet yosys census
(flow keep hook, `census/`) showed the structure was not fanout-safe:
- registers without a reset value sat in async-reset processes (e_tag, fa0/fb0/fa1, slot/tag/pub_buffer/pub_* captures),
  so yosys made the reset group their enable: reset_core[13] drove 162 loads;
- pub_d1 182 / pub_active 154 loads (single controls of the 32 wn_k copies), fd1_k 64, ev operand copies 52, fold copy 50;
- the wrapper copies relied on keep_hierarchy only (a flow that flattens them merges all 97 ev copies back: 2,064 loads);
- MUT "bp release one edge early" is an equivalent mutant (entry index renaming) -- replaced.
Fixes (RTL: ot_hbm_sm_pv_merge_distributed.sv / _core.sv):
- every no-reset register in a plain clocked process (its enable is a reset register or a reset capture, low in reset);
- NS 64 operand slices of 8 bits (kept fd0/fd1/turn-state copies per slice), ev = 5 first captures -> 137 kept second
  copies (64 operand, 64 stack-write byte, 8 per-entry recurrence, 1 control), first-tag 2 -> 64, fold_start 4 copies,
  pub_start 4 copies, pub_slot 5 copies, kept pub_d0 x32 (pub_buffer enables) + 3, pub_d1 x8 + 3, pub_active x8;
- per-entry busy/fl/fin/e_tag recurrence on the entry's own ev copy;
- reset tree 2 -> 8 -> 54 third-level groups (<= 32 flops each), capture/release leaves keep_hierarchy + (* keep *) q.

## Evidence
- bench/ (Verilator 5.050 on the fleet, `run_pv_merge_distributed_bench.sh`): candidate vs independent SAFE2 reference
  wrapper at +1 age, EVERY output bit EVERY edge (no X/valid mask), golden on the reference stream; idle tag/sum carry junk.
  PASS: exact, tight, reassert (rst_n re-asserted mid-merge with junk on every command input), stopclk (assert with the
  clock stopped: tree/captures/core state checked cleared with no edge), tight_reassert, xrand_* (random initial state,
  payload compared under valid). FAIL witnesses (`^PVM FAIL mismatches=[1-9]`): pubearly, mut1-5 (SAFE2 core), mut6 (ev
  operand copy early), mut7 (control ev copy early), mut8 (stack-write copy early), mut11 (first-tag copy early),
  mut9_reassert (e_busy group never reset: passes cold, fails on reassert), mut10_stopclk (one second-level node
  synchronous: passes cold, fails stopped-clock).
- census/ (fleet yosys 0.68 + physical/common_flow/ot_keep_regs.tcl, ASAP7 RVT TT): 15,381 flops; every flop outside the
  shared fp32 adder drives <= 32 loads (named max 32); all 2/8/54 reset, 5/137 ev, 2/64 first-tag kept copies survive
  as distinct paramods. Remaining >32: 160 flops inside ot_hdc_fp32_add_lat (a1_swap 142, a1 75, lz_w 66, sum_w 53,
  rnd 53, b2_in 48, s2_byp 35) -- the shared closed adder, identical in SAFE2 s4a (CLOSED TT +50); WAIVED here, owed
  to a fanout-safe adder leaf (separate item).
- price.json: +1 input/result edge on every ATT.PV record (tools/hbm_pvm_edge_cost.py): DS +40.0 cycles/token
  (0.0069%), Qwen +72.0 (0.0057%); +1 cold reset-release edge once per reset.
