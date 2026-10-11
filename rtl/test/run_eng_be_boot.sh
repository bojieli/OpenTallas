#!/bin/bash
# s81-svceng-1011 Engram boot gate (stack HBM client): base (576 sectors) and EXPECT 1152 must PASS, HMUT 1 must FAIL.
# Usage (repo root): run_eng_be_boot.sh <out>  [one <name> <args...>]   exit 0 iff PASS
set -u
O=$1; mkdir -p $O; E=rtl/dsrom_sys/engram
F="rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv rtl/hdc/v41/ot_hdc_engram_hash_shipped.sv rtl/hdc/v41/ot_hdc_engram_gather.sv $E/ot_dsrom_engram_lookup.sv $E/ot_dsrom_engram_rowsink.sv $E/dsfd_engram_lkp.sv $E/dsfd_engram_sink.sv $E/ot_dsrom_engram_prefetch.sv rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv rtl/dsrom_sys/s81_ctrl/ot_s81_slab_ep.sv $E/dsfd_engram_c.sv $E/ot_dsrom_engram_boot_dispatch.sv $E/ot_dsrom_engram_boot_ctrl_map.sv $E/ot_dsrom_engram_rowstripe_service.sv $E/ot_dsrom_engram_rowstripe_read.sv rtl/dsrom_sys/s81_ingest/ot_s81_engram_aperture.sv $E/ot_s81_eng_half.sv rtl/test/tb_eng_be_die.sv rtl/test/tb_eng_be_boot.sv"
run() { n=$1; shift
  verilator --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Irtl/test --top-module tb_eng_be_boot -Mdir $O/obj_$n "$@" $F > $O/$n.build 2>&1 || { echo BUILD_FAIL > $O/$n.log; return 2; }
  $O/obj_$n/Vtb_eng_be_boot > $O/$n.log 2>&1; grep -q '^PASS' $O/$n.log && return 0 || return 1; }
if [ "${2:-}" = one ]; then shift 2; run "$@"; rc=$?; echo "ENG_BE_BOOT_ONE $1 rc=$rc"; exit $rc; fi
( run base; echo $? > $O/base.rc ) & ( run big -GEXPECT=1152 -GD=30; echo $? > $O/big.rc ) & ( run corrupt -GHMUT=1; echo $? > $O/corrupt.rc ) & wait
b=$(cat $O/base.rc); g=$(cat $O/big.rc); c=$(cat $O/corrupt.rc); v=PASS
[ $b -eq 0 ] && [ $g -eq 0 ] && [ $c -eq 1 ] || v=FAIL
echo "ENG_BE_BOOT_GATE $v base=$b big=$g corrupt=$c ($(grep -h ENGBOOT $O/base.log | head -1))" | tee $O/verdict.log
[ $v = PASS ]
