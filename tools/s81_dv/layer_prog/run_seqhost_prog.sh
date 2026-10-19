#!/bin/bash
# run_seqhost_prog.sh <die tree R> <prog dir> <out dir>: build tb_dv_prog_seqhost on the REAL dsdv_seq_host of the die tree
# (the file list of rtl/dsrom_sys/s81_dv/unit/test/run_seq_host_bench.sh, goldens dropped), boot the compiled programme,
# check it (check_seqhost.py).  Verilator 5.050 (the closure daemon's pin).  Prints SEQHOST_PROG PASS/FAIL.
set -u
R=$(realpath $1); P=$(realpath $2); O=$3; mkdir -p $O; O=$(realpath $O)
H=$(cd "$(dirname "$0")" && pwd)
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
U=$R/rtl/dsrom_sys/s81_dv/unit
F="$R/rtl/lib/ot_async_fifo.sv $R/rtl/lib/ot_reset_sync.sv $R/rtl/lib/ot_rst_relay.sv $R/rtl/link/ot_link_afifo.sv
   $R/rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv $R/rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv $R/rtl/hdc/ingest/ot_hdc_kv_ingest.sv
   $R/rtl/hdc/ingest/ot_rom_host_ingest.sv $R/physical/rom_host_ingest/rtl/dsfd_host.sv
   $R/rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv
   $R/rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_c.sv
   $R/rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv $U/ot_dsdv_fixed_issue.sv $U/ot_dsdv_walk_issue.sv $U/ot_dsdv_vstop.sv $U/dsdv_sh_sd.sv $U/dsdv_seq_host.sv
   $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
$V --version > $O/verilator.version
sha256sum $F $H/tb_dv_prog_seqhost.sv > $O/sources.sha256
if [ ! -x $O/obj/tb ]; then
  /usr/bin/time -v -o $O/build.time $V --binary --timing -j ${J:-8} -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT \
    +define+DSFD_HOST_C_STATIC --top-module tb_dv_prog_seqhost --Mdir $O/obj -o tb $F $H/tb_dv_prog_seqhost.sv > $O/build.log 2>&1 \
    || { echo "SEQHOST_PROG BUILD_FAIL"; grep -m5 %Error $O/build.log; exit 3; }
fi
N=$(grep -c . $P/prog/host_boot.memh)
$O/obj/tb +dir=$P +n=$N +cyc=${CYC:-3000} > $O/run.log 2>&1
python3 $H/check_seqhost.py --dir ${REF:-$P} --log $O/run.log ${EXPECT_C:+--expect-c $EXPECT_C}
