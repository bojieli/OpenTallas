#!/usr/bin/env python3
"""Full37word localphase upset and actual8-cell identity seats; run remotely."""
import argparse,json,subprocess,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BANK='rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank_veto.sv'
TB=r'''
module tb;
reg clk=0;always #5 clk=~clk;
reg por_n=0;wire [2367:0] q;wire normal,fault,repairing;
ot_hbm_w2_protected_bank_veto_on #(.WORDS(37),.STAGE(0),.DIST(1),.LOCAL_PHASE(1),.HOLD_SEAT(1)) dut(
.clk(clk),.por_n(por_n),.load(1'b0),.load_sel(1'b0),.fatal(1'b0),.encoded_d(2664'b0),.q(q),.normal(normal),.fault(fault),.repairing(repairing));
integer k;
initial begin
repeat(2)@(negedge clk);por_n=1;
for(k=0;k<40&&!normal;k=k+1)@(negedge clk);
if(!normal||fault||q!==0)$fatal(1,"boot");
force dut.word[16].lph.u_phase.q=4'b1010;
for(k=0;k<6&&!fault;k=k+1)@(negedge clk);
if(!fault||normal)$fatal(1,"unchecked phase selection replica escaped");
$display("PASS full37word localphase selection upset");$finish;
end
initial begin #5000;$fatal(1,"timeout");end
endmodule
'''
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False);tb=out/'tb.sv';tb.write_text(TB)
    bank=ROOT/BANK
    results=[]
    for name,text,expected in [('positive',bank.read_text(),0),('missing_phase_identity',bank.read_text().replace('(local_phase!={sel_bit,phase})',"1'b0"),1),('odd_delay_chain',bank.read_text().replace('n<8;n=n+1','n<7;n=n+1').replace('assign y=stage[8]','assign y=stage[7]'),1)]:
        rtl=out/(name+'.sv');rtl.write_text(text);sim=out/(name+'.vvp')
        p=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(sim),str(ROOT/'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv'),str(ROOT/'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv'),str(rtl),str(tb)],capture_output=True,text=True)
        (out/(name+'.compile.log')).write_text(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError(p.stderr)
        p=subprocess.run(['vvp',str(sim)],capture_output=True,text=True);(out/(name+'.run.log')).write_text(p.stdout+p.stderr)
        results.append(dict(name=name,returncode=p.returncode,expected=expected,log=p.stdout+p.stderr))
        if bool(p.returncode)!=bool(expected):raise RuntimeError(str(results[-1]))
        sim.unlink()
    record=dict(verdict='PASS',cases=results,source_sha256={BANK:hashlib.sha256(bank.read_bytes()).hexdigest(),'tools/w2_phase_copy_gate.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    (out/'terminal.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
if __name__=='__main__':main()
