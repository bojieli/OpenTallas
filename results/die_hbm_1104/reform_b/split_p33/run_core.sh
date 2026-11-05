#!/bin/bash
# run_core.sh: whole body core lockstep, flat against composition, both with kit face models. Must FAIL: tile MUT 1,2 (seam).
set -u; Q=/srv/opentallas-scratch2/claude/hbm-reform-b5/q2n; R=/srv/opentallas-scratch3/claude/hbm-reform-b3/wt; O=$Q/core; mkdir -p $O; G=$Q/gen; C=ot_hfd_coll_q2n2_body_core
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; FW="python3 $R/physical/die_plan/hbm/over_cap_split/reform_1103/facewrap.py --no-hier --clk-re clk --rst-re rst"
python3 -I - $O <<'P'
import re,sys
O=sys.argv[1]
def patch(src,dst):
    t=open(src).read()
    R_="assign { "+" , ".join(f"\\u_body.g_iss256.u_issuer.uop_d1[{i}] " for i in range(1535,-1,-1))+" } = tb_core.force_d1;"
    t,n=re.subn(r"assign \{ \\u_body\.g_iss256\.u_issuer\.uop_d1\[1535\] [^}]*\} = [^;]*;",lambda m_:R_,t)
    assert n==1,(src,n); open(dst,'w').write(t)
patch('/tmp/b5body.sv',O+'/old.sv'); patch('/srv/opentallas-scratch2/claude/hbm-reform-b5/q2n/gen/ot_q2nf_rest.sv',O+'/rest.sv')
t=open('/tmp/b5body.sv').read();i=t.index('module ot_hfd_coll_q2n2_body_core (');j=t.index('\n);',i)
P=[(m[1],int(m[2])+1 if m[2] else 1,m[3]) for m in re.finditer(r"^\s*(input|output)\s+wire\s*(?:\[(\d+):0\]\s*)?(\w+),?\s*$",t[i:j],re.M)]
L=[];CK=[];RAND=[];CMP=[];pa=[];pb=[]
for d,w,n in P:
    if d=='input':
        if 'clk' in n: L.append(f" wire [{w-1}:0] {n}={{{w}{{clk}}}};")
        elif n=='rst_n': continue
        else:
            L.append(f" reg [{w-1}:0] {n}=0;")
            if n in('cfg_v','desc_v','launch_v','cfg_target','cfg_addr','cfg_data','desc_base','desc_limit','desc_loops') or n.endswith('_fault'): pass
            elif n=='phy_up': RAND.append(" phy_up=2'b11;")
            else: RAND.append(f" for(integer i=0;i+32<={w};i=i+32) {n}[i+:32]=$urandom; for(integer i={w//32*32};i<{w};i=i+1) {n}[i]=$urandom;")
        pa.append(f".{n}({n})");pb.append(f".{n}({n})")
    else:
        L.append(f" wire [{w-1}:0] a_{n},b_{n};")
        pa.append(f".{n}(a_{n})");pb.append(f".{n}(b_{n})")
        CMP.append(f"  if(a_{n}!==b_{n})begin err=err+1;if(err<12)$display(\"DIFF {n} cyc %0d\",cyc);end\n  if(|a_{n})nz=nz+1;")
open(O+'/tb_core.sv','w').write(f"""`timescale 1ns/1ps
`default_nettype none
module tb_core #(parameter integer MUT=0)();
 reg clk=0,rst_n=0;always #1 clk=~clk;
 reg [1535:0] force_d1=0;
{chr(10).join(L)}
 ot_hfd_coll_q2n2_body_core__fs u_a(.rst_n(rst_n),{",".join(pa)});
 ot_hfd_coll_q2n2_body_core__p33fs u_b(.rst_n(rst_n),{",".join(pb)});
 integer cyc=0,err=0,nz=0;
 always @(negedge clk) if(rst_n&&cyc>60)begin
{chr(10).join(CMP)}
 end
 initial begin
  repeat(16)@(negedge clk);rst_n=1;
  repeat(`CYC)begin @(negedge clk);cyc=cyc+1;
   for(integer i=0;i<1536;i=i+32)force_d1[i+:32]=$urandom;
   force_d1[9:0]=10'h3ff;
   for(integer d=0;d<15;d=d+1)force_d1[26+d*4+:4]=$urandom%9;
   if(cyc<50)force_d1[10+:15]=0;
{chr(10).join(RAND)}
  end
  $display("CORE cycles %0d nonzero_out %0d errors %0d",cyc,nz,err);
  if(err!=0)$fatal(1,"FAIL");$display("PASS");$finish;
 end
endmodule
`default_nettype wire
""")
P
$FW --top $C --out $O/old.fs.sv -- $O/old.sv > $O/fw1.log 2>&1 || { echo FW1; tail -3 $O/fw1.log; exit 3; }
$FW --top ot_q2nf_rest --out $O/rest.fs.sv -- $O/rest.sv > $O/fw2.log 2>&1 || { echo FW2; tail -3 $O/fw2.log; exit 3; }
$FW --top ot_q2nf_qout --pass-param MUT --out $O/t.fs.sv -- $G/ot_q2nf_split.sv > $O/fw3.log 2>&1 || { echo FW3; exit 3; }
sed -E 's/\bot_q2nf_qout__fs u_q/ot_q2nf_qout__fs #(.MUT(tb_core.MUT)) u_q/' $G/comp/${C}__p33fs.sv > $O/comp.fs.sv
sed -i 's/#(.MUT(tb_core.MUT)) //' $O/comp.fs.sv; python3 -I - $O/comp.fs.sv <<'P'
import sys,re
f=sys.argv[1];t=open(f).read()
t=t.replace('module ot_hfd_coll_q2n2_body_core__p33fs (','module ot_hfd_coll_q2n2_body_core__p33fs #(parameter integer MUT=0)(').replace('ot_q2nf_qout__fs u_q(','ot_q2nf_qout__fs #(.MUT(MUT)) u_q(')
open(f,'w').write(t)
P
sed -i 's/ot_hfd_coll_q2n2_body_core__p33fs u_b(/ot_hfd_coll_q2n2_body_core__p33fs #(.MUT(MUT)) u_b(/' $O/tb_core.sv
cat > $O/face_reg.sv <<'V'
module ot_hbm_face_reg #(parameter integer W=1)(input wire clk, input wire [W-1:0] d, output reg [W-1:0] q); always @(posedge clk) q<=d; endmodule
V
MACS=""; for m in ot_sram_1r1w_64x512_m1_r2c2 ot_sram_1rw_256x64_m4_r2c2 ot_sram_1r1w_256x256_m2_r2c2; do MACS="$MACS $(ls $R/physical/asap7_memory_macros/$m/$m.v $R/physical/asap7_memory_macros_v2/$m/$m.v 2>/dev/null | head -1)"; done; echo macros $MACS
rc=0
for sp in ${RUNS:-m0:PASS: s1:FAIL:-GMUT=1 s2:FAIL:-GMUT=2}; do IFS=: read n e f <<<"$sp"; d=$O/obj_$n
 $VL --binary --timing -O1 -j 12 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -DCYC=${CYC:-2000} --top-module tb_core $f -Mdir $d -o sim $O/tb_core.sv $O/old.fs.sv $O/old.sv $O/rest.fs.sv $O/rest.sv $O/t.fs.sv $G/ot_q2nf_split.sv $O/comp.fs.sv $O/face_reg.sv $MACS > $d.build.log 2>&1 || { echo "$n BUILD FAIL"; grep -m8 %Error $d.build.log | cut -c1-240; rc=1; continue; }
 timeout 900 $d/sim > $d.run.log 2>&1; r=$?; g=PASS; [ $r != 0 ] && g=FAIL; v=BAD; [ $g = $e ] && v=OK; [ $v = OK ] || rc=1
 echo "$n expect=$e got=$g $v | $(grep -E '^CORE|^DIFF' $d.run.log | head -3 | tr '\n' ' ' | cut -c1-200)"; done
echo CORE_EXIT $rc
