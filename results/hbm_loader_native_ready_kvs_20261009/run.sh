#!/usr/bin/env bash
set -euo pipefail
cd /srv/opentallas-data/codex/loader-read/95294ff25
mkdir out/ready-regress
base="merged-src/ot_hbm_svc_core.sv src/ot_hbm_accel_cdc_fifo.sv src/ot_hbm_write_source_pc.sv src/ot_hbm_kport_map.sv src/ot_hdc_v41x_idx_hbm.sv readyfix-src/ot_hbm_loader_pc_service_lease.sv src/ot_hbm_loader_service_boundary.sv merged-src/ot_hbm_svc_core_native.sv merged-src/ot_hbm_index_lines.sv"
for enabled in 0 1; do
iverilog -g2012 -s tb_loader_service_kvs -Ptb_loader_service_kvs.NATIVE=$enabled -o out/ready-regress/kvs$enabled.vvp $base concurrent-src/tb_loader_service_kvs.sv
vvp out/ready-regress/kvs$enabled.vvp +nsec=1024 +reps=1 > out/ready-regress/kvs$enabled.log
rg 'KVS_BENCH errors=0 PASS' out/ready-regress/kvs$enabled.log
done
iverilog -g2012 -s tb_loader_service_kvs -Ptb_loader_service_kvs.NATIVE=1 -Ptb_loader_service_kvs.CONCURRENT=1 -o out/ready-regress/concurrent.vvp $base concurrent-src/tb_loader_service_kvs.sv
vvp out/ready-regress/concurrent.vvp +nsec=1024 +reps=1 > out/ready-regress/concurrent.log
rg 'KVS_BENCH errors=0 PASS' out/ready-regress/concurrent.log
python3 - <<'PY'
from pathlib import Path
s=Path('readyfix-src/ot_hbm_loader_pc_service_lease.sv').read_text()
assert s.count('read_debt==0&&write_debt==0')==1
Path('out/ready-regress/mutant.sv').write_text(s.replace('read_debt==0&&write_debt==0','write_debt==0'))
PY
mutbase=${base/readyfix-src\/ot_hbm_loader_pc_service_lease.sv/out\/ready-regress\/mutant.sv}
iverilog -g2012 -s tb_loader_service_kvs -Ptb_loader_service_kvs.NATIVE=1 -Ptb_loader_service_kvs.CONCURRENT=1 -o out/ready-regress/mutant.vvp $mutbase concurrent-src/tb_loader_service_kvs.sv
set +e
vvp out/ready-regress/mutant.vvp +nsec=1024 +reps=1 > out/ready-regress/mutant.log
rc=$?
set -e
test "$rc" != 0
rg 'native stole live normal read beat debt' out/ready-regress/mutant.log
sha256sum readyfix-src/*.sv merged-src/*.sv concurrent-src/*.sv src/*.sv > out/ready-regress/source_sha256.txt
