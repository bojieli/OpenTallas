`timescale 1ns/1ps
module tb;
reg clk=0;always #0.416 clk=~clk;
reg por_n=0,retained=0;reg[71:0]co=0;reg qlast=0;wire coc,v,drained,fault;
reg ready=0;wire[544:0]tu;wire[72:0]owner;
reg[72:0]pk[0:863-1];reg[544:0]gold[0:118-1];
integer sent=0,got=0,credits=8,cyc=0,errors=0;reg mutant;
ot_hbm_native_candidate_format #(.ENABLE(1))dut(.clk(clk),.por_n(por_n),
.owner_valid(1'b1),.owner_fault(1'b0),.retained(retained),.owner_frame(73'h123456789abcdef),
.owner_rank(7'd73),.tu_kind(1'b1),.tu_dst(8'd9),.co(co),.co_quarter_last(qlast),.coc(coc),
.tu_v(v),.tu_r(ready),.tu(tu),.tu_owner(owner),.drained(drained),.fault(fault));
initial begin
$readmemh("packets.mem",pk);$readmemh("flits.mem",gold);mutant=$test$plusargs("MUT_ID");
repeat(4)@(negedge clk);por_n=1;repeat(2)@(negedge clk);retained=1;
while(got<118 && cyc<863*40+100)begin
@(negedge clk);cyc=cyc+1;ready=(cyc%10==0);co=0;qlast=0;
if(sent<863&&credits>0&&cyc%3!=0)begin
co=pk[sent][71:0];qlast=pk[sent][72];if(mutant&&sent==30)co[38]=!co[38];
sent=sent+1;credits=credits-1;end
@(posedge clk);
if(coc)credits=credits+1;
if(v&&ready)begin
if(tu!==gold[got]||owner!==73'h123456789abcdef)begin errors=errors+1;$display("MISMATCH flit=%0d",got);end
got=got+1;end
if(fault)$fatal(1,"FAULT");
end
@(negedge clk);co=0;qlast=0;repeat(5)@(negedge clk);
if(got!=118||sent!=863||!drained||credits!=8)$fatal(1,"PROTOCOL sent=%0d got=%0d credits=%0d",sent,got,credits);
$display("FORMAT_DONE packets=%0d flits=%0d cycles=%0d errors=%0d",sent,got,cyc,errors);
if(errors)$fatal(1,"EXACT_MISMATCH");$finish;
end
endmodule
