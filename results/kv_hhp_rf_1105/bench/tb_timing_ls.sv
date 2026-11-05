`timescale 1ps/1fs
// DIE-KV-71/HHP 11-05: old vs new ot_qkd_static_kv_timing, every output on every edge, random stimulus.  +seed= +cycles=
module tb_timing_ls;
  parameter integer PROFILE_P=0, CTX=1, SR=1;
  reg clk=0, rst_n=0; always #416 clk=~clk;
  reg desc_v=0; reg [18:0] desc_row=0; reg [10:0] desc_n=1; reg go=0; reg rrd=0,rs=0,rw=0,boot=0;
  reg [9:0] desc_first=0; reg dc=0,dv=0,dk=0; reg [7:0] k0=0;
  reg wr_v=0; reg [4:0] wr_bank=0, wr_col=0; reg s_v=0,s_we=0; reg [4:0] s_bank=0,s_col=0; reg [18:0] s_row=0; reg [346:0] s_ctx=0;
  `define PORTS(p) .clk(clk),.rst_n(rst_n),.desc_v(desc_v),.desc_r(p``desc_r),.desc_row(desc_row),.desc_n(desc_n),.go(go),.next_posted(1'b0),\
   .row_v(p``row_v),.row_prio(p``row_prio),.row_gnt(1'b1),.row_op(p``row_op),.row_bank(p``row_bank),.row_row(p``row_row),.col_v(p``col_v),.col_bank(p``col_bank),.col_col(p``col_col),\
   .reserved_rd(rrd),.reserved_static_col(rs),.reserved_write_col(rw),.boot_static_col(boot),.desc_first(desc_first),.desc_context(dc),.desc_vpass(dv),.desc_k_order_b(dk),.desc_k_count0(k0),\
   .schedule_fault(p``sf),.phase_idle(p``idle),.busy(p``busy),.ref_fault(p``rf),.wr_v(wr_v),.wr_bank(wr_bank),.wr_col(wr_col),.wr_r(p``wr_r),.col_we(p``col_we),.wr_rd(1'b0),.col_aq(p``col_aq),\
   .s_context(s_ctx),.col_context(p``ctx),.s_v(s_v),.s_we(s_we),.s_bank(s_bank),.s_col(s_col),.s_row(s_row),.s_r(p``s_r),.col_sr(p``col_sr),.s_pop(p``s_pop)
  `define WIRES(p) wire p``desc_r,p``row_v,p``row_prio,p``col_v,p``sf,p``idle,p``busy,p``rf,p``wr_r,p``col_we,p``col_aq,p``s_r,p``col_sr,p``s_pop; wire [2:0] p``row_op; wire [4:0] p``row_bank,p``col_bank,p``col_col; wire [18:0] p``row_row; wire [346:0] p``ctx;
  `WIRES(o_) `WIRES(n_)
  localparam P = "CORE_CLOCK(1),.SROW(1)";
  ot_qkd_static_kv_timing_old #(.CORE_CLOCK(1),.STATIC_REFRESH(SR),.CONTEXT_DESC(CTX),.PROFILE(PROFILE_P),.SROW(1),.SQD(4),.S_STARVE(8),.READY_CUT(1),.ENABLE(1),.REF_MODE(1),.PC(0),.WR_EN(1),.WQ(4),.AQ_RD(0)) old(`PORTS(o_));
  ot_qkd_static_kv_timing     #(.CORE_CLOCK(1),.STATIC_REFRESH(SR),.CONTEXT_DESC(CTX),.PROFILE(PROFILE_P),.SROW(1),.SQD(4),.S_STARVE(8),.READY_CUT(1),.ENABLE(1),.REF_MODE(1),.PC(0),.WR_EN(1),.WQ(4),.AQ_RD(0)) dut(`PORTS(n_));
  wire [640:0] ov={o_desc_r,o_row_v,o_row_prio,o_col_v,o_sf,o_idle,o_busy,o_rf,o_wr_r,o_col_we,o_col_aq,o_s_r,o_col_sr,o_s_pop,o_row_op,o_row_bank,o_col_bank,o_col_col,o_row_row};
  wire [640:0] nv={n_desc_r,n_row_v,n_row_prio,n_col_v,n_sf,n_idle,n_busy,n_rf,n_wr_r,n_col_we,n_col_aq,n_s_r,n_col_sr,n_s_pop,n_row_op,n_row_bank,n_col_bank,n_col_col,n_row_row};
  integer seed=1, cycles=400000, cyc=0, sincerst=0, prd=30, prs=20, prw=10, pwr=5, psv=20, pgo=20, bset=4;
  longint c_rd=0,c_wr=0,c_s=0,c_sp=0,c_pblk_rd=0,c_pblk_wr=0,c_fp=0,c_ref=0,c_act=0,c_pre=0;
  reg faulted=0; integer fcyc=0; reg [346:0] o_ctx_q=0; reg sqne_q=0; longint c_fault=0,c_ill=0;
  wire ill=PROFILE_P==0 && ((rrd&&!old.on.legal_rd)||(rs&&!old.on.legal_static)||(rw&&!old.on.legal_write)||(int'(rrd)+int'(rs)+int'(rw)>1));
  function automatic int r(int m); return $urandom_range(m-1,0); endfunction
  initial begin
    if(!$value$plusargs("seed=%d",seed)) seed=1; if(!$value$plusargs("cycles=%d",cycles)) cycles=400000;
    void'($urandom(seed));
    forever begin
      @(negedge clk);
      cyc++; sincerst++;
      if(sincerst%3000==1) begin prd=r(100); prs=r(40); prw=r(40); pwr=r(30); psv=r(60); pgo=r(100); bset=1+r(32);
        if(r(2)==0) begin prd=90; prs=r(3); prw=r(3); pwr=r(3); psv=40; pgo=90; bset=4; end end
      if(sincerst>20000 || (n_rf && sincerst>4000) || (faulted && sincerst>fcyc+30)) begin rst_n=0; sincerst=0; faulted=0; end
      else if(sincerst>4) rst_n=1;
      boot=r(100)<3; go=r(100)<pgo; rrd=0; rs=0; rw=0;
      // PROFILE 0: slots follow the OLD core's own permission, as a compiled calendar does; a rare injected slot must fault the same
      if(PROFILE_P==0) begin
        #1 rs=r(100)<prs && old.on.legal_static;
        #1 rrd=r(100)<prd && old.on.legal_rd; rw=!rrd && r(100)<prw && old.on.legal_write;
        if(r(3000)==0 && !faulted) case(r(3)) 0:rrd=1; 1:rs=1; 2:rw=1; endcase
      end else begin rrd=r(100)<prd; rs=r(100)<prs; rw=r(100)<prw; end
      if(!desc_v || n_desc_r) begin
        desc_v=r(100)<40; dc=CTX!=0 && r(2)==1; dv=r(2)==1; dk=r(2)==1; k0=r(64);
        desc_row=64+r(4); desc_n=dc?(1+r(128)):(1+r(512)); desc_first=dc?r(64):r(int'(desc_n));
      end
      wr_v=r(100)<pwr; wr_bank=r(bset); wr_col=r(32);
      s_v=r(100)<psv; s_we=r(4)==0; s_bank=r(bset); s_col=r(32); s_row=64+r(3); for(int i=0;i<11;i++) s_ctx[i*32+:32]=$urandom;
    end
  end
  always @(posedge clk) begin o_ctx_q<=o_ctx; sqne_q<=rst_n && old.on.sq_n!=0; end
  always @(posedge clk) if(rst_n && !faulted && ill) begin
    faulted<=1; fcyc<=sincerst; c_ill++;
    if({o_col_v,o_col_we,o_col_sr,o_s_pop}!=={n_col_v,n_col_we,n_col_sr,n_s_pop}) begin $display("FAIL cycle %0d slot-fault pins old %b new %b",cyc,{o_col_v,o_col_we,o_col_sr,o_s_pop},{n_col_v,n_col_we,n_col_sr,n_s_pop}); $finish; end
  end else if(rst_n && faulted) begin
    if(o_sf!==n_sf) begin $display("FAIL cycle %0d sticky fault old %b new %b",cyc,o_sf,n_sf); $finish; end
    if(o_sf!==1'b1 && sincerst>fcyc+1) begin $display("FAIL cycle %0d injected slot did not fault",cyc); $finish; end
  end else if(rst_n) begin
    if(old.on.s_pblk!==((dut.on.rp_sp?dut.on.sb_oh:32'b0)|(dut.on.cp_sp?dut.on.c_oh:32'b0)) || old.on.c_sp!==dut.on.c_sp ||
       old.on.sprio!==dut.on.sprio || old.on.ref_due_n!==dut.on.ref_due_n || old.on.ras_z!==dut.on.ras_z || old.on.rtp_z!==dut.on.rtp_z ||
       old.on.wcand_q!==dut.on.wcand_q || (old.on.wcand_q && (old.on.wab!==dut.on.wab || old.on.wab_oh!==dut.on.wab_oh)) ||
       old.on.legal_rd!==dut.on.legal_rd || old.on.legal_static!==dut.on.legal_static) begin
      $display("FAIL cycle %0d internal: s_pblk/c_sp/sprio/ref_due_n/ras_z/rtp_z/legal",cyc); $finish; end
    if(ov!==nv || (sqne_q && o_ctx_q!==n_ctx)) begin
      $display("FAIL cycle %0d since_rst %0d old %h new %h ctx_diff %0d",cyc,sincerst,ov,nv,o_ctx_q!==n_ctx); $finish; end
    c_rd+=dut.on.rd_ok; c_wr+=dut.on.wr_ok; c_s+=dut.on.s_go; c_sp+=dut.on.rp_sp; c_fp+=dut.on.forced_pre;
    c_pblk_rd+=dut.on.rd_ok0 && !dut.on.s_go && ((dut.on.rp_sp && |(dut.on.rd_oh & dut.on.sb_oh)) || (dut.on.cp_sp && |(dut.on.rd_oh & dut.on.c_oh)));
    c_pblk_wr+=dut.on.wr_ok0 && !dut.on.s_go && ((dut.on.rp_sp && |(dut.on.hb_oh & dut.on.sb_oh)) || (dut.on.cp_sp && |(dut.on.hb_oh & dut.on.c_oh)));
    c_ref+=n_row_v && n_row_op==6; c_act+=n_row_v && n_row_op==1; c_pre+=n_row_v && n_row_op==0;
    if(cyc>=cycles) begin
      $display("PASS injected %0d cycles %0d rd %0d wr %0d s_go %0d rp_sp %0d forced_pre %0d pblk_rd %0d pblk_wr %0d ref %0d act %0d pre %0d",c_ill,cyc,c_rd,c_wr,c_s,c_sp,c_fp,c_pblk_rd,c_pblk_wr,c_ref,c_act,c_pre);
      $finish; end
  end
endmodule
