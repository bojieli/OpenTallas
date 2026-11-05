#!/usr/bin/env bash
# run_lock.sh REPO OUT: cycle-exact lockstep of the part 25 composition, sw tile HREG=0 (u_ref) against sw tile HREG=1 (u_new), same
# stimulus as tb_wbq.sv; every output pin of the two compositions compared on every edge (===). HBM-GAPS-3 11-05.
# PASS: m0, slow K, E quadrant. Must FAIL (negative controls, mutant on the HREG=1 side only): seam MUT 2 (one g_d bit), root RMUT 2.
set -u; cd "${1:?}"; OUT=$(realpath -m "${2:?}"); mkdir -p "$OUT"; rc=0
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P=results/die_hbm_1104/reform_b/split_p25; S=rtl/hbm_accel/loader/service_native; D=rtl/hbm_accel/cores_split/reform_1105b
MAC=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
L="rtl/lib/ot_reset_sync.sv rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv $S/ot_hbm_svc_pc_ctrl_leaf.sv"
FW="python3 physical/die_plan/hbm/over_cap_split/reform_1103/facewrap.py --no-hier --clk-re clk --rst-re rst"
$FW --top ot_wbq_root --pass-param MUT --out $OUT/root.fs.sv -- $D/ot_wbq_split.sv > /dev/null || exit 3
$FW --top ot_wbq_sw --out $OUT/sw.fs.sv -- $D/ot_wbq_split.sv > /dev/null || exit 3
$FW --top ot_wbq_sw --param HREG=1 --out $OUT/sw1.fs.tmp -- $D/ot_wbq_split.sv > /dev/null || exit 3
sed 's/^module ot_wbq_sw__fs\b/module ot_wbq_sw__fs1/' $OUT/sw1.fs.tmp > $OUT/sw1.fs.sv
sed -e 's/^module ot_hbm_svc_wb_kport_q__p25fs\b/module ot_hbm_svc_wb_kport_q__p25fs1/' -e 's/ot_wbq_sw__fs u_sw/ot_wbq_sw__fs1 u_sw/' $P/ot_hbm_svc_wb_kport_q__p25fs.sv > $OUT/p25fs1.sv
grep -q 'ot_wbq_sw__fs1 u_sw' $OUT/p25fs1.sv && grep -q '#(.HREG(1)) u_fcore' $OUT/sw1.fs.sv && ! grep -q 'HREG' $OUT/sw.fs.sv || { echo "LOCK setup FAIL"; exit 3; }
cat > $OUT/face_reg.sv <<'V'
module ot_hbm_face_reg #(parameter integer W=1)(input wire clk, input wire [W-1:0] d, output reg [W-1:0] q); always @(posedge clk) q<=d; endmodule
V
# tb: tb_wbq with the flat reference replaced by the HREG=0 composition, plus an every-edge pin compare
python3 -I - "$P/tb_wbq.sv" "$OUT/tb_lock.sv" <<'PY'
import sys; s=open(sys.argv[1]).read()
a="ot_hbm_svc_wb_kport_q__fs u_ref("; assert s.count(a)==1; s=s.replace(a,"ot_hbm_svc_wb_kport_q__p25fs u_ref(")
a="ot_hbm_svc_wb_kport_q__p25fs #(.MUT(MUT),.RMUT(RMUT)) u_new("; assert s.count(a)==1
s=s.replace(a,"ot_hbm_svc_wb_kport_q__p25fs1 #(.MUT(MUT),.RMUT(RMUT)) u_new(")
s=s.replace("module tb_wbq;","module tb_lock;")
a=" // first fault report"; assert s.count(a)==1
s=s.replace(a,''' // LOCK: every output pin, every edge after reset release
 int lockbad=0;longint lockfirst=-1;
 always @(posedge c)if(rst)begin
  if(v[0]!==v[1]||a[0]!==a[1]||d[0]!==d[1]||rd[0]!==rd[1]||bv[0]!==bv[1]||bb[0]!==bb[1]||bt[0]!==bt[1]||wa[0]!==wa[1]||f[0]!==f[1])begin
   if(lockfirst<0)begin lockfirst=cyc;$display("LOCK first mismatch t=%0d v %h %h a %0b d %0b rd %b %b bv %b %b wa %h %h f %b %b",cyc,v[0],v[1],a[0]===a[1],d[0]===d[1],rd[0],rd[1],bv[0],bv[1],wa[0],wa[1],f[0],f[1]);end lockbad=lockbad+1;end
 end
 final $display("LOCK edges_bad %0d first %0d",lockbad,lockfirst);
'''+a)
a="if(w[0]==tot_sect&&"; assert s.count(a)==1; s=s.replace(a,"if(lockbad==0&&w[0]==tot_sect&&")
# one K partner draw per edge, shared by both sides (tb_wbq draws per side), so the two compositions see the same K stimulus
a="  for(u=0;u<2;u=u+1)begin\n   if(wa[u]!=0"; assert s.count(a)==1
s=s.replace(a,"  rrdy=(SLOW!=0)?16'($urandom&$urandom&$urandom&$urandom):16'($urandom|$urandom);\n  for(p=0;p<16;p=p+1)rdn[p]=($urandom%((SLOW!=0)?16:4)==0);\n"+a)
a="if(q[u][p]>0&&$urandom%((SLOW!=0)?16:4)==0)"; assert s.count(a)==1; s=s.replace(a,"if(q[u][p]>0&&rdn[p])")
a="rdy[u]<=(SLOW!=0)?($urandom&$urandom&$urandom&$urandom):($urandom|$urandom);"; assert s.count(a)==1; s=s.replace(a,"rdy[u]<=rrdy;")
s=s.replace(" int lockbad=0;"," bit [15:0] rrdy;bit rdn[0:15];int lockbad=0;")
open(sys.argv[2],"w").write(s)
PY
one() { local n=$1 e=$2; shift 2; local d=$OUT/obj_$n
  "$VL" --binary --timing -O1 -j ${J:-6} -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_lock "$@" -Mdir $d -o sim $OUT/tb_lock.sv $P/ot_hbm_svc_wb_kport_q__p25fs.sv $OUT/p25fs1.sv $D/ot_wbq_split.sv \
   $OUT/root.fs.sv $OUT/sw.fs.sv $OUT/sw1.fs.sv $OUT/face_reg.sv $MAC $L > $d.build.log 2>&1 || { echo "$n BUILD FAIL"; grep -m8 %Error $d.build.log | cut -c1-220; return 1; }
  timeout ${SIMT:-900} $d/sim > $d.run.log 2>&1; local r=$?; local g=PASS; [ $r != 0 ] && g=FAIL
  local v=BAD; [ $g = $e ] && v=OK
  echo "$n expect=$e got=$g $v | $(grep -E '^LOCK edges' $d.run.log | tail -1) | $(grep -E '^WBQ s' $d.run.log | tail -1 | cut -c1-200)"; [ $v = OK ]
}
for spec in ${RUNS:-m0:PASS: slow:PASS:-GSLOW=1 east:PASS:-GQUAD=1 s2:FAIL:-GMUT=2 r2:FAIL:-GRMUT=2}; do
  IFS=: read n e f <<<"$spec"; one $n $e $f || rc=1
done
echo LOCK_EXIT $rc; exit $rc
