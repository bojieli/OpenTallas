#!/bin/bash
# layer_rom_bench.sh OUT [MUT=0] [NTOK=2]: the compiler-constant layer programme (qkd_static_kv_layer_programme_img)
# vs the boot-loaded module + the KV link calendar sequencer (tb_layer_programme_rom).  Recompiles the link calendar and
# the layer roots and refuses a committed image that differs.  One LAYER_ROM line; exit 0 only on PASS.  Repo root.
set -u
O=$1; M=${2:-0}; NT=${3:-2}
mkdir -p "$O"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
python3 tools/qwen_split/d2d_link_calendar.py --out "$O/cal" --txl 6 --phy 5 --profile program --txd-c 1,1,1,2 --txd-k 1,2,1,1 \
  --host-stages 0 --link-handoff results/arch/qwen_split_compute_1014/res_train_decision_1015/decision.json --pinreg \
  > "$O/calendar.log" 2>&1 || { echo "LAYER_ROM FAIL calendar compile"; exit 1; }
python3 tools/qwen_split/d2d_cal_seq_image.py "$O/cal" "$O/cal/img.svh" && cmp -s "$O/cal/img.svh" rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh \
  || { echo "LAYER_ROM FAIL committed link sequencer image differs from the compiler"; exit 1; }
rm -rf "$O/lp"
python3 tools/qwen_static_kv/layer_roots_from_link.py "$O/cal" "$O/lp" > "$O/roots.log" 2>&1 || { echo "LAYER_ROM FAIL roots compile"; tail -2 "$O/roots.log"; exit 1; }
cmp -s "$O/lp/layer_programme_image.svh" rtl/qwen_sys/static_kv_20261014/layer_programme_image.svh \
  || { echo "LAYER_ROM FAIL committed layer image differs from the compiler"; exit 1; }
S=rtl/qwen_sys/static_kv_20261014; D=rtl/qwen_sys/d2d_static_20261015
$VL --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 4 \
  -I$S -I$D --top-module tb_layer_programme_rom -GMUT=$M -GNTOK=$NT -GGOLD="\"$O/lp\"" --Mdir "$O/obj_m$M" \
  $S/qkd_static_kv_layer_programme.sv $S/qkd_static_kv_layer_programme_rom.sv $D/qkd_d2d_cal_seq_pin.sv $D/ot_qwen_d2d_cal_seq.sv \
  $D/ot_qwen_d2d_cal_seq_dies.sv rtl/test/qwen_static_kv/tb_layer_programme_rom.sv > "$O/build_m$M.log" 2>&1 \
  || { echo "LAYER_ROM FAIL build"; grep -m5 '%Error' "$O/build_m$M.log"; exit 1; }
"$O/obj_m$M/Vtb_layer_programme_rom" > "$O/run_m$M.log" 2>&1
grep -E '^ERR' "$O/run_m$M.log" | head -4
line=$(grep -E '^LAYER_ROM ' "$O/run_m$M.log" | tail -1)
echo "${line:-LAYER_ROM FAIL no verdict line}"
case "$line" in "LAYER_ROM PASS"*) exit 0;; *) exit 1;; esac
