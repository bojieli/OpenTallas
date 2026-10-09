`timescale 1ns/1ps
module tb_qwen_dspark_transient_kv;
 reg clk=0,rst=0,bv=0,ret=0,fence=1,wv=0,wd_r=0,rv=0,orr=0;
 always #0.555555 clk=~clk;
 reg [63:0] bid=64'hfedcba9876543210,wid,rid;
 reg [13:0] bp=8191,wp,rp;reg [2:0] ww,rw;reg [7:0] ws=211,rs=249;
 reg [511:0] data;wire br,retr,wr,w_done,rr,ov,fault;
 wire [63:0] wdid,oid;wire [7:0] wds,os;wire [13:0] op;wire [2:0] ow;
 wire [511:0] output_data;wire [31:0] corrected;
 ot_qwen_dspark_transient_kv #(.ENABLE(1),.POSITIONS(8)) dut(
  .clk(clk),.rst_n(rst),.begin_v(bv),.begin_r(br),.begin_id(bid),.begin_pos(bp),.retire_v(ret),.allcopy_fenced(fence),.retire_r(retr),
  .w_v(wv),.w_r(wr),.w_id(wid),.w_pos(wp),.w_word(ww),.w_sequence(ws),.w_data(data),.w_done_v(w_done),.w_done_r(wd_r),.w_done_id(wdid),.w_done_sequence(wds),
  .r_v(rv),.r_r(rr),.r_id(rid),.r_pos(rp),.r_word(rw),.r_sequence(rs),.o_v(ov),.o_r(orr),.o_data(output_data),.o_id(oid),.o_sequence(os),.o_pos(op),.o_word(ow),.fault(fault),.corrected_reads(corrected));
 function automatic [511:0] pattern(input integer row);
  for(integer b=0;b<64;b=b+1)pattern[b*8+:8]=8'(row*17+b*29);
 endfunction
 task automatic reset;
  begin @(negedge clk);rst=0;wv=0;rv=0;ret=0;bv=0;wd_r=0;orr=0;fence=1;repeat(3)@(negedge clk);rst=1;repeat(3)@(negedge clk);end
 endtask
 task automatic start;
  begin @(negedge clk);if(!br)$fatal(1,"no owner credit");bv=1;@(negedge clk);bv=0;end
 endtask
 task automatic write_row(input integer row);
  integer t;
  begin @(negedge clk);if(!wr)$fatal(1,"no write credit");wid=bid;wp=bp+14'(row/8);ww=3'(row%8);data=pattern(row);wv=1;
   @(negedge clk);wv=0;t=0;while(!w_done&&t<10)begin @(negedge clk);t=t+1;end
   if(!w_done||fault||wdid!==bid||wds!==ws)$fatal(1,"actual macro write completion missing");
   repeat(3)begin @(negedge clk);if(!w_done||wr||rr)$fatal(1,"write credit earlyrelease");end
   wd_r=1;@(negedge clk);wd_r=0;
  end
 endtask
 task automatic read_row(input integer row,input integer expect_fault);
  integer t;
  begin @(negedge clk);if(!rr)$fatal(1,"no read credit");rid=bid;rp=bp+14'(row/8);rw=3'(row%8);rv=1;
   @(negedge clk);rv=0;t=0;while(!ov&&!fault&&t<10)begin @(negedge clk);t=t+1;end
   if(expect_fault)begin if(!fault||ov||wr||rr)$fatal(1,"UE not quarantined");end
   else begin
    if(!ov||fault||output_data!==pattern(row)||oid!==bid||os!==rs||op!==rp||ow!==rw)$fatal(1,"transient payload/14bitposition/cohort failure row=%0d",row);
    repeat(3)begin @(negedge clk);if(!ov||wr||rr||output_data!==pattern(row)||oid!==bid)$fatal(1,"read lease unstableduringstall");end
    orr=1;@(negedge clk);orr=0;
   end
  end
 endtask
 integer row,bitindex;
 initial begin
  reset();start();for(row=0;row<64;row=row+1)write_row(row);
  for(row=63;row>=0;row=row-1)read_row(row,0);
  for(bitindex=0;bitindex<720;bitindex=bitindex+1)begin
   @(negedge clk);
   if(bitindex<512)dut.memories[0].macro_inst.arr[0][bitindex]=~dut.memories[0].macro_inst.arr[0][bitindex];
   else dut.memories[1].macro_inst.arr[0][bitindex-512]=~dut.memories[1].macro_inst.arr[0][bitindex-512];
   read_row(0,0);
   @(negedge clk);
   if(bitindex<512)dut.memories[0].macro_inst.arr[0][bitindex]=~dut.memories[0].macro_inst.arr[0][bitindex];
   else dut.memories[1].macro_inst.arr[0][bitindex-512]=~dut.memories[1].macro_inst.arr[0][bitindex-512];
  end
  if(corrected!==720)$fatal(1,"correction counter wrong");
  @(negedge clk);dut.memories[0].macro_inst.arr[0][0]=~dut.memories[0].macro_inst.arr[0][0];dut.memories[0].macro_inst.arr[0][1]=~dut.memories[0].macro_inst.arr[0][1];read_row(0,1);
  reset();bid=bid+1;start();write_row(0);
  @(negedge clk);fence=0;ret=1;@(negedge clk);ret=0;@(negedge clk);if(!fault||wr||rr)$fatal(1,"premature unfenced retirement");
  reset();bid=bid+1;start();
  @(negedge clk);rid=bid;rp=bp;rw=0;rv=1;@(negedge clk);rv=0;@(negedge clk);if(!fault||ov)$fatal(1,"unwritten read accepted");
  reset();bid=bid+1;start();write_row(0);
  @(negedge clk);rid=bid+1;rp=bp;rw=0;rv=1;@(negedge clk);rv=0;@(negedge clk);if(!fault||ov)$fatal(1,"stale owner read accepted");
  $display("QWEN_TRANSIENT_KV_PASS realmacros=2 rows=64 words512=1 positions8191through8198=1 fullcohort64_seq8=1 singlebit720=1 UE_quarantine=1 heldcredits=1 negative_fence_unwritten_stale=1");$finish;
 end
endmodule
