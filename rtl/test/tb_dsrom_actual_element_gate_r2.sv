`timescale 1ps/1ps
// R2 PREPARE ONLY: settle falling-edge propagation before checking; period remains 833 ps.
// Fixture-only duty-phase adjustment (high 417 -> 416 ps, low 416 -> 417 ps).
// No clockgate RTL, arithmetic, geometry, timing qualification, or adoption change.
module actual_element_case #(parameter BF=0, XF=4);
    reg clk=0,rst_n=1;
    reg cfg_go=0;
    reg [5:0] cfg_ph=0;
    reg [2:0] cfg_np=0;
    reg go=0;
    reg go_bf=0;
    reg xs_v=0;
    reg [7:0] xs_p=0;
    reg [2:0] xs_b=0;
    reg [1:0] xs_sv=0;
    reg [255:0] xs_q0=0;
    reg [9:0] xs_e0=0;
    reg [255:0] xs_q1=0;
    reg [9:0] xs_e1=0;
    reg [2:0] xs_pos=0;
    reg [2:0] xb_pos=0;
    reg xb_v=0;
    reg [2:0] xb_b=0;
    reg [3:0] xb_sv=0;
    reg [31:0] xb_u=0;
    reg [1023:0] xb_d=0;
    wire [1:0] r_pv;
    wire [63:0] r_pval;
    wire [31:0] r_prow;
    wire [9:0] r_pseg;
    wire [9:0] r_pnseg;
    wire [1:0] r_perr;
    wire [5:0] r_ppos;
    wire r_busy;
    wire r_fault;
    wire r_quiet;
    wire [1:0] c_pv;
    wire [63:0] c_pval;
    wire [31:0] c_prow;
    wire [9:0] c_pseg;
    wire [9:0] c_pnseg;
    wire [1:0] c_perr;
    wire [5:0] c_ppos;
    wire c_busy;
    wire c_fault;
    wire c_quiet;
    ref_ot_v41_pair_w17w10 #(.NSEG(8),.NCH(16),.XF(XF),.LV(5),.BF16(BF),.MTP(1),.EARLY(1),.FAST(1),.PP(1),.BP(0),.PHW(6),.INSTANCE(BF?"bf":"q")) ref_dut
      (.clk(clk),.rst_n(rst_n),.cfg_go(cfg_go),.cfg_ph(cfg_ph),.cfg_np(cfg_np),.go(go),.go_bf(go_bf),.xs_v(xs_v),.xs_p(xs_p),.xs_b(xs_b),.xs_sv(xs_sv),.xs_q0(xs_q0),.xs_e0(xs_e0),.xs_q1(xs_q1),.xs_e1(xs_e1),.xs_pos(xs_pos),.xb_pos(xb_pos),.xb_v(xb_v),.xb_b(xb_b),.xb_sv(xb_sv),.xb_u(xb_u),.xb_d(xb_d),.pv(r_pv),.pval(r_pval),.prow(r_prow),.pseg(r_pseg),.pnseg(r_pnseg),.perr(r_perr),.ppos(r_ppos),.busy(r_busy),.fault(r_fault),.quiet(r_quiet));
    cand_ot_v41_pair_w17w10 #(.NSEG(8),.NCH(16),.XF(XF),.LV(5),.BF16(BF),.MTP(1),.EARLY(1),.FAST(1),.PP(1),.BP(0),.PHW(6),.INSTANCE(BF?"bf":"q")) cand_dut
      (.clk(clk),.rst_n(rst_n),.cfg_go(cfg_go),.cfg_ph(cfg_ph),.cfg_np(cfg_np),.go(go),.go_bf(go_bf),.xs_v(xs_v),.xs_p(xs_p),.xs_b(xs_b),.xs_sv(xs_sv),.xs_q0(xs_q0),.xs_e0(xs_e0),.xs_q1(xs_q1),.xs_e1(xs_e1),.xs_pos(xs_pos),.xb_pos(xb_pos),.xb_v(xb_v),.xb_b(xb_b),.xb_sv(xb_sv),.xb_u(xb_u),.xb_d(xb_d),.pv(c_pv),.pval(c_pval),.prow(c_prow),.pseg(c_pseg),.pnseg(c_pnseg),.perr(c_perr),.ppos(c_ppos),.busy(c_busy),.fault(c_fault),.quiet(c_quiet));
    integer cycles=0,partials=0,issues=0,gated=0,opened=0,loads=0;
    integer phase_outputs=0,ph,np,p,u,bl,l;
    task compare_all;
      if(ref_dut.u_e.gclk !== (clk & ref_dut.u_e.g_cg.u_cg.en_l)) $fatal(1,"gate latch behavior");
      if(ref_dut.u_e.g_cg.u_cg.en_l !== cand_dut.u_e.g_cg.u_cg.en_l) $fatal(1,"DIFF gate latch");
      if ({r_pv,r_pval,r_prow,r_pseg,r_pnseg,r_perr,r_ppos,r_busy,r_fault,r_quiet} !== {c_pv,c_pval,c_prow,c_pseg,c_pnseg,c_perr,c_ppos,c_busy,c_fault,c_quiet}) $fatal(1,"DIFF public cycle=%0d",cycles);
      if(ref_dut.go_e !== cand_dut.go_e) $fatal(1,"DIFF go_e cycle=%0d",cycles);
      if(ref_dut.act !== cand_dut.act) $fatal(1,"DIFF act cycle=%0d",cycles);
      if(ref_dut.ld_run !== cand_dut.ld_run) $fatal(1,"DIFF ld_run cycle=%0d",cycles);
      if(ref_dut.ld_k !== cand_dut.ld_k) $fatal(1,"DIFF ld_k cycle=%0d",cycles);
      if(ref_dut.ld_a !== cand_dut.ld_a) $fatal(1,"DIFF ld_a cycle=%0d",cycles);
      if(ref_dut.ld_np !== cand_dut.ld_np) $fatal(1,"DIFF ld_np cycle=%0d",cycles);
      if(ref_dut.c_v !== cand_dut.c_v) $fatal(1,"DIFF c_v cycle=%0d",cycles);
      if(ref_dut.c_a !== cand_dut.c_a) $fatal(1,"DIFF c_a cycle=%0d",cycles);
      if(ref_dut.c_d !== cand_dut.c_d) $fatal(1,"DIFF c_d cycle=%0d",cycles);
      if(ref_dut.u_e.gclk !== cand_dut.u_e.gclk) $fatal(1,"DIFF u_e.gclk cycle=%0d",cycles);
      if(ref_dut.u_e.cg_en !== cand_dut.u_e.cg_en) $fatal(1,"DIFF u_e.cg_en cycle=%0d",cycles);
      if(ref_dut.u_e.drain !== cand_dut.u_e.drain) $fatal(1,"DIFF u_e.drain cycle=%0d",cycles);
      if(ref_dut.u_e.walk_busy !== cand_dut.u_e.walk_busy) $fatal(1,"DIFF u_e.walk_busy cycle=%0d",cycles);
      if(ref_dut.u_e.n_run !== cand_dut.u_e.n_run) $fatal(1,"DIFF u_e.n_run cycle=%0d",cycles);
      if(ref_dut.u_e.bn_run !== cand_dut.u_e.bn_run) $fatal(1,"DIFF u_e.bn_run cycle=%0d",cycles);
      if(ref_dut.u_e.w_run !== cand_dut.u_e.w_run) $fatal(1,"DIFF u_e.w_run cycle=%0d",cycles);
      if(ref_dut.u_e.w_q !== cand_dut.u_e.w_q) $fatal(1,"DIFF u_e.w_q cycle=%0d",cycles);
      if(ref_dut.u_e.w_b !== cand_dut.u_e.w_b) $fatal(1,"DIFF u_e.w_b cycle=%0d",cycles);
      if(ref_dut.u_e.w_c !== cand_dut.u_e.w_c) $fatal(1,"DIFF u_e.w_c cycle=%0d",cycles);
      if(ref_dut.u_e.w_j !== cand_dut.u_e.w_j) $fatal(1,"DIFF u_e.w_j cycle=%0d",cycles);
      if(ref_dut.u_e.w_s !== cand_dut.u_e.w_s) $fatal(1,"DIFF u_e.w_s cycle=%0d",cycles);
      if(ref_dut.u_e.w_h !== cand_dut.u_e.w_h) $fatal(1,"DIFF u_e.w_h cycle=%0d",cycles);
      if(ref_dut.u_e.f_cnt !== cand_dut.u_e.f_cnt) $fatal(1,"DIFF u_e.f_cnt cycle=%0d",cycles);
      if(ref_dut.u_e.issue !== cand_dut.u_e.issue) $fatal(1,"DIFF u_e.issue cycle=%0d",cycles);
      if(ref_dut.u_e.pop !== cand_dut.u_e.pop) $fatal(1,"DIFF u_e.pop cycle=%0d",cycles);
      if(ref_dut.u_e.hazard !== cand_dut.u_e.hazard) $fatal(1,"DIFF u_e.hazard cycle=%0d",cycles);
      if(ref_dut.u_e.a_ctr !== cand_dut.u_e.a_ctr) $fatal(1,"DIFF u_e.a_ctr cycle=%0d",cycles);
      if(ref_dut.u_e.rom_addr !== cand_dut.u_e.rom_addr) $fatal(1,"DIFF u_e.rom_addr cycle=%0d",cycles);
      if(ref_dut.u_e.i1_v !== cand_dut.u_e.i1_v) $fatal(1,"DIFF u_e.i1_v cycle=%0d",cycles);
      if(ref_dut.u_e.i2x_v !== cand_dut.u_e.i2x_v) $fatal(1,"DIFF u_e.i2x_v cycle=%0d",cycles);
      if(ref_dut.u_e.i2_v !== cand_dut.u_e.i2_v) $fatal(1,"DIFF u_e.i2_v cycle=%0d",cycles);
      if(ref_dut.u_e.i2_t !== cand_dut.u_e.i2_t) $fatal(1,"DIFF u_e.i2_t cycle=%0d",cycles);
      if(ref_dut.u_e.i2_q0 !== cand_dut.u_e.i2_q0) $fatal(1,"DIFF u_e.i2_q0 cycle=%0d",cycles);
      if(ref_dut.u_e.i2_q1 !== cand_dut.u_e.i2_q1) $fatal(1,"DIFF u_e.i2_q1 cycle=%0d",cycles);
      if(ref_dut.u_e.i2_bk !== cand_dut.u_e.i2_bk) $fatal(1,"DIFF u_e.i2_bk cycle=%0d",cycles);
      if(ref_dut.u_e.fam !== cand_dut.u_e.fam) $fatal(1,"DIFF u_e.fam cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[0].cap !== cand_dut.u_e.g_mac[0].cap) $fatal(1,"DIFF u_e.g_mac[0].cap cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[0].cap_hold !== cand_dut.u_e.g_mac[0].cap_hold) $fatal(1,"DIFF u_e.g_mac[0].cap_hold cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[0].g_pp.cap0 !== cand_dut.u_e.g_mac[0].g_pp.cap0) $fatal(1,"DIFF u_e.g_mac[0].g_pp.cap0 cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[0].g_pp.cap1 !== cand_dut.u_e.g_mac[0].g_pp.cap1) $fatal(1,"DIFF u_e.g_mac[0].g_pp.cap1 cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[0].g_pp.rd0 !== cand_dut.u_e.g_mac[0].g_pp.rd0) $fatal(1,"DIFF u_e.g_mac[0].g_pp.rd0 cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[0].g_pp.rd1 !== cand_dut.u_e.g_mac[0].g_pp.rd1) $fatal(1,"DIFF u_e.g_mac[0].g_pp.rd1 cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[0].g_pp.u_rom0.ce_in !== cand_dut.u_e.g_mac[0].g_pp.u_rom0.ce_in) $fatal(1,"DIFF u_e.g_mac[0].g_pp.u_rom0.ce_in cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[0].g_pp.u_rom1.ce_in !== cand_dut.u_e.g_mac[0].g_pp.u_rom1.ce_in) $fatal(1,"DIFF u_e.g_mac[0].g_pp.u_rom1.ce_in cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[0].g_pp.u_rom0.addr_in !== cand_dut.u_e.g_mac[0].g_pp.u_rom0.addr_in) $fatal(1,"DIFF u_e.g_mac[0].g_pp.u_rom0.addr_in cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[0].g_pp.u_rom1.addr_in !== cand_dut.u_e.g_mac[0].g_pp.u_rom1.addr_in) $fatal(1,"DIFF u_e.g_mac[0].g_pp.u_rom1.addr_in cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[0].l0_t !== cand_dut.u_e.g_mac[0].l0_t) $fatal(1,"DIFF u_e.g_mac[0].l0_t cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[0].l1_t !== cand_dut.u_e.g_mac[0].l1_t) $fatal(1,"DIFF u_e.g_mac[0].l1_t cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[0].ci_tag !== cand_dut.u_e.g_mac[0].ci_tag) $fatal(1,"DIFF u_e.g_mac[0].ci_tag cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[0].b_tag !== cand_dut.u_e.g_mac[0].b_tag) $fatal(1,"DIFF u_e.g_mac[0].b_tag cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[0].b_pos !== cand_dut.u_e.g_mac[0].b_pos) $fatal(1,"DIFF u_e.g_mac[0].b_pos cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[0].t_tree !== cand_dut.u_e.g_mac[0].t_tree) $fatal(1,"DIFF u_e.g_mac[0].t_tree cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[0].t_pos !== cand_dut.u_e.g_mac[0].t_pos) $fatal(1,"DIFF u_e.g_mac[0].t_pos cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[1].cap !== cand_dut.u_e.g_mac[1].cap) $fatal(1,"DIFF u_e.g_mac[1].cap cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[1].cap_hold !== cand_dut.u_e.g_mac[1].cap_hold) $fatal(1,"DIFF u_e.g_mac[1].cap_hold cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[1].g_pp.cap0 !== cand_dut.u_e.g_mac[1].g_pp.cap0) $fatal(1,"DIFF u_e.g_mac[1].g_pp.cap0 cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[1].g_pp.cap1 !== cand_dut.u_e.g_mac[1].g_pp.cap1) $fatal(1,"DIFF u_e.g_mac[1].g_pp.cap1 cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[1].g_pp.rd0 !== cand_dut.u_e.g_mac[1].g_pp.rd0) $fatal(1,"DIFF u_e.g_mac[1].g_pp.rd0 cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[1].g_pp.rd1 !== cand_dut.u_e.g_mac[1].g_pp.rd1) $fatal(1,"DIFF u_e.g_mac[1].g_pp.rd1 cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[1].g_pp.u_rom0.ce_in !== cand_dut.u_e.g_mac[1].g_pp.u_rom0.ce_in) $fatal(1,"DIFF u_e.g_mac[1].g_pp.u_rom0.ce_in cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[1].g_pp.u_rom1.ce_in !== cand_dut.u_e.g_mac[1].g_pp.u_rom1.ce_in) $fatal(1,"DIFF u_e.g_mac[1].g_pp.u_rom1.ce_in cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[1].g_pp.u_rom0.addr_in !== cand_dut.u_e.g_mac[1].g_pp.u_rom0.addr_in) $fatal(1,"DIFF u_e.g_mac[1].g_pp.u_rom0.addr_in cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[1].g_pp.u_rom1.addr_in !== cand_dut.u_e.g_mac[1].g_pp.u_rom1.addr_in) $fatal(1,"DIFF u_e.g_mac[1].g_pp.u_rom1.addr_in cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[1].l0_t !== cand_dut.u_e.g_mac[1].l0_t) $fatal(1,"DIFF u_e.g_mac[1].l0_t cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[1].l1_t !== cand_dut.u_e.g_mac[1].l1_t) $fatal(1,"DIFF u_e.g_mac[1].l1_t cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[1].ci_tag !== cand_dut.u_e.g_mac[1].ci_tag) $fatal(1,"DIFF u_e.g_mac[1].ci_tag cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[1].b_tag !== cand_dut.u_e.g_mac[1].b_tag) $fatal(1,"DIFF u_e.g_mac[1].b_tag cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[1].b_pos !== cand_dut.u_e.g_mac[1].b_pos) $fatal(1,"DIFF u_e.g_mac[1].b_pos cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[1].t_tree !== cand_dut.u_e.g_mac[1].t_tree) $fatal(1,"DIFF u_e.g_mac[1].t_tree cycle=%0d",cycles);
      if(ref_dut.u_e.g_mac[1].t_pos !== cand_dut.u_e.g_mac[1].t_pos) $fatal(1,"DIFF u_e.g_mac[1].t_pos cycle=%0d",cycles);
    endtask
    task tick;
      compare_all(); #416; clk=1; #1; compare_all();
      if(rst_n) begin
        if(ref_dut.u_e.issue) issues=issues+1;
        if(ref_dut.c_v) loads=loads+1;
        if(ref_dut.u_e.gclk) opened=opened+1; else gated=gated+1;
        if(r_pv[0]) begin
          partials=partials+1; phase_outputs=phase_outputs+1;
          if(r_prow[15:0]<16'h100 || r_prow[15:0]>16'h107 || r_pseg[4:0]!=0 || r_pnseg[4:0]!=1 || r_ppos[2:0]>=np)
            $fatal(1,"tag/walk scoreboard");
        end
        if(ph==4 && r_pv[1]) $fatal(1,"inactive second row emitted");
      end
      #415;clk=0;#1;cycles=cycles+1;compare_all();
    endtask
    task gap(input integer n); xs_v=0;xb_v=0;repeat(n) tick();endtask
    task reset_now;
      go=0;cfg_go=0;xs_v=0;xb_v=0;rst_n=0;#1;compare_all();
      if(r_pv || r_fault || r_busy) $fatal(1,"async reset controls");
      repeat(2) tick();rst_n=1;gap(4);
    endtask
    task load_phase(input integer phase_id,input integer positions);
      ph=phase_id;np=positions;cfg_ph=phase_id;cfg_np=positions-1;
      cfg_go=1;tick();cfg_go=0;gap(32);phase_outputs=0;
    endtask
    task start_phase;
      go_bf=(ph==3);go=1;tick();go=0;gap(4);
    endtask
    task stream_phase;
      for(p=0;p<np;p=p+1) for(bl=0;bl<8;bl=bl+1) for(u=0;u<8;u=u+1) begin
        if(ph==3) begin
          xb_v=1;xb_b=bl;xb_pos=p;xb_sv=1;xb_u=u;
          for(l=0;l<64;l=l+1) xb_d[16*l+:16]=(l%2)?16'hbf80:16'h3f81;
        end else begin
          xs_v=1;xs_p=u;xs_b=bl;xs_sv=3;xs_pos=p;
          xs_q0={32{8'h38}};xs_q1={32{8'hb8}};xs_e0=0;xs_e1=0;
        end
        tick();gap(39); // fixed bounded source pacing, no oracle injection
      end
      gap(256);
    endtask
    initial begin
      ph=0;np=1;reset_now();gap(160);
      // Empty go suppressed by unchanged act logic; next operation must still work.
      load_phase(0,1);start_phase();gap(160);
      if(phase_outputs!=0 || ref_dut.act || issues!=0) $fatal(1,"empty go");
      for(ph=1;ph<=5;ph=ph+1) begin
        if(ph==3 && !BF) continue;
        load_phase(ph,ph==5?6:1);start_phase();stream_phase();
        if(phase_outputs!=8*np) $fatal(1,"walk count ph=%0d got=%0d",ph,phase_outputs);
        if(r_fault || r_busy || !r_quiet) $fatal(1,"legal drain/fault/quiet");
      end
      // Cancel walker, captured words, arithmetic and tags while in flight.
      load_phase(2,1);start_phase();xs_v=1;xs_sv=3;xs_p=0;xs_b=0;tick();gap(5);reset_now();gap(160);
      if(r_pv || r_fault || r_busy || !r_quiet) $fatal(1,"reset drain");
      // Restart configuration after cancellation and prove outputs reappear.
      load_phase(BF?3:1,1);start_phase();stream_phase();
      if(phase_outputs!=8 || r_fault || !r_quiet) $fatal(1,"restart");
      if(partials==0 || issues==0 || gated==0 || opened==0 || loads<25*7) $fatal(1,"coverage");
      $display("PASS actual-element BF=%0d cycles=%0d partials=%0d issues=%0d gated=%0d opened=%0d loads=%0d",BF,cycles,partials,issues,gated,opened,loads);
      $finish;
    end
endmodule
module tb_q; actual_element_case #(.BF(0),.XF(4)) test(); endmodule
module tb_bfcolumn; actual_element_case #(.BF(1),.XF(8)) test(); endmodule
