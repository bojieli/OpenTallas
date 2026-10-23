#!/bin/bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
out=$(realpath -m "${1:?OUT}");c=${2:-0};cm=${3:-0};im=${4:-0}
mkdir -p "$out"
cd "$repo"
python3 - <<'CHECK'
import hashlib,json
from pathlib import Path
p=Path('results/rtl/hbm_host_su_sparse_1022/prepared_identity.json')
for n,r in json.load(open(p))['sources'].items():
 assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256'],n
CHECK
cp results/rtl/hbm_host_su_sparse_1022/image.mem results/rtl/hbm_host_su_sparse_1022/quarter.mem "$out/"
iverilog -g2012 -s tb_hostprog -P tb_hostprog.CASE="$c" -P tb_hostprog.CMUT="$cm" -P tb_hostprog.IMUT="$im" -o "$out/sim.vvp" \
 results/rtl/hbm_host_su_sparse_1022/prepared_tb.sv \
 rtl/hbm_accel/host_static_20261015/ot_hbm_host_static_ingress_obs.sv \
 rtl/hbm_accel/host_static_20261015/ot_hbm_static_cfg_collar.sv \
 rtl/hbm_accel/generic/adapters/static_su/programme/ot_hbm_su_programme_root_h5.sv \
 rtl/lib/ot_rst_relay.sv \
 rtl/hbm_accel/generic/adapters/static_su/programme/ot_hbm_su_programme_pgcol.sv \
 rtl/hbm_accel/generic/adapters/static_su/programme/ot_hbm_su_programme.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$out/build.log" 2>&1
cd "$out"
vvp -n sim.vvp
