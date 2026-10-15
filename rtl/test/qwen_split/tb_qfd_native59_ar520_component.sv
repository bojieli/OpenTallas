`timescale 1ns/1ps
// Declared SU/VM/HOST/remote-native548 boundary stimuli. This verifies the
// selected local composition only, not arithmetic or physical/full-token closure.
module tb_qfd_native59_ar520_component;
 parameter integer BAD_RESULT=0,CODEC_MUT=0,BAD_COMMIT=0,NO_VISIBILITY=0,NATIVE_PROFILE=0,BAD_STATUS=0,BAD_ADDRESS=0;localparam HEADS=1;
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg context_v=0,q_committed=0,kvslot=0,xslot=0,qslot=0,txslot=0,rxslot=0,rxv=0,visibility_slot=0,complete_slot=0;
 reg[5:0]stage=1;reg[17:0]token=50994,position=255;reg[379:0]cmd=0;reg[481:0]si=0;
 reg[1:0]kvindex=0;reg[4:0]qb=0,tb=0,rb=0;reg[3:0]tk=0,rk=0;
 reg[63:0]we=0;reg[1535:0]wa=0;reg[2047:0]wd=0;reg[523:0]q=0;reg[547:0]rxdata=0;
 reg[38:0]raw_v=0;reg[311:0]raw_line=0;reg[623:0]raw_mask=0;
 reg[7:0]pending=0;reg[4:0]pending_beat[0:7];integer ppidx;
 // Declared VM boundary model only. Actual SRAM timing/mutants are proven by
 // q_vm_commit e10417cf4. This bench checks this parent wires that fence.
 always @(posedge ck)begin
  pending<={pending[6:0],wv};pending_beat[0]<=wb;
  for(ppidx=1;ppidx<8;ppidx=ppidx+1)pending_beat[ppidx]<=pending_beat[ppidx-1];
 end
 always @(negedge ck)begin
  raw_v=0;raw_line=0;raw_mask=0;
  if(pending[7])begin
   raw_v[7+pending_beat[7]]=!(BAD_COMMIT&&pending_beat[7]==7);
   raw_line[8*(7+pending_beat[7])+:8]=49;
   raw_mask[16*(7+pending_beat[7])+:16]=16'hffff;
  end
 end
 wire[519:0]vm_ar;
 wire q_epoch,q_start;wire[58:0]xid;wire[1:0]xgen;wire[523:0]x3;wire tv,wv,completed,fault;wire[547:0]td;wire[19:0]ww;wire[4:0]wb;wire[58:0]wt;wire[511:0]wdata;wire[94:0]ret;
 localparam[58:0]TAG={16'd9,6'd1,18'd50994,13'd255,6'd0};
 qfd_native59_compute_service #(.CODEC_MUT(CODEC_MUT),.NATIVE_PROFILE(NATIVE_PROFILE))dut(
 .ck_context(ck),.ck_service(ck),.ck_format(ck),.ck_record(ck),.ck_qtag(ck),.ck_x3(ck),.rst_n(rst_n),
 .host_epoch_valid(1'b1),.host_fused_capability(1'b1),.host_epoch(16'd9),.host_tag({16'd9,6'd0,18'd50994,13'd255,6'd0}),.host_generation(2'd1),.layer_context_v(context_v),.command_stage(stage),.native_token(token),.native_position(position),.native_cmd(cmd),
 .native_issue({si[293:270],si[269:268],si[36:1],si[0]}),.kv_we(we),.kv_waddr(wa),.kv_wdata(wd),.kv_word_slot(kvslot),.kv_word_index(kvindex),.kv_x3_slot(xslot),.x3(x3),.x3_identity(xid),.x3_generation(xgen),
 .vm_q_epoch(q_epoch),.vm_q_start(q_start),.q_committed(q_committed),.q_fault(1'b0),.q(q),.q_slot(qslot),.q_slot_beat(qb),
 .tx_slot(txslot),.tx_slot_kind(tk),.tx_slot_beat(tb),.native_tx_v(tv),.native_tx_payload(td),.native_rx_v(rxv),.native_rx_payload(rxdata),.rx_slot(rxslot),.rx_slot_kind(rk),.rx_slot_beat(rb),
 .vm_ar(vm_ar),
 .write_commit_v(raw_v),.write_commit_line(raw_line),.write_commit_mask(raw_mask),.visibility_slot(visibility_slot),.complete_slot(complete_slot),.completed(completed),.native_ret(ret),.fault(fault));
 // Observe the actual physical face; TAG/address are internal fence state only.
 assign wv=vm_ar[519];assign wb=vm_ar[516:512];assign wdata=vm_ar[511:0];
 assign ww=dut.vm_write_word;assign wt=dut.vm_write_tag;
 // The external native_ret face must observe the internal service at exactly
 // one edge, including availability revocation and late faults.
 reg[94:0]expected_ret;
 always @(posedge ck)if(rst_n)begin
  expected_ret=dut.service_ret_raw;
  #0.001;
  if(ret!==expected_ret)$fatal(1,"FAIL native_ret registered observation edge");
 end
 integer ep=0,i,j,l,p,k,h,di,errors=0,kvcount=0,qcount=0,cmdcount=0,writecount=0,epochcount=0,startcount=0;reg[511:0]expected;
 function automatic [7:0] code(input integer k,input integer h,input integer d);
  integer x;begin x=(k*91+h*37+d+ep*17)%254;if(x>=127)x=x+1;code=x;end
 endfunction
 function automatic [31:0] decode(input [7:0] b);
  reg [3:0] e;reg [2:0] m;begin e=b[6:3];m=b[2:0];
   if(e!=0)decode={b[7],8'(e+120),m,20'd0};
   else if(m[2])decode={b[7],8'd120,m[1:0],21'd0};
   else if(m[1])decode={b[7],8'd119,m[0],22'd0};
   else if(m[0])decode={b[7],8'd118,23'd0};
   else decode={b[7],31'd0};
  end
 endfunction
 function automatic [23:0] address(input integer k,input integer h,input integer d);
  begin if(k==0)address=((h*512+position/16)*128+d)*16+position%16;
   else address=HEADS*1048576+(h*8192+position)*128+d;end
 endfunction

 task step;begin @(negedge ck);end endtask
 task issue(input integer kind,input integer count,input[23:0]dest);begin
  si=0;si[0]=1;si[18:1]=1;si[36:19]=count;si[269:268]=2;si[293:270]=dest;step();si[0]=0;
 end endtask
 task writes(input integer kind,input integer base,input integer length);integer d,ll,pp;begin
  for(d=base;d<base+length;d=d+64)begin
   we=64'hffffffffffffffff;
   for(ll=0;ll<64;ll=ll+1)begin pp=(ll*17)%64;wa[24*ll+:24]=address(kind,0,d+pp);wd[32*ll+:32]=decode(code(kind,0,d+pp));end
   step();we=0;
  end
 end endtask
 always @(negedge ck)if(rst_n)begin
  if(q_epoch)epochcount=epochcount+1;
  if(q_start)startcount=startcount+1;
  if(x3[523])begin
   k=x3[514];h=x3[513];di=x3[512]*64;expected=0;
   for(j=0;j<64;j=j+1)expected[8*j+:8]=code(k,h,di+j);
   if(xid!=TAG||xgen!=1||x3[522:515]!=8'h40||h!=0||x3[511:0]!==expected)errors=errors+1;
   kvcount=kvcount+1;
  end
  if(tv)begin
   if(td[542:539]==1)begin if(td[511:0]!={493'd0,18'd255,1'b1})errors=errors+1;cmdcount=cmdcount+1;end
   else if(td[542:539]==2)begin
    if(td[516:512]!=qcount||td[511:0]!=={16{32'(qcount+100)}})errors=errors+1;
    qcount=qcount+1;
   end else errors=errors+1;
   if(td[547:543]!=0||td[538:533]!=0||td[532:517]!=9)errors=errors+1;
  end
  if(wv)begin
   if(vm_ar[518:517]!=0||ww!=3167+writecount||wb!=writecount||wt!=TAG||wdata!=={16{32'(writecount+200)}})errors=errors+1;
   writecount=writecount+1;
  end
 end
 // Corrupt a real internal registered address while leaving physical beat/data
 // unchanged. The local fence must reject the aliased write before completion.
 initial if(BAD_ADDRESS)begin
  wait(wv&&wb==7);force dut.vm_write_word=20'd0;
  @(negedge ck);@(negedge ck);release dut.vm_write_word;
 end
 initial begin
 repeat(4)step();rst_n=1;context_v=1;step();context_v=0;repeat(2)step();
 issue(0,128,address(1,0,0));writes(1,0,128);
 issue(1,64,address(0,0,0));writes(0,0,64);
 issue(2,64,address(0,0,64));writes(0,64,64);
 repeat(3)step();
 for(i=0;i<7;i=i+1)begin kvslot=i<4;kvindex=i;xslot=i>=3;step();end
 kvslot=0;xslot=0;repeat(3)step();q_committed=1;
 cmd=380'h0000003000001000001000c5f0000000000000000000000000100358000000000000000000000000080100000080401;step();cmd=0;txslot=1;tk=1;tb=0;step();txslot=0;
 repeat(2)step();
 // A future rawhead context must not relabel this already accepted operation.
 stage=3;token=42;position=8191;
 for(i=0;i<33;i=i+1)begin
  qslot=i<32;qb=i;q=i<32?{1'b1,3'd1,2'd0,6'(i),{16{32'(i+100)}}}:524'd0;
  txslot=i>0;tk=2;tb=i-1;step();
 end
 qslot=0;q=0;txslot=0;step();
 for(i=0;i<33;i=i+1)begin
  rxv=i<32;rxslot=i<32;rk=3;rb=i;
  rxdata={5'd0,4'd3,6'd0,16'(BAD_RESULT&&i==7?10:9),5'(i),{16{32'(i+200)}}};step();
 end
 rxv=0;rxslot=0;step();
 repeat(12)step();visibility_slot=!NO_VISIBILITY;step();visibility_slot=0;rxv=1;rxslot=1;rk=4;rb=0;rxdata={5'd0,4'd4,6'd0,16'd9,5'd0,507'd0,(BAD_STATUS?5'b01101:5'b01001)};step();
 rxv=0;rxslot=0;step();complete_slot=1;step();complete_slot=0;
 if(BAD_RESULT||BAD_COMMIT||NO_VISIBILITY||BAD_STATUS||BAD_ADDRESS)begin
  if(!fault||completed)$fatal(1,"FAIL stale remote metadata or missing SRAM commit qualified local completion");
  $display("PASS selected local native service invalid result or missing SRAM commit faults before completion");$finish;
 end
 if(!completed)$fatal(1,"FAIL internal completion slot shifted");
 step(); // exported status observes completion exactly one service edge later
 if(fault||ret[93:78]!=32||ret[1:0]!=3||kvcount!=4||qcount!=32||cmdcount!=1||writecount!=32||epochcount!=1||startcount!=1||errors)
  $fatal(1,"FAIL selected local native service fault%0d complete%0d ret%h KV%0d Q%0d CMD%0d writes%0d errors%0d",fault,completed,ret,kvcount,qcount,cmdcount,writecount,errors);
 $display("PASS selected local native service actualSI/KVformatter+QproducerTAG+native548codec+32VMcommit 4KV/32Q/32results no duplicateQ no credits");$finish;
 end
 initial begin #5000;$fatal(1,"timeout");end
endmodule
