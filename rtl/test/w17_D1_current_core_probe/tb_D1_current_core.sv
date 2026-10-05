`timescale 1ns/1ps
// SOURCE ONLY: controlled two-instruction diagnostic; no original token run.
module tb_D1_current_core(output wire [31:0] observed_cycle);
localparam ROM_PHW=6,ROM_R=128,ROM_FBW=1+ROM_PHW+3+1+1+1+8+3+2+256+10+256+10+3+3+1+3+4+32+1024,ROM_FRW=ROM_R*69;
localparam ATW=1+16+1+512*16+1+4+4*16*265+1+1+32*16+1,AFW=4+16+4+4*16*32+4*16+2+8+4*16*16*32+4*16*16;
localparam CL_LANES=16,CL_PW=32*CL_LANES+3+32;
wire  window_prime_ready;
wire  done;
wire [31:0] cycles;
wire [7:0] fault;
wire [4:0] unit_busy;
wire [2:0] issue_unit;
wire [13:0] dbg_pc;
wire [63:0] dbg_state;
wire [31:0] dbg_words;
wire [23:0] dbg_fs;
wire [ROM_FBW-1:0] rom_fb;
wire [ATW-1:0] att_to;
wire [AFW-1:0] att_from;
wire  ucie_ctx_valid;
wire [CL_PW-1:0] ucie_ctx_rec;
wire [1:0] ucie_ccr_out;
wire [1:0] bl_ctx_valid;
wire [CL_PW-1:0] bl_ctx_rec;
wire [3:0] bl_ccr_out;
reg clk=0;always #0.5 clk=~clk;reg rst_n=0,start=0,prime_v=0;integer diag_cycle=0;always @(posedge clk) if(rst_n)diag_cycle<=diag_cycle+1;reg[20:0]prime_row=0;wire d1_valid;wire[3:0]d1_predicates;wire[11:0]d1_context;
ot_v41_rt_die_D1_current #(.SIM_D1(1),.SUN(256),.SUM(64),.CL_DEPTH(512),.ROM_PHW(6)) probe(
.clk(clk),
.rst_n(rst_n),
.start(start),
.token(21'd0),
.pos(21'd127),
.user(10'd0),
.cfg_ik_base(30'd268435456),
.window_region_valid(1'b1),
.window_region_base(30'd262144),
.window_region_count(30'd2176),
.window_prime_v(prime_v),
.window_prime_ready(window_prime_ready),
.window_prime_user(10'd0),
.window_prime_row(prime_row),
.rope_table_present('0),
.rope_reserved_end('0),
.rope_plain_base('0),
.rope_yarn_base('0),
.done(done),
.cycles(cycles),
.fault(fault),
.unit_busy(unit_busy),
.issue_unit(issue_unit),
.dbg_pc(dbg_pc),
.dbg_state(dbg_state),
.dbg_words(dbg_words),
.dbg_fs(dbg_fs),
.rom_fb(rom_fb),
.rom_fr('0),
.rom_ffault('0),
.att_to(att_to),
.att_from(att_from),
.ucie_ctx_valid(ucie_ctx_valid),
.ucie_ctx_ready('0),
.ucie_ctx_rec(ucie_ctx_rec),
.ucie_ccr_in('0),
.ucie_crx_valid('0),
.ucie_crx_rec('0),
.ucie_ccr_out(ucie_ccr_out),
.bl_ctx_valid(bl_ctx_valid),
.bl_ctx_ready('0),
.bl_ctx_rec(bl_ctx_rec),
.bl_ccr_in('0),
.bl_crx_valid('0),
.bl_crx_rec('0),
.bl_ccr_out(bl_ccr_out));
wire job_v,q_v,kv_v,sc_cr,p_v,pv_cr;wire[15:0]job_t;wire[8191:0]q_w;wire[3:0]kv_m;wire[16959:0]kv_w;wire[511:0]p_w;
wire job_ready,q_ready,kv_ready,p_ready,sc_v,pv_v;wire[15:0]sc_row;wire[3:0]sc_m;wire[2047:0]sc_y;wire[63:0]sc_f;wire[7:0]pv_c;wire[32767:0]pv_y;wire[1023:0]pv_f;
assign {job_v,job_t,q_v,q_w,kv_v,kv_m,kv_w,sc_cr,p_v,p_w,pv_cr}=att_to;
assign att_from={job_ready,q_ready,kv_ready,p_ready,sc_row,sc_m,sc_y,sc_f,sc_v,pv_v,pv_c,pv_y,pv_f};
ot_hdc_v41x_attn #(.H(16),.D(512),.TD(32),.NL(4),.TROWS(640),.PWORDS(1),.PHYS(0)) endpoint(
.clk(clk),.rst_n(rst_n),.job_v(job_v),.job_t(job_t),.job_ready(job_ready),.q_v(q_v),.q_w(q_w),.q_ready(q_ready),
.kv_v(kv_v),.kv_m(kv_m),.kv_w(kv_w),.kv_ready(kv_ready),.sc_cr(sc_cr),.sc_v(sc_v),.sc_row(sc_row),.sc_m(sc_m),.sc_y(sc_y),.sc_f(sc_f),
.p_v(p_v),.p_w(p_w),.p_ready(p_ready),.pv_v(pv_v),.pv_c(pv_c),.pv_y(pv_y),.pv_f(pv_f),.pv_cr(pv_cr),.qk_iss(),.pv_iss());
// Same reset epoch. Priming marks retained zero synthetic rows; no payload/golden injection.
initial begin
  repeat(4) @(negedge clk);rst_n=1;
  for(integer row=0;row<128;row++) begin
    @(negedge clk);prime_v=1;prime_row=row;
    do @(posedge clk);while(!window_prime_ready);
  end
  @(negedge clk);prime_v=0;
  // Source model target only. Actual descriptor acceptance must be observed, never forced.
  // Start immediately after real same-reset priming; no cycle-12300 wait.
  start=1;@(negedge clk);start=0;
end
assign observed_cycle=32'(diag_cycle);
always @(negedge clk) if(diag_cycle>=512) begin
  $display("D1_PREFIX_CYCLE_CAP_NO_COMPLETION_CREDIT cycles=%0d",diag_cycle);$finish;
end
endmodule
