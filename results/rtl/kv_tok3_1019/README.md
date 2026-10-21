# KV-TOK3 10-19: controlled N-step G7 vehicles, startup-repaired GEN9 vehicles, r2 u1 cycles

Scope TOK.QW.KV (1u/4u KV attention), MU.QW.KVATT. Successor of KV-TOK2 (results/rtl/kv_tok2_1019). Tools in tools/kv_tok3/.
Failed verdicts of every earlier vehicle stay preserved; nothing here edits RTL, gold, programme dates or deadlines.

## (1) Controlled G7 fixture -> N-step (u4pack NSTEP 4, u4cal NSTEP 8)
Cause of the block: the exact-u1 identity adapter (g7_identity_bind.svh, codex 7512369a3) `$fatal`s when NSTEP != 1 and
instantiates the ledger with NPROG=1, so 4-user programmes cannot run on the r2 binary. It is compiled into the TOP, so
"no rebuild" is satisfied as: the 401 hierarchical CHILD objects of r2 are reused byte-identical (sha-checked against the
monitor lane's reuse audit before and after the build), only the top is re-verilated/compiled.
- kva_identity_scoreboard_n.sv: the reviewed ledger + runtime `n_active` (entries >= n_active are never owned, looked up,
  compared or required; count must not change). Diff vs the original is 12 lines (see the file header).
- kva_identity_bind_n.svh: expected identity per step k = {epoch_k, layer_k, T-1, token_k}; the d2d face identity is the
  unique step whose configured (epoch, layer) equals the header (no fallback; uniq_ep already `$fatal`s on duplicates).
  At NSTEP=1 it reduces exactly to the u1 adapter. `kva_identity_bind_n_v1_g7.svh` is the copy compiled into
  controlled_n (literal V base 10); the committed v2 takes the V base from `KVA_AUTH_VBASE` (default 10) -- same text for G7.
- run_g7_controlled_n.py: copies r2 children (not the top's own `Vtb_qwk_stk_WS__hier.dir/verFiles.dat`, which every top
  frontend rewrites: try 1 refused on exactly that file), builds, runs u4pack + u4cal + u1 (N-adapter regression vs r2 u1)
  in parallel, strict verdict identity_verdict.parse_verdict (exactly one SMOKE_PASS + rc0).
- try 2 OOM-killed at --mem 48 in the top frontend (48 G peak); try 3 runs at --mem 160 (the monitor lane's size).

## (2) Startup repair ported to the boot-word fixture of the GEN9 vehicles (WSQK / P0 / P1)
The G7 authority fixture was bounded to ONE archived cut (generate.py refuses any other cut SHA; hand-fixed depths/names;
g7_fault_bind.svh hand-listed). GEN9 vehicles are fresh cuts (and P0/P1 have 2 stacks, 16 groups), so the repair must be
generated from each cut:
- gen_kva_authority.py: traces TX / sequencer / K[g] / V[g] observers back through the cut's relay stations to the
  producer port (bit-level lookup, bus ports included), maps producer TYPE -> actual qualifier + reset (kvs_attn,
  qkd_ectl3_kiss_st, qkd_pv16_vport_b), refuses anything else (multi-clock, disconnected hop, unknown producer) so a
  vehicle never runs unrepaired; emits kva_auth_defs.svh (path count / V base), authority.svh, kva_fault_bind.svh
  (every ECTL / V port / strip af / e-read owner fault, armed by its own captured reset), authority_manifest.json.
- CONTROL (g7_generator_control/): on the archived G7 WSQK cut the generator reproduces the reviewed authority.svh
  line-for-line (only `18'h3ffff` spelled `{18{1'b1}}`) and g7_fault_bind.svh identically (index 18 renumbered 13):
  18 paths, 510 captures, depths 9,5,69,69,67,63,56,47,34,51,6,4,... = the source lane's frontiers. On the G7 P0 pair cut:
  34 paths / 989 captures, 28 fault probes.
- repair_kva_fixture_n.py: the reviewed repair_g7_fixture.repair() on the SAME original driver (sha 668c9ade, identical in
  kv-token-pickup-1019) + cut-generic path count / V base + N-step adapter + generated fault bind.
- kva_vehicle.sh.patch / run_kv_attn_mu.sh.patch: run the generator after the cut (KVA_AUTH_FAIL -> exit 2), require the
  generated files, compile kva_authority_path.sv + kva_identity_scoreboard_n.sv with the bench.
- lint_fixture.sh: elaboration control (Verilator 5.050 --lint-only) on the archived G7 WSQK and P0 cuts.
- gen9_waiter3.sh replaces KV-TOK2's waiter (PID 3163282), which watched the DELETED 7f9501c62 run on ep6 (GEN9 moved to
  e4eb15c83 on ep5, which also PREP FAILed 17:04) and staged the unrepaired fixture. waiter3 scans every host for the
  newest strict kvs14r-*-gen9s* run without PREP FAIL and with the vehicle inputs, stages the repaired tools into a
  run-unique dir on THAT host (data locality) and launches WSQK:128 / P0:300 / P1:300 (u1 u4cal u4pack).

## (3) Cycles
See the "r2 u1" section below (filled when the r2 u1 sim is terminal).

## State 10-19 17:50 PT
- Elaboration control: lint_g7_WSQK Verilator 5.050 --lint-only rc0, 0 errors (evidence/lint_g7_WSQK_pass.log; 119 GB
  flat). lint_g7_P0 still elaborating (ep5, 200 GB). The first lint attempts OOM-killed at 64 GB (evidence/).
- controlled_n try 3: ep5 unit oth-ubuntu-599360-1792455422, top frontend running; result
  /srv/opentallas-scratch/claude/kv-tok3-1019/controlled_n/sim_{u4pack,u4cal,u1}.json (u4cal ~8 h expected: 24k-cycle calendar).
- r2 u1 (KV-TOK2, unit oth-ubuntu-2356307-1792452476) still simulating at 1 h 19 min (orig fixture u1 took 49.6 min;
  the controlled fixture adds 510 capture monitors + ledger). No cycles yet.
- (3) Cycle extraction contract: G7 WSQK is KVA_QK_ONLY (PV pairs outside the cut, no RESULT). From the KVA_STEP /
  KVA_STACK lines only issue/run/start_qk, K-request span and strip-partial (ap) span are real; they bound the QK part of
  the priced 1,555 busy / 1,816 window, never the whole service. The full busy/window needs P0/P1 (pvfin beat 0) or the
  all-stack vehicle.
- GEN9 waiter3 armed (local PID 903562, log artifacts/kv-tok3-1019/gen9_waiter3.log). KV-TOK2's waiter 3163282 was no
  longer running at 17:49 (it never launched anything).
