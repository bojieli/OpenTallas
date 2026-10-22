#!/bin/bash
# KV-FRAMEPINS 10-20: die-path bench of the OBSX observations (dcal adm_done/cal_ready/running/layer, d2d recovery_cycles
# -> relayed kv_oneway buses -> HOST window) under the fleet's pinned Verilator 5.050.
#   tools/qwen_kv_die/obsx_path_bench.sh MUT OUTDIR   MUT 0 = PASS; 1..4 = window mutants (OBS_MUT); 5/6 = path mutants
#   shape (NB / NF / EXT_LSB) is read from rtl/qwen_sys/kv_host_obs_20261019/host_obs_map_x.json (the generated OBSX map)
set -u
M=${1:-0}; O=${2:-/tmp/obsx_path_bench}; mkdir -p "$O/obj_m$M"
R=$(cd "$(dirname "$0")/../.." && pwd)
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin"; do [ -d "$_d" ] && export PATH="$_d:$PATH"; done
verilator --version
SH=$(python3 -c "
import json;d=json.load(open('$R/rtl/qwen_sys/kv_host_obs_20261019/host_obs_map_x.json'))
e=[o for o in d['obs'] if o.get('die_source')]
assert [o['name'] for o in e]==['obs_dcal_adm_done','obs_dcal_cal_ready','obs_dcal_running','obs_dcal_layer','obs_d2d_recovery_cycles'], e
assert all(b['lsb']==a['lsb']+a['width'] for a,b in zip(e,e[1:])) and e[-1]['lsb']+e[-1]['width']==d['NB']
print(f\"-DOBS_NB={d['NB']} -DOBS_NF={d['NF']} -DEXT_LSB={e[0]['lsb']}\")") || exit 2
OM=0; PM=0; case $M in 1|2|3|4) OM=$M;; 5|6) PM=$M;; esac
verilator --binary --timing -Wno-fatal -Wno-WIDTHTRUNC -Wno-WIDTHEXPAND $SH -DOBS_MUT=$OM -DPATH_MUT=$PM ${OBSX_DEFS:-} \
  --top-module tb_kv_obsx_path -Mdir "$O/obj_m$M" "$R/rtl/qwen_sys/kv_host_obs_20261019/qkd_host_obs_csr.sv" \
  "$R/rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv" "$R/rtl/test/qwen_host/tb_kv_obsx_path.sv" \
  > "$O/build_m$M.log" 2>&1 || { tail -30 "$O/build_m$M.log"; exit 2; }
"$O/obj_m$M/Vtb_kv_obsx_path" > "$O/bench_m$M.log" 2>&1
tail -12 "$O/bench_m$M.log"
grep -q "TB_KV_OBSX_PATH PASS" "$O/bench_m$M.log"
