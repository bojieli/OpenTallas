`timescale 1ns/1ps
`default_nettype none
// DIE-HBM-88 vL7 RRMIR lock-step bench: ot_svgr_top_cachecut (new file, RRMIR from define) vs the vL7 file renamed *_ref
// (f69e0b0bbb), same parameters otherwise.  Protocol-steered random stimulus from the REFERENCE state: programme store,
// descriptor tables (good + bad descriptors), run / ids, per-bank seam completes, random read data, injected seam_h_fault /
// seam_bfault pulses, stream-only / hbm-only / both resets (also mid-run).  Every cachecut output compared every edge (!==),
// after the new inputs settle.  With RRM=1, internal invariants: mirrors == producer state, reserve_ready == reference.
`ifndef P1V
`define P1V 1
`endif
`ifndef OIL
`define OIL 1
`endif
`ifndef IDC
`define IDC 1
`endif
`ifndef XS
`define XS 1
`endif
`ifndef LBK
`define LBK 4
`endif
`ifndef RRM
`define RRM 1
`endif
`ifndef WDEC
`define WDEC 1
`endif
`ifndef GS
`define GS 1
`endif
`ifndef GR
`define GR 2
`endif
`ifndef NCYC
`define NCYC 200000
`endif
`ifndef SEED
`define SEED 1
`endif
`ifndef STOP1
`define STOP1 0
`endif
module tb;
 localparam integer LBANKS=`LBK, LB=(LBANKS>2)?2:1, NID=6, IDW=9, PAW=11, DAW=8;
 reg clk=0; always #5 clk=~clk;
 reg stream_rst_n=0,hbm_rst_n=0;
 reg [1:0] id_stack=0; reg [2:0] id_sm=0;
 reg seam_h_fault=0; reg [7:0] seam_complete=0,seam_bfault=0; reg [15:0] seam_complete_bank=0; reg [2047:0] seam_read_data=0;
 reg program_cfg_we=0; reg [PAW-1:0] program_cfg_addr=0; reg [255:0] program_cfg_data=0;
 reg desc_we=0; reg [DAW-1:0] desc_addr=0; reg [255:0] desc_data=0;
 reg run_v=0; reg [DAW-1:0] run_base=0; reg [DAW:0] run_count=0; reg [7:0] run_layer=0;
 reg ids_v=0; reg [7:0] ids_layer=0; reg [IDW*NID-1:0] ids=0; reg [15:0] ids_cohort=0;
 // outputs
 `define OUTS(p) wire p``res_v,p``s_fault,p``stop,p``running,p``run_done,p``pa,p``fault; wire [96:0] p``res_word; wire [7:0] p``read_v; \
   wire [1:0] p``read_bank; wire [47:0] p``read_row; wire [1098:0] p``smp; wire [82:0] p``smc; wire [42:0] p``er; \
   wire [1081:0] p``lt0,p``lt1; wire [569:0] p``lb0,p``lb1; wire [11:0] p``fm;
 `OUTS(a_)
 `OUTS(b_)
 `define CONN(p) .id_stack(id_stack),.id_sm(id_sm),.stream_clk(clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n), \
   .seam_res_v(p``res_v),.seam_res_word(p``res_word),.seam_s_fault(p``s_fault),.seam_h_fault(seam_h_fault), \
   .seam_stop(p``stop),.seam_read_v(p``read_v),.seam_read_bank(p``read_bank),.seam_read_row(p``read_row), \
   .seam_complete(seam_complete),.seam_complete_bank(seam_complete_bank),.seam_bfault(seam_bfault),.seam_read_data(seam_read_data), \
   .program_cfg_we(program_cfg_we),.program_cfg_addr(program_cfg_addr),.program_cfg_data(program_cfg_data), \
   .desc_we(desc_we),.desc_addr(desc_addr),.desc_data(desc_data),.run_v(run_v),.run_base(run_base),.run_count(run_count),.run_layer(run_layer), \
   .ids_v(ids_v),.ids_layer(ids_layer),.ids(ids),.ids_cohort(ids_cohort), \
   .running(p``running),.run_done(p``run_done),.program_active(p``pa),.fault(p``fault), \
   .sm_packet(p``smp),.sm_command(p``smc),.expected_request(p``er),.lt0(p``lt0),.lt1(p``lt1),.lb0(p``lb0),.lb1(p``lb1),.fm(p``fm)
 ot_svgr_top_cachecut_ref #(.LBANKS(LBANKS),.NID(NID),.IDW(IDW),.PAW(PAW),.PREL(1),.DD(256),.ID_COHORT(`IDC),.XSLOT(`XS),.OPEN_IL(`OIL),
  .CACHE_RW_SRAM(1),.P1(`P1V),.CACHE_WDEC(`WDEC),.CACHE_GSEL(`GS),.CACHE_GREP(`GR)) ref_i(`CONN(a_));
 ot_svgr_top_cachecut #(.LBANKS(LBANKS),.NID(NID),.IDW(IDW),.PAW(PAW),.PREL(1),.DD(256),.ID_COHORT(`IDC),.XSLOT(`XS),.OPEN_IL(`OIL),
  .CACHE_RW_SRAM(1),.P1(`P1V),.CACHE_WDEC(`WDEC),.CACHE_GSEL(`GS),.CACHE_GREP(`GR),.RRMIR(`RRM)) dut_i(`CONN(b_));
 wire [6000:0] va={a_res_v,a_s_fault,a_stop,a_running,a_run_done,a_pa,a_fault,a_res_word,a_read_v,a_read_bank,a_read_row,a_smp,a_smc,a_er,a_lt0,a_lt1,a_lb0,a_lb1,a_fm};
 wire [6000:0] vb={b_res_v,b_s_fault,b_stop,b_running,b_run_done,b_pa,b_fault,b_res_word,b_read_v,b_read_bank,b_read_row,b_smp,b_smc,b_er,b_lt0,b_lt1,b_lb0,b_lb1,b_fm};
 // reference state used to steer stimulus and count coverage
 wire [LBANKS-1:0] r_alloc=ref_i.feed.producer.allocated, r_ready=ref_i.feed.producer.ready_q;
 wire r_sf=ref_i.feed.producer.stream_fault, r_srst=ref_i.feed.producer.srst, r_drain=ref_i.feed.producer.draining;
 wire r_stv=ref_i.issuer.st_v, r_rr=ref_i.feed.reserve_ready, r_fire=ref_i.feed.reserve_fire, r_irun=ref_i.issuer.running;
 wire [LB-1:0] r_rbank=ref_i.feed.reserve_bank;
 wire [7:0] r_layer=ref_i.issuer.layer_q; wire [15:0] r_coh=ref_i.issuer.run_cohort_q;
 integer seed=`SEED, cyc=0, mism=0, ibad=0, first_mism=-1, first_ibad=-1, k, b;
 integer n_fire=0,n_stall=0,n_stall_alloc=0,n_stall_flt=0,n_sf_rise=0,n_start=0,n_dend=0,n_hf=0,n_bf=0,n_hf_stv=0,n_rst_s=0,n_rst_h=0,n_rst_b=0,
   n_desc=0,n_bad_desc=0,n_runs=0,n_fire_bank[0:3],n_realloc=0,n_res_out=0,n_dfault=0,n_ifault=0,n_xctl=0,n_tgt=0;
 reg pr_sf=0, pr_df=0, pr_if=0;
 function [31:0] rnd(input integer d); rnd=$random(seed); endfunction
 function integer ur(input integer n); ur=$unsigned($random(seed))%n; endfunction
 // life state machine
 localparam S_RST=0,S_PROG=1,S_DESC=2,S_RUN=3;
 integer st=S_RST, cnt=0, L=60, nd=8, dbase=0, ga=0, life=0, rst_len=0, rst_kind=0, ids_at=-1, sf_age=0, last_fire_bank=-1;
 reg [255:0] dw;
 task mkdesc(input integer addr, input integer i);
  integer rows;
  begin
   dw=0;
   dw[255:240]=(ur(400)==0)?16'h5d14:16'h5d15;
   dw[239:232]=(ur(400)==0)?addr+1:addr;
   if(`XS)dw[206:200]=rnd(0);
   dw[199]=rnd(0);dw[198:197]=rnd(0);dw[196:195]=rnd(0);
   dw[194:191]=(ur(5)==0)?rnd(0):4'd0;
   dw[188:177]=rnd(0);
   k=ur(100); dw[176:173]=(k<60)?4'd0:(1+ur(NID)); // a_sel > NID (issuer faults) selects past ids_q: X in RTL sim, not injected
   dw[172:158]=ur(4);dw[157:143]=ur(4);
   ga=ga+120+ur(500); dw[142:119]=ga;
   dw[118:103]=(dw[194:191]==0)?16'd1:(1+ur(3));
   {dw[190],dw[102:92]}=(ur(40)==0)?ur(4096):L;
   {dw[189],dw[91:82]}=0;
   dw[81:72]=rnd(0);
   rows=1+ur(64); if(ur(60)==0)rows=(ur(2)==0)?0:65+ur(60);
   dw[71:65]=rows;
   dw[64:49]=rnd(0);
   dw[48:47]=rnd(0);
   dw[46:32]=ur(4096);
   dw[31:30]=(ur(50)==0)?id_stack+1:id_stack;
   dw[29:10]=(ur(50)==0)?(20'd1<<ur(20)):20'd0;
   dw[9:7]=rnd(0);
   dw[6:0]=(ur(50)==0)?(7'd1<<ur(7)):7'd0;
   if(dw[255:240]!=16'h5d15||dw[239:232]!=addr||dw[31:30]!=id_stack||dw[29:10]!=0||dw[6:0]!=0||rows==0||rows>64)n_bad_desc=n_bad_desc+1;
   n_desc=n_desc+1;
  end
 endtask
 initial for(k=0;k<4;k=k+1)n_fire_bank[k]=0;
 always @(negedge clk) begin
  // ---------------- drive ----------------
  program_cfg_we=0;desc_we=0;run_v=0;ids_v=0;seam_complete=0;seam_complete_bank=rnd(0);seam_h_fault=0;seam_bfault=0;
  for(k=0;k<64;k=k+1)seam_read_data[k*32+:32]=rnd(0);
  program_cfg_addr=rnd(0);program_cfg_data={rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0)};
  desc_addr=rnd(0);desc_data={rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0),rnd(0)};
  run_base=rnd(0);run_count=rnd(0);run_layer=rnd(0);ids_layer=rnd(0);ids=rnd(0);ids_cohort=rnd(0);
  case(st)
   S_RST: begin
     if(cnt==0)begin
      rst_kind=ur(4); // 0,1 both; 2 stream only; 3 hbm only
      rst_len=1+ur(3);
     end
     stream_rst_n=!(rst_kind!=3); hbm_rst_n=!(rst_kind!=2);
     if(rst_kind!=3)begin id_stack=rnd(0);id_sm=rnd(0);end
     cnt=cnt+1;
     if(cnt>rst_len)begin
      stream_rst_n=1;hbm_rst_n=1;cnt=0;
      if(rst_kind==3)st=S_RUN; else begin st=S_PROG;L=30+ur(100);life=life+1;end
      if(rst_kind==3)n_rst_h=n_rst_h+1; else if(rst_kind==2)n_rst_s=n_rst_s+1; else n_rst_b=n_rst_b+1;
     end
   end
   S_PROG: begin
     program_cfg_we=1;program_cfg_addr=cnt;
     program_cfg_data=0;program_cfg_data[255:240]=16'hc7a1;program_cfg_data[234:224]=cnt;
     program_cfg_data[117]=(cnt==L-1);
     if(ur(3000)==0)program_cfg_data[200]=1; // bad word, rare
     cnt=cnt+1; if(cnt==L)begin cnt=0;st=S_DESC;nd=2+ur(30);dbase=ur(256-nd);ga=0;end
   end
   S_DESC: begin
     desc_we=1;desc_addr=dbase+cnt;mkdesc(dbase+cnt,cnt);desc_data=dw;
     cnt=cnt+1; if(cnt==nd)begin cnt=0;st=S_RUN;end
   end
   S_RUN: begin
     if(cnt==0)begin run_v=1;run_base=dbase;run_count=(ur(30)==0)?0:nd;run_layer=ur(4);ids_at=2+ur(6);n_runs=n_runs+1;end
     if(cnt==ids_at)begin ids_v=(ur(20)!=0);ids_layer=(ur(30)==0)?r_layer+1:r_layer;ids_cohort=(ur(30)==0)?r_coh+1:r_coh;end
     // completes: steer to allocated, not-yet-ready banks
     for(b=0;b<LBANKS;b=b+1)if(r_alloc[b]&&!r_ready[b]&&ur(3)==0)begin
      k=ur(8);seam_complete[k]=1;seam_complete_bank[2*k+:2]=b;
     end
     if(ur(300)==0)seam_complete[ur(8)]=1;
     if(ur(3000)==0)begin seam_h_fault=1;n_hf=n_hf+1;if(r_stv)n_hf_stv=n_hf_stv+1;end
     if(ur(3000)==0)begin seam_bfault[ur(8)]=1;n_bf=n_bf+1;end
`ifdef TGT
     // targeted: an h / b fault pulse on an edge where the reference would otherwise fire a reserve
     if(r_stv&&r_srst&&!r_alloc[r_rbank]&&!r_sf&&ur(6)==0)begin if(ur(2)==0)seam_h_fault=1;else seam_bfault[ur(8)]=1;n_tgt=n_tgt+1;end
`endif
     if(r_sf)sf_age=sf_age+1; else sf_age=0;
     cnt=cnt+1;
     if(ur(5000)==0)begin st=S_RST;cnt=0;end
     else if(sf_age>(150+ur(400))||cnt>(2500+ur(6000)))begin st=S_RST;cnt=0;sf_age=0;end
   end
  endcase
  // ---------------- compare (inputs settled) ----------------
  #1;
  if(stream_rst_n||1)begin
   if(va!==vb)begin mism=mism+1;if(first_mism<0)begin first_mism=cyc;
     $display("MISMATCH cyc %0d res_v %b/%b s_fault %b/%b stop %b/%b run %b/%b fault %b/%b res_word %0d read_v %b/%b smp %0d smc %0d er %0d lt %0d lb %0d",cyc,
      a_res_v,b_res_v,a_s_fault,b_s_fault,a_stop,b_stop,a_running,b_running,a_fault,b_fault,a_res_word!==b_res_word,a_read_v,b_read_v,
      a_smp!==b_smp,a_smc!==b_smc,a_er!==b_er,(a_lt0!==b_lt0)||(a_lt1!==b_lt1),(a_lb0!==b_lb0)||(a_lb1!==b_lb1));
     if(`STOP1)begin $display("RESULT STOP1 first_mism %0d first_ibad %0d ibad %0d",cyc,first_ibad,ibad);$finish;end end end
`ifdef RRM1
   // internal invariants of the mirror form
   for(b=0;b<LBANKS;b=b+1)begin
    if(dut_i.feed.g_rr_mirror.av_i[b]!==(!dut_i.feed.producer.allocated[b]&&!dut_i.feed.producer.stream_fault)||
       dut_i.feed.g_rr_mirror.av_f[b]!==(!dut_i.feed.producer.allocated[b]&&!dut_i.feed.producer.stream_fault)||
       dut_i.feed.producer.g_sfm.sf_p[b]!==dut_i.feed.producer.stream_fault)begin ibad=ibad+1;if(first_ibad<0)first_ibad=cyc;end
   end
   if(dut_i.feed.producer.g_sfm.sf_d!==dut_i.feed.producer.stream_fault||dut_i.feed.reserve_ready!==r_rr||dut_i.feed.reserve_fire!==r_fire)
    begin ibad=ibad+1;if(first_ibad<0)first_ibad=cyc;end
`endif
  end
`ifdef DBGC
  if(cyc>=`DBGC-12&&cyc<=`DBGC)$display("DBG %0d srst %b/%b stv %b rr %b/%b fire %b/%b rbank %0d alloc %b/%b sf %b/%b hf %b bf %b ok %b/%b drain %b start %b avi %b avf %b sfp %b sfd %b nsf_p %b clr %b keep %b resv %b/%b st_rst %b hbm_rst %b",cyc,
   r_srst,dut_i.feed.producer.srst,r_stv,r_rr,dut_i.feed.reserve_ready,r_fire,dut_i.feed.reserve_fire,r_rbank,r_alloc,dut_i.feed.producer.allocated,r_sf,dut_i.feed.producer.stream_fault,seam_h_fault,seam_bfault,
   ref_i.feed.producer.descriptor_ok,dut_i.feed.rrm_desc_ok,r_drain,ref_i.issuer.start_v,dut_i.feed.g_rr_mirror.av_i,dut_i.feed.g_rr_mirror.av_f,dut_i.feed.producer.g_sfm.sf_p,dut_i.feed.producer.g_sfm.sf_d,
   dut_i.feed.rrm_nsf_p,dut_i.feed.rrm_clr,dut_i.feed.rrm_alloc_keep,a_res_v,b_res_v,stream_rst_n,hbm_rst_n);
`endif
  // coverage (reference)
  if(r_fire)begin n_fire=n_fire+1;n_fire_bank[r_rbank]=n_fire_bank[r_rbank]+1;end
  if(r_stv&&!r_rr)begin n_stall=n_stall+1;if(r_alloc[r_rbank])n_stall_alloc=n_stall_alloc+1;if(r_sf||seam_h_fault||(|seam_bfault))n_stall_flt=n_stall_flt+1;end
  if(a_res_v)n_res_out=n_res_out+1;
  if((r_stv&&(^r_rr===1'bx))||(r_fire&&(^ref_i.feed.producer.descriptor_ok===1'bx)))n_xctl=n_xctl+1;
  if(r_sf&&!pr_sf)n_sf_rise=n_sf_rise+1; pr_sf=r_sf;
  if(ref_i.feed.descriptor_fault&&!pr_df)n_dfault=n_dfault+1; pr_df=ref_i.feed.descriptor_fault;
  if(ref_i.issuer.fault&&!pr_if)n_ifault=n_ifault+1; pr_if=ref_i.issuer.fault;
  if(ref_i.issuer.start_v)n_start=n_start+1;
  if(ref_i.feed.producer.draining&&ref_i.feed.producer.o_v==0&&0)n_dend=n_dend;
  cyc=cyc+1;
  if(cyc==`NCYC)begin
   $display("RESULT RRM %0d P1 %0d OIL %0d IDC %0d XS %0d LBK %0d WDEC %0d GS %0d GR %0d seed %0d cycles %0d mism %0d first_mism %0d ibad %0d first_ibad %0d",
    `RRM,`P1V,`OIL,`IDC,`XS,`LBK,`WDEC,`GS,`GR,`SEED,cyc,mism,first_mism,ibad,first_ibad);
   $display("COVER tgt %0d xctl %0d lives %0d runs %0d desc %0d bad_desc %0d fires %0d (b0 %0d b1 %0d b2 %0d b3 %0d) res_v_out %0d stall %0d stall_alloc %0d stall_fault %0d sf_rises %0d dfault %0d ifault %0d starts %0d hf %0d hf_while_stv %0d bf %0d rst both %0d stream %0d hbm %0d",
    n_tgt,n_xctl,life,n_runs,n_desc,n_bad_desc,n_fire,n_fire_bank[0],n_fire_bank[1],n_fire_bank[2],n_fire_bank[3],n_res_out,n_stall,n_stall_alloc,n_stall_flt,n_sf_rise,n_dfault,n_ifault,n_start,n_hf,n_hf_stv,n_bf,n_rst_b,n_rst_s,n_rst_h);
   $finish;
  end
 end
 // drain-end count (reference): allocated bit falling while draining
 reg [LBANKS-1:0] pr_alloc=0;
 integer bb;
 always @(posedge clk) begin #2; for(bb=0;bb<LBANKS;bb=bb+1) if(pr_alloc[bb]&&!r_alloc[bb]&&r_srst) n_dend=n_dend+1; pr_alloc=r_alloc; end
 final $display("DRAINEND %0d", n_dend);
endmodule
`default_nettype wire
