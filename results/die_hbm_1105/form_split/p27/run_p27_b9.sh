#!/usr/bin/env bash
# HBM-REFORM-B9 BREG variant: opsb_group rd declared +1 edge (registered bank inputs).
# HBM-FORM-SPLIT part 27 lock-step: uncut kit core ot_hgi_sfu_core_split3__opstore_b vs 3 tile composition. Face flops of the kit
# shell turn into wires in the DUT, each tile carries its own. run_p27.sh KITRTL OUT [CYCLES]; MUT 0 must PASS, MUT 1/2/3 must FAIL.
set -u
KR=$1; O=$2; CYC=${3:-3000}; H=$(cd "$(dirname "$0")" && pwd); W=$H/../../../..
RT=$W/rtl/hbm_accel/cores_split/reform_1105s/opstore; BB=$W/physical/die_plan/hbm/over_cap_split/reform_1103; SM=${SRAM_MODEL:-$H/sram_256x256_bench.sv}
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}; mkdir -p "$O"
T=ot_hgi_sfu_core_split3__opstore_b; LEAF=$KR/ot_hgi_su_unit.sv
for M in group output; do python3 -I $BB/facewrap.py --top ot_hgi_sfu_opsb_$M --clk-re '^clk$' --rst-re '^rst_n$' --out $O/${M}__fs.sv $RT/ot_hgi_sfu_opsb_tiles.sv $LEAF $SM > $O/$M.json || exit 1; done
python3 -I $BB/facewrap.py --top $T --out $O/ref_unused.sv $KR/*.sv $SM > $O/ref_ports.json || exit 1
sed -e "s/^module $T (/module ${T}__split (/" -e "s/ot_hbm_face_reg #/ot_hbm_face_wire #/" -e "s/${T}__fcore u_fcore/${T}__fcore_split u_fcore/" $KR/${T}__fshell.sv > $O/dut_top.sv
sed -e "s/module ${T}__fcore (/module ${T}__fcore_split (/" -e "s/ot_hgi_sfu_split3_opstore_b_core u_core/ot_hgi_sfu_opsb__comp #(.MUT(\`OT_MUT)) u_core/" $KR/${T}__wrap.sv > $O/dut_fcore.sv
grep -c "ot_hgi_sfu_opsb__comp" $O/dut_fcore.sv
cat > $O/face_wire.sv <<'E'
module ot_hbm_face_wire #(parameter integer W = 1) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    assign q = d;
endmodule
E
python3 -I - $O/ref_ports.json $O/spec.json $T $CYC <<'P'
import json,sys
p=json.load(open(sys.argv[1])); P=p['ports']; T=sys.argv[3]; st={}
for n,(d,w) in P.items():
    if d=='input' and (n.endswith('_ra') or n.endswith('_lwa') or n.endswith('sw_addr') or n.endswith('sr_addr')):
        aw=24 if w%24==0 and not n.endswith('addr') else 15
        st[n]="{"+",".join(f"{aw}'($urandom & ((cyc % 7 == 0) ? 32'hffffffff : 32'h7fff))" for _ in range(w//aw))+"}"
json.dump(dict(ref=T,dut=T+'__split',ports=P,clocks=p['clk'],resets=p['rst'],reset_cycles=10,warmup=150,cycles=int(sys.argv[4]),stim=st,hold={},shift={"g_operand_2_u_group_rd":1,"g_operand_3_u_group_rd":1}),open(sys.argv[2],'w'),indent=1)
P
python3 -I $BB/lockstep_gen.py $O/spec.json $O/tb.sv
for M in ${MUTS:-0 1 2 3}; do
  rm -rf $O/obj_m$M; $V --binary -j 16 -Wno-fatal -Wno-lint -Wno-style -DOT_MUT=$M --top-module tb -Mdir $O/obj_m$M -o sim \
    $O/tb.sv $KR/*.sv $SM $RT/*.sv $H/opstore_b__comp.sv $O/group__fs.sv $O/output__fs.sv $O/dut_top.sv $O/dut_fcore.sv $O/face_wire.sv > $O/build_m$M.log 2>&1 || { tail -20 $O/build_m$M.log | cut -c1-240; exit 2; }
  $O/obj_m$M/sim > $O/sim_m$M.log 2>&1; echo "MUT $M: $(grep LOCKSTEP $O/sim_m$M.log | cut -c1-200)"
done
sha256sum $KR/*.sv $RT/*.sv $SM > $O/sources.sha256
