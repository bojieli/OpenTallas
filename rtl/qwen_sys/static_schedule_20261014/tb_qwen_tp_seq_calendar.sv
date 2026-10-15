`timescale 1ns/1ps
// Controller/real-VM-macro mechanism proof. Core completion and collective
// loopback are EXPLICIT interface fixtures, not native arithmetic/8die proof.
module tb_qwen_tp_seq_calendar;
 parameter integer MUT=0;
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0,start=0,pw_v=0;reg[9:0]pw_addr=0;reg[63:0]pw_data=0;
 wire done,fault,ready,busy,core_start;wire[17:0]ntok,ctok,cpos;wire[31:0]nval;
 wire[11:0]base;wire dre;wire[5:0]da;reg[63:0]dq=0;reg[63:0]descriptors[0:7];
 reg core_done=0;wire vre,vwe;wire[19:0]vra,vwa;wire[511:0]vrq,vwd;
 wire cv,cl,cm;wire[511:0]cd;wire[31:0]tag;wire rv,rl;wire[511:0]rd;
 wire vvalid;integer elapsed=-1,txcount=0,rxcount=0,starts=0,finishes=0;
 ot_qwen_tp_seq_calendar #(.VRL(3))dut(.clk(clk),.rst_n(rst_n),.rst_nw(rst_n),.start(start),.token(18'd140123),.pos(18'd8191),.stage(6'd1),
 .pw_v(pw_v),.pw_addr(pw_addr),.pw_data(pw_data),.done(done),.next_token(ntok),.next_val(nval),.fault(fault),.image_ready(ready),.coll_busy(busy),
 .core_start(core_start),.core_token(ctok),.core_pos(cpos),.core_done(core_done),.core_next_token(18'd5),.core_next_val(32'h3f800000),.core_fault(1'b0),
 .prog_base(base),.desc_re(dre),.desc_addr(da),.desc_q(dq),.vm_re(vre),.vm_raddr(vra),.vm_rq(vrq),.vm_rvalid(vvalid),
 .vm_we(vwe),.vm_waddr(vwa),.vm_wdata(vwd),.c_valid(cv),.c_ready(1'b0),.c_data(cd),.c_last(cl),.c_mode(cm),.c_tag(tag),
 .r_valid(rv&&!(MUT==1&&rxcount==255)),.r_data(rd),.r_last(rl),.r_rank(3'd0),.r_err(1'b0));
 always @(posedge clk)if(dre)dq<=descriptors[da];
 // Four real ASAP7 SRAM macros provide a full256word/4096scalar AR operand.
 reg fill=0;reg[8:0]filladdr=0;reg[511:0]filldata=0;
 wire[511:0]mq;
 for(genvar bank=0;bank<4;bank=bank+1)begin:g_vm
 ot_sram_1r1w_512x128_m4_r2c2 mem(.clk(clk),.r_ce_in(vre),.r_addr_in(vra[8:0]),.rd_out(mq[128*bank+:128]),
 .w_ce_in(fill||vwe),.w_addr_in(fill?filladdr:vwa[8:0]),.wd_in(fill?filldata[128*bank+:128]:vwd[128*bank+:128]),.w_mask_in({128{1'b1}}),
 .rr_en(2'b0),.rr_addr(14'd0),.cr_en(2'b0),.cr_sel(14'd0));
 end
 ot_hdc_delay #(.W(512),.D(2))data_pipe(clk,rst_n,mq,vrq);
 ot_hdc_delay #(.W(1),.D(3),.RESET(1))valid_pipe(clk,rst_n,vre,vvalid);
 // Explicit collective-interface loopback fixture; source is real VM data.
 ot_hdc_delay #(.W(514),.D(288),.RESET(1))collective_fixture(clk,rst_n,{cv,cl,cd},{rv,rl,rd});
 function automatic[511:0]word(input integer row);word={16{32'h3f800000+32'(row)}};endfunction
 task wr(input[9:0]a,input[63:0]d);
 @(negedge clk);pw_v=1;pw_addr=a;pw_data=d;@(negedge clk);pw_v=0;
 endtask
 task segment(input integer k,input[31:0]s,e,t,r,input[63:0]d);
 wr(961+4*k,{e,s});wr(962+4*k,{r,t});wr(963+4*k,k==2?0:64'h0000000000010001);wr(964+4*k,d);
 endtask
 integer i;string path;
 always @(negedge clk)begin
 core_done=(elapsed==16||elapsed==612||elapsed==1212);
 end
 always @(posedge clk)begin
 if(start)elapsed<=0;else if(elapsed>=0)elapsed<=elapsed+1;
 if(core_start)begin
  starts<=starts+1;
  if((starts==0&&(elapsed!=4||base!=0))||(starts==1&&(elapsed!=600||base!=14))||(starts==2&&(elapsed!=1200||base!=22)))$fatal(1,"fixed core start %0d %0d %0d",starts,elapsed,base);
 end
 if(cv)begin
  if(cd!==word(txcount%256)||tag!=={18'd140123,8'hff,6'(txcount/256)}||cl!==(txcount%256==255)||cm)$fatal(1,"actual VM/tag/last payload mismatch count%0d tag%h",txcount,tag);
  txcount<=txcount+1;
 end
 if(rv)rxcount<=rxcount+1;
 if(done)begin
  finishes<=finishes+1;
  if(elapsed!=1217||txcount!=512||starts!=3||fault!==(MUT==1))$fatal(1,"fixed completion %0d tx%0d starts%0d fault%b",elapsed,txcount,starts,fault);
  $display("PASS actual2xAR256 VM macro controller fixeddone1217 tx512 starts3 mutant%0d fault%b",MUT,fault);$finish;
 end
 if(elapsed>1220)$fatal(1,"stage stretched beyond compiled deadline");
 end
 initial begin
 if(!$value$plusargs("DESCRIPTORS=%s",path))$fatal(1,"actual released descriptors required");
 $readmemh(path,descriptors,0,2);for(i=3;i<8;i=i+1)descriptors[i]=0;
 repeat(4)@(negedge clk);rst_n=1;
 fill=1;for(i=0;i<256;i=i+1)begin filladdr=i;filldata=word(i);@(negedge clk);end fill=0;
 wr(0,0);segment(0,4,16,32,320,descriptors[0]);segment(1,600,612,640,928,descriptors[1]);segment(2,1200,1212,0,0,descriptors[2]);
 wr(973,{32'h53475431,32'd1216});wr(974,{32'h53475453,24'd0,6'd1,2'd3});wr(975,0);wr(1023,64'h5850463100001046);
 if(!ready||fault)$fatal(1,"image config failed");
 @(negedge clk);start=1;@(negedge clk);start=0;
 end
endmodule
