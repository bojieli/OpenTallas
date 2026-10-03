#!/usr/bin/env bash
# Fresh pinned source snapshot/worktree only. No wall/process caps; host admission.
set -euo pipefail
TASK_ROOT=$1
TASK_SRC=$TASK_ROOT/wt
TASK_OUT=$TASK_ROOT/runs
mkdir -p "$TASK_OUT"
cd "$TASK_SRC"
test -z "$(git status --porcelain)"
run_case() {
  local name=$1 top=$2 source=$3 clk=$4 sdc=$5
  local result=$TASK_OUT/$name
  mkdir "$result"
  set +e
  python3 tools/run_abi3_physical_persistent.py --persistent-workdir "$result/work" --launch-receipt "$result/launch.json" \
    --view asap7 --top "$top" --source "$source" --param W=512 --param ENABLE=1 \
    --clock-port "$clk" --clock-period-ns 0.833333 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
    --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages synth,pnr \
    --core-utilization 30 --place-density 0.5 --hold-margin-ns 0.01 \
    --orfs-var ADDER_MAP_FILE= --orfs-var NUM_CORES=16 --orfs-var "SDC_FILE=/src/$sdc" \
    --nickname-tag "rom_clock_$name" --purpose signoff_target --output "$result/physical.json" > "$result/driver.log" 2>&1
  local rc=$?
  printf '%s\n' "$rc" > "$result/driver.exit"
  if compgen -G "$result/work/orfs/results/asap7/*/base/6_final.odb" > /dev/null; then
    python3 tools/w18/corner_sta.py --orfs-dir "$result/work/orfs" --output "$result/corner_sta.json" > "$result/corner.log" 2>&1
    printf '%s\n' "$?" > "$result/corner.exit"
  fi
  set -e
}
run_case meso_w512_d4 ot_meso_fifo rtl/common/ot_meso_fifo.sv wclk physical/rom_clock/meso_w512_d4.sdc
run_case fwd_w512 ot_fwd_link_stage rtl/common/ot_fwd_link_stage.sv fclk_i physical/rom_clock/fwd_w512.sdc
printf '0\n' > "$TASK_ROOT/campaign.exit"
