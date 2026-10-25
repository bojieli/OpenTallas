`timescale 1ns/1ps
// Actual PROFILE0 ELASTIC controller driven only by independent compiled runs.
// Only external PHY/HBM is modeled. No PROFILE1/trace discovery is instantiated.
module tb_controller_calendar_core;
 parameter integer MUT=0, TIMING_MUT=0, DEFAULT_MITER=0, MITER_MUT=0;
 reg ck=0;always #(DEFAULT_MITER ? 0.512 : 0.4165) ck=~ck;
 reg rn=0,we=0,seal=0,go=0;reg[5:0]layer=0;reg[15:0]epoch_in=100;reg[4:0]addr=0;reg[63:0]data=0;
 wire owner,rd,sr,wr,raw,calfault,idle;wire[42:0]cmd;wire[15:0]epoch;
 qkd_controller_hbm_calendar #(.MUT(MUT),.CORE_CLOCK(DEFAULT_MITER ? 0 : 1))cal(ck,rn,we,addr,data,seal,go,epoch_in,layer,owner,cmd,rd,sr,wr,epoch,raw,calfault,idle);
 wire [327:0]po;wire[293:0]co;wire[260:0]er;wire fault,cf;wire[15:0]oe;
 reg[288:0]pi=0;
 qkd_ctrl_pc_host_static #(.CORE_CLOCK((TIMING_MUT || DEFAULT_MITER) ? 0 : 1),.PROFILE(0),.ELASTIC(1),.RAW_WD(256),.TQD(64))dut(
 .pll_hbm(ck), .pll_hbm_port(ck), .pll_hbm_ecc(ck), .pll_hbm_cdc(ck), .pll_hbm_obs(ck),.hrst(rn),.ck(ck),.rsi(rn),.pc(5'd13),.ci(319'b0),.co(co),.es(288'b0),.er(er),.po(po),.pi(pi),.ki(33'b0),.ko(),.fi(1'b0),.fo(fault),
 .static_cmd_owner(owner),.static_cmd(cmd),.reserved_rd(rd),.reserved_static_col(sr),.reserved_write_col(wr),.static_epoch(epoch),.expected_raw_valid(raw),
 .cfg_stack(2'b0),.es_context(318'b0),.es_expected_valid(1'b0),.es_expected_identity(61'b0),.es_expected_address(29'b0),.es_expected_pc(5'b0),.es_expected_stack(2'b0),
 .native_commit_valid(),.native_commit_identity(),.native_commit_address(),.corrected_epoch(oe),.completion_v(),.completion_we(),.completion_fault(cf),.idle_core(),.idle_hbm(),.drain_fault_core(),.drain_fault_hbm());
 function automatic[255:0]payload(input integer sector,row);
 for(integer j=0;j<8;j++)payload[j*32+:32]=32'hac100000^32'(sector*311+j*31+row*65537);
 endfunction
 function automatic[71:0]ecc(input[63:0]d);
 reg[71:0]c;integer j;begin c=0;j=0;for(integer p=1;p<=71;p++)if((p&(p-1))!=0)begin c[p-1]=d[j];j++;end
 for(integer k=0;k<7;k++)for(integer p=1;p<=71;p++)if((p&(1<<k))!=0)c[(1<<k)-1]^=c[p-1];c[71]=^c[70:0];ecc=c;end
 endfunction
 function automatic[287:0]encode(input[255:0]d);for(integer j=0;j<4;j++)encode[j*72+:72]=ecc(d[j*64+:64]);endfunction
 reg[127:0]image[0:15];reg[288:0]due[0:100000];reg expected_rd[0:4095];integer openrow[0:31];

 generate if(DEFAULT_MITER)begin:legacy_miter
 wire[0:0] gold_desc_r;
 wire[0:0] gold_row_v;
 wire[0:0] gold_row_prio;
 wire[2:0] gold_row_op;
 wire[4:0] gold_row_bank;
 wire[18:0] gold_row_row;
 wire[0:0] gold_col_v;
 wire[4:0] gold_col_bank;
 wire[4:0] gold_col_col;
 wire[0:0] gold_schedule_fault;
 wire[0:0] gold_phase_idle;
 wire[0:0] gold_busy;
 wire[0:0] gold_ref_fault;
 wire[0:0] gold_wr_r;
 wire[0:0] gold_col_we;
 wire[0:0] gold_col_aq;
 wire[346:0] gold_col_context;
 wire[0:0] gold_s_r;
 wire[0:0] gold_col_sr;
 wire[0:0] gold_s_pop;
 ot_qkd_static_kv_timing_legacy_ref #(.SROW(1),.SQD(4),.S_STARVE(8),.READY_CUT(1),.ENABLE(1),.REF_MODE(1),.PC(0),.REF_PHASE(0),.WR_EN(1),.WQ(4),.T_REFIPB(MITER_MUT ? 116 : 118)) gold(
 .clk(dut.u_sched.u_ctl.core.clk),
 .rst_n(dut.u_sched.u_ctl.core.rst_n),
 .desc_v(dut.u_sched.u_ctl.core.desc_v),
 .desc_row(dut.u_sched.u_ctl.core.desc_row),
 .desc_n(dut.u_sched.u_ctl.core.desc_n),
 .go(dut.u_sched.u_ctl.core.go),
 .next_posted(dut.u_sched.u_ctl.core.next_posted),
 .row_gnt(dut.u_sched.u_ctl.core.row_gnt),
 .reserved_rd(dut.u_sched.u_ctl.core.reserved_rd),
 .reserved_static_col(dut.u_sched.u_ctl.core.reserved_static_col),
 .reserved_write_col(dut.u_sched.u_ctl.core.reserved_write_col),
 .boot_static_col(dut.u_sched.u_ctl.core.boot_static_col),
 .desc_first(dut.u_sched.u_ctl.core.desc_first),
 .desc_context(dut.u_sched.u_ctl.core.desc_context),
 .desc_vpass(dut.u_sched.u_ctl.core.desc_vpass),
 .desc_k_order_b(dut.u_sched.u_ctl.core.desc_k_order_b),
 .desc_k_count0(dut.u_sched.u_ctl.core.desc_k_count0),
 .wr_v(dut.u_sched.u_ctl.core.wr_v),
 .wr_bank(dut.u_sched.u_ctl.core.wr_bank),
 .wr_col(dut.u_sched.u_ctl.core.wr_col),
 .wr_rd(dut.u_sched.u_ctl.core.wr_rd),
 .s_context(dut.u_sched.u_ctl.core.s_context),
 .s_v(dut.u_sched.u_ctl.core.s_v),
 .s_we(dut.u_sched.u_ctl.core.s_we),
 .s_bank(dut.u_sched.u_ctl.core.s_bank),
 .s_col(dut.u_sched.u_ctl.core.s_col),
 .s_row(dut.u_sched.u_ctl.core.s_row),
 .desc_r(gold_desc_r),
 .row_v(gold_row_v),
 .row_prio(gold_row_prio),
 .row_op(gold_row_op),
 .row_bank(gold_row_bank),
 .row_row(gold_row_row),
 .col_v(gold_col_v),
 .col_bank(gold_col_bank),
 .col_col(gold_col_col),
 .schedule_fault(gold_schedule_fault),
 .phase_idle(gold_phase_idle),
 .busy(gold_busy),
 .ref_fault(gold_ref_fault),
 .wr_r(gold_wr_r),
 .col_we(gold_col_we),
 .col_aq(gold_col_aq),
 .col_context(gold_col_context),
 .s_r(gold_s_r),
 .col_sr(gold_col_sr),
 .s_pop(gold_s_pop));
 always @(negedge ck)if(rn)begin
 if({dut.u_sched.u_ctl.core.desc_r,dut.u_sched.u_ctl.core.row_v,dut.u_sched.u_ctl.core.row_prio,dut.u_sched.u_ctl.core.row_op,dut.u_sched.u_ctl.core.row_bank,dut.u_sched.u_ctl.core.row_row,dut.u_sched.u_ctl.core.col_v,dut.u_sched.u_ctl.core.col_bank,dut.u_sched.u_ctl.core.col_col,dut.u_sched.u_ctl.core.schedule_fault,dut.u_sched.u_ctl.core.phase_idle,dut.u_sched.u_ctl.core.busy,dut.u_sched.u_ctl.core.ref_fault,dut.u_sched.u_ctl.core.wr_r,dut.u_sched.u_ctl.core.col_we,dut.u_sched.u_ctl.core.col_aq,dut.u_sched.u_ctl.core.col_context,dut.u_sched.u_ctl.core.s_r,dut.u_sched.u_ctl.core.col_sr,dut.u_sched.u_ctl.core.s_pop} !== {gold_desc_r,gold_row_v,gold_row_prio,gold_row_op,gold_row_bank,gold_row_row,gold_col_v,gold_col_bank,gold_col_col,gold_schedule_fault,gold_phase_idle,gold_busy,gold_ref_fault,gold_wr_r,gold_col_we,gold_col_aq,gold_col_context,gold_s_r,gold_col_sr,gold_s_pop})$fatal(1,"LEGACY_MITER default timing core mismatch");
 end
 end endgenerate
 integer pa[0:31],pp[0:31],pr[0:31],pf[0:31],pg_rd[0:3],pg_act[0:3];
 integer act_hist[0:3];integer last_act=-1000000;
 reg[31:0] bank_open=0;
 initial begin
 for(integer b=0;b<32;b++)begin pa[b]=-1000000;pp[b]=-1000000;pr[b]=-1000000;pf[b]=-1000000;end
 for(integer g=0;g<4;g++)begin pg_rd[g]=-1000000;pg_act[g]=-1000000;act_hist[g]=-1000000;end
 end
 task physical_min(input integer since,input integer old_cycles,input string kind);
  if((edge_num-since)*(DEFAULT_MITER ? 1024 : 833) < old_cycles*1024)$fatal(1,"PHYSICAL_MIN %s: %0dps < %0dps",kind,(edge_num-since)*(DEFAULT_MITER ? 1024 : 833),old_cycles*1024);
 endtask
 always @(negedge ck)if(rn)begin
  if(po[0])begin
   automatic integer b=po[8:4],op=po[3:1];
   case(op)
    0:begin
      physical_min(pa[b],28,"tRAS");physical_min(pr[b],6,"tRTP");
      bank_open[b]=0;pp[b]=edge_num;
    end
    1:begin
      physical_min(pp[b],16,"tRP");physical_min(pf[b],196,"tRFCpb");
      physical_min(pg_act[b&3],4,"tRRDL");physical_min(last_act,3,"tRRDS");
      physical_min(act_hist[0],15,"tFAW");
      for(integer n=0;n<3;n++)act_hist[n]=act_hist[n+1];act_hist[3]=edge_num;
      if(bank_open[b])$fatal(1,"PHYSICAL_MIN ACT on open bank");
      bank_open[b]=1;pa[b]=edge_num;pg_act[b&3]=edge_num;last_act=edge_num;
    end
    6:begin
      if(bank_open[b])$fatal(1,"PHYSICAL_MIN REFPB on open bank");
      physical_min(pp[b],16,"tRP before REFpb");pf[b]=edge_num;
    end
    default:;
   endcase
  end
  if(po[28])begin
   automatic integer b=po[34:30];
   if(!bank_open[b])$fatal(1,"PHYSICAL_MIN RD on closed bank");
   physical_min(pa[b],19,"tRCD");physical_min(pg_rd[b&3],3,"tCCDL");
   pr[b]=edge_num;pg_rd[b&3]=edge_num;
  end
 end
 integer edge_num=0,reads=0,landed=0,last_arrival=0,jitter=0,origin=-100000,relative_edge,frame_reads=0,frame_landed=0;
 string image_path,expect_path;
 initial begin
 void'($value$plusargs("JITTER=%d",jitter));
 if(!$value$plusargs("IMAGE=%s",image_path))$fatal(1,"missing compiled image");
 if(!$value$plusargs("EXPECT=%s",expect_path))$fatal(1,"missing independent slot image");
 $readmemh(expect_path,expected_rd);$readmemh(image_path,image);for(integer j=0;j<100001;j++)due[j]=0;for(integer j=0;j<32;j++)openrow[j]=-1;
 repeat(6)@(negedge ck);rn=1;repeat(150)@(negedge ck);
 for(integer i=0;i<32;i++)begin we=1;addr=5'(i);data=i<16?image[i][63:0]:image[i-16][127:64];@(negedge ck);end
 we=0;repeat(3)@(negedge ck);seal=1;@(negedge ck);seal=0;repeat(3)@(negedge ck);
 for(integer l=0;l<36;l++)begin
 layer=6'(l);epoch_in=16'(100+l);frame_reads=0;frame_landed=0;
 go=1;@(negedge ck);go=0;
 repeat(2500)@(negedge ck);
 if(frame_reads!=512||frame_landed!=512)$fatal(1,"FAIL native calendar frame%0d reads%0d landed%0d",l,frame_reads,frame_landed);
 end
 if(reads!=18432||landed!=18432)$fatal(1,"FAIL native calendar count reads%0d landed%0d",reads,landed);
 $display("PASS core833 native controller +independent physical JEDEC PROFILE0 frames=36 reads=%0d landed=%0d jitter=%0d",reads,landed,jitter);$finish;
 end
 always @(posedge ck)begin
 edge_num++;if(go)origin=edge_num;relative_edge=edge_num-origin;
 if(rn)begin
 if(relative_edge>=5&&relative_edge<2500&&po[28]!==expected_rd[relative_edge-5])$fatal(1,"FAIL native calendar PHY timeline edge%0d",relative_edge);
 if(relative_edge>=(DEFAULT_MITER ? 33 : 39)+jitter&&relative_edge<2500&&co[0]!==expected_rd[relative_edge-(DEFAULT_MITER ? 33 : 39)-jitter])$fatal(1,"FAIL native calendar corrected timeline edge%0d",relative_edge);
 if(po[0]&&po[3:1]==1)openrow[po[8:4]]=po[27:9];
 if(po[28])begin
 automatic integer bank=po[34:30],col=po[39:35],sec=((bank>>2)<<7)|(col<<2)|(bank&3),arrival=edge_num+(DEFAULT_MITER ? 23 : 29)+jitter;
 if(po[29]||openrow[bank]!=64+integer'(layer))$fatal(1,"FAIL native calendar PHY row/direction bank%0d row%0d",bank,openrow[bank]);
 if(arrival<=last_arrival)arrival=last_arrival+1;last_arrival=arrival;
 due[arrival]={encode(payload(sec,openrow[bank])),1'b1};reads++;frame_reads++;
 end
 if(co[0])begin
 automatic integer o=frame_landed-256,sec=frame_landed<256?frame_landed:512+((o&8)<<4)+((o>>4)<<3)+(o&7);
 if(oe!=epoch_in||{co[11:9],co[7:1]}!=10'(sec)||co[281:26]!==payload(sec,64+integer'(layer)))$fatal(1,"FAIL native calendar actual data index%0d",landed);
 landed++;frame_landed++;
 end
 if(fault||cf||calfault)begin
 $display("CAUSE ctl%0b port%0b ecc%0b ecdc%0b late%0b wmis%0b tag%0b rawbad%0b obs%0b ref%0b",dut.u_sched.ctl_fault,dut.u_sched.port_fault,dut.u_sched.ecc_fault,dut.u_sched.f_ecdc,dut.u_sched.f_late,dut.u_sched.f_wmis,dut.u_sched.f_tag,dut.u_sched.raw_bad,dut.u_sched.native_observer_fault,dut.u_sched.u_ctl.core.ref_fault);
 $display("DETAIL schedule%0b cmd%0b early%0b raw%0b legalrd%0b j%0d go%0b open%h done%h",dut.u_sched.u_ctl.core.on.fault_schedule,dut.u_sched.f_cmd,dut.u_sched.f_early,dut.u_sched.f_raw,dut.u_sched.u_ctl.core.on.legal_rd,dut.u_sched.u_ctl.core.on.j,dut.u_sched.u_ctl.core.go,dut.u_sched.u_ctl.core.on.open,dut.u_sched.u_ctl.core.on.done);$fatal(1,"FAIL native calendar fault edge%0d fo%0b cf%0b cal%0b",edge_num,fault,cf,calfault);end
 end
 end
 always @(negedge ck)pi=due[edge_num+1];
endmodule
