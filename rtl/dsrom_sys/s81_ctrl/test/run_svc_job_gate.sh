#!/bin/bash
# s81-svceng-1011 engine-4 (svc) gate: tb_s81_svc_job (NS slabs = ot_s81_svc_job + closed IO hub ot_s81ph_svc_io + protocol
# sources, one dsfd_svc_join adapter).  base x3 seeds and NS 1/2/4 must PASS; negatives must FAIL: dropstart (TBMUT 1),
# wrongdesc_end (TBMUT 2), wrongdesc_nq (TBMUT 3), earlydone (svc_job MUT 5), nogate (svc_job MUT 1 = q passes unarmed,
# with TBMUT 1), partialdone (join MUT 5 = done when ANY slab is done), lostcmd (join MUT 6).
# Usage (repo root): run_svc_job_gate.sh <out dir>   exit 0 iff PASS
set -u
O=$1; mkdir -p $O
F="rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv rtl/dsrom_sys/s81_ctrl/ot_s81_slab_ep.sv rtl/dsrom_sys/s81_ctrl/ot_s81_svc_job.sv rtl/dsrom_sys/s81_ph/svc/ot_s81ph_svc_io.sv rtl/common/ot_fwd_link_stage.sv rtl/dsrom_sys/s81_ph/ot_s81ph_rfifo.sv rtl/dsrom_sys/s81_ph/svc/ot_s81ph_svc_io_tiles.sv rtl/dsrom_sys/s81_ph/svc/dsfd_svcio_job.sv rtl/dsrom_sys/s81_ctrl/test/tb_s81_svc_job.sv"
run() { n=$1; shift
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_s81_svc_job -Mdir $O/obj_$n "$@" $F > $O/$n.build 2>&1 || { echo BUILD_FAIL > $O/$n.log; return 2; }
  $O/obj_$n/Vtb_s81_svc_job > $O/$n.log 2>&1; grep -q '^PASS' $O/$n.log && return 0 || return 1; }
if [ "${2:-}" = one ]; then shift 2; run "$@"; rc=$?; echo "SVC_JOB_ONE $1 rc=$rc"; exit $rc; fi   # single run (closure-loop negative bench)
for c in "b1 -GSEED=1" "b2 -GSEED=2 -GNJ=80" "b3 -GSEED=3 -GLEAD=40" "ns1 -GNS=1 -GSEED=4" "ns4 -GNS=4 -GSEED=5" "tile1 -GTILE=1 -GSEED=6" "tile4 -GTILE=1 -GNS=4 -GSEED=7 -GNJ=80" \
         "dropstart -GTBMUT=1" "wrongdesc_end -GTBMUT=2" "wrongdesc_nq -GTBMUT=3" "earlydone -GJMUT=5" \
         "nogate -GJMUT=1 -GTBMUT=1" "partialdone -GJNMUT=5" "lostcmd -GJNMUT=6" "tile_earlydone -GTILE=1 -GJMUT=5" "tile_dropstart -GTILE=1 -GTBMUT=1"; do
  set -- $c; ( run "$@"; echo $? > $O/$1.rc ) &
done; wait
v=PASS; line=""
for n in b1 b2 b3 ns1 ns4 tile1 tile4; do r=$(cat $O/$n.rc); line="$line $n=$r"; [ $r -eq 0 ] || v=FAIL; done
for n in dropstart wrongdesc_end wrongdesc_nq earlydone nogate partialdone lostcmd tile_earlydone tile_dropstart; do r=$(cat $O/$n.rc); line="$line $n=$r"; [ $r -eq 1 ] || v=FAIL; done
echo "SVC_JOB_GATE $v$line ($(grep -h SVCJOB $O/b1.log | grep -oE 'cycles=[0-9]+'))" | tee $O/verdict.log
[ $v = PASS ]
