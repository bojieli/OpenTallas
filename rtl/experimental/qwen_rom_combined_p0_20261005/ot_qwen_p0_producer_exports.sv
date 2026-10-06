`timescale 1ns/1ps
// Export only existing producer hierarchy/ports. No transport, controller,
// buffering or completion generator is added. SIMULATION backend only;
// actual successor binding and warm/held/ACK seam approval belong to Descartes.
module ot_qwen_p0_producer_exports #(
    parameter integer NSTK=4, NPC=128, LAYERS=1, PHASE=0,
    parameter integer PULLIN=0, PROTECTED=0, SYNC=2
)(
    input wire clk, hclk, rst_n, warm_rst_n,
    input wire d_v, go,
    output wire d_rdy,
    input wire [18:0] d_row,
    input wire [10:0] d_n,
    output wire [NPC-1:0] l_v, w_room, wd_v,
    output wire [NPC*17-1:0] l_sec,
    output wire [NPC*8-1:0] l_row,
    output wire [NPC*256-1:0] l_data,
    input wire [NPC-1:0] l_pop, w_v,
    input wire [NPC*24-1:0] w_sec,
    input wire [NPC*256-1:0] w_data,
    input wire [NPC*9-1:0] w_tag,
    output wire [NPC*9-1:0] wd_tag,
    output wire fault,
    output wire [15:0] fault_code,
    output wire join_desc_committed, join_go_committed,
    output wire [NPC-1:0] join_write_reserved
);
    initial if(PROTECTED!=1 || NSTK!=4 || NPC!=128 || LAYERS!=1 || PULLIN!=0 || SYNC!=2)
        $fatal(1,"producer exports require explicit protected full service shape");
    assign join_desc_committed=u_hbm.protected_dv && u_hbm.desc_r;
    assign join_go_committed=u_hbm.protected_go;
    for(genvar p=0;p<NPC;p=p+1)begin:write_owner
        // Definitive protected source reservation, not the leading room grant.
        assign join_write_reserved[p]=u_hbm.pc[p].protected_path.u_cdc.u_w.accept;
    end
    ot_qwen_hbm_stream4_cdc #(.NSTK(NSTK), .NPC(NPC), .MEM_WORDS(LAYERS * 131072), .TAGW(9), .PHASE(PHASE), .PULLIN(PULLIN),
        .PROTECTED(PROTECTED), .SYNC(SYNC)) u_hbm (
        .clk(clk), .rst_n(rst_n), .warm_rst_n(warm_rst_n), .hclk(hclk), .d_v(d_v), .d_rdy(d_rdy), .d_row(d_row), .d_n(d_n), .go(go),
        .l_v(l_v), .l_sec(l_sec), .l_row(l_row), .l_data(l_data), .l_pop(l_pop),
        .w_v(w_v), .w_sec(w_sec), .w_data(w_data), .w_tag(w_tag), .w_room(w_room), .wd_v(wd_v), .wd_tag(wd_tag),
        .fault(fault), .fault_code(fault_code));
endmodule
