`timescale 1ns/1ps
module tb_selector_static;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[3:0]op=0;reg[1:0]pass=0;reg[7:0]addr=0;reg[9:0]k=512;
 reg[2367:0]in_line=0;wire[3:0]out_v;wire[2367:0]out_line;wire fault;
 wire[3:0]selected_v;wire[2367:0]selected_line;
 wire[15:0]threshold_observe;wire[55:0]selected_observe;
 ot_hbm_idx_selector_static #(.MUT(MUT)) dut(.clk_ctl(clk),.clk_q({4{clk}}),.clk_mem({12{clk}}),.*);
 reg[2367:0]lines[0:170];reg gold[0:10943];reg[15:0]scores[0:10943];reg seen[0:10943];
 integer errors=0,checked=0,frame,cyc=0,firstemit,beginframe;string fn;
 always @(posedge clk)cyc<=cyc+1;
 task automatic tick(input integer o,input integer a,input integer p);
  begin @(negedge clk);op=4'(o);addr=8'(a);pass=2'(p);end
 endtask
 always @(negedge clk)begin
  for(integer q=0;q<4;q=q+1)if(out_v[q])begin
   if(firstemit<0)firstemit=cyc;
   for(integer l=0;l<16;l=l+1)if(out_line[q*592+l*37])begin
    integer id;id=int'(out_line[q*592+l*37+17+:20]);checked++;
    if(id>=10944)errors++;
    else begin
     if(!gold[id]||seen[id]||scores[id]!==out_line[q*592+l*37+1+:16])begin errors++;if(errors<8)$display("bad id%0d frame%0d",id,frame);end
     seen[id]=1;
    end
   end
  end
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  for(frame=0;frame<3;frame=frame+1)begin
   fn=$sformatf("lines%0d.hex",frame);$readmemh(fn,lines);
   fn=$sformatf("gold%0d.hex",frame);$readmemh(fn,gold);
   fn=$sformatf("scores%0d.hex",frame);$readmemh(fn,scores);
   for(integer j=0;j<10944;j=j+1)seen[j]=0;
   checked=0;firstemit=-1;beginframe=cyc;
   tick(1,0,0);tick(3,0,0);
   for(integer a=0;a<171;a=a+1)begin tick(2,a,0);in_line=lines[a];end
   tick(0,0,0);tick(0,0,0);
   for(integer b=31;b>=0;b=b-1)tick(5,b,0);
   tick(0,0,0);
   for(integer p=1;p<3;p=p+1)begin
    tick(3,0,p);
    for(integer a=0;a<171;a=a+1)tick(4,a,p);
    tick(0,0,p);tick(0,0,p);
    for(integer b=(p==2?63:31);b>=0;b=b-1)tick(5,b,p);
    tick(0,0,p);
   end
   for(integer a=0;a<171;a=a+1)tick(6,a,2);
   tick(0,0,2);tick(0,0,2);tick(7,0,2);tick(0,0,2);
   for(integer a=0;a<32;a=a+1)tick(8,a,2);
   tick(0,0,2);repeat(3)tick(0,0,2);
   for(integer j=0;j<10944;j=j+1)if(gold[j]!==seen[j])errors++;
   if(checked!=512||fault)errors++;
   $display("IDX_SELECTOR_STATIC MUT%0d frame%0d checked%0d errors%0d fault%0d edges%0d firstemit%0d threshold%h selected%h",MUT,frame,checked,errors,fault,cyc-beginframe,firstemit-beginframe,threshold_observe,selected_observe);
  end
  if(errors)$fatal(1,"fullshape exact selector mismatch");$finish;
 end
endmodule
