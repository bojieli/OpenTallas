"""Generate/run private field-copy component tests on an admitted fleet host."""
from pathlib import Path
import argparse, subprocess

TB=r'''
`timescale 1ps/1ps
module tb;
parameter integer PHASE=0, MUTANT=0;
reg wc=0,rc=0,rsi=0;
reg [31:0] rng=32'h95e31a67;
always #500 wc=~wc;
initial begin #(500+PHASE); forever begin rc=~rc; #500; end end
always @(negedge wc) rng<={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
initial begin #10000;rsi=1;#490000;rsi=0;#12000;rsi=1;end
wire [3:0] bank,vld;
wire [11:0] epo;
wire reference;
wire [69:0] copies;
ot_pl_land_local_w #(.W(1)) w(.ck(wc),.rsi(rsi),.i(rng[0]),.bank(bank),.epo(epo),.vld(vld));
ot_pl_land_local_r #(.W(1),.K(2)) r(.ck(rc),.rsi(rsi),.bank(bank),.epo(epo),.vld(vld),.o(reference));
ot_pl_land_field_copies #(.COPIES(70),.K(MUTANT?3:2)) u(.ck(rc),.rsi(rsi),.bank(bank),.epo(epo),.vld(vld),.o(copies));
integer checks=0;
always @(posedge rc) begin
    #1;
    if($time>30000) begin
        if(copies!={70{reference}}) $fatal(1,"FIELD_COPY_MISMATCH phase=%0d mutant=%0d time=%0t ref=%0b copies=%h",PHASE,MUTANT,$time,reference,copies);
        checks=checks+1;
    end
    if(checks==1400) begin $display("PASS field copies phase=%0d mutant=%0d checks=%0d two resets",PHASE,MUTANT,checks);$finish;end
end
initial begin #1800000;$fatal(1,"timeout");end
endmodule
'''

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    (out/'tb.sv').write_text(TB)
    sources=['rtl/common/landed_parent/ot_pl_land.sv','rtl/common/landed_parent/ot_pl_land_field_copies.sv']
    for phase in [-80,0,80]:
        for mutant in [0,1]:
            stem=f'p{phase}_m{mutant}';obj=out/stem
            cmd=['verilator','--binary','--timing','-Wno-fatal','-DSYNTHESIS','--top-module','tb','-j','2','--Mdir',str(obj),f'-GPHASE={phase}',f'-GMUTANT={mutant}',*sources,str(out/'tb.sv')]
            with (out/f'{stem}_build.log').open('w') as log: subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
            with (out/f'{stem}.log').open('w') as log:r=subprocess.run([str(obj.resolve()/'Vtb')],stdout=log,stderr=subprocess.STDOUT)
            msg=(out/f'{stem}.log').read_text()
            if not mutant and (r.returncode or 'PASS field copies' not in msg):raise RuntimeError(msg)
            if mutant and (not r.returncode or 'FIELD_COPY_MISMATCH' not in msg):raise RuntimeError('missing wrong-age witness: '+msg)
            print(stem,'PASS' if not mutant else 'MUTANT_REJECTED',flush=True)
    # Native generic synthesis, preserving kept individual output flop hierarchy.
    script='read_verilog -sv -DSYNTHESIS '+sources[1]+'; chparam -set COPIES 70 ot_pl_land_field_copies; hierarchy -check -top ot_pl_land_field_copies; synth -top ot_pl_land_field_copies -flatten -noabc -nofsm -noshare; write_json '+str(out/'netlist.json')
    with (out/'yosys.log').open('w') as log:subprocess.run(['yosys','-p',script],stdout=log,stderr=subprocess.STDOUT,check=True)
if __name__=='__main__':main()
