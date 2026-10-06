`timescale 1ns/1ps
// One full32-PC protected boundary; each accepted sector has its own lane.
// Descartes owns ot_qwen_s4_parallel_protected_pc and its sector/control codec.
// No shared row arbiter, no raw bypass. A minimal gate does not prove routing.
module ot_qwen_p0_parallel_bank #(
    parameter integer ENABLE=0,PC_BASE=0,MEM_WORDS=36*131072,
    parameter integer LANDING_RSEL=0,LOCAL_WIRE_SPANS=0
)(
    input wire clk,hclk,por_n,warm_rst_n,
    output wire [31:0] l_v,w_room,wd_v,c_fault,h_fault,c_quiet,h_quiet,
    output wire [32*17-1:0] l_sec,
    output wire [32*8-1:0] l_row,
    output wire [32*256-1:0] l_data,
    input wire [31:0] l_pop,w_v,wd_accept,
    input wire [32*24-1:0] w_sec,
    input wire [32*256-1:0] w_data,
    input wire [32*9-1:0] w_tag,
    output wire [32*9-1:0] wd_tag,
    input wire [31:0] h_lv,h_av,h_hand,h_wcon,
    input wire [32*17-1:0] h_lsec,
    input wire [32*8-1:0] h_lrow,
    input wire [32*256-1:0] h_ldata,
    input wire [32*9-1:0] h_atag,
    output wire [32*3-1:0] h_cred,
    output wire [31:0] h_wv,h_cv,
    output wire [32*24-1:0] h_wsec,h_csec,
    output wire [32*256-1:0] h_cdata,
    output wire [32*9-1:0] h_ctag
);
    initial if(ENABLE && (LANDING_RSEL!=1 || PC_BASE%32!=0 || PC_BASE>96 || MEM_WORDS!=36*131072))
        $fatal(1,"parallel P0 requires selected corrected RSEL1/full36/stack-aligned identity");
    generate if(ENABLE)begin:active
        for(genvar pc=0;pc<32;pc=pc+1)begin:lane
            ot_qwen_s4_parallel_protected_pc #(.ENABLE(1),.PC_ID(PC_BASE+pc),
                .MEM_WORDS(MEM_WORDS),.LANDING_RSEL(LANDING_RSEL),
                .LOCAL_WIRE_SPANS(LOCAL_WIRE_SPANS)) u_pc(
                .clk(clk),.hclk(hclk),.por_n(por_n),.warm_rst_n(warm_rst_n),
                .l_v(l_v[pc]),
                .l_sec(l_sec[pc*17+:17]),
                .l_row(l_row[pc*8+:8]),
                .l_data(l_data[pc*256+:256]),
                .l_pop(l_pop[pc]),
                .w_v(w_v[pc]),
                .w_sec(w_sec[pc*24+:24]),
                .w_data(w_data[pc*256+:256]),
                .w_tag(w_tag[pc*9+:9]),
                .w_room(w_room[pc]),
                .wd_v(wd_v[pc]),
                .wd_tag(wd_tag[pc*9+:9]),
                .wd_accept(wd_accept[pc]),
                .c_fault(c_fault[pc]),
                .h_lv(h_lv[pc]),
                .h_lsec(h_lsec[pc*17+:17]),
                .h_lrow(h_lrow[pc*8+:8]),
                .h_ldata(h_ldata[pc*256+:256]),
                .h_cred(h_cred[pc*3+:3]),
                .h_wv(h_wv[pc]),
                .h_wsec(h_wsec[pc*24+:24]),
                .h_hand(h_hand[pc]),
                .h_wcon(h_wcon[pc]),
                .h_cv(h_cv[pc]),
                .h_csec(h_csec[pc*24+:24]),
                .h_cdata(h_cdata[pc*256+:256]),
                .h_ctag(h_ctag[pc*9+:9]),
                .h_av(h_av[pc]),
                .h_atag(h_atag[pc*9+:9]),
                .h_fault(h_fault[pc]),
                .c_quiet(c_quiet[pc]),
                .h_quiet(h_quiet[pc]));
        end
    end else begin:off
        assign {l_v,w_room,wd_v,c_fault,h_fault,l_sec,l_row,l_data,wd_tag,
                h_cred,h_wv,h_cv,h_wsec,h_csec,h_cdata,h_ctag}='0;
        assign c_quiet='1;assign h_quiet='1;
    end endgenerate
endmodule
