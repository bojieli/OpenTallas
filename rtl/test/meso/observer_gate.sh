#!/bin/bash
set -eu
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
observer_dir=$(cd "$(dirname "$0")" && pwd)
observer_repo=$(cd "$observer_dir/../../.." && pwd)
python3 "$observer_dir/observer_gate.py" "$observer_repo" .
for variant in observer_cut observer_ready_mutant observer_fault_mutant; do
 verilator --binary --timing -j 4 -Wno-fatal --top-module tb_observer "$variant.sv" --Mdir "obj_$variant" > "$variant.build.log" 2>&1
 if "obj_$variant/Vtb_observer" > "$variant.run.log" 2>&1;then
  cat "$variant.run.log"
  if [ "$variant" != observer_cut ]; then echo MUTANT_SURVIVED;exit 1;fi
 else
  cat "$variant.run.log"
  if [ "$variant" = observer_cut ];then exit 1;fi
  echo "$variant CAUGHT"
 fi
done
