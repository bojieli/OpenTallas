#!/bin/bash
# s81-spwfc 2026-10-13: exact bench of the CLUSTER form of dsfd_sp_capture_c (ctrl_c/dsfd_sp_capture_c_cl.sv).
# The gather -> capture golden bench (tb_s81ph_gather_capture +UNORD, rd64 reference) drives a shim named
# dsfd_sp_capture that holds the cluster form (DUT, its t_vm goes to the bench) and the reference
# ctrl_c/dsfd_sp_capture_c.sv (S81PH_CAP_SAFE) in lockstep: t_vm compared every ck and ckv edge, t_cd every ckv edge.
# usage (source root): tools/s81_ph/capc_bench.sh <out> <tag> "<cases>" [defines...]; verdict "CAPC_BENCH PASS|FAIL"
set -u
OUT=$1; TAG=$2; CASES=$3; shift 3
d='+define+S81PH_CAP_SAFE'; for x in "$@"; do d="$d +define+$x"; done
mkdir -p $OUT/gen_$TAG; G=$OUT/gen_$TAG
for c in $CASES; do
  case $c in mix) a="mix 7";; mix11) a="mix 11";; mix12) a="mix 12";; mix13) a="mix 13";; *) a="$c 7";; esac
  [ -f $OUT/stim_$c.txt ] || python3 rtl/dsrom_sys/s81_ph/test/gen_stim.py $a $OUT/stim_$c.txt
done
sed -e 's/module dsfd_sp_capture_v1/module capc_ref_v1/; s/module dsfd_sp_capture /module capc_ref_core /; s/dsfd_sp_capture_v1 #/capc_ref_v1 #/' \
  rtl/dsrom_sys/s81_ph/dsfd_sp_capture.sv > $G/capc_ref_core.sv
sed -e 's/module dsfd_sp_capture_c /module capc_ref /; s/dsfd_sp_capture #/capc_ref_core #/' \
  rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_capture_c.sv > $G/capc_ref.sv
grep -q 'module capc_ref_core ' $G/capc_ref_core.sv && grep -q 'module capc_ref ' $G/capc_ref.sv && grep -q 'capc_ref_core #' $G/capc_ref.sv \
  || { echo "CAPC_BENCH FAIL rename"; exit 1; }
cat > $G/capc_shim.sv <<'S'
`timescale 1ns/1ps
module dsfd_sp_capture (input wire [0:0] ck, input wire [0:0] rst, input wire [0:0] ckv, input wire [0:0] rsv,
    input wire [6946:0] f_gather, output wire [13375:0] t_vm);
    wire [13375:0] rv; wire [11:0] rc, dc;
    capc_ref u_ref (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_gather(f_gather), .t_vm(rv), .t_cd(rc));
    dsfd_sp_capture_c u_dut (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_gather(f_gather), .t_vm(t_vm), .t_cd(dc));
    integer mm = 0, tg = 0, nw = 0; reg tq = 1'b0; reg live = 1'b0;
    always @(posedge ckv[0]) if (rsv[0]) begin
        live <= 1'b1;
        if (live) begin
            if (rv !== t_vm || rc !== dc) begin mm = mm + 1; if (mm < 5) $display("CAPC_EQ MISMATCH t=%0t cd %h/%h", $time, rc, dc); end
            if (dc[11] !== tq) begin tg = tg + 1; tq <= dc[11]; end
            if (|t_vm[13311:0]) nw = nw + 1;
        end
    end
    final $display("CAPC_EQ mismatches=%0d tcd_toggles=%0d vm_active_cycles=%0d %s", mm, tg, nw, (mm == 0 && nw > 0) ? "EQ_PASS" : "EQ_FAIL");
endmodule
S
verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN \
  --top-module tb_s81ph_gather_capture $d -Mdir $OUT/obj_$TAG -o sim \
  rtl/v41rom/ot_v41_ret.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/gpu/ot_fp32_add_rne_deep.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv \
  rtl/dsrom_sys/rd64_capture/ot_dsrom_rd64_vm_capture.sv rtl/dsrom_sys/rd64_capture/ot_dsrom_s81_phase_capture_profile.sv \
  rtl/common/ot_ratio_cdc_fifo.sv rtl/dsrom_sys/s81_ph/ot_s81ph_ret_root_p.sv rtl/dsrom_sys/s81_ph/ot_s81ph_root_blk.sv \
  rtl/dsrom_sys/s81_ph/ot_s81ph_root_tile.sv rtl/dsrom_sys/s81_ph/ot_s81ph_gather.sv \
  rtl/dsrom_sys/s81_ph/ot_s81ph_cap_p.sv rtl/dsrom_sys/s81_ph/ot_s81ph_capture.sv rtl/dsrom_sys/s81_ph/ot_s81ph_cap_tile.sv \
  rtl/dsrom_sys/s81_ph/dsfd_sp_gather.sv $G/capc_ref_core.sv $G/capc_ref.sv rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_capture_c_cl.sv $G/capc_shim.sv \
  rtl/dsrom_sys/s81_ph/test/tb_s81ph_gather_capture.sv > $OUT/build_$TAG.log 2>&1 || { tail -5 $OUT/build_$TAG.log; echo "CAPC_BENCH FAIL build"; exit 1; }
for c in $CASES; do $OUT/obj_$TAG/sim +UNORD +STIM=$OUT/stim_$c.txt > $OUT/run_${TAG}_$c.log 2>&1 & done
wait
for c in $CASES; do
  echo "$TAG $c: $(grep -h SUMMARY $OUT/run_${TAG}_$c.log) $(grep -h 'RESULT' $OUT/run_${TAG}_$c.log | tail -1) $(grep -h '^CAPC_EQ mismatches' $OUT/run_${TAG}_$c.log | tail -1)"
done | tee $OUT/summary_$TAG.txt
if grep -v 'RESULT PASS.*EQ_PASS' $OUT/summary_$TAG.txt | grep -q . || ! grep -q . $OUT/summary_$TAG.txt; then echo "CAPC_BENCH FAIL" | tee -a $OUT/summary_$TAG.txt; exit 1; fi
echo "CAPC_BENCH PASS cases=$(grep -c EQ_PASS $OUT/summary_$TAG.txt)" | tee -a $OUT/summary_$TAG.txt
