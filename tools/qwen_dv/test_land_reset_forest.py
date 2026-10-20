"""Fleet-only comparison of unchanged reset ages and >32 chunk distribution."""
from pathlib import Path
import argparse,subprocess
TB=r'''
`timescale 1ps/1ps
module tb;
parameter integer PHASE=0,MUTANT=0;
localparam integer W=1088,C=(W+23)/24;
reg wc=0,rc=0,rsi=0;
reg[W-1:0] data=1;
always #500 wc=~wc;
initial begin #(500+PHASE);forever begin rc=~rc;#500;end end
always @(negedge wc) data<={data[W-2:0],data[W-1]^data[19]^data[3]^data[0]};
initial begin #10000;rsi=1;#490000;rsi=0;#12000;rsi=1;end
wire old_wr,old_rr;
wire[C:0] wr,rr;
ot_pl_pad #(.W(1),.N(8)) wp(.ck(wc),.d(rsi),.q(old_wr));
ot_pl_pad #(.W(1),.N(8)) rp(.ck(rc),.d(rsi),.q(old_rr));
ot_pl_land_reset_forest #(.DEPTH(8),.LEAVES(C+1)) wf(.ck(wc),.d(rsi),.q(wr));
ot_pl_land_reset_forest #(.DEPTH(MUTANT?9:8),.LEAVES(C+1)) rf(.ck(rc),.d(rsi),.q(rr));
wire[4*W-1:0] bank0,bank1;
wire[11:0] epo0,epo1;
wire[4*C-1:0] vld0,vld1;
wire[W-1:0] o0,o1;
ot_pl_land_chunk_w #(.W(W)) w0(.ck(wc),.rsi(old_wr),.i(data),.bank(bank0),.epo(epo0),.vld(vld0));
ot_pl_land_vector_reset_w #(.W(W)) w1(.ck(wc),.rsi(wr[C:1]),.i(data),.bank(bank1),.epo(epo1),.vld(vld1));
ot_pl_land_chunk_r #(.W(W)) r0(.ck(rc),.rsi(old_rr),.bank(bank0),.epo(epo0),.vld(vld0),.o(o0));
ot_pl_land_vector_reset_r #(.W(W)) r1(.ck(rc),.rsi(rr[C:1]),.bank(bank1),.epo(epo1),.vld(vld1),.o(o1));
integer checks=0;
always @(posedge rc) begin
    #1;
    if($time>9000) begin
        if(rr!={(C+1){old_rr}}) $fatal(1,"RESET_FOREST_AGE_MISMATCH phase=%0d mutant=%0d",PHASE,MUTANT);
        if($time>30000 && o0!==o1) $fatal(1,"RESET_FOREST_DATA_MISMATCH phase=%0d time=%0t",PHASE,$time);
        checks=checks+1;
    end
    if(checks==1400) begin $display("PASS reset forest phase=%0d chunks=%0d leaves=%0d checks=%0d two resets",PHASE,C,C+1,checks);$finish;end
end
always @(posedge wc) begin #1;if($time>9000 && wr!={(C+1){old_wr}}) $fatal(1,"RESET_FOREST_WRITE_AGE_MISMATCH");end
initial begin #1800000;$fatal(1,"timeout");end
endmodule
'''
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);(out/'tb.sv').write_text(TB)
    src=['rtl/common/landed_parent/'+x for x in ['ot_pl_land.sv','ot_pl_land_field_copies.sv','ot_pl_land_reset_forest.sv']]
    for phase in [-80,0,80]:
        for mutant in [0,1]:
            stem=f'p{phase}_m{mutant}';obj=out/stem
            cmd=['verilator','--binary','--timing','-Wno-fatal','-DSYNTHESIS','--top-module','tb','-j','2','--Mdir',str(obj),f'-GPHASE={phase}',f'-GMUTANT={mutant}',*src,str(out/'tb.sv')]
            with(out/f'{stem}_build.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
            with(out/f'{stem}.log').open('w') as log:r=subprocess.run([str(obj.resolve()/'Vtb')],stdout=log,stderr=subprocess.STDOUT)
            msg=(out/f'{stem}.log').read_text()
            if not mutant and(r.returncode or 'PASS reset forest' not in msg):raise RuntimeError(msg)
            if mutant and(not r.returncode or 'RESET_FOREST_AGE_MISMATCH' not in msg):raise RuntimeError('missing reset age witness: '+msg)
            print(stem,'PASS' if not mutant else 'MUTANT_REJECTED',flush=True)
    script='read_verilog -sv -DSYNTHESIS '+' '.join(src[1:])+'; hierarchy -check -top ot_pl_land_reset_forest; synth -top ot_pl_land_reset_forest -flatten -noabc -nofsm -noshare; write_json '+str(out/'netlist.json')
    with(out/'yosys.log').open('w') as log:subprocess.run(['yosys','-p',script],stdout=log,stderr=subprocess.STDOUT,check=True)
if __name__=='__main__':main()
