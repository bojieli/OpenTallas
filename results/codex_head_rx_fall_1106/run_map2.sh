#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/codex-head-rx-fall-1106
mkdir map2
cp wt/rtl/dsrom_sys/s81_head/ot_s81hd_pma_rx_capture.sv map2/capture.sv
cp rx_map.sv map2/
docker run --rm --memory=4g --cpus=2 -v "$PWD/map2:/work" -w /work openroad/orfs:asap7lock bash -lc '
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 set -euo pipefail
 f=(/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*SEQ*RVT*TT*.lib*)
 test "${#f[@]}" = 1
 case "${f[0]}" in *.gz) gzip -cd "${f[0]}" > seq_tt.lib;; *) cp "${f[0]}" seq_tt.lib;; esac
 for mode in 0 1; do
  yosys -Q -T -p "read_verilog -sv capture.sv rx_map.sv; chparam -set MODE $mode rx_map; hierarchy -top rx_map; flatten; synth -top rx_map -noabc; dfflibmap -liberty seq_tt.lib; stat; write_json map$mode.json" > map$mode.log 2>&1
 done
 chmod -R a+rX /work
'
