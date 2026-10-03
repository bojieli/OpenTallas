# Qwen3-8B ROM: measured p-position verify layer (step 1 gate)

Default-off, new files only. Branch claude/qwen-rom-dspark-20261003.

## Result (measured.json, run{1,2,4}.json)
| p | L0 | L1 | per extra position |
|---|---|---|---|
| 1 | 3,931 | 3,930 | - |
| 2 | 5,487 | 5,486 | +1,556 |
| 4 | 8,715 | 8,714 | +1,595 avg |

Every position's X after L0 and L1, all 4 dies, is bit-exact vs p sequential AR decodes on the ISA golden (oracle_p2/p4.json). p = 1 is the pinned AR256 program word for word and its cycles.
Model (pricing recheck): +1,497 widened AR with SU serial, +1,028 with SU overlap. The measured increment is 4-7% above the serial figure: the scheduler does not overlap SU across positions yet.

## Pieces
- tools/qwen_rom_verify_program_w12.py: p-position layer and head programs (POS_OFF bits [902:900], wide AR count in descriptor [23:20], ARGMAX_NEXT kind 3); --self-check.
- tools/qwen_rom_verify_core_emit_w12.py: VPOS core (per-position DYN tables).
- rtl/rom/ot_qwen_tp_seq_w12_vp.sv (ENABLE_ARP), rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_vp.sv, qwen_rom_rt_w12_vp.cpp, tools/qwen_rom_rt_verify_w12.py.
- tools/qwen_rom_verify_oracle_w12.py (layer golden), tools/qwen_rom_verify_head_oracle_w12.py (36-layer block AR golden + per-position argmax: [50994, 67, 2168, 16] for tokens [0, 50994, 279, 13]).

## Replay
See chain.sh (ot-epyc1tb /srv/opentallas-scratch/claude/qwen-rom-dspark). Env for generators: QWEN_O4_TP=4 QWEN_O4_GROUPS=6144 HDC_SU_WIDTH=64; oracles HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8.
Images: pinned PVE1 /home/ubuntu/w12/img_tp4 and st_tp4_sw64 (emitter-source drift is recorded, image digests verified).

## Not done
Head RTL runs (queued), SS/FF closure of the VPOS/ARP additions, SU overlap scheduling, near-HBM attention in the runtime, drafter program, accept/commit loop, end-to-end.
