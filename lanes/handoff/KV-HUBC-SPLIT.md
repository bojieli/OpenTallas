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

## UPDATE 11-17 (after COORD go-ahead): prior art + blockers
- Clone: epyc10 /srv/opentallas-scratch2/claude/kv-hubc-split/wt (ot-lane-clone, main 5a5a7f84f4, cone tools,rtl,physical/die_plan/qwen_kvsys). Base plan = D16 tree epyc10 kw45/src_kv_pin_eb1e73448bd0_hg5_340b90be_d16 (hub_C: soft 2160x1676, hard_cores ahub + kvs_ctl, pvfin/seq__u_core/pvN,pvS/ctl still soft in contents).
- PRIOR ART (reuse, do not rewrite): (a) pvfin pair = hard core qkd_pv_fin_s8 (NL=8, IN_STAGE=1, 207.36x194.4 um, ref_tile qkd_pv_fin_s8_pin, wrapper qkd_pv_fin_s2x8, 2 per hub_C; KV-PVFIN-1 / KV-101-PVFIN.md, form code kv101_rst2_form.py on branch claude/kv-101-pvfin-1113 @6fa4a6c454; s8 routed signoff NOT reached: s8f TT+138.93/FF-2.75, 21 hold, replaced by s8pin2, routed EQ PENDING). (b) whole-split event branch claude/kv-101-split-1113 (tools/die_plan/type_split.py, 54 types, NOT merged, bind at 14 errors, V-word pads open). (c) ring rebind tool KV-HGSPLIT-1115-hgsplit.py: fails on hub_C (KeyError clock.landing_contract; hub types carry only tap clocks), so hub_C needs the 6 hub_C ring masters (kv_cland_w549/523/300/294/292_ew, w259_ns x8, PLACEREP=1) wired by a hub-specific row writer.
- SIZE ARITHMETIC (OVERSIZE-1 numbers, not re-synthesized): 773.8k -> rings ~654k -> minus u_pvfin 267k = ~387k, only 3% under the cap and before pin buffers; so seq__u_core (qkd_seq_core_static_s) or the pv ctl pair must also become a core, else part is NEAR/OVER.
- NOT DONE: no synth (no yosys on PATH on epyc10; kit_gen_lint frontend path must be used), no RTL/plan branch, no test, no gate, no READY. No job running.
