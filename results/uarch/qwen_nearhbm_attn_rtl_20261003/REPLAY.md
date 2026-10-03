# Near-HBM attention for the Qwen3-8B ROM die (TP4): exact RTL, replay

This directory holds the evidence for the near-HBM attention unit. The design is NEW and default-off. No pinned module is edited and nothing in the shipped core instantiates it. It was sized by the model-only pricing in `inputs/` (`near_hbm_attention_pricing.md`, generator `price_near_hbm_attention.py`).

| step | record | verdict |
|---|---|---|
| 1. partitioned scheme == golden (Python) | `partition_exactness.json` | PASS, 400 cases (ctx 1..8192, 6 stimulus kinds); negative controls are caught |
| exact BF16 x E4M3 product unit | `prod_exhaustive.json` | PASS on all 2^24 operand pairs |
| 3. RTL 4 stacks + hub vs golden, head_dim 128 | `gate_hd128_r1_dpi.json` | PASS, 20/20 cases bit-exact (1,024 outputs each), including 5 at ctx 8191/8192 |
| real arithmetic RTL == host-float stand-ins | `real_vs_dpi_hd16.json` | PASS: identical outputs and cycle marks |
| 4. SS 1.2 GHz pre-layout unit screens | `ss_screens.json` | see the table below |

## The scheme

The golden is `tools/hdc_golden.py` `decode_token_tp` / `attend` at G = 6144, where `attn_splits` = (128, 512). The scale is `F(1/sqrt(128))` = 0x3DB504F3. It is not 0.25: the golden's "0.25: exact" comment holds only for head_dim 16.

Position t lives in stack (t mod 512) div 128. Each layer runs these passes:

- **K pass.** Scores are formed and stored, and each stack keeps a local max.
- **Max exchange.** The hub takes the max over the four stacks.
- **Exp pass.** It computes e = exp(s - M). bf16(e) is stored. The 8-position Z chunks are summed sequentially in an 8-cycle adder loop, with one chain per round, so each 64-position tile is transposed in time. Z tree levels 1-4 run per 128-position block.
- **V pass.** Each residue group of 8 maps to the 8 slots of a lane-adder loop: chunk c is the sequential sum add(acc, V x bf16(e)) over t = c mod 512. The stack's 128 residues pass in order through one 512-wide streaming pairwise tree (P.V levels 1-7).
- **Hub.** It computes P.V levels 8-9 and Z levels 5-10, then the golden reciprocal and the multiply.

## Replay

```
# 1. partition proof (about 20 min)
python3 tools/qwen_nearhbm_attn_ref.py prove --cases 400 --out partition_exactness.json
# product unit, exhaustive
verilator --cc --exe --build --top-module ot_qwen_nearhbm_prod rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv \
  rtl/test/nearhbm/tb_qwen_nearhbm_prod.cpp -o Vprod && ./obj_dir/Vprod
# 3. vectors (short paths), bench builds (Verilator 5.050), gate
for spec in 1:normal 2:tiny 7:peaky 9:wide 100:mixed 128:normal 129:flat 511:peaky 512:wide 513:tiny 1000:normal \
            2048:mixed 3001:peaky 4097:flat 6143:wide 8191:tiny 8192:normal 8192:peaky 8192:mixed 8192:wide; do
  c=${spec%%:*}; k=${spec##*:}
  python3 tools/qwen_nearhbm_attn_ref.py vectors --ctx $c --seed $((c*7+${#k})) --kind $k --out /tmp/nhb/v/${c}_$k
done
rtl/test/nearhbm/build_nearhbm_tb.sh /tmp/nhb/d128r1 128 1 dpi        # R = row engines per stack
python3 tools/qwen_nearhbm_attn_gate.py --bin /tmp/nhb/d128r1 --hd 128 --r 1 --vectors /tmp/nhb/v --out gate_hd128_r1_dpi.json
# real units vs stand-ins (head_dim 16 debug vehicle: NHB_HD=16 vectors)
NHB_HD=16 python3 tools/qwen_nearhbm_attn_ref.py vectors --ctx 3000 --seed 3000 --out /tmp/nhb/v16_3000
rtl/test/nearhbm/build_nearhbm_tb.sh /tmp/nhb/r16r1 16 1 real; rtl/test/nearhbm/build_nearhbm_tb.sh /tmp/nhb/d16r1 16 1 dpi
```

The head_dim-128 bench uses host-float stand-ins (`rtl/test/nearhbm/sim_nhb_fp_lat_dpi.sv` and the repo's `sim_hdc_v41x_fastfp_dpi.sv`) for the binary32 adder and multiplier. The real units' Kogge-Stone networks make Verilator emit about 1 MB of C++ per instance, and this bench has about 13,000 instances. The precedent is `rtl/test/sim_hdc_v41x_fastfp_dpi.sv`.

The exact product unit and every composition, control path and order run as RTL. At head_dim 16 the real-unit bench and the stand-in bench give identical results.

## Unit closure at SS 1.2 GHz (pre-layout screen, 60 ps; `ss_screens.json`)

| unit | SS pre-layout fmax | 1.2 GHz | cell area (um2) |
|---|---|---|---|
| ot_qwen_nearhbm_prod (exact product, LAT 4) | 1,388 MHz | closes | 90 |
| ot_hdc_fp32_add_lat7 | 1,648 MHz | closes | 555 |
| ot_hdc_fp32_mul_lat6 | 1,450 MHz | closes | 891 |
| ot_hdc_fp32_mul_lat5 | 1,065 MHz | fails | 895 |
| ot_mac_bf16_fp32_pipe (RS 0 / RS 1) | 593 / 793 MHz | fails, so not used | 432 / 486 |
| ot_hdc_exp_q (LAT-3 fast FP inside) | 644 MHz | fails | 6,678 |
| ot_hdc_recip_q (LAT-3 fast FP inside) | 712 MHz | fails | 4,901 |

exp and reciprocal need their binary32 steps on the closing units: ADD LAT 7 and MUL LAT 6.

- exp depth: 49 to 102 (+53 cycles).
- reciprocal depth: 28 to 58 (+30 cycles).

The reciprocal is off the critical path, because Z is complete before the V pass ends. Each new depth needs the 2^32 equivalence proof before adoption.

The full P&R of the row engine and the hub is a separate launch. Its manifests and verdicts are recorded in `pnr/`.
