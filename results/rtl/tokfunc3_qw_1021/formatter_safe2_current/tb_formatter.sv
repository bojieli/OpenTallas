`timescale 1ns/1ps
module tb_formatter;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,eb=0,iv=0,slot=0;reg[17:0]pos=0,ino=1,ini=0;reg[1:0]ik=0,wi=0;
 reg[63:0]we=0;reg[1535:0]wa=0;reg[2047:0]wd=0;
 wire idle,drained,wv,fault;wire[10:0]tag;wire[511:0]data;wire[7:0]fc;
 ot_qfd_su_kv_static_posted #(.ENABLE(1),.HEADS(1),.KV_FP8(1),.SAFE(2),.LOCAL_CTL(0)) dut
 (.clk(clk),.rst_n(rst_n),.epoch_begin(eb),.epoch_pos(pos),.issue_v(iv),.issue_kind(ik),.issue_nout(ino),.issue_nin(ini),
 .kv_we(we),.kv_waddr(wa),.kv_wdata(wd),.epoch_idle(idle),.drained(drained),.word_v(wv),.word_tag(tag),.word_data(data),
 .word_slot(slot),.word_index(wi),.word_index_pub(16'd0),.epoch_begin_pub(2'd0),.word_slot_pub(2'd0),.word_ctl_pub(),.fault(fault),.fault_code(fc));
 integer mode=0,p=255,checks=0,cyc=0,startslot=0;always @(posedge clk)cyc<=cyc+1;
 function automatic[7:0] code(input integer idx);code=8'((idx*37+19)%120+1);endfunction
 function automatic[31:0] decode(input[7:0] b);
 reg[3:0]e;reg[2:0]m;begin e=b[6:3];m=b[2:0];
 if(e!=0)decode={b[7],8'(e+120),m,20'd0};
 else if(m[2])decode={b[7],8'd120,m[1:0],21'd0};
 else if(m[1])decode={b[7],8'd119,m[0],22'd0};
 else if(m[0])decode={b[7],8'd118,23'd0};else decode={b[7],31'd0};end endfunction
 task tick;begin @(posedge clk);#1;end endtask
 task drive;begin @(negedge clk);end endtask
 task require(input bit ok,input string why);begin checks++;if(!ok)begin $display("FMT_FAIL mode=%0d cycle=%0d fault=%0b code=%h %s",mode,cyc,fault,fc,why);$fatal;end end endtask
 initial begin
  if($value$plusargs("MODE=%d",mode));if($value$plusargs("POS=%d",p));
  repeat(4)tick();drive();rst_n=1;pos=p;eb=1;tick();drive();eb=0;repeat(3)tick();
  for(integer k=0;k<3;k++)begin drive();iv=1;ik=2'(k);ini=(k==0)?128:64;tick();end
  drive();iv=0;repeat(3)tick();
  // Exactly all 256 distinct K/V byte seats, eight actual native lanes each edge.
  for(integer b=0;b<32;b++)begin
   drive();we=64'hff;wa=0;wd=0;
   for(integer l=0;l<8;l++)begin
    integer idx,dim;idx=b*8+l;dim=idx%128;
    wa[24*l+:24]=(idx<128)?24'(((p/16)*128+dim)*16+p%16):24'(1048576+p*128+dim);
    wd[32*l+:32]=decode(code(idx));
   end
   if(mode==1&&b==31)we=64'h7f; // missing byte must be detected at compiled word slot
   if(mode==2&&b==7)wa[0+:24]=24'(((p/16)*128+55)*16+p%16); // duplicate seat
   if(mode==3&&b==4)wd[0+:32]=32'h7fc00001; // not a representable native FP8 value
   tick();
  end
  drive();we=0;repeat(5)tick();
  if(mode==2||mode==3)begin require(fault,"malformed native write was accepted");require(fc[(mode==2)?3:1],"wrong fault bit");$display("FMT_CAUSAL_REJECT mode=%0d checks=%0d code=%h",mode,checks,fc);$finish;end
  for(integer w=0;w<4;w++)begin
   drive();slot=1;wi=2'(w);startslot=cyc;tick();require(!wv,"word escaped before two capture edges");drive();slot=0;tick();
   if(mode==1&&w==3)begin require(fault&&fc[6]&&!wv,"missing seat did not fail scheduled word");$display("FMT_CAUSAL_REJECT mode=%0d checks=%0d code=%h",mode,checks,fc);$finish;end
   require(wv&&!fault,"missing or faulted compiled word");require(cyc-startslot==2,"word slot capture age changed");
   require(tag=={3'b010,5'd0,1'(w/2),1'd0,1'(w%2)},"word tag/order");
   for(integer j=0;j<64;j++)require(data[8*j+:8]==code(64*w+j),"word byte differs");
   tick();require(!wv,"word valid did not pulse");
  end
  repeat(3)tick();require(drained&&idle&&!fault,"epoch failed to drain");
  $display("FMT_PASS SAFE=2 LOCAL_CTL=0 POS=%0d words=4 bytes=256 slot_to_word=2 checks=%0d",p,checks);$finish;
 end
endmodule
