#!/bin/bash
set -eu
W=$(realpath -m "$1");mkdir -p "$W"
F=($(python3 - <<'PY'
import re
print(' '.join(re.search(r'F=\((.*?)\)\n',open('tools/s81_dv/eng_rr/run_eng_rr.sh').read(),re.S).group(1).split()))
PY
))
F=("${F[@]:0:${#F[@]}-1}" tools/s81_dv/eng_rr/inactive/ot_ra640_inactive_ref.sv tools/s81_dv/eng_rr/inactive/tb_ra640_inactive_miter.sv "${F[@]: -1}")
python3 tools/s81_dv/eng_rr/prep_rom.py "$W/rom" > "$W/prep.log" 2>&1
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --binary --timing -j "${J:-8}" -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE -CFLAGS -O1 +define+OT_S81ENG_RR_N32 +define+OT_S81ENG_RR_MUL_N32 +define+OT_ENGRAM_CRCMAT --top-module tb_dsdv_eng_rr "${F[@]}" --Mdir "$W/obj" -o sim > "$W/build.log" 2>&1
for seed in 1 2 3;do
 "$W/obj/sim" +OT_ROM_DIR="$W/rom" +SEED="$seed" +NW=3 > "$W/seed$seed.log" 2>&1
 python3 tools/s81_dv/eng_rr/check_eng_rr.py "$W/seed$seed.log" "$PWD" >> "$W/seed$seed.log" 2>&1
 grep 'RA640_INACTIVE_MITER\|TB_ENG_RR PASS\|ENG_RR_PY' "$W/seed$seed.log" | tail -3
done
set +e
"$W/obj/sim" +OT_ROM_DIR="$W/rom" +LOOKUP_MUT=1 +NW=3 > "$W/mutant.log" 2>&1
rc=$?
set -e
if [ "$rc" = 0 ] || ! grep -q 'RA640_INACTIVE_MITER mismatch' "$W/mutant.log";then echo 'INACTIVE_MUTANT NOT CAUGHT';exit 1;fi
echo 'INACTIVE_MUTANT CAUGHT'
