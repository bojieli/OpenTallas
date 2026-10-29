#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
w=/srv/opentallas-scratch2/claude/wt/codex-qc-a0-0251
r=/srv/opentallas-scratch2/claude/codex-qc-a0-0251/icg_full
mapfile -t src < "$r/files.txt"
src+=("$r/asap7_functional.v")
sudo docker run --rm -v "$r":/out openroad/orfs:asap7lock bash -lc 'set -e; files=$(find /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -maxdepth 1 -name "asap7sc7p5t_*RVT_TT_*" -not -name "*FAKE*" | sort | tr "\n" " "); yosys -p "read_liberty -ignore_miss_func -ignore_miss_dir $files; write_verilog -noattr /out/asap7_functional.v"; chown 1000:1000 /out/asap7_functional.v' > "$r/cell_models.log" 2>&1
python3 "$r/patch_asr.py"
python3 "$w/tools/qwen_romleaf/a0core/equiv/gen_rom.py" "$r/rom" 48
verilator --binary --timing -j 16 -O2 -Wno-fatal -Wno-PINMISSING -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN +define+TB_NL +define+OT_ROM_CONST0_KV --top-module tb_a0_icg -Mdir "$r/obj" "$r/tb_a0_icg_current.sv" "${src[@]}" > "$r/build.log" 2>&1
"$r/obj/Vtb_a0_icg" +OT_ROM_DIR="$r/rom" > "$r/positive.log" 2>&1
grep A0ICG_PASS "$r/positive.log"
"$r/obj/Vtb_a0_icg" +OT_ROM_DIR="$r/rom" +ICG_MUT=1 > "$r/mutant.log" 2>&1
grep A0ICG_FAIL "$r/mutant.log"
