# KV-HUBC-SPLIT handoff (Sonnet lane, 11-17)
Class e7483c8821: kv3_hub_C 773,818 cells > 400k cap. KV-R3 ACK 09:08 already on record.
## Findings (read only, no job launched, no branch/RTL change yet)
- RTL: physical/die_plan/qwen_kvsys/bind/bound_pv/rtl/kv3_hub_C_part.sv (6860 lines). Top-level children: u_pvfin (qkd_pv_fin_s ADD_LAT7 MUL_LAT6, ~267k cells = 54% of native, per OVERSIZE-1 attr.py), u_seq_u_core (qkd_seq_core_static_s), qkd_ahub_static_dw, qkd_kvs_ctl, qkd_kvs_attn_fl, 2x ot_qwen_tp8_pv_wide_ctl_tbf, 2x qkd_pv_rs_hd_f, plus 2587 ot_dp_dly and 350 ot_dp_st (landing/delay rings, PLACEREP=1).
- OVERSIZE-1 (lanes/handoff/OVERSIZE-1.md): ring rebind to hard ring cores gives 769k -> ~654k; still needs 3-way split (pvfin core + 2 engine halves). KV-RING-CORES-MERGED.tsv holds the ring masters.
- Fable KV types note: u_pvfin + pvfin_out core, engine core; re-capture AHUB native params (AP_OFS, FR_OFS, Z_IN_STRIDE) in the same change.
- Proposed cut: (1) u_pvfin as child type kv3_hubC_pvfin (in: p0/p1 beat/data/epoch/valid, rz, cal, start; out: out_*, fault; all ports already w_/d-prefixed pipeline nets, cut on registered ports); (2) rings -> hard ring cores per MERGED.tsv; (3) u_seq_u_core + ahub/kvs engine halves as 2 parts <=400k each. Expected parts: pvfin ~267k, rings+shell ~150k, engine ~2x170k (ESTIMATE, not synthesized).
## Plan event
Rides the NEXT KV event (HG7 / D18+), not HG6: HG6 v5 gate is unresolved (bind FAIL 31 on D18). Needs hub_C plan row + part_bound rows.
## Next
Branch claude/kv-hubc-split-1117 on ot-lane-clone; emit split RTL + test; synth part sizes on epyc10 via ot-run; READY; pilot after apply; export AGIdock+rtx-pro.
