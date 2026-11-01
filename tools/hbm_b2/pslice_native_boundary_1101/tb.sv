`timescale 1ns/1ps
module tb;
 parameter integer MUT=0;
 reg clk=0; always #0.4165 clk=~clk;
 reg rst_n=0,cfg_we=0,start=0;
 reg[15:0] cfg_bank=0,length=0;reg[6:0] cfg_row=0;reg[255:0]cfg_data=0;
 wire[2490-1:0] a,b;
 old_ot_hbm_su_programme_pslice_c5 #(.SB(2470),.NCX(1)) gold
  (.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_bank(cfg_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),.start(start),.length(length),
   .busy(a[2489]),.valid(a[2488]),.done(a[2487]),.fault(a[2486]),.edge_index(a[2485:2470]),.command(a[2469:0]));
 ot_hbm_su_programme_pslice_c5 #(.SB(2470),.NCX(1),.NATIVE_PINS(1),.MUT(MUT)) dut
  (.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_bank(cfg_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),.start(start),.length(length),
   .busy(b[2489]),.valid(b[2488]),.done(b[2487]),.fault(b[2486]),.edge_index(b[2485:2470]),.command(b[2469:0]));
 integer cycles=0,bad=0,known=0,unknown=0,valids=0,nonzero=0,writes=0,starts=0,warm=0;
 integer j;
 always @(posedge clk) begin
  #0.001;cycles=cycles+1;
  for(j=0;j<2490;j=j+1)begin
   if(a[j]===1'b0 || a[j]===1'b1)begin
    known=known+1;
    if(b[j]!==a[j])begin
     bad=bad+1;
     if(bad<9)$display("MISMATCH cycle=%0d bit=%0d ref=%b cand=%b rst=%b cfg=%b start=%b",cycles,j,a[j],b[j],rst_n,cfg_we,start);
    end
   end else unknown=unknown+1;
  end
  if(a[2488]===1'b1)begin valids=valids+1;if(a[2469:0]!==2470'b0)nonzero=nonzero+1;end
  if(cfg_we)writes=writes+1;if(start)starts=starts+1;
 end
 task drive(input integer we,bank,row,input reg[255:0]dat,input integer st,len);
 begin @(negedge clk);cfg_we=we;cfg_bank=bank;cfg_row=row;cfg_data=dat;start=st;length=len;end endtask
 integer col,bank,row,k;
 initial begin
  // First writes before and immediately on root release exercise old reset-qualified capture.
  drive(1,0,0,{16{16'd1}},0,0);drive(1,4,1,{8{32'h12345678}},0,0);
  @(negedge clk);rst_n=1;
  repeat(12)drive(1,4,1,{8{32'hfedcba98}},0,0);
  for(col=0;col<10;col=col+1)begin
   drive(1,32*col,0,{16{16'd1}},0,0);
   for(bank=4;bank<17;bank=bank+1)
    for(row=0;row<3;row=row+1)drive(1,32*col+bank,row,{8{32'h10203040^(col<<16)^(bank<<8)^row}},0,0);
  end
  repeat(10)drive(0,0,0,0,0,0);
  for(k=0;k<12;k=k+1)begin
   drive(0,0,0,0,1,16+k);
   repeat(55)drive(0,0,0,0,0,0);
  end
  // Reset remains short; no 64-edge assertion assumption. Memory contents persist.
  @(negedge clk);rst_n=0;cfg_we=1;cfg_bank=4;cfg_row=1;cfg_data={8{32'h55555555}};warm=warm+1;
  #0.4165;rst_n=1;
  repeat(12)drive(1,4,1,{8{32'h89abcdef}},0,0);
  repeat(10)drive(0,0,0,0,0,0);
  drive(0,0,0,0,1,31);repeat(60)drive(0,0,0,0,0,0);
  @(negedge clk);#0.1;rst_n=0;warm=warm+1;#0.08;rst_n=1;
  repeat(14)drive(1,4,1,{8{32'h13579bdf}},0,0);
  for(k=0;k<500;k=k+1)begin
   drive(($urandom%8)==0,32*($urandom%11)+($urandom%18),$urandom%3,{8{$urandom}},($urandom%17)==0,1+$urandom%32);
  end
  repeat(80)drive(0,0,0,0,0,0);
  $display("RESULT MUT=%0d cycles=%0d mismatches=%0d known=%0d unknown=%0d valid=%0d nonzero=%0d writes=%0d starts=%0d warm=%0d",MUT,cycles,bad,known,unknown,valids,nonzero,writes,starts,warm);
  if(bad==0 && valids>40 && nonzero>0 && starts>12 && warm==2)$display("PASS");else $display("FAIL");
  $finish;
 end
endmodule
