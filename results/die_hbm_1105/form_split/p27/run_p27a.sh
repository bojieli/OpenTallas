#!/usr/bin/env bash
# HBM-FORM-SPLIT part 27 lock-step, opstore_a: uncut kit core vs 2 operand tiles + rest. run_p27a.sh KITRTL OUT [CYCLES]
# Scenario R (MUT 0,1,2,3): full random pins, all outputs except the sticky fault flag cycle-exact. Scenarios F0, F1 (MUT 0,4 / 0,5): stimulus without any error except
# bank conflicts of one operand group, so the fault comes only from that group. fault window: ref(t-2) <= dut(t) <= ref(t). MUT 0 PASS, every mutant FAIL.
set -u
KR=$1; O=$2; CYC=${3:-3000}; H=$(cd "$(dirname "$0")" && pwd); W=$H/../../../..
RT=$W/rtl/hbm_accel/cores_split/reform_1105s/opstore; BB=$W/physical/die_plan/hbm/over_cap_split/reform_1103; SM=${SRAM_MODEL:-$H/sram_256x256_bench.sv}
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}; mkdir -p $O
T=ot_hgi_sfu_core_split3__opstore_a; LEAF=$KR/ot_hgi_su_unit.sv
for M in group0 group1; do python3 -I $BB/facewrap.py --top ot_hgi_sfu_opsa_$M --clk-re '^clk$' --rst-re '^rst_n$' --out $O/${M}__fs.sv $RT/ot_hgi_sfu_opsa_group.sv $LEAF $SM > $O/$M.json || exit 1; done
python3 -I $BB/facewrap.py --top ot_hgi_sfu_opsa_rest --clk-re '^clk$' --rst-re '^rst_n$' --out $O/rest__fs.sv $RT/ot_hgi_sfu_opsa_rest.sv > $O/rest.json || exit 1
python3 -I $BB/facewrap.py --top $T --out $O/ref_unused.sv $KR/*.sv $SM > $O/ref_ports.json || exit 1
sed -e "s/^module $T (/module ${T}__split (/" -e "s/ot_hbm_face_reg #/ot_hbm_face_wire #/" -e "s/${T}__fcore u_fcore/${T}__fcore_split u_fcore/" $KR/${T}__fshell.sv > $O/dut_top.sv
sed -e "s/module ${T}__fcore (/module ${T}__fcore_split (/" -e "s/ot_hgi_sfu_split3_opstore_a_core u_core/ot_hgi_sfu_opsa__comp #(.MUT(\`OT_MUT)) u_core/" -e "s/\.u_core_u_engine_u_memory_fault(glue_1)/.u_core_u_engine_u_memory_fault(fi)/" $KR/${T}__wrap.sv > $O/dut_fcore.sv
python3 -I - $O/dut_fcore.sv <<'P'
import sys,re
f=sys.argv[1]; s=open(f).read()
chk='''    wire fi; reg r1 = 1'b0, r2 = 1'b0, seen = 1'b0;
    always @(posedge clk) begin r1 <= tb.r_glue_1; r2 <= r1; end
    wire fok = (fi <= tb.r_glue_1) && (r2 <= fi);
    assign glue_1 = fok ? tb.r_glue_1 : ~tb.r_glue_1;
    final $display("FAULT ref=%b dut=%b", tb.r_glue_1, fi);
'''
s,c=re.subn(r"(\n\s*ot_hgi_sfu_opsa__comp )",lambda m:"\n"+chk+m[1].lstrip("\n"),s,1); assert c==1
open(f,"w").write(s)
P
cat > $O/face_wire.sv <<'E'
module ot_hbm_face_wire #(parameter integer W = 1) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    assign q = d;
endmodule
E
python3 -I - $O/ref_ports.json $O $T $CYC <<'P'
import json,sys
p=json.load(open(sys.argv[1])); P=p['ports']; O=sys.argv[2]; T=sys.argv[3]; CYC=int(sys.argv[4])
A='x_u_core_u_engine_u_arithmetic_'; M='x_u_core_u_engine_u_memory_'
def rep(w,e,n): return "{"+",".join([e]*(w//n))+"}"
def spec(st,cy): return dict(ref=T,dut=T+'__split',ports=P,clocks=p['clk'],resets=['x_u_core_u_engine_u_arithmetic_rst_control_n'],reset_cycles=10,warmup=150,cycles=cy,stim=st,hold={},shift={})
json.dump(spec({},CYC),open(O+'/spec_R.json','w'),indent=1)
for g in (0,1):
    st={}
    for n,(d,w) in P.items():
        if d!='input': continue
        if n=='glue' or n.endswith('rd_src') or n.endswith('vm_waddr') or n.endswith('_flt'): st[n]=f"{w}'d0"
        elif n.endswith('rd_re'): st[n]="{"+",".join(f"(i_re{g}_b && {int(i%4==g)})" for i in range(w))+"}".replace("i_re%d_b"%g,"1")
        elif n.endswith('rd_addr'): st[n]=rep(w,"24'($urandom & 32'h1f)",24)
        elif n.endswith('sw_addr') or n.endswith('sr_addr'): st[n]=rep(w,"15'($urandom & 32'h3f)",15)
        elif n.endswith('stage_group'): st[n]=rep(w,"2'd%d"%g,2)
    for n in st:
        if n.endswith('rd_re'): st[n]="{"+",".join(f"1'({int(i%4==g)} & $urandom)" for i in range(P[n][1]))+"}"
    json.dump(spec(st,CYC),open(O+f'/spec_F{g}.json','w'),indent=1)
P
run() { # scenario mutant
  S=$1; M=$2; D=$O/obj_${S}_m$M; python3 -I $BB/lockstep_gen.py $O/spec_$S.json $O/tb_$S.sv; rm -rf $D
  $V --binary -j 12 -Wno-fatal -Wno-lint -Wno-style -DOT_MUT=$M --top-module tb -Mdir $D -o sim $O/tb_$S.sv $KR/*.sv $SM $RT/ot_hgi_sfu_opsa_group.sv $RT/ot_hgi_sfu_opsa_rest.sv $H/opstore_a__comp.sv $O/group0__fs.sv $O/group1__fs.sv $O/rest__fs.sv $O/dut_top.sv $O/dut_fcore.sv $O/face_wire.sv > $O/build_${S}_m$M.log 2>&1 || { tail -12 $O/build_${S}_m$M.log | cut -c1-240; return 2; }
  $D/sim > $O/sim_${S}_m$M.log 2>&1; echo "SCEN $S MUT $M: $(grep -E 'LOCKSTEP' $O/sim_${S}_m$M.log | cut -c1-170) $(grep FAULT $O/sim_${S}_m$M.log | tail -1)"
}
for x in "R 0" "R 1" "R 2" "R 3" "F0 0" "F0 4" "F1 0" "F1 5"; do run $x & done; wait
sha256sum $KR/*.sv $RT/ot_hgi_sfu_opsa_*.sv $SM > $O/sources_a.sha256
