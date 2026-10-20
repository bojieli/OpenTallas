#!/bin/bash
set -euo pipefail
export PATH=/opt/oss-cad-suite/bin:$PATH
ROOT=$PWD
export PYTHONPATH=$ROOT/tools/hbm_static:$ROOT/tools/hbm_layer_vehicle
mkdir -p review/producer review/calendar
python3 tools/hbm_layer_vehicle/test_native_producer_calendar.py > review/compiler_tests.log 2>&1
P=$ROOT/results/rtl/token_producer_fix_1019/producer
cd review/producer
verilator --version > version.log
verilator --binary --timing -Wno-fatal --top-module tb --Mdir obj -j 2 "$P/tb_all.sv" "$P/ot_hbm_su_programme_pslice_c5.sv" > build.log 2>&1
for c in 0 1 2 3; do
  N=$(wc -l < "$P/case$c/expected.mem"); W=$(wc -l < "$P/case$c/config.mem")
  obj/Vtb +CFG="$P/case$c/config.mem" +GOLD="$P/case$c/expected.mem" +N=$N +W=$W > case$c.log 2>&1
  grep 'PRODUCER PASS' case$c.log
done
if obj/Vtb +CFG="$P/config_old.mem" +GOLD="$P/expected.mem" +N=44 +W=56 > old_bank.log 2>&1; then exit 1; fi
grep 'PRODUCER FAIL' old_bank.log
if obj/Vtb +CFG="$P/config_fixed.mem" +GOLD="$P/expected.mem" +N=44 +W=56 +STARTUP=5 > old_startup.log 2>&1; then exit 1; fi
grep 'PRODUCER FAIL' old_startup.log
cd "$ROOT/review/calendar"
cp "$ROOT"/results/rtl/hbm_native_calendar_1019/exact_sources/*.sv .
cp "$ROOT"/rtl/hbm_accel/generic/adapters/static_su/ot_hbm_su_static_vm_ports.sv .
cp "$ROOT"/results/rtl/hbm_native_calendar_1019/readback_expected.mem .
cp "$ROOT"/results/rtl/hbm_token_calendar_closure_1019/release18_tb.sv .
cp "$ROOT"/tools/hbm_layer_vehicle/native_su_calendar.py .
python3 - <<'PY'
from pathlib import Path
import hashlib
import su_programme_compile as C
model=C.lower_columns(Path('readback_expected.mem'),Path('readback_image'),resident_edges=7111)
assert hashlib.sha256(Path('readback_image/config.mem').read_bytes()).hexdigest()=='24458498ceae5222d7f59c2adcf9812c542b8d84711e35f328fd88ab26b7fd62'
PY
python3 native_su_calendar.py readback_expected.mem release18_cal --first-serial 2675 --bridge-serial 2675 --bridge-stream 3567 --host-launch 3500 --rows 160 --request-lane-edges 4
cp release18_cal/calendar.mem calendar.mem
sha256sum *.sv native_su_calendar.py readback_expected.mem readback_image/config.mem calendar.mem > inputs.sha256
verilator --binary --timing -Wno-fatal --top-module tb --Mdir obj -j 2 release18_tb.sv ckgen.sv pgp.sv bridge.sv release.sv tap_exact.sv vmb.sv hfd_hgi_vm_calendar_f20.sv ot_hbm_host_cfg_leaf_sw.sv ot_hbm_su_static_vm_ports.sv > build.log 2>&1
W=$(wc -l < readback_image/config.mem)
obj/Vtb +CFG=readback_image/config.mem +GOLD=readback_expected.mem +N=62 +W=$W > positive.log 2>&1
tail -3 positive.log
for m in 1 2 3; do
 if obj/Vtb +CFG=readback_image/config.mem +GOLD=readback_expected.mem +N=62 +W=$W +MUT=$m > mutant$m.log 2>&1; then exit 1; fi
 grep -E 'PRODUCER FAIL|NATIVE_DATA FAIL' mutant$m.log
done
mkdir wrong
python3 native_su_calendar.py readback_expected.mem wrong --first-serial 2675 --bridge-serial 2675 --bridge-stream 3567 --host-launch 3500 --rows 160 --request-lane-edges 3
if (cd wrong; ../obj/Vtb +CFG=../readback_image/config.mem +GOLD=../readback_expected.mem +N=62 +W=$W > ../wrong_lane.log 2>&1); then exit 1; fi
grep -E 'PRODUCER FAIL|NATIVE_DATA FAIL' wrong_lane.log
echo NATIVE_COMPONENT_REVIEW_PASS_NO_TOKEN_QUALIFICATION
