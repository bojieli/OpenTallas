# QW-ROMCAP: exact Qwen ROM capacity, all stages, pinned static layout (10-20, COORD 21:13)

`tools/qwen_romcap/exact_capacity.py` runs the REAL allocator (`hdc_qwen_layer0_rom_w12.matrix_plan`, compact banks = the
released layout; `PL.matrix` for lm_head) at TP8 / G3072 on the exact per-rank shard shapes, against the pinned resident
slots (`qwen_static_schedule/rom_relocation.stage_bases`) and the physical banks (RTL leaf + image builders + the die's
ROM_BIND audit). Shape-only allocator, so exact for all 8 ranks x 37 stages (36 layers + head).

Fleet run: ot-run unit `oth-ubuntu-3866224-1792556923` on ot-epyc6, die = dv2f20g5r2b `out/case/rom_bind.json`
(48 clusters / 768 tiles / 7,680 macros, 5 banks x 2 cols x 4096 rows per tile, audit PASS).

| store | resident (pinned) | physical | fill |
|---|---|---|---|
| code ROM per tile | 36 x 512 + 1,600 = 20,032 rows | 5 x 4,096 = 20,480 | **97.81 %** (banks 0-3 100 %, bank 4 89.1 %) |
| scale ROM per port | 36 x 816 + 1,200 = 30,576 | 16 x 4,096 = 65,536 | 46.66 % |
| every stage vs its pinned slot | layer 512/816, head 1,600/1,200 | | 100.0 % (exact, no overlap) |

VERDICT PASS: worst stage = 100 % of its slot (slots sized exactly to the allocation), worst physical = code ROM 97.81 %
(448 rows free = 0.87 layer slot). Layer layout: qkv 0-64, o 64-112, gu 112-368, down 368-512 (scale 0-48-336-528-816).
Not covered: weight bytes (qwen_code_rom / qwen_scale_rom proofs), programme/table ROM (QW-PROGSTORE packer 3,816/4,096 rows = 93.2 %),
layer constant ROM (RoPE/norm CROM) placement.
