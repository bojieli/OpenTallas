#!/usr/bin/env python3
"""Production-width storage mechanism gate; no native arithmetic/age qualification."""
import pathlib, subprocess, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
RTL = ROOT/'rtl/dsrom_sys/s81_ph/svc/h/ot_s81_svc_static_store.sv'
TB = r'''
module tb;
parameter WIDTH=2132, DEPTH=8, COUNT=160, MUTANT=0;
localparam AW=$clog2(DEPTH);
reg clk=0; always #5 clk=~clk;
reg rst_n=0, put_slot=0, producer_v=0, get_slot=0, available=1;
reg [AW-1:0] pa=0, ga=0;
reg [31:0] pi=0, gi=0, actual=0;
reg [WIDTH-1:0] data=0;
wire rv; wire [31:0] ri; wire [WIDTH-1:0] rd; wire [6:0] fc;
ot_s81_svc_static_store #(.WIDTH(WIDTH),.DEPTH(DEPTH)) dut(
.clk(clk),.rst_n(rst_n),.put_slot(put_slot),.put_addr(pa),.put_id(pi),
.producer_v(producer_v),.producer_id(actual),.producer_data(data),
.get_slot(get_slot),.get_addr(ga),.get_id(gi),.consumer_available(available),
.result_v(rv),.result_id(ri),.result_data(rd),.fault_code(fc));
integer cycle, sent=0;
initial begin
repeat(2) @(negedge clk); rst_n=1;
// Full score shape: 640 rows / four lanes = 160 actual-width score records.
// Second elaboration covers all eight 8456-bit PV records. This is a storage
// boundary fixture, not a guessed arithmetic production microcalendar.
for(cycle=0; cycle<COUNT+DEPTH+2; cycle=cycle+1) begin
put_slot=cycle<COUNT; producer_v=put_slot;
pa=cycle%DEPTH; pi=cycle; actual=pi; data={WIDTH{1'b1}} ^ WIDTH'(cycle);
get_slot=cycle>=DEPTH && cycle<COUNT+DEPTH;
ga=(cycle-DEPTH)%DEPTH; gi=cycle-DEPTH;
if(cycle==3 && MUTANT==1) producer_v=0;
if(cycle==3 && MUTANT==2) actual=999;
if(cycle==3 && MUTANT==3) pa=0;
if(cycle==DEPTH && MUTANT==4) available=0;
if(cycle==COUNT && MUTANT==5) begin producer_v=1; actual=3; end
if(cycle==DEPTH && MUTANT==6) ga=DEPTH-1;
@(posedge clk); #1;
if(rv !== get_slot) $fatal(1,"calendar moved");
if(rv) begin
sent=sent+1;
if(MUTANT==0 && (ri!==gi || rd!==({WIDTH{1'b1}} ^ WIDTH'(gi))))
$fatal(1,"payload/id mismatch");
end
@(negedge clk);
end
if(sent!=COUNT) $fatal(1,"drain/done cycle changed");
if(MUTANT==0 && fc!=0) $fatal(1,"normal fault %h",fc);
if(MUTANT==1 && !fc[1]) $fatal(1,"missing producer undetected");
if(MUTANT==2 && !fc[2]) $fatal(1,"identity mutant undetected");
if(MUTANT==3 && !fc[5]) $fatal(1,"capacity mutant undetected");
if(MUTANT==4 && !fc[3]) $fatal(1,"unavailable drain undetected");
if(MUTANT==5 && !fc[0]) $fatal(1,"late producer undetected");
if(MUTANT==6 && !fc[4]) $fatal(1,"stale slot undetected");
$display("PASS width=%0d depth=%0d count=%0d mutant=%0d faults=%h",WIDTH,DEPTH,COUNT,MUTANT,fc);
$finish;
end
endmodule
'''
def main():
    with tempfile.TemporaryDirectory(prefix='s81-static-store-') as work:
        work=pathlib.Path(work); (work/'tb.sv').write_text(TB)
        for width,depth,count in [(2132,8,160),(8456,4,8)]:
            for mutant in range(7):
                out=work/'sim'
                subprocess.run(['iverilog','-g2012','-s','tb',f'-Ptb.WIDTH={width}',
                    f'-Ptb.DEPTH={depth}',f'-Ptb.COUNT={count}',f'-Ptb.MUTANT={mutant}',
                    '-o',str(out),str(RTL),str(work/'tb.sv')],check=True)
                subprocess.run(['vvp',str(out)],check=True)
if __name__=='__main__': main()
