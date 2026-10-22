# Opt-in QKH safe32 binding and profiles

`OT_KV_QKH_SAFE32=1` selects the new source modules only with the static ASTK heads and `OT_KV_KPV_LK=1`. The generated source is `rtl/qwen_sys/split_20261014/ot_qkh_head_native_r4_s_lk_nc32c.sv`; its two head modules preserve every connection and clock home and replace only the lane8 and KPV-lockstep ktree child types. Regenerate with `python3 tools/qwen_kv_die/head_qkh_safe32_rtl.py`; add `--check` to verify the snapshot. The original generator and both existing snapshots are byte-identical to the pre-patch source.

`kv_expand` selects the exact successor RTL/view maps, and requires both complete parameter profiles plus matching frozen native receipts BEFORE writing expanded die artifacts, even with `OT_KV_PARAM_DIAG=1`. Lane8 profile: ADD_LAT=7, LTW=12. Ktree profile: ADD_LAT=7, MUL_LAT=6, SCALE=0x3DB504F3, MUT=0. Old modules/views and diagnostic autoprofiles cannot qualify these successors.

After both actual views are CLOSED and their native audits are PROVEN, produce profiles using the canonical receipt producer:

```sh
python3 tools/qwen_kv_die/kv_qkh_safe32.py --root /absolute/pinned/source --audits /actual/audits --base /existing/profiles.json --out /absolute/pinned/source/results/rtl/qkh_qualified_NEW
```

The output must be a fresh source-root directory so frozen receipts remain immutable. Missing/wrong profiles or source/view hashes refuse; conflicting base entries refuse rather than silently replacing them. There is no manufactured positive native receipt in this patch or its tests.

Enablement is still BLOCKED on the two actual CLOSED views, PROVEN native receipts, and a qualified head placement plan for the 172.8um lane8 and 172.8x129.6um ktree. The current old head placement plan is not relabelled as fitting: the existing full-size containment/overlap guards continue to refuse a larger leaf that does not fit. The accepted slot growth must be carried into the die lead's actual plan before selection. The source-pinned static-head unused-output role must also be requalified explicitly for the new successor master; no existing role waiver is broadened by this patch. The existing static-source refusal in legacy kv_expand is preserved; this patch does not license a static graph to inherit a legacy frame.

Validation: five pure Python source-selection/default-preservation/causal-refusal checks PASS. No RTL simulation, physical closure, or positive native parameter qualification is claimed by those tests. The arithmetic modules retain their separately pinned R9 real-RTL PASS/mutant FAIL evidence; no arithmetic source changed here.
