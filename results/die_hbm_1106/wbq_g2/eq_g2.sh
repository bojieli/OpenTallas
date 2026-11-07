#!/bin/bash
# eq_g2.sh REPO OUT [MUT]: yosys equivalence, ot_wbq_root (OT_WBQ_N1M, gold) vs ot_wbq_root_g2 (gate, two ot_wbq_root_grp).
# Payload macro = blackbox (same master both sides), everted to ports (expose -evert) and matched by lane: gate u_gG.g_lane[k] =
# gold g_lane[4G+k] (rd_out shared input, every macro input an equiv output). equiv_make (ports by name) + equiv_struct + equiv_simple -seq + equiv_induct;
# PASS = equiv_status -assert. MUT=1..: gate mutants (same as bench_g2.sh) must FAIL.
W=$1; O=$2; MUT=${3:-0}; mkdir -p $O; Y=${YOSYS:-$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys}
F=$W/rtl/hbm_accel/cores_split/reform_1105b/ot_wbq_split.sv
L="$W/rtl/lib/ot_reset_sync.sv $W/rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv"
mod() { awk -v m="$1" '$0 ~ "^module "m"( |#|\\()"{p=1} p{print} p&&/^endmodule/{exit}' $F; }
mod ot_wbq_root > $O/gold.sv
{ mod ot_wbq_root_grp; mod ot_wbq_root_g0; mod ot_wbq_root_g1; mod ot_wbq_root_g2; } > $O/gate0.sv
case $MUT in
 0) cp $O/gate0.sv $O/gate.sv;;
 1) sed 's/ot_wbq_root_grp #(.G(1),.CRED(CRED),.MUT(MUT)) u_grp/ot_wbq_root_grp #(.G(0),.CRED(CRED),.MUT(MUT)) u_grp/' $O/gate0.sv > $O/gate.sv;;
 2) sed 's/\.wd0(wd4),\.wd1(wd5)/.wd0(wd5),.wd1(wd4)/' $O/gate0.sv > $O/gate.sv;;
 3) sed "s/wire \[1:0\] sel=ne\[0\]?2'd0:ne\[1\]?2'd1:/wire [1:0] sel=ne[1]?2'd1:ne[0]?2'd0:/" $O/gate0.sv > $O/gate.sv;;
 4) awk '/u_g1/{f=1} f&&/g_credit\(g_credit\[1\]\)/{sub(/g_credit\[1\]/,"g_credit[0]");f=0} {print}' $O/gate0.sv > $O/gate.sv;;
esac
[ $MUT != 0 ] && cmp -s $O/gate0.sv $O/gate.sv && { echo "MUT $MUT NOT APPLIED"; exit 9; }
cat > $O/bb.v <<'V'
(* blackbox *) module ot_sram_1r1w_128x256_m1_r0c0_g256(input clk, input r_ce_in, input [6:0] r_addr_in, output [255:0] rd_out,
 input w_ce_in, input [6:0] w_addr_in, input [255:0] wd_in, input w_mask_in); endmodule
V
prep() { cat <<Y
read_verilog -sv -DOT_WBQ_N1M $L $O/$1.sv
read_verilog -lib $O/bb.v
hierarchy -top $2
proc; flatten; expose -evert t:ot_sram_1r1w_128x256_m1_r0c0_g256
memory -nomap; memory_map; async2sync; opt_clean
rename $2 $1
tee -q -o $O/w_$1.txt select -list w:*
write_rtlil $O/$1.il
Y
}
for s in gold:ot_wbq_root gate:ot_wbq_root_g2; do prep ${s%%:*} ${s##*:} > $O/prep_${s%%:*}.ys
 $Y -q -l $O/prep_${s%%:*}.log $O/prep_${s%%:*}.ys > /dev/null 2>&1 || { echo "MUT=$MUT prep ${s%%:*} FAIL"; exit 3; }; done
# gate names -> gold names: u_g0.X -> X, u_g1.g_lane[k].X -> g_lane[k+4].X, u_g1.copy_row[k] / pending_row[k] -> [k+4],
# u_gG.credit -> credit[G] (u_gG.u_grp.X: the master wrapper level is stripped too); only when the gold name exists (read_pending, the 4-bit group vectors and the group-1 copies of the
# shared control keep their gate names and are matched by equiv_struct / induction);
# the group-1 copies of the shared control state get an equiv_add to the gold register (proven, not assumed: equiv_induct).
python3 -I - $O/w_gold.txt $O/w_gate.txt $O/add.ys > $O/ren.ys <<'P'
import re, sys
gold = {l.strip().split('/', 1)[1] for l in open(sys.argv[1]) if '/' in l}
gate = {l.strip().split('/', 1)[1] for l in open(sys.argv[2]) if '/' in l}
print('cd gate'); add = []
for l in open(sys.argv[2]):
    if '/' not in l: continue
    n = l.strip().split('/', 1)[1]; m = re.match(r'u_g([01])\.(?:u_grp\.)?(.*)$', n)
    if not m: continue
    G, r = int(m[1]), m[2]
    r = re.sub(r'^g_lane\[(\d)\]', lambda x: 'g_lane[%d]' % (int(x[1]) + 4 * G), r)
    r = re.sub(r'^(copy_row|pending_row)\[(\d)\]', lambda x: '%s[%d]' % (x[1], int(x[2]) + 4 * G), r)
    if r == 'credit': r = 'credit[%d]' % G
    if G == 1 and not (r.startswith('g_lane[') or r.startswith(('copy_row[', 'pending_row[', 'credit['))):
        if r in gold and re.match(r'^(base\[\d\]|total\[\d\]|committed\[\d\]|filling|fill_bank|ordinal|copy_q|u_(root|hbm)_reset\.reset_pipe)$', r): add.append((r, n))
        continue
    if r.startswith('read_pending') or r not in gold or r in gate: continue
    print('rename %s %s' % (n, r))
print('cd ..')
open(sys.argv[3], 'w').write('cd equiv\n' + ''.join('equiv_add -try %s_gold %s_gate\n' % a for a in add) + 'equiv_add read_pending_gold[3:0] u_g0.u_grp.read_pending_gate\nequiv_add read_pending_gold[7:4] u_g1.u_grp.read_pending_gate\n' + 'cd ..\n')
P
cat > $O/eq.ys <<Y
read_rtlil $O/gold.il
design -stash gold
read_rtlil $O/gate.il
$(cat $O/ren.ys)
design -stash gate
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
equiv_make gold gate equiv
hierarchy -top equiv
$(cat $O/add.ys)
equiv_struct
equiv_simple -seq 4
equiv_induct -seq 4
equiv_status -assert
Y
timeout ${EQT:-3000} $Y -q -l $O/eq.log $O/eq.ys > /dev/null 2>&1; rc=$?
echo "MUT=$MUT rc=$rc $(grep -E 'Found [0-9]+ \$equiv cells|Of those cells|unproven' $O/eq.log | tr '\n' ' ' | cut -c1-300)"
exit $rc
