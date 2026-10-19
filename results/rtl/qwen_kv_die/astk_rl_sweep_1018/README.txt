AD-KV-ASTK 2026-10-18: is the static ASTK strip calendar parametric in the chain hop latency RL (landed / die-relayed hops)?
Bench tools/qwen_kv_die/astk_er_static_bench.sh (KVD_RL, KVD_ZAGE), Verilator 5.050 on ot-epyc4.
rl1_m0, rl2_m0, rl3_m0, rl3_m4: src 27d14db0d. rl3_z*: src 1c2a17f84 (adds KVD_ZAGE).
RL 1, Z age 1000: PASS (the current calendar).
RL 2 / RL 3, Z age 1000: strip == reference (0 lockstep mismatches) but the FIRST Z block (words 0..3) is read before it arrives
  (zeros) and the ctl Z fault fires -> the compiler's Z start age must move with RL.
RL 3, Z age 1004 / 1008: still FAIL (word 3); Z age 1016 / 1032: PASS (all functional counts + lockstep).
=> landed / relayed hops need ONLY the compiler Z start (cal[31:16]) moved by <= 8 (RL - 1) edges (16 at RL 3; scores, LMAX,
   e reads unchanged). No leaf RTL change for the RL itself. rl3_m4 (tap visibility mutant) FAILs lockstep at RL 3.
