`timescale 1ns/1ps
// The real package/stage/HC/banked-VM/hop chain, H load/store only. This is
// not a full layer: coefficients, fields and FP POST/NORM remain separate.
module tb_s81_native_transfer_controller #(parameter integer MUT=0,STALL=0,TX_DEPTH=32,TX_SRAM=1);
 reg ck=0,rst=0;always #0.4166 ck=~ck;
 reg pw=0;reg[6:0] pa=0;reg[27:0] pd=0;
 reg iv=0,il=0;reg[511:0] id=0;wire ir,ov,ol;wire[511:0] od;reg outready=1;
 wire[11:0] cmdv,dnv;wire[1007:0] cmdd;wire[95:0] dnt;
 wire vmwe,vmre;wire[13:0] vmwa,vmra;wire[511:0] vmwd;wire[85:0] head;
 wire hcgo;wire[1:0] hrq,trq,hrs,trs;wire[27:0] hra,tra;wire[1023:0] hrd,trd;
 wire[7:0] hw;wire[111:0] hwa;wire[127:0] hwm;wire[4095:0] hwd;
 wire[31:0] commit;wire[447:0] commit_a;wire[511:0] commit_m;
 wire[11:0] m_iv,m_iw,m_ov;wire[167:0] m_row;wire[191:0] m_mask;wire[6143:0] m_d,m_od;
 wire mf,hf,cf,tf;wire[2:0] mfc;wire[3:0] tfc;wire[15:0] cfc;wire[8:0] hdone;wire[1:0] hstatus;
 wire[31:0] jobs;
 assign dnv={9'd0,hdone[8],2'd0};assign dnt={72'd0,hdone[7:0],16'd0};
 ot_s81_ctrl #(.ROLE(0),.MY_ID(17),.SRC_LO(16),.SRC_HI(16),.MAXU(16),.XW(640),.RXB(0),.TXB(6144),
 .H_TRANSFER(1),.HC_SLOT_REBASE(1),.USE_VM_RVALID(1),.OUT_DEPTH(TX_DEPTH),.HOP_OUT_SRAM(TX_SRAM),.STUCK(10000)) ctrl(
 .clk(ck),.rst_n(rst),.source_token_dead(1'b0),.eng_rb_v(1'b0),.eng_rb_user(12'd0),.eng_rb_n(3'd0),
 .pw_v(pw),.pw_a(pa),.pw_d(pd),.prog_len(8'd3),.cfg_users_static(12'd16),
 .in_valid(iv),.in_ready(ir),.in_data(id),.in_last(il),.out_valid(ov),.out_ready(outready),.out_data(od),.out_last(ol),
 .cmd_v(cmdv),.cmd_d(cmdd),.dn_v(dnv),.dn_tag(dnt),.hop_go(1'b0),.vm_we(vmwe),.vm_waddr(vmwa),.vm_wdata(vmwd),
 .vm_re(vmre),.vm_raddr(vmra),.vm_rq(m_od[11*512+:512]),.vm_rvalid(m_ov[11]),
 .hc_queue_head(MUT==2?(head^86'd128):head),.hc_normal_inputs_present(1'b0),.hc_inputs_present(hcgo),
 .hc_vm_rq_v(hrq),.hc_vm_rq_row(hra),.hc_vm_rs_v(hrs),.hc_vm_rs_d(hrd),
 .transfer_vm_rq_v(trq),.transfer_vm_rq_row(tra),.transfer_vm_rs_v(trs),.transfer_vm_rs_d(trd),
 .hc_commit_v(commit),.hc_commit_row(commit_a),.hc_commit_mask(MUT==3?(commit_m&{32{16'h0001}}):commit_m),
 .transfer_fault(tf),.transfer_fault_code(tfc),.am_v(1'b0),.am_pos(21'd0),.am_tok(21'd0),.am_val(32'd0),
 .boot_ok(1'b1),.hc_valid(1'b0),.hc_op(2'd0),.hc_tag(8'd0),.hc_user(8'd0),.hc_pos(21'd0),.hc_token(21'd0),
 .cpl_ready(1'b1),.fault(cf),.fault_vec(cfc),.st_jobs(jobs));
 dsfd_sp_hc_c #(.NG(256),.HIER(1),.HALF(1),.CSPLIT(1),.TAIL_SPLIT(2),.CNL_PIN(1),.CHAIN_STEP(6),.LANE_SPECIALIZE(1)) hc(
 .ck(ck),.rst(rst),.c_cmd({cmdv[2],cmdd[168+:84]}),.c_done(hdone),.c_st(hstatus),.f_inp(hcgo),.t_head(head),
 .y_v(1'b0),.y_rdy(),.y_d(8192'd0),.rq_v(hrq),.rq_row(hra),.rs_v(hrs),.rs_d(hrd),
 .wq_v(hw),.wq_row(hwa),.wq_mask(hwm),.wq_d(hwd),.f_tr0('0),.f_tr1('0),.f_tr2('0));
 assign m_iv={vmre,hw,trq,vmwe};assign m_iw={1'b0,8'hff,2'b00,1'b1};
 assign m_row={vmra,hwa,tra,vmwa};assign m_mask={16'd0,hwm,32'd0,16'hffff};assign m_d={512'd0,hwd,1024'd0,vmwd};
 assign trs=m_ov[2:1];assign trd=m_od[512+:1024];
 ot_s81ph_vm_mem #(.NP(12),.NB(32),.QD(8),.RQ(16),.MACRO(0)) vm(.clk(ck),.rst_n(rst),.grp(1'b0),
 .i_v(m_iv),.i_we(m_iw),.i_row(m_row),.i_mask(m_mask),.i_d(m_d),.o_v(m_ov),.o_d(m_od),
 .fault(mf),.fault_code(mfc),.max_occ(),.commit_v(commit),.commit_row(commit_a),.commit_mask(commit_m));
 function automatic [511:0] word(input integer user,input integer row);
 for(integer j=0;j<16;j=j+1)word[32*j+:32]=32'(user*977+row*2654435761+j*97);
 endfunction
 integer cy=0,beats=0,errors=0,messages=0,loads=0,stores=0,first=-1,last=-1;
 reg[1279:0] written=0;integer early=0;
 always @(posedge ck)if(rst)begin
 cy=cy+1;
 if(head[84])begin if(head[29:27]==0)loads=loads+1;if(head[29:27]==1)stores=stores+1;end
 for(integer b=0;b<32;b=b+1)if(commit[b]&&commit_a[b*14+:14]>=6144&&commit_a[b*14+:14]<7424)
   written[commit_a[b*14+:14]-6144]=1;
 if(vmre && !written[vmra-6144])early=early+1;
 if(ov&&outready)begin
  if(beats==0)begin
   if(od[11:0]!=18||od[23:12]!=17||od[39:28]!=640||od[51:40]!=messages)errors=errors+1;
   if(first<0)first=cy;
  end else if(od!==word(messages,beats-1) || ol!=(beats==640))errors=errors+1;
  beats=beats+1;
  if(ol)begin if(beats!=641)errors=errors+1;messages=messages+1;beats=0;last=cy;end
 end
 end
 always @(negedge ck)if(rst)outready=!(STALL&&cy%11<5);
 task automatic send(input [511:0] data,input bit islast);
  iv=1;id=data;il=islast;
  do @(posedge ck);while(!ir);
  @(negedge ck);iv=0;il=0;
 endtask
 initial begin
  repeat(6)@(negedge ck);rst=1;repeat(128)@(negedge ck);
  pw=1;pa=0;pd=MUT==1?28'h2000000:28'h2800000;@(negedge ck);pa=1;pd=MUT==1?28'h2101800:28'h2901800;
  @(negedge ck);pa=2;pd=28'h7000121;@(negedge ck);pw=0;repeat(6)@(negedge ck);
  for(integer user=0;user<2;user=user+1)begin
   id=0;id[11:0]=17;id[23:12]=16;id[27:24]=1;id[39:28]=640;id[51:40]=user;
   id[72:52]=0;id[146:126]=21'd27;id[207:186]=22'd1048576;
   send(id,0);
   for(integer r=0;r<640;r=r+1)begin
    if(STALL&&r%16==8)repeat(9)@(negedge ck);
    send(word(user,r),r==639);
   end
  end
  repeat(12000)@(negedge ck);
  if(messages!=2||loads!=2||stores!=2||cf||tf||mf||hstatus[0]||early)errors=errors+1;
  $display("NATIVE_DEBUG seq_run=%0d kind=%0d issue=%0d returned=%0d hland_active=%0d mode=%0d requested=%0d delivered=%0d landed=%0d slot=%0d fresh=%0d live=%0d fifo=%0d",
   hc.u_hc.g_hier.u_cb.u_seq.run,hc.u_hc.g_hier.u_cb.u_seq.kind,hc.u_hc.g_hier.u_cb.u_seq.ci,hc.u_hc.g_hier.u_cb.u_seq.cr,
   ctrl.g_htransfer.hboundary.landing.u_core.c_act,ctrl.g_htransfer.hboundary.landing.u_core.c_mode,
   ctrl.g_htransfer.hboundary.landing.u_core.c_req,ctrl.g_htransfer.hboundary.landing.u_core.c_del,
   ctrl.g_htransfer.hboundary.landing.u_core.l_cnt,ctrl.g_htransfer.hboundary.landing.u_core.l_slot,
   ctrl.g_htransfer.hboundary.landing.u_core.fresh,ctrl.g_htransfer.hboundary.landing.u_core.l_live,
   ctrl.g_htransfer.hboundary.landing.u_core.n);
  $display("NATIVE_LANDING streamed_loads=%0d vm_fallback_loads=%0d",ctrl.g_htransfer.hboundary.stream_count,ctrl.g_htransfer.hboundary.vm_count);
  $display("TB_S81_NATIVE_TRANSFER_CONTROLLER mut=%0d stall=%0d messages=%0d accepted_loads=%0d accepted_stores=%0d jobs=%0d errors=%0d early=%0d faults=%b%b%b%b first=%0d last=%0d %s",MUT,STALL,messages,loads,stores,jobs,errors,early,cf,tf,mf,hstatus[0],first,last,errors==0?"PASS":"FAIL");$finish;
 end
endmodule
