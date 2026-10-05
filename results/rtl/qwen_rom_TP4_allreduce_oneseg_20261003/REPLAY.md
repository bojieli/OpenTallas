# Qwen3-8B ROM TP4: the all-reduce as one stream (replay)

The user decided on 2026-10-03 to send the whole 4,096-element all-reduce vector as one 256-word stream. This is opt-in and default-off.

## What changed
- **No existing file changed.** Every pinned program and image is byte-identical. The default generator's descriptors (`AR_WORDS=128`) equal the pinned `img_tp4/L*-d*/segments.hex`.
- **The opt-in already existed in source but had not been measured on the runtime:**
  - `rtl/rom/ot_qwen_tp_seq_w12.sv` `ENABLE_AR256` (default 0);
  - generator `QWEN_O4_AR_WORDS=256`;
  - `tools/qwen_rom_rt_token_w12.py --enable-ar256`.
- **Added:**
  - `tools/qwen_rom_ar256_stage_images.py` derives one-stream stage images from pinned ones. It merges each (128, END-only 128) descriptor pair into one count-0 (=256) descriptor and drops the lone END word. `--self-check` proves that this equals the generator's own `AR_WORDS=256` output (`generator_self_check.json`, 4 dies, with and without post-TP scales).
  - `rtl/test/tb_qwen_tp4_ar256_vl.sv` and `tools/qwen_tp4_ar256_verilator_gate.py` form the Verilator gate (`verilator_gate.json`).

## Replay
```
# 1. collective gate (seconds; Verilator 5.050)
python3 tools/qwen_tp4_ar256_verilator_gate.py --work /tmp/X/vg --result /tmp/X/vg.json
# 2. one-stream images from the pinned TP4 SW64 stage list (ot-pve1:/home/ubuntu/w12/st_tp4_sw64/stages.txt)
python3 tools/qwen_rom_ar256_stage_images.py --stages STAGES --only L0,L1 --out IMG256
# 3. runtime, one AR256-enabled build; A = pinned split images, B/C = one-stream images
A="--tp 4 --su-width 64 --lv 7 --smin 7 --smax 11 --tcut 7 --code-banks 5 --mem-extra 1 --bd 41 --xvm 1 \
   --nws 5 --tws 38 --ord 7 --coll-lat 339 --enable-ar256"
python3 tools/qwen_rom_rt_token_w12.py --workdir W --stages STAGES_L0L1 --token-oracle ORACLE_TP4 --preload VM_X $A --coll-depth 1024
python3 tools/qwen_rom_rt_token_w12.py --workdir W --stages IMG256/stages.txt ... $A --coll-depth 1024   # B
python3 tools/qwen_rom_rt_token_w12.py --workdir W --stages IMG256/stages.txt ... $A --coll-depth 256    # C
```
- On ot-pve1 the paths were:
  - source `c5ae2f69d` (git archive) at `/home/ubuntu/qar1/src`;
  - the build at `/home/ubuntu/qar1/bld`;
  - the oracle at `/home/ubuntu/w12/oracle_tp4`;
  - the preload at `/tmp/qwen-vocab-embed-token0/vm_x_fp32.hex`.
- Run scripts: `/home/ubuntu/qar1/build.sh` and `runs.sh`.
- With `ENABLE_AR256=1`, behaviour changes only for a count-0 all-reduce descriptor. That is why run A, on the pinned split images, is the same-binary baseline.

## Results
- **Verilator gate** (`verilator_gate.json`):
  - one-stream 624 cycles against split 987 per all-reduce;
  - bit-exact in both modes and identical between them;
  - faults identical;
  - DEPTH 256 needs no stalls, while 128 stalls 552 cycles.
- **Runtime** (`measured.json`, `runtime/`):
  - L0/L1 measured 4,669/4,668 split and 3,931/3,930 one-stream, at both DEPTH 1,024 and 256;
  - every X is bit-exact against the retained TP4 terminal (L0 7631b189, L1 bd905163).
- **Physical:** there is no RTL change, so this is a pathfinding screen only (`physical_screen/`, ASAP7 TT, pre-layout, synth+sta, 0.833 ns). `ot_qwen_tp_seq_w12` with `ENABLE_AR256=1` adds 22 cells (+2.1 µm²) with no new critical path. Two things fall outside this screen:
  - the sequencer misses 1.2 GHz pre-layout in both settings, which is a pre-existing issue;
  - SS/FF closure in context was not run.
