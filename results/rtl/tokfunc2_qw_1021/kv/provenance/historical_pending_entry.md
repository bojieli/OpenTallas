# TOK-FUNC-QW stage kv -- PENDING on KV-MU7 job4b (10-21 09:01)
- job4b: ot-epyc5 /srv/opentallas-scratch2/claude/kv-mu6-kvattn4-1020/out_0e597ed1c, unit oth-ubuntu-1443002-1792562956
  (job4.sh pid 1443002 alive 09:00; top C++ compile `make -j 6` running ~3.5 h, 2 cc1plus at ~32 GB each). No summary/record yet.
- Source check (57 files the build read, job4b src_0e597ed1c vs assembly c0f8097f3): 53 identical; 3 bench-only (tb_kvattn_rel.sv,
  kvattn_rel_dp.sv, kvattn_rel.vlt; absent on the assembly); 1 differs: rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv
  (assembly adds RX_FREE/TX_FREE params, default 0 = as built; KV-side instantiator qkd_kvs_attn_r16 identical, leaves them 0)
  -> functionally the assembly's KV attention RTL. NOT relaunched (job4b alive, source equivalent).
  Diff list: /home/ubuntu/scratch/tokfunc-qw-1021/kv_src_diff.txt (+ kv_job4b_src.sha).
- When job4b finishes, collect (on ot-epyc5; copy stage_kv.collect.py there):
  python3 -I stage_kv.collect.py /srv/opentallas-scratch/claude/tokfunc-qw-1021 \
     --out /srv/opentallas-scratch2/claude/kv-mu6-kvattn4-1020/out_0e597ed1c \
     --src-note "KV-MU7 job4b claude/kv-mu6-kvattn-1020 0e597ed1c (GEN9 9fb1918f6 RTL == c0f8097f3 attention RTL, 53/54 files identical, 1 default-0 param add)" \
     --result /srv/opentallas-scratch2/claude/kv-mu6-kvattn4-1020/tokfunc_kv_result.json
  (RUNROOT does not exist on ep5: src_commit will read '?', set it to c0f8097f3 by hand or pass a RUNROOT with src/ASM_COMMIT.)
  Expect u1+u4 T1024/4096/8192 + peaky + T8191 KVATTN_REL PASS, 7 mutants FAIL, T32768 REFUSED (tile/cal fault).
- Rerun form (die closure or fresh): ot-run --mem 700 --dir /srv/opentallas-scratch/claude/tokfunc-qw-1021 -- bash
  /srv/opentallas-scratch/claude/tokfunc-qw-1021/kv/bin/stage_kv.sh /srv/opentallas-scratch/claude/tokfunc-qw-1021 [--die-netlist DIR]

2026-10-21T11:43:46.787674-07:00 liveness: originaljob1443002 alive12h30; cc1plus3688589 elapsed3h14 CPU99.7%,RSS40.6GB; record.json absent. No restart/build/mutation. Original527STG nowterminalFAIL preserved6aa4847b1/c50ae63c8, LMtaildiagcomplete.
