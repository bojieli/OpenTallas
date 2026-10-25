"""Build the head SerDes adapter's exact-reuse vehicle from the existing real
KP4/PMA loop bench. Usage: python3 tools/s81_head/serdes_link_eq.py OUTDIR.
Run OUTDIR/run.sh via ot-run. No physical PHY/pad-plan closure is claimed.
"""
from pathlib import Path
import sys,shutil
ROOT=Path(__file__).resolve().parents[2]
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
link=ROOT/'rtl/dsrom_sys/s81_link'
text=(link/'tb_s81_pdie_link.sv').read_text()
a='ot_pdie_serdes #(.DMUT(DMUT)) u_a (.clk(ca), .rst(rst), .tx(txa), .rx(rxa), .st(sta), .pma_tx(pa), .pma_tck(tca), .pma_rx(pb), .pma_rck(tcb));'
b='''ot_s81hd_serdes_link u_a (.ck(ca), .rst_n(rst), .coll_i0(txa), .coll_o0({sta,rxa}), .pma_tx(pa), .pma_tck(tca), .pma_rx(pb), .pma_rck(tcb));
        wire [511:0] ref_rx; wire [1:0] ref_st; wire [543:0] ref_pma; wire ref_tck;
        ot_pdie_serdes ref_a (.clk(ca), .rst(rst), .tx(txa), .rx(ref_rx), .st(ref_st), .pma_tx(ref_pma), .pma_tck(ref_tck), .pma_rx(pb), .pma_rck(tcb));
        integer eq_bad=0;
        always @(posedge ca) if(rst && cyc>100)begin
            #0.001;
            if({sta,rxa,pa,tca} !== {ref_st,ref_rx,ref_pma,ref_tck})begin
                eq_bad=eq_bad+1;
                if(eq_bad<4)$display("HEAD_SERDES_MISMATCH cyc=%0d",cyc);
            end
        end
        final begin
            if(eq_bad)$display("HEAD_SERDES_EQ FAIL mismatches=%0d",eq_bad);
            else $display("HEAD_SERDES_EQ PASS");
        end'''
assert a in text;text=text.replace(a,b,1);(out/'tb_s81_pdie_link.sv').write_text(text)
files=['ot_s81_kp4_common.sv','ot_s81_kp4_enc.sv','ot_s81_kp4_bm.sv','ot_s81_kp4_dsyn.sv','ot_s81_kp4_ddly.sv','ot_s81_kp4_dchn.sv','ot_s81_kp4_dout.sv','ot_s81_kp4_dec.sv','ot_pdie_serdes.sv','ot_s81_gf1024.svh','ot_s81_kp4_enc_mat.svh','ot_s81_kp4_syn_mat.svh']
for f in files:shutil.copyfile(link/f,out/f)
for n in ['ot_sram_1r1w2c_64x546_m1','ot_sram_1r1w_32x546_m1']:
 shutil.copyfile(ROOT/'physical/asap7_memory_macros'/n/(n+'.v'),out/(n+'.v'))
shutil.copyfile(ROOT/'rtl/dsrom_sys/s81_head/ot_s81hd_serdes_link.sv',out/'ot_s81hd_serdes_link.sv')
(out/'run.sh').write_text('''#!/bin/bash
set -uo pipefail
D=$(cd "$(dirname "$0")" && pwd);cd "$D"
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
for mode in good mutant; do
 args=(); [ "$mode" = mutant ] && args=(-DOT_S81HD_SERDES_MUT_STATUS)
 verilator --binary --timing -j 8 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT +incdir+. --top-module tb_s81_pdie_link -GSERDES=1 -GNB=1200 "${args[@]}" --Mdir "obj_$mode" -o tb *.sv ot_sram_1r1w2c_64x546_m1.v ot_sram_1r1w_32x546_m1.v > "build_$mode.log" 2>&1 || { tail -8 "build_$mode.log";exit 2; }
 "./obj_$mode/tb" +verilator+seed+3 > "run_$mode.log" 2>&1 || exit 3
 tail -6 "run_$mode.log"
 if [ "$mode" = good ]; then grep -q "HEAD_SERDES_EQ PASS" "run_$mode.log" && grep -q "stA=10 stB=10 PASS" "run_$mode.log" || exit 4
 else grep -q "HEAD_SERDES_EQ FAIL" "run_$mode.log" || exit 5;echo MUTANT_CAUGHT;fi
done
''')
print(out)
