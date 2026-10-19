#!/usr/bin/env bash
# HBMA-SVC 2026-10-17: ot_hbm_svc_stack_fault bench.  run_stack_fault_bench.sh OUT MUT [OWN_W] [NPC NG ND]
# HBM-KITS-B/SFAULT 2026-10-18: Verilator 5.050 (the closure daemon's version; SIM=iverilog keeps the old path) and the
# d4g binding NPC 16 / NG 4 / ND 8 (defaults 32 / 8 / 8 = the per-stack module).
set -u
cd "$(dirname "$0")/../../../.."
out=$(realpath -m "${1:?out}"); mut=${2:-0}; own=${3:-6}; npc=${4:-32}; ng=${5:-8}; nd=${6:-8}; mkdir -p "$out"
n=rtl/hbm_accel/loader/service_native
src=("$n/tb_hbm_svc_stack_fault.sv" "$n/ot_hbm_svc_stack_fault.sv" "$n/ot_hbm_svc_async_fifo.sv" rtl/lib/ot_reset_sync.sv)
sha256sum "${src[@]}" > "$out/source.sha256"
if [[ ${SIM:-verilator} == iverilog ]]; then
 iverilog -g2012 -s tb_hbm_svc_stack_fault -P tb_hbm_svc_stack_fault.MUT=$mut -P tb_hbm_svc_stack_fault.OWN_W=$own \
  -P tb_hbm_svc_stack_fault.NPC=$npc -P tb_hbm_svc_stack_fault.NG=$ng -P tb_hbm_svc_stack_fault.ND=$nd \
  -o "$out/sim.vvp" "${src[@]}" > "$out/build.log" 2>&1 || { cat "$out/build.log"; echo "BUILD_FAIL"; exit 2; }
 vvp -n "$out/sim.vvp" > "$out/sim.log" 2>&1
else
 vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
 [[ -x $vl ]] || { echo "BUILD_FAIL verilator 5.050 not found at $vl"; exit 2; }
 "$vl" --version | tee "$out/verilator.version"
 grep -q '^Verilator 5.050' "$out/verilator.version" || { echo "BUILD_FAIL not Verilator 5.050"; exit 2; }
 "$vl" --binary --timing -j "${JOBS:-2}" -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hbm_svc_stack_fault \
  -GMUT=$mut -GOWN_W=$own -GNPC=$npc -GNG=$ng -GND=$nd --Mdir "$out/obj" -o sim "${src[@]}" > "$out/build.log" 2>&1 \
  || { tail -30 "$out/build.log"; echo "BUILD_FAIL"; exit 2; }
 "$out/obj/sim" > "$out/sim.log" 2>&1
 rm -rf "$out/obj"
fi
grep -E "^(PASS|FAIL)|source|legal" "$out/sim.log"
grep -q "^PASS tb_hbm_svc_stack_fault" "$out/sim.log"
