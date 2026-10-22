`timescale 1ns/1ps
module tb_stream;
parameter ND=4, NP=40;
reg clk=0; always #5 clk=~clk;
reg rst_n=0;
reg [255:0] desc[0:ND-1]; reg [511:0] pay[0:NP-1];
integer cycle=0; integer finished[0:1];
initial begin $readmemh("desc.mem",desc);$readmemh("pay.mem",pay);repeat(8)@(negedge clk);rst_n=1;end
always @(posedge clk)begin
 cycle<=cycle+1;
 if(cycle>200000)$fatal(1,"STREAM_TIMEOUT");
 if(finished[0]&&finished[1])begin $display("STREAM_PAIR_DONE cycles=%0d",cycle);$finish;end
end
genvar g;
generate for(g=0;g<2;g=g+1)begin:pair
 integer di=0,pi=0,writes=0,dones=0,idle=0,fd;
 reg [31:0]rnd=32'h13482971+g;
 wire dv=rst_n&&di<ND&&rnd[0];wire iv=rst_n&&pi<NP&&rnd[1];wire ready=rst_n&&rnd[2];
 wire dr,ir,wv,rv,dvout,busy;wire[31:0]wa,ra,ns,nb;wire[255:0]wd;wire[7:0]tag;
 reg held=0;reg[31:0]held_a;reg[255:0]held_d;
 initial begin finished[g]=0;fd=$fopen(g?"candidate.log":"baseline.log","w");end
 qkd_host_native_engine #(.AW(32),.HDMAX(128),.KVHMAX(2),.QKV(1),.APIPE(0),.SPIPE6(g),.QPIPE(2),.NATIVE_ROWS(1),.QMUT(0)) dut(
 .clk(clk),.clk_bank({2{clk}}),.clk_out(clk),.rst_n(rst_n),
 .d_v(dv),.d_rdy(dr),.d_data(di<ND?desc[di]:256'd0),.in_v(iv),.in_rdy(ir),.in_data(pi<NP?pay[pi]:512'd0),
 .w_v(wv),.w_rdy(ready),.w_addr(wa),.w_data(wd),.r_v(rv),.r_rdy(1'b0),.r_addr(ra),.rd_v(1'b0),.rd_data(256'd0),
 .done_v(dvout),.done_tag(tag),.busy(busy),.n_sectors(ns),.n_beats(nb));
 always @(negedge clk)rnd<={rnd[30:0],rnd[31]^rnd[21]^rnd[1]^rnd[0]};
 always @(posedge clk)if(rst_n&&!finished[g])begin
  if(dv&&dr)di<=di+1;if(iv&&ir)pi<=pi+1;
  if(held&&(!wv||wa!==held_a||wd!==held_d))$fatal(1,"STALLED_WRITE_CHANGED engine=%0d",g);
  held<=wv&&!ready;if(wv&&!ready)begin held_a<=wa;held_d<=wd;end
  if(rv)$fatal(1,"UNEXPECTED_READ");
  if(wv&&ready)begin $fdisplay(fd,"W %08x %064x",wa,wd);writes<=writes+1;end
  if(dvout)begin $fdisplay(fd,"D %02x %0d",tag,writes);dones<=dones+1;end
  if(di==ND&&pi==NP&&!busy)idle<=idle+1;else idle<=0;
  if(idle==8)begin
   if(dones!=ND||ns!=writes)$fatal(1,"STREAM_ACCOUNTING engine=%0d dones=%0d ns=%0d writes=%0d",g,dones,ns,writes);
   $fclose(fd);finished[g]=1;$display("STREAM_ENGINE_DONE engine=%0d writes=%0d dones=%0d",g,writes,dones);
  end
 end
end endgenerate
endmodule
