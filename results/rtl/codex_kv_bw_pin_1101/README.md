# Opt-in CTL boot-valid pin boundary

`qkd_kv_es_fan_root2_b_nc32_bpin` is an unused opt-in variant. The canonical golden stays byte-identical. In its S32 path it factors the registered boot-valid acceptance product: existing `bw_p[0]` is the sole raw-valid capture, the same 19 registers capture the independent acceptance guard, and their same-edge Q values form the original selector. Every bit of the full boot word keeps its original cycle. Added mission/boot cycles = 0. No new external port, reset rule or arithmetic change.

The actual full fan-root lockstep passed six MUT/RCOPIES/PH1C profiles for 4,096 cycles, checking both 784-bit outputs and fault. All four applicable guard-bypass controls were caught (MUT1 already intentionally bypasses the guard). RTL synth input-fanout check shows the original raw valid drives logic plus one pin FF, while the variant drives only the existing FF D.

This is functional and structural evidence, not timing/SIGNED evidence. Integration into the current CTL profile remains opt-in and requires its ordinary exactness, face, placement/timing and sign-off gates. Run the portable source-extracted coupon with `physical/die_plan/qwen_kvsys/cores/harden/tests/bw_pin/run.sh <scratch-output>` via ot-run.
