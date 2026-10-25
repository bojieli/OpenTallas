`timescale 1ns/1ps
// Existing service entry ABI plus static all-quarter SO source assembly.
module dsdv_svc_rs_pvso_entry #(parameter integer PVSO_ENABLE=0, parameter integer MUT = 0, parameter integer DIE_ID = 0, parameter integer ST = 0,
                           parameter bit SRAM_MACRO = 0, parameter integer PV_IDENTITY = 0, parameter bit SMT = 1,
                           parameter logic [39:0] FM = {40{1'b1}}) (   // S81-P9-FACE face mask -> dsdv_svc_rs_c
    input  wire ck, rst, input wire [3:0] sid,
    input  wire [32:0] j, output wire [1:0] jd, input wire [512:0] q,   // the die's 513-b q lane {d 512, v} input wire [291:0] hw, output wire [8:0] hc,
    output wire fault, output wire [1:0] st_rg,
    input  wire [4*805-1:0] dn_i, output wire [4*805-1:0] dn_o, input wire [4*16-1:0] up_i, output wire [4*16-1:0] up_o,
    input  wire [4*514-1:0] ri, output wire [4*514-1:0] ro,
    input  wire [3:0] gi_v, input wire [4*2132-1:0] gi_d, output wire [3:0] go_v, output wire [4*2132-1:0] go_d,
    input  wire [3:0] si_v, input wire [4*1076-1:0] si_d, output wire [3:0] so_v, output wire [4*1076-1:0] so_d,
    output wire [2*341-1:0] rq, input wire [1:0] rk, wd, rv, input wire [2*256-1:0] r_data, input wire [2*17-1:0] r_tag,
    input  wire [2*4-1:0] r_beat, input wire [1:0] hs,
    output wire pv_v, output wire [512:0] pv_d, output wire [47:0] pv_x,
    input wire [561:0] local_pv_landed,peer_pv,
    output wire so_ready,so_done,output wire[11:0]so_fault_code

`ifdef RS_OBS
    , output wire w_v, output wire [13:0] w_a, output wire [15:0] w_m, output wire [511:0] w_d, output wire [11:0] w_st
    , output wire [2678:0] obs
`endif
);
    /*verilator hier_block*/
`ifndef RS_OBS
    wire w_v; wire [13:0] w_a; wire [15:0] w_m; wire [511:0] w_d; wire [11:0] w_st;
`endif
    wire so_cfg_v,so_param_v,so_launch,program_fault;
    wire[19:0]so_owner,so_param_owner;wire[20:0]so_position,so_param_position;
    wire[7:0]so_se_jid,so_jid;wire[15:0]so_local_first,so_peer_first;
    wire[2:0]so_param_row;wire[511:0]so_param_d;wire[514:0]q_filtered;
    dsdv_pv_so_program #(.ENABLE(PVSO_ENABLE),.TF(0)) u_program(.clk(ck),.rst_n(rst),.q({2'b00,q}),.q_pass(q_filtered),
      .cfg_v(so_cfg_v),.owner(so_owner),.position(so_position),.se_jid(so_se_jid),.so_jid(so_jid),
      .local_first(so_local_first),.peer_first(so_peer_first),.param_v(so_param_v),.param_row(so_param_row),
      .param_owner(so_param_owner),.param_position(so_param_position),.param_d(so_param_d),.launch(so_launch),.fault(program_fault));
    wire generated_v,ingress_fault,join_fault,entry_fault;
    wire[511:0]generated_d;wire[514:0]q_entry;
    wire joined_v;wire[1:0]joined_quarter;wire[512:0]joined_d;
    reg collision;
    always @(posedge ck or negedge rst)if(!rst)collision<=0;else if(generated_v && q_filtered[0])collision<=1;
    assign q_entry=generated_v?{2'd0,generated_d,1'b1}:q_filtered;
    assign fault=entry_fault|ingress_fault|join_fault|collision|program_fault;
    generate if(PVSO_ENABLE!=0)begin:g_join
      dsdv_pv_half_join u_join(.clk(ck),.rst_n(rst),.cfg_v(so_cfg_v),
       .local_first(so_local_first),.peer_first(so_peer_first),.local_pv(local_pv_landed),.peer_pv(peer_pv),
       .pv_v(joined_v),.pv_quarter(joined_quarter),.pv_d(joined_d),.fault(join_fault));
    end else begin:g_nojoin
      assign joined_v=0;assign joined_quarter=0;assign joined_d=0;assign join_fault=0;
    end endgenerate
    dsdv_pv_so_ingress #(.ENABLE(PVSO_ENABLE),.HEADER_DEN(1)) u_ingress(.clk(ck),.rst_n(rst),
      .cfg_v(so_cfg_v),.cfg_owner(so_owner),.cfg_position(so_position),.cfg_se_jid(so_se_jid),.cfg_so_jid(so_jid),
      .pv_v(joined_v),.pv_quarter(joined_quarter),.pv_d(joined_d),
      .param_v(so_param_v),.param_row(so_param_row),.param_owner(so_param_owner),.param_position(so_param_position),.param_d(so_param_d),
      .den_v(1'b0),.den_mask(16'd0),.den_owner(20'd0),.den_jid(8'd0),.launch(so_launch),
      .q_v(generated_v),.q_d(generated_d),.ready(so_ready),.done(so_done),.fault(ingress_fault),.fault_code(so_fault_code));
    dsdv_svc_rs_c #(.ENTRY(1), .MUT(MUT), .DIE_ID(DIE_ID), .ST(ST), .SRAM_MACRO(SRAM_MACRO), .SMT(SMT), .PV_IDENTITY(PVSO_ENABLE!=0?1:PV_IDENTITY), .FM(FM)) u (.ck(ck),
        .rst(rst), .sid(sid), .j(j), .jd(jd), .q(q_entry), .hw(hw), .hc(hc), .fault(entry_fault), .st_rg(st_rg), .dn_i(dn_i),
        .dn_o(dn_o), .up_i(up_i), .up_o(up_o), .ri(ri), .ro(ro), .gi_v(gi_v), .gi_d(gi_d), .go_v(go_v), .go_d(go_d),
        .si_v(si_v), .si_d(si_d), .so_v(so_v), .so_d(so_d), .rq(rq), .rk(rk), .wd(wd), .rv(rv), .r_data(r_data),
        .r_tag(r_tag), .r_beat(r_beat), .hs(hs), .pv_v(pv_v), .pv_d(pv_d), .pv_x(pv_x), .w_v(w_v), .w_a(w_a), .w_m(w_m),
        .w_d(w_d), .w_st(w_st)
`ifdef RS_OBS
        , .obs(obs)
`endif
        );
endmodule
