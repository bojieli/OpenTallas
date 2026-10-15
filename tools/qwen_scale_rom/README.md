# Actual TP8 scale-ROM masks

`build.py` imports the released, checkpoint-pinned scale payloads without quantization or floating-point computation. It checks the source image hashes, TP/rank/layer identity, checkpoint lock and revision, exact 256-bit word format, and emitted program addresses. The resident image holds 36 × 816 layer words followed by 1,200 head words: 30,576 words. Stage-local padding is preserved. The four head chunks retain local scale bases 0, 384, 768 and 1,152.

Every one of the 24 physical result-port groups holds the same dense image for its die rank. Its four columns contain four banks each. The real native macro IDs are `qslab_b{band}_h{half}_g{group}_c{column}_b{bank}`. The builder emits all 384 named masks per rank; identical replica payloads share an inode on the build host. It independently decodes every physical mask bitline and verifies all 266 bits against the exact source word, including the ten zero spare bits. All eight rank directories are distinct immutable ROM cohorts. No layer-by-layer ROM swapping is needed.

The actual command producer must add `816 × layer` to a layer-local `me_wcs`, or 29,376 for the head. WSRC=1 operations retain their original addresses. This is a static compiler/RTL integration requirement, not permission for a runtime memory adapter to change addresses. The manifest includes every actual emitted program SHA, decoded operation, local address bound, active physical slot, resident stage base and mask hash.

Run on a staged fleet source tree under `ot-run`:

```bash
python3 tools/qwen_scale_rom/build.py --banks /absolute/released/banks --out /absolute/fresh/masks
bash tools/qwen_scale_rom/run_rtl.sh /absolute/fresh/rtl /absolute/fresh/masks 0
python3 tools/qwen_scale_rom/run_remaining.py --binary /absolute/fresh/rtl/obj/Vtb_scale_masks --images /absolute/fresh/masks --out /absolute/fresh/remaining
```

The full native bank bench instantiates all 384 actual ROM macros, streams every resident word through all 24 native column groups at one word/cycle, and checks the actual registered seven-edge group response. Expected words observe results only. The same binary checks all eight released rank cohorts. A one-bit mutation in one actual instance mask must cause a numerical failure; removing one instance mask must fail initialization. Empty/default ROM contents cannot qualify.

These checks establish actual mapped scale storage, payload identity, banking, format and deterministic service. The complete native tree/controller command must still produce these addresses, and the actual result-half postmultiply must consume the returned words on its scheduled edge. Full layer/token arithmetic, physical TT/FF/DRC, clock phases and token cost remain separate requirements. The C++ `RomVmAdapter` remains diagnostic until the complete native memory and compute composition replaces it.
