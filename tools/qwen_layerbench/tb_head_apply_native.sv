`timescale 1ns/1fs
// Generated finite source initializers are replaced by prepare_head_apply_gate.py.
module tb_mu_native;
parameter integer HEAD_BAD_REPLY=0;
reg ck=0;always #0.416500 ck=~ck;
reg rst_n=0;reg[115:0]cmd=0;reg wv=0,tv=0;reg[1:0]tk=0;reg[23:0]wa=0,ta=0;
reg[511:0]wd=0;reg[1023:0]td=0;
reg[1023:0]prog[0:11][0:3],rawprog[0:11][0:3],gains[0:11][0:23];reg[31:0]gold[0:11][0:383];integer nwords[0:11];
integer s,u,j,k,l,active=0,cyc=0,origin,count,beats,total=0,idx,ea,localidx;
integer sample_edge=0,issue_edge=-1,first_read_edge=-1,first_operand_edge=-1;
integer first_write_edge=-1,last_write_edge=-1,first_bf16_edge=-1,last_bf16_edge=-1;
wire [7:0] head_operand_capture;
assign head_operand_capture[0]=dut.u_head0.u_h.u_lane.s1_v;
assign head_operand_capture[1]=dut.u_head1.u_h.u_lane.s1_v;
assign head_operand_capture[2]=dut.u_head2.u_h.u_lane.s1_v;
assign head_operand_capture[3]=dut.u_head3.u_h.u_lane.s1_v;
assign head_operand_capture[4]=dut.u_head4.u_h.u_lane.s1_v;
assign head_operand_capture[5]=dut.u_head5.u_h.u_lane.s1_v;
assign head_operand_capture[6]=dut.u_head6.u_h.u_lane.s1_v;
assign head_operand_capture[7]=dut.u_head7.u_h.u_lane.s1_v;
reg[383:0]seen;reg[63:0]beatseen;reg[31:0]expected,actual;reg[23:0]oa;
qfd_dv_s8_flat dut(.ck(ck),.rst_n(rst_n),.cmd_i(cmd),.hr_i('0),.rs_s('0),.rs_n('0),.l9_i('0),.st_up_i('0),.st_dn_i('0),.sc_up_i('0),.sc_dn_i('0),.ch_up_i('0),.ch_dn_i('0),.ag_up_i('0),.treq_i('0));
// Same reset adapter and SU window01 gating as actual qfd_dv_s6_stm.
wire srst; qfd_dv_s5_rst2 u_sr(.ck(ck),.rst_n(rst_n),.rst(srst));
wire[7:0]xwe=(|dut.L_vm_we&&dut.L_vm_waddr[23:22]==2'b01)?dut.L_vm_we:8'd0;
reg cfg=0;wire[1087:0]oe,ow;wire xv,xbad,sfault;wire[23:0]xa;wire[1023:0]xd;
qfd_dv_stream_tile stream(.ck(ck),.rst_n(srst),.sid(4'(s)),.cfg_v(cfg),.cfg_dir(2'b11),.cfg_tag(28'h4845414),
 .sw_lo('0),.sw_v(1'b0),.sw_hi('0),.se_lo('0),.se_v(1'b0),.se_hi('0),.so_e(oe),.so_w(ow),
 .xw_we(xwe),.xw_addr(dut.L_vm_waddr),.xw_data(dut.L_vm_wdata),
 .tw_we(),.tw_kind(),.tw_addr(),.tw_data_lo(),.tw_data_hi(),.xt_v(xv),.xt_a(xa),.xt_d_lo(xd[511:0]),.xt_d_hi(xd[1023:512]),.xt_bad(xbad),.fault(sfault));
function automatic[15:0]bf16(input[31:0]v);reg[32:0]r;begin r={1'b0,v}+33'h7fff+{32'd0,v[16]};bf16=r[31:16];end endfunction
initial begin
 force dut.w16_we=wv;force dut.w16_addr=wa;force dut.w16_data=wd;
 force dut.tw_we=tv;force dut.tw_kind=tk;force dut.tw_addr=ta;force dut.tw_data=td;
 // SOURCE_INITIALIZERS
 repeat(64)@(negedge ck);rst_n=1;repeat(64)@(negedge ck);
 for(s=0;s<12;s=s+1)for(u=0;u<4;u=u+1)begin
  cfg=1;@(negedge ck);cfg=0;
  for(j=0;j<nwords[s];j=j+16)begin
   wv=1;wa=24'(4096*u+j);for(l=0;l<16;l=l+1)wd[32*l+:32]=32'h40000000+32'(u*8388608);@(negedge ck);
  end
  wa=24'(4096*u+400);wd=0;wd[31:0]=32'h3f000000;@(negedge ck);wv=0;
  tv=1;tk=1;
  for(j=0;j<nwords[s]/16;j=j+1)begin
   ta=24'(128*u+68+j);td=gains[s][j];
   if($test$plusargs("MUT_GAIN")&&s==0&&u==1&&j==0)td[31:0]=32'h3f800000;
   @(negedge ck);
  end
  tk=3;ta=24'(64*u+8);td=prog[s][u];
  if($test$plusargs("MUT_RAW_X"))td=rawprog[s][u];
  @(negedge ck);tv=0;repeat(32)@(negedge ck);
  active=1;seen=0;beatseen=0;count=0;beats=0;origin=cyc+1;
  issue_edge=-1;first_read_edge=-1;first_operand_edge=-1;first_write_edge=-1;last_write_edge=-1;first_bf16_edge=-1;last_bf16_edge=-1;
  cmd=(116'(16+128*u)<<4)|116'd3;
  if($test$plusargs("MUT_USER")&&u==1)cmd=(116'd16<<4)|116'd3;
  @(negedge ck);cmd=0;repeat(256)@(negedge ck);active=0;
  if(count!=nwords[s]||beats!=nwords[s]/64)$fatal(1,"HEAD_COVERAGE slice%0d user%0d words%0d beats%0d",s,u,count,beats);
  if(dut.su_fault||dut.vm_fault||sfault||xbad)$fatal(1,"HEAD_NATIVE_FAULT");
  if(issue_edge<0||first_read_edge<issue_edge||first_operand_edge<first_read_edge||first_write_edge<first_operand_edge||first_bf16_edge<first_write_edge||last_write_edge<first_write_edge||last_bf16_edge<first_bf16_edge)$fatal(1,"HEAD_DATE_COVERAGE");
  $display("HEAD_NATIVE_DATES slice=%0d user=%0d calr_sample=%0d first_read=%0d first_operand=%0d first_write=%0d last_write=%0d first_bf16=%0d last_bf16=%0d read_age=%0d operand_age=%0d write_age=%0d stream_age=%0d",s,u,issue_edge,first_read_edge,first_operand_edge,first_write_edge,last_write_edge,first_bf16_edge,last_bf16_edge,first_read_edge-issue_edge,first_operand_edge-issue_edge,first_write_edge-issue_edge,first_bf16_edge-issue_edge);
  $display("NATIVE_HEAD_CASE_PASS slice%0d user%0d words%0d beats%0d pidx%0d",s,u,count,beats,16+128*u);
 end
 if(total!=16384)$fatal(1,"HEAD_TOTAL %0d",total);
 $display("NATIVE_HEAD_APPLY_PASS cases48 words16384 actualgain4096 users4 nativeMA_AB_then_MC streamBF16");$finish;
end
// Observer samples the values that actual posedge receivers consume. A read
// request is distinct from S2 operand capture (s1_v); no guessed +ML date.
always @(posedge ck)begin
 sample_edge=sample_edge+1;
 if(active)begin
  if(cmd[0]&&cmd[3:1]==3'd1)begin if(issue_edge>=0)$fatal(1,"HEAD_DUPLICATE_ISSUE");issue_edge=sample_edge;end
  if(first_read_edge<0&&(|dut.L_va_re|| |dut.L_vb_re|| |dut.L_crom_re))first_read_edge=sample_edge;
  if(first_operand_edge<0&&|head_operand_capture)first_operand_edge=sample_edge;
  if(|dut.L_vm_we)begin if(first_write_edge<0)first_write_edge=sample_edge;last_write_edge=sample_edge;end
  if(oe[1087])begin if(first_bf16_edge<0)first_bf16_edge=sample_edge;last_bf16_edge=sample_edge;end
 end
end
always @(negedge ck)begin
 cyc=cyc+1;
 if(active)begin
  for(k=0;k<8;k=k+1)if(dut.L_vm_we[k])begin
   oa=dut.L_vm_waddr[24*k+:24];actual=dut.L_vm_wdata[32*k+:32];ea=integer'(oa)-4194304;
   if(ea<0||ea>=4096||ea/128%12!=s)$fatal(1,"HEAD_WRONG_OUTPUT_ADDR %h",oa);
   localidx=(ea/128/12)*128+ea%128;
   expected=gold[s][localidx]+32'(u*8388608);
   if(localidx>=nwords[s]||seen[localidx]||actual!==expected)$fatal(1,"HEAD_NATIVE_VALUE slice%0d user%0d local%0d got%h expected%h",s,u,localidx,actual,expected);
   seen[localidx]=1;count=count+1;total=total+1;
  end
  if(oe[1087])begin
   ea=integer'(oe[1075:1052]);idx=ea/64;
   if(ea>=4096||ea%64||ea/128%12!=s||beatseen[idx]||ow!==oe)$fatal(1,"HEAD_STREAM_ADDRESS %h",oe[1075:1052]);
   beatseen[idx]=1;beats=beats+1;
   for(l=0;l<64;l=l+1)begin
    localidx=(ea/128/12)*128+ea%128+l;expected=gold[s][localidx]+32'(u*8388608);
    if(oe[16*l+:16]!==bf16(expected))$fatal(1,"HEAD_BF16_VALUE slice%0d user%0d local%0d got%h expected%h",s,u,localidx,oe[16*l+:16],bf16(expected));
   end
   $display("NATIVE_HEAD_BEAT slice%0d user%0d eaddr%0d offset%0d",s,u,ea,cyc-origin);
  end
 end
end
endmodule
