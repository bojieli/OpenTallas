#!/bin/bash
set -eu
source ~/.opentallas-env
cd /srv/opentallas-scratch/codex/s81-index-hbm-native-r1
set +e
/usr/bin/time -v bash -c 'set -e; cd src; verilator --cc -Wno-fatal --top-module DsromS81IndexHbm --Mdir ../obj rtl/test/dsrom_s81_native_index_hbm/DsromS81IndexHbm.sv rtl/chip/ot_chip_v41x_hbm_karb.sv rtl/dsrom_sys/c8/ot_hdc_v41x_idx_hbm_c8.sv rtl/hdc/v41x/ot_hdc_v41x_idx_ring_port.sv rtl/hdc/v41x/ot_hdc_v41x_idx_ring_kwr.sv; make -C ../obj -f VDsromS81IndexHbm.mk -j8; g++ -std=c++17 -c -I../obj -I"$VERILATOR_ROOT/include" -I"$VERILATOR_ROOT/include/vltstd" tools/runtime/dsrom/s81_minimum_index_hbm.cpp -o ../s81_minimum_index_hbm.o' > build.log 2>resources.log
status=$?
printf '{"exit_code":%d,"source":"8089cdc29","scope":"native index backend and callback compile only"}\n' "$status" > terminal.json
exit "$status"
