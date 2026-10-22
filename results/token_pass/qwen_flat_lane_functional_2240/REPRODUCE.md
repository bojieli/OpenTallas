This is the exact current flat lane 0 component proof. It does not qualify the eight-lane parent, physical clocks, native mapping, or a token programme. The older STG4 `SU_LT=1` receipts remain separate.

The admitted source tree was created from QK commit `1f7a4aedb`, taking the six HDC files and macro folder listed by `identity.json`, plus `tools/hdc_golden.py` and `results/arch/qwen_flat_ml1_2000/MODEL.json`. The exact bench and runner are commit `01a62111b`. Copy the selected MODEL file to `src/MODEL.json`; the runner checks every selected source hash and exact parameter value before building. Functional simulation uses the real macro `.v`; physical source identity retains the corresponding `_bb.v` hash.

The original immutable source and both binaries remain on gold2 at `/srv/opentallas-scratch/claude/codex-qwen-flat-functional-2240/src` and `../run_r1/obj_m{0,1}`. The original normal admission command was:

```sh
ot-run --mem 12 --threads 2 --dir /srv/opentallas-scratch/claude/codex-qwen-flat-functional-2240/src -- python3 tools/qwen_flat_lane_2235/run.py
```

Preserve the original result directory. A reproduction needs a fresh lane with the same source layout because the runner refuses to overwrite `run_r1`. The positive and existing `OT_TLS_MUT` runs are sequential within the same admitted job. All command arguments, source/golden/image/binary hashes, NBA guards, build logs and numerical output are retained here.

The bench holds reset for eight edges, allows 140 edges before each class's first input, and drains for 150 edges. Its populated-history reset uses the same eight-edge assertion and 140-edge guard. It does not prove a shorter production startup guard. Once issued, the measured source-relative retirement deltas are 19, 68, 47, 56 and 99 for NONE, EXP, RECIP, RSQRT and SIGM; VM writes occur one edge later. These are lane pin observations, not whole-programme dispatch or route dates.
