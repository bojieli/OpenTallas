// PREPARE ONLY additive r4. Valid loader diagnostics; LAT8 admission; real upstream source cadence; one full-sized pair causal diagnostic.
// No fabricated FIFO push, root result, clockgate logic, golden injection or timing credit.
`timescale 1ns/1ps
module tb_dsrom_upstream_pair_cadence;
  reg clk=0,rst_n=0,q_go=0;
  wire ready,idle,s_ready,s_idle,a_fault,s_fault;
  wire s_go;wire [5:0] s_ph;wire [2:0] s_np;
  wire [18:0] s_xbase,s_xps,s_obase,s_ops;wire [1:0] s_fmt;
  wire x_re;wire [18:0] x_addr;reg [2047:0] x_q=0;
  reg [31:0] vm [0:524287];reg [8191:0] rom_dir;
  wire [1:0] pv,perr;wire [63:0] pval;wire [31:0] prow;
  wire [9:0] pseg,pnseg;wire [5:0] ppos;wire busy,p_fault,quiet;
  wire cfg_go;
  wire [5:0] cfg_ph;
  wire [2:0] cfg_np;
  wire go;
  wire go_bf;
  wire xs_v;
  wire [7:0] xs_p;
  wire [2:0] xs_b;
  wire [1:0] xs_sv;
  wire [255:0] xs_q0;
  wire [9:0] xs_e0;
  wire [255:0] xs_q1;
  wire [9:0] xs_e1;
  wire [2:0] xs_pos;
  wire [2:0] xb_pos;
  wire xb_v;
  wire [2:0] xb_b;
  wire [3:0] xb_sv;
  wire [31:0] xb_u;
  wire [1023:0] xb_d;
  integer k;always @(posedge clk) if(x_re)
    for(k=0;k<64;k=k+1)begin
      if(int'(x_addr)+k>=524288)$fatal(1,"VM bounds");
      x_q[32*k+:32]<=vm[int'(x_addr)+k];
    end
  ot_v41_rom_adapt #(.PHW(6),.VAW(19)) u_adapt (
    .clk(clk),
    .rst_n(rst_n),
    .q_go(q_go),
    .q_xbase(30'd0),
    .q_nb(8'd16),
    .q_wbase(30'd0),
    .q_ind(1'b0),
    .q_ibase(30'd0),
    .q_istride(30'd0),
    .q_obase(30'd4096),
    .q_unrounded(1'b1),
    .m_go(1'b0),
    .m_k(21'd0),
    .m_split(2'd0),
    .m_wbase(30'd0),
    .m_xbase(30'd0),
    .m_xks(30'd0),
    .m_xcs(30'd0),
    .m_xjs(30'd0),
    .m_obase(30'd0),
    .m_ots(30'd0),
    .m_ojs(30'd0),
    .m_round(1'b0),
    .m_amax(1'b0),
    .m_mmode(1'b0),
    .i_m(3'd2),
    .i_xps(30'd512),
    .i_ops(30'd257),
    .ready(ready),
    .idle(idle),
    .vi_re(),
    .vi_addr(),
    .vi_q(32'd0),
    .s_go(s_go),
    .s_ph(s_ph),
    .s_np(s_np),
    .s_xbase(s_xbase),
    .s_xps(s_xps),
    .s_obase(s_obase),
    .s_ops(s_ops),
    .s_fmt(s_fmt),
    .s_ready(s_ready),
    .s_idle(s_idle),
    .fault(a_fault));
  ot_v41_spine_w17w10 #(.PHW(6),.SAW(14),.R(128),.VAW(19),.VRD(64),.KMAX(6144),.BST(2),.NSEG(8)) u_spine (
    .clk(clk),
    .rst_n(rst_n),
    .go(s_go),
    .i_ph(s_ph),
    .i_np(s_np),
    .i_xbase(s_xbase),
    .i_xps(s_xps),
    .i_obase(s_obase),
    .i_ops(s_ops),
    .i_fmt(s_fmt),
    .ready(s_ready),
    .idle(s_idle),
    .x_re(x_re),
    .x_addr(x_addr),
    .x_q(x_q),
    .w_we(),
    .w_addr(),
    .w_data(),
    .f_cfg_go(cfg_go),
    .f_cfg_ph(cfg_ph),
    .f_cfg_np(cfg_np),
    .f_go(go),
    .f_go_bf(go_bf),
    .f_xs_v(xs_v),
    .f_xs_p(xs_p),
    .f_xs_b(xs_b),
    .f_xs_sv(xs_sv),
    .f_xs_q0(xs_q0),
    .f_xs_e0(xs_e0),
    .f_xs_q1(xs_q1),
    .f_xs_e1(xs_e1),
    .f_xs_pos(xs_pos),
    .f_xb_pos(xb_pos),
    .f_xb_v(xb_v),
    .f_xb_b(xb_b),
    .f_xb_sv(xb_sv),
    .f_xb_u(xb_u),
    .f_xb_d(xb_d),
    .f_bus(),
    .r_v(128'd0),
    .r_row(2048'd0),
    .r_pos(384'd0),
    .r_fp32(4096'd0),
    .r_bf16(2048'd0),
    .r_e(128'd0),
    .f_fault(p_fault),
    .fault(s_fault),
    .phase_cycles());
  ot_v41_pair_w17w10 #(.NSEG(8),.NCH(16),.XF(4),.LV(5),.BF16(0),.MTP(1),.EARLY(1),
    .FAST(1),.PP(1),.BP(0),.PHW(6),.FIX_SECOND_ROW_INDEX(1),.GRADUAL_RNE(1),.WAKE_REG(1),.INSTANCE("e1")) u_pair (
    .clk(clk),
    .rst_n(rst_n),
    .cfg_go(cfg_go),
    .cfg_ph(cfg_ph),
    .cfg_np(cfg_np),
    .go(go),
    .go_bf(go_bf),
    .xs_v(xs_v),
    .xs_p(xs_p),
    .xs_b(xs_b),
    .xs_sv(xs_sv),
    .xs_q0(xs_q0),
    .xs_e0(xs_e0),
    .xs_q1(xs_q1),
    .xs_e1(xs_e1),
    .xs_pos(xs_pos),
    .xb_pos(xb_pos),
    .xb_v(xb_v),
    .xb_b(xb_b),
    .xb_sv(xb_sv),
    .xb_u(xb_u),
    .xb_d(xb_d),
    .pv(pv),
    .pval(pval),
    .prow(prow),
    .pseg(pseg),
    .pnseg(pnseg),
    .perr(perr),
    .ppos(ppos),
    .busy(busy),
    .quiet(quiet),
    .fault(p_fault));
  integer cycles=0,emitted=0,pushes=0,pops=0,issues=0,rows=0,profile;
  reg [1:0] seen=0;
  reg pre_overflow,pre_ffault,pre_gate;integer pre_count,pre_push,pre_pop,pre_issue,pre_hazard;
  task tick;
    // Same 833ps fixture tick as reviewed r2; settle checks after each transition.
    #416;
    pre_count=int'(u_pair.u_e.f_cnt);pre_push=int'(u_pair.u_e.npush);
    pre_pop=int'(u_pair.u_e.pop);pre_issue=int'(u_pair.u_e.issue);
    pre_hazard=int'(u_pair.u_e.hazard);pre_ffault=u_pair.u_e.ffault;
    pre_gate=u_pair.u_e.gclk===1'b0 && u_pair.u_e.g_wake.g_leaf[0].u_cg.en_l;
    pre_overflow=pre_count+pre_push>4+pre_pop;
    if(rst_n)begin
      $display("EDGE cycle=%0d adapt=%0d spine=%0d smpos=%0d smi=%0d have0=%0d have1=%0d sok=%0d adv=%0d cfg=%0d go=%0d xs=%0d u=%0d b=%0d pos=%0d sv=%0d cnt=%0d npush=%0d pop=%0d issue=%0d hazard=%0d gate=%0d",
        cycles,u_adapt.st,u_spine.st,u_spine.sm_pos,u_spine.sm_i,u_spine.have[0],u_spine.have[1],u_spine.s_ok,u_spine.s_adv,
        cfg_go,go,xs_v,xs_p,xs_b,xs_pos,xs_sv,pre_count,pre_push,pre_pop,pre_issue,pre_hazard,pre_gate);
      if(xs_v)begin
        if(xs_p!=0 || xs_b!=emitted%8 || xs_pos!=emitted/8 || xs_sv!=3)$fatal(1,"EMITTED_ORDER");
        $display("EMITTED cycle=%0d p=%0d b=%0d pos=%0d q0=%h e0=%h q1=%h e1=%h",cycles,xs_p,xs_b,xs_pos,xs_q0,xs_e0,xs_q1,xs_e1);
        emitted=emitted+1;
      end
      if(pre_gate)begin pushes=pushes+pre_push;pops=pops+pre_pop;issues=issues+pre_issue;end
    end
    if(rst_n)begin
      $display("LOADER cycle=%0d valid=%0d addr=%0d ld_run=%0d ld_k=%0d",cycles,u_pair.c_v,u_pair.c_a,u_pair.ld_run,u_pair.ld_k);
      if(u_pair.c_v && u_pair.c_a>=25)$fatal(1,"VALID_CONFIG_ADDRESS cycle=%0d addr=%0d",cycles,u_pair.c_a);
    end
    clk=1;#1;
    if(rst_n)begin
      if(a_fault)$fatal(1,"UPSTREAM_ADAPTER_FAULT cycle=%0d",cycles);
      // First local sticky fault is checked before the spine re-observes it next edge.
      if(u_pair.u_e.ffault && !pre_ffault)begin
        $display("FIRST_FAULT cycle=%0d pos=%0d cnt=%0d npush=%0d pop=%0d issue=%0d hazard=%0d overflow=%0d gate=%0d emitted=%0d pushes=%0d pops=%0d issues=%0d pairfault=%0d spinefault=%0d",
          cycles,xs_pos,pre_count,pre_push,pre_pop,pre_issue,pre_hazard,pre_overflow,pre_gate,emitted,pushes,pops,issues,p_fault,s_fault);
        $display("FIRST_FAULT_SOURCE wpos=%0d npos=%0d slot=%0d ca=%0d valid=%0d ld_run=%0d ld_k=%0d cd=%h row0=%h row1=%h",u_pair.u_e.w_pos,u_pair.u_e.n_pos,u_pair.u_e.w_cnt,u_pair.c_a,u_pair.c_v,u_pair.ld_run,u_pair.ld_k,u_pair.c_d,u_pair.u_e.s_row[0],u_pair.u_e.s_row[8]);
        if(!pre_overflow || !pre_gate)$fatal(1,"FIRST_FAULT_DIFFERENT_CAUSE");
        if(profile!=5)$fatal(1,"CONTROL_FIRST_FAULT");
        $display("REPRODUCED_FIRST_XFIFO_OVERFLOW profile=5 cycle=%0d",cycles);$finish;
      end else begin
      if(p_fault || s_fault)$fatal(1,"OTHER_FAULT cycle=%0d",cycles);
      if(pv[1])$fatal(1,"IDLE_MACRO_EMITTED");
      if(pv[0])begin
        $display("PUBLIC row=%0d seg=%0d nseg=%0d pos=%0d value=%h err=%0d",prow[15:0],pseg[4:0],pnseg[4:0],ppos[2:0],pval[31:0],perr[0]);
        if(prow[15:0]!=256 || pseg[4:0]!=0 || pnseg[4:0]!=1 || ppos[2:0]>1 || perr[0] || pval[31:0]!=32'h44000000)
          $fatal(1,"PUBLIC_ORACLE_DIFFERENCE");
        if(seen[ppos[2:0]])$fatal(1,"DUPLICATE_PUBLIC");
        seen[ppos[2:0]]=1;rows=rows+1;
      end
      end
    end
    #415;clk=0;#1;cycles=cycles+1;
    if(u_pair.u_e.gclk!==1'b0)$fatal(1,"FALL_GATE_SETTLE");
  endtask
  initial begin
    if(!$value$plusargs("PROFILE=%d",profile) || profile!=8)$fatal(1,"STALE_IMAGE_ADMISSION_PROFILE");
    if(!$value$plusargs("OT_ROM_DIR=%s",rom_dir))$fatal(1,"ROM_DIR");
    $readmemh({rom_dir,"/VM_input.hex"},vm);
    rst_n=0;#1;repeat(3)tick();rst_n=1;#1;
    repeat(4)tick();if(!ready)$fatal(1,"ADAPTER_NOT_READY");q_go=1;tick();q_go=0;
    repeat(1024)tick();
    if(profile==5)$fatal(1,"STATIC_WITNESS_NOT_REPRODUCED");
    if(rows!=2 || seen!=2'b11 || emitted!=16 || pushes!=16 || pops!=16 || issues!=16 || busy || !quiet)
      $fatal(1,"CONTROL_COVERAGE rows=%0d emitted=%0d pushes=%0d pops=%0d issues=%0d busy=%0d quiet=%0d",rows,emitted,pushes,pops,issues,busy,quiet);
    $display("PASS_EXISTING_FAST_PROFILE rows=2 emitted=16 pushes=16 pops=16 issues=16");
    $finish;
  end
endmodule
