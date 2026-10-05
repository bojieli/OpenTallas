`timescale 1ns/1ps
// Additive simulation-only read-only source observations. No new protocol.
module dsrom_runtime_consumers #(
    parameter integer FAST = 0,
    parameter integer PP = 0,
    parameter integer BP = 0,
    parameter integer NP = 8,
    parameter integer R = 2,
    parameter integer NBF = 2,
    parameter integer PHW = 6,
    parameter integer SAW = 14,
    parameter integer VAW = 30,
    parameter integer VRD = 64,
    parameter integer KMAX = 6144,
    parameter integer BST = 17,
    parameter integer RST = 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    input  wire [PHW-1:0]    i_ph,
    input  wire [2:0]        i_np,
    input  wire [VAW-1:0]    i_xbase,
    input  wire [VAW-1:0]    i_xps,
    input  wire [VAW-1:0]    i_obase,
    input  wire [VAW-1:0]    i_ops,
    output wire              ready,
    output wire              idle,
    output wire [R-1:0]      o_we,
    output wire [R*VAW-1:0]  o_addr,
    output wire [R*32-1:0]   o_data,
    output wire              fault,
    output wire [31:0]       phase_cycles
`ifdef RT_CUT
    ,
    output wire              fb_cfg_go,
    output wire [PHW-1:0]    fb_cfg_ph,
    output wire [2:0]        fb_cfg_np,
    output wire              fb_go,
    output wire              fb_go_bf,
    output wire              fb_xs_v,
    output wire [7:0]        fb_xs_p,
    output wire [2:0]        fb_xs_b,
    output wire [1:0]        fb_xs_sv,
    output wire [255:0]      fb_xs_q0,
    output wire [9:0]        fb_xs_e0,
    output wire [255:0]      fb_xs_q1,
    output wire [9:0]        fb_xs_e1,
    output wire [2:0]        fb_xs_pos,
    output wire [2:0]        fb_xb_pos,
    output wire              fb_xb_v,
    output wire [2:0]        fb_xb_b,
    output wire [3:0]        fb_xb_sv,
    output wire [31:0]       fb_xb_u,
    output wire [1023:0]     fb_xb_d,
    input  wire [R-1:0]      fr_v,
    input  wire [16*R-1:0]   fr_row,
    input  wire [3*R-1:0]    fr_pos,
    input  wire [32*R-1:0]   fr_fp32,
    input  wire [16*R-1:0]   fr_bf16,
    input  wire [R-1:0]      fr_e,
    input  wire              fr_fault
`endif
,
    output wire obs_VM_re,
    output wire [VAW-1:0] obs_VM_addr,
    output wire obs_AQ_in,
    output wire [13:0] obs_AQ_k,
    output wire [1:0] obs_AQ_out,
    output wire [14:0] obs_have,
    output wire obs_sm_adv,
    output wire [15:0] obs_sm_i,
    output wire [47:0] obs_sm_word,
    output wire [14:0] obs_sm_have,
    output wire [14:0] obs_sm_need,
    output wire obs_sm_wait,
    output wire [18:0] obs_rows_left,
    output wire obs_ld_run,
    output wire obs_sm_run
,
input wire [VAW-1:0] obs_probe_addr,
output wire [31:0] obs_probe_data,
output wire obs_VI_re,
output wire [VAW-1:0] obs_VI_addr,
output wire [31:0] obs_VI_data,
output wire obs_spine_idle,
output wire obs_phase_accept,
output wire [PHW-1:0] obs_phase,
output wire [VAW-1:0] obs_key
);
localparam integer AW=30, NW=21, W=16, IL=8, VM_AW=19, ROM_R=R, X_ROM=1;
reg [31:0] vm[0:(1<<VM_AW)-1];
reg [8*1024-1:0] rom_dir;integer ii,q;
initial begin
 for(ii=0;ii<(1<<VM_AW);ii=ii+1)vm[ii]=0;
 if($value$plusargs("OT_ROM_DIR=%s",rom_dir))$readmemh({rom_dir,"/vm.hex"},vm);
end
wire s_go,s_ready,s_idle,a_fault,sp_fault;
wire [PHW-1:0] s_ph;wire [2:0] s_np;
wire [VAW-1:0] s_xbase,s_xps,s_obase,s_ops;wire [1:0] s_fmt;
wire rom_xre,rom_vre;wire [AW-1:0] rom_xaddr,rom_vaddr;
reg [64*32-1:0] rom_xq;reg [31:0] rom_vq;
wire [ROM_R-1:0] rom_we;wire [ROM_R*AW-1:0] rom_waddr;wire [ROM_R*32-1:0] rom_wdata;
ot_v41_rom_adapt #(.AW(AW),.NW(NW),.W(W),.IL(IL),.PHW(PHW),.VAW(VAW)) u_radapt(
 .clk(clk),.rst_n(rst_n),.q_go(go),.q_xbase(i_xbase),.q_nb(8'd160),.q_wbase(30'd2097152),
 .q_ind(1'b1),.q_ibase(30'd366688),.q_istride(30'd4096),.q_obase(i_obase),.q_unrounded(1'b0),
 .m_go(1'b0),.m_k('0),.m_split('0),.m_wbase('0),.m_xbase('0),.m_xks('0),.m_xcs('0),.m_xjs('0),.m_obase('0),.m_ots('0),.m_ojs('0),.m_round(1'b0),.m_amax(1'b0),.m_mmode(1'b0),
 .i_m(3'd1),.i_xps(i_xps),.i_ops(i_ops),.ready(ready),.idle(idle),.vi_re(rom_vre),.vi_addr(rom_vaddr),.vi_q(rom_vq),
 .s_go(s_go),.s_ph(s_ph),.s_np(s_np),.s_xbase(s_xbase),.s_xps(s_xps),.s_obase(s_obase),.s_ops(s_ops),.s_fmt(s_fmt),.s_ready(s_ready),.s_idle(s_idle),.fault(a_fault));
ot_v41_spine_w17w10 #(.PHW(PHW),.SAW(16),.R(R),.VAW(AW),.VRD(64),.KMAX(6144),.BST(BST)) u_spine(
 .clk(clk),.rst_n(rst_n),.go(s_go),.i_ph(s_ph),.i_np(s_np),.i_xbase(s_xbase),.i_xps(s_xps),.i_obase(s_obase),.i_ops(s_ops),.i_fmt(s_fmt),.ready(s_ready),.idle(s_idle),
 .x_re(rom_xre),.x_addr(rom_xaddr),.x_q(rom_xq),.w_we(rom_we),.w_addr(rom_waddr),.w_data(rom_wdata),
 .f_cfg_go(fb_cfg_go),.f_cfg_ph(fb_cfg_ph),.f_cfg_np(fb_cfg_np),.f_go(fb_go),.f_go_bf(fb_go_bf),
 .f_xs_v(fb_xs_v),.f_xs_p(fb_xs_p),.f_xs_b(fb_xs_b),.f_xs_sv(fb_xs_sv),.f_xs_q0(fb_xs_q0),.f_xs_e0(fb_xs_e0),.f_xs_q1(fb_xs_q1),.f_xs_e1(fb_xs_e1),.f_xs_pos(fb_xs_pos),
 .f_xb_pos(fb_xb_pos),.f_xb_v(fb_xb_v),.f_xb_b(fb_xb_b),.f_xb_sv(fb_xb_sv),.f_xb_u(fb_xb_u),.f_xb_d(fb_xb_d),.f_bus(),
 .r_v(fr_v),.r_row(fr_row),.r_pos(fr_pos),.r_fp32(fr_fp32),.r_bf16(fr_bf16),.r_e(fr_e),.f_fault(fr_fault),.fault(sp_fault),.phase_cycles(phase_cycles));
always @(posedge clk) begin
        if (X_ROM != 0) begin
            if (rom_xre) for (q = 0; q < 64; q = q + 1) rom_xq[32*q +: 32] <= vm[rom_xaddr[VM_AW-1:0] + VM_AW'(q)];
            if (rom_vre) rom_vq <= vm[rom_vaddr[VM_AW-1:0]];
            for (q = 0; q < ROM_R; q = q + 1) if (rom_we[q]) vm[rom_waddr[q*AW +: VM_AW]] <= rom_wdata[32*q +: 32];
        end

end
assign o_we=rom_we;assign o_addr=rom_waddr;assign o_data=rom_wdata;assign fault=a_fault|sp_fault;
assign obs_VM_re=rom_xre;assign obs_VM_addr=rom_xaddr;
assign obs_AQ_in=u_spine.rq_v;assign obs_AQ_k=u_spine.rq_k;assign obs_AQ_out=u_spine.aq_vo;
assign obs_have=u_spine.have[0];assign obs_sm_adv=u_spine.s_adv;assign obs_sm_i=u_spine.sm_i;assign obs_sm_word=u_spine.sw;
assign obs_sm_have=u_spine.have[0];assign obs_sm_need=u_spine.need_q;assign obs_sm_wait=u_spine.sm_run&&u_spine.sw_v&&!u_spine.s_ok;
assign obs_rows_left=u_spine.rows_left;assign obs_ld_run=u_spine.ld_run;assign obs_sm_run=u_spine.sm_run;
assign obs_probe_data=vm[obs_probe_addr[VM_AW-1:0]];
assign obs_VI_re=rom_vre;assign obs_VI_addr=rom_vaddr;assign obs_VI_data=rom_vq;
assign obs_spine_idle=s_idle;assign obs_phase_accept=s_go&&s_ready;assign obs_phase=s_ph;assign obs_key=u_radapt.key;
endmodule
