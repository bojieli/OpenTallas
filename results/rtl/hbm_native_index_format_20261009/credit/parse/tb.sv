`timescale 1ns/1ps
module tb;
reg clk=0;always #0.416 clk=~clk;
reg por_n=0,fv=0,tr=0;reg[544:0]flit=0;
wire fr,tv,last,drained,fault;wire[33:0]tuple;wire[7:0]src;wire[15:0]idx;wire[3:0]slot;wire[72:0]owner;
integer sent=0,got=0,cyc=0,j;reg mutant;
ot_hbm_native_candidate_parse #(.ENABLE(1))dut(.clk(clk),.por_n(por_n),
.owner_valid(1'b1),.owner_fault(1'b0),.owner_frame(73'h123456),.expected_kind(1'b1),.expected_dst(8'd9),
.flit_v(fv),.flit_r(fr),.flit(flit),.flit_owner(73'h123456),.tuple_v(tv),.tuple_r(tr),.tuple(tuple),
.tuple_src(src),.tuple_index(idx),.tuple_slot(slot),.quarter_last(last),.tuple_owner(owner),.drained(drained),.fault(fault));
initial begin
mutant=$test$plusargs("MUT_RESERVED");repeat(4)@(negedge clk);por_n=1;
while(got<60&&cyc<1000)begin
@(negedge clk);cyc=cyc+1;fv=sent<4;tr=cyc%5!=0;flit=0;
for(j=0;j<15;j=j+1)flit[34*j+:34]=sent*100+j;
flit[511]=1;flit[527:512]=sent<<14;flit[535:528]=73;flit[543:536]=9;flit[544]=1;
if(mutant)flit[510]=1;
@(posedge clk);
if(fv&&fr)sent=sent+1;
if(tv&&tr)begin
if(tuple!==34'((got/15)*100+got%15)||slot!==4'(got%15)||src!=73||idx!==16'((got/15)<<14)||last!==(got%15==14)||owner!==73'h123456)$fatal(1,"PARSE_MISMATCH");
got=got+1;end
if(fault)$fatal(1,"RESERVED_REJECTED");
end
@(negedge clk);fv=0;repeat(3)@(negedge clk);
if(got!=60||sent!=4||!drained)$fatal(1,"PROTOCOL");
$display("PARSE_DONE tuples=60 cycles=%0d",cyc);$finish;
end
endmodule
