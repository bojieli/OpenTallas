TOK-QK-6 2026-10-27 (lane ~/coord/lanes/TOK-QK.md). Price runs on paper and checks only. No builds, no sims.
Work dir: intel2:/srv/opentallas-scratch2/claude/tok-qk-6-1027. Tools: main 441bad4d3a (tools/die_plan gen.py/r8.py,
results/token_pass/toksched_1025/kv_v39r_price.py lane-class model, tools/throughput accepted_cost DAG qwen_rom).
Labels: CHECKED = reproduced here from the named file. UNCHECKED = model/estimate.

(1) KV plan hm_r26q3 256600e2 vs hm_r26q2 1d257518 (plan sha256 in q2/q3.plan.sha256; r8pair.sh, diff.py, price.py)
  - Plan latency tables: 130 lanes change, sum +210 (68x+1, 47x+2, 12x+3, 3x+4). This is the same as the
    KV-PLAN-EVAL event table (CHECKED).
  - R8 landing on both plans from the SAME kv44 bind bus groups (fault_exempt -> invariant_split -> rebase-bind
    kv44_bind_latency -> gen.py latency --bus leaf --replica type --fold-r8).
    * q2: 344 members padded, max pad 16.
    * q3: 342 members padded, max pad 17.
    * Folded lane cycles: 136 lanes change, +215.
    * 171 of 5,537 R8 members change their landed age (127x+1, 38x+2, 5x+3, 1x+4) (CHECKED).
  - Token-path members (CHECKED):
    * attention TX d2d_kv.att_tx_payload/att_tx_v: 55 -> 56, so +1 per layer;
    * inbound kvs_attn/kvs_ctl d2d__* (RX/KVN): 0 changed;
    * embedding kvs_emb.d2d__emb_tx_slot: 51 -> 52, so +1 per token. The kvs_emb.d2d__svc status bits also go
      54 -> 55 (not on the token DAG), and kvs_emb.i_hroot_WN goes 7 -> 8.
    * changed sinks by family: pvw 47, host 32, kvs_emb 26, astk 21, vport 20, d2d_kv 9, seq 8, slg 8.
  - Price (kv_v39r_price.py on the folded lane delta, kv_v39r_price_q3.json):
    * direct = 36 x 1 + embed 1 = +37 cycles/token;
    * DAG qwen_rom 249431 -> 249468 = -0.015 %.
    * On the current QCE 296,341 cycles at 833 ps (Codex 08:28 basis): 296378, 4051.0 -> 4050.5 tok/s, -0.0125 %.
      This is +1 cycle over the KV-PLAN-EVAL -0.012 % (36): the extra cycle is the embed emb_tx_slot.
  - Interior serial bracket (every family serial once per layer: vport_slg 2, pv_rows 4, ahub 1, seq/hroot 1, acal 1):
    +361/token = -0.122 % (QCE basis), DAG -0.145 % (UNCHECKED: this is a bound, not a path).
    * Without the PV rows (the PV exact calendar holds them, as in Codex 674cd499f): +217 = -0.073 %.
  - Verdict: immaterial (-0.0125 % direct, <= -0.12 % bound). LEDGER: KV hm_r26q3 ft_slots graft = -0.0125 % direct
    (Qwen ROM).
  - Limit: these are the plan-tool R8 numbers. The final native image (bind4/current R8 + PV calendar regen for +210)
    is still owed by the plan/image owners, and it decides exposure.
(2) KV fallback 128-group compose (claude/fallback-plans-1027@1b7d068ad8; crossings codex d06cccbc4
    row_groups_crossings.json; fb128_lane_delta.py)
  - Lane delta: +3 per landed face, mapped by lane id onto hm_r26. 2,084 lanes / 10,785 lane-cycles. 0 endpoint
    mismatches vs the q3 lane table (CHECKED, equals the packet).
  - kv_v39r_price.py (kv_v39r_price_fb128.json):
    * d2d RX bundle sys_c -> hub_C +33 (11 faces) and attention TX +33, so +66 per layer;
    * embed +123/token (RX 33 + px hop 3 + PC chain 27 + emb slot 30 + row tx 30, serial upper);
    * PRICED +2,499 cycles/token: DAG -0.99 %; QCE basis 296341 -> 298840, 4051.0 -> 4017.1 tok/s, -0.836 %;
    * interior bracket +5,307: DAG -2.08 %, QCE -1.76 % (UNCHECKED bound).
  - PHY<->PC mission buses stay synchronous in this plan, so there is no PHY hop term.
  - Boot: +3/hop wavefront, 0 per token.
  - Compared with the 8-region reference (-0.36 % / -0.66 % DAG), this is about 2.7x. It is driven by the multi-face FT
    chains (3k per lane), not by the number of groups.
  - Variant forwarded-clock FT (one landing per lane, +3 max; needs FT-slot tooling that main does not have;
    kv_v39r_price_fb128_fwdft.json): +252/token, DAG -0.10 %, QCE -0.085 %; bracket +792 = -0.27 %.
  - Ledger context: Qwen 1.47 accepted + 7.12 proposed. Adding -0.84..-1.76 % stays under the 15 % target. MATERIAL vs
    the 8-region plan: if the fallback triggers, price the fwd-FT option or 2x2 blocks at S1.
(3) MODDUP on the B48 KV list (moddup/)
  - check_moddup.py (tok-qk-5 f316f3cd96) on intel2 tok-qk5/b48_vl.f:
    * pre: FAIL, 1 duplicate (ot_qkvd_kcmd_tap in kcmd_tap.sv and kv_desc.sv).
    * RM36 list: the snapshot kv_desc.sv is swapped for the kv-rtl-moddup ec613d58ef blob e9bceb27 (the only diff vs
      the snapshot is the deleted module + comment, CHECKED). Result PASS, 0 duplicates, 3 identical copies dropped
      (CHECKED).
    * ROOT-MERGE-36 had not landed at 11:40. Recheck = confirm main's kv_desc.sv blob is e9bceb27.
  - The live corrected B48 (Codex intel1 unit 1384010; it has no gate) lists kcmd_tap.sv before kv_desc.sv. Verilator
    therefore uses the 1-stage copy = the kept copy (CHECKED, hierMkArgs.f lines 235/236).
  - No KV die-slice bench is waiting on the gate. The KVL chain is still disarmed.
