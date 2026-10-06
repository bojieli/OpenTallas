`timescale 1ns/1ps
// Source-owned C17 correction candidate. The complete transaction is retimed
// with its protection snapshot. ENABLE stays OFF until real producer commit
// and drain integration, exactness, and loaded SS60/FF25 qualification pass.
// packet = {leaf valid/key/row, result data/mask/address/we, tag, valid,
//           warm-index marker}; see dsrom_fh_fault_retire_model().
module ot_hdc_v41_fh_fault_retire #(
    parameter integer ENABLE=0, PACKET_BITS=5510,
    // MARGIN (default 0; margin-first 1): one more fault level - two kept global copies of the
    // quadrant OR, one per die half, between the quadrants and the relays - so every hop of the
    // fault tree is half the head or less; the packet pipe is five deep (+1 retirement cycle).
    // group_fault[g] (per-group lane faults, MARGIN only) joins the rows of group g at the
    // arithmetic-fault cycle.
    parameter integer MARGIN=0
)(
    input wire clk,rst_n,
    input wire packet_v,
    input wire [PACKET_BITS-1:0] packet,
    input wire [63:0] poison,
    input wire [3:0] address_fault,
    input wire arithmetic_fault,
    input wire [3:0] group_fault,
    output wire retired_v,
    output wire [PACKET_BITS-1:0] retired_packet,
    output wire [63:0] lane_veto,
    output wire [3:0] write_veto,
    output wire fault,
    output wire busy
);
    genvar p,l,g;
    generate if(!ENABLE) begin : g_original
        wire f=(|poison)||(|address_fault)||arithmetic_fault;
        assign retired_v=packet_v;
        assign retired_packet=packet;
        assign lane_veto={64{f}};
        assign write_veto={4{f}};
        assign fault=f;
        assign busy=1'b0;
    end else begin : g_cut
        localparam integer DEPTH=MARGIN?5:4;
        reg [PACKET_BITS-1:0] packet_pipe[0:DEPTH-1];
        reg [DEPTH-1:0] valid_pipe;
        reg [7:0] row_fault;
        reg [3:0] quadrant_fault;
        wire [15:0] relay_fault;
        integer st,r;
        always @(posedge clk) begin
            packet_pipe[0]<=packet;
            for(st=1;st<DEPTH;st=st+1) packet_pipe[st]<=packet_pipe[st-1];
        end
        always @(posedge clk or negedge rst_n)
            if(!rst_n) begin valid_pipe<=0;row_fault<=0;quadrant_fault<=0;end
            else begin
                valid_pipe<={valid_pipe[DEPTH-2:0],packet_v};
                // Each eight-bank capture is a 2-row x4-column cluster,
                // not a full-width row. Both halves share the same original
                // W16 address-fault source. No bank or protection bit drops.
                for(r=0;r<8;r=r+1)
                    row_fault[r]<=(|poison[(r/2)*16+(r%2)*4+:4])||
                        (|poison[(r/2)*16+8+(r%2)*4+:4])||address_fault[r/2]||arithmetic_fault||
                        (MARGIN!=0&&group_fault[r/2]);
                for(r=0;r<4;r=r+1)
                    quadrant_fault[r]<=row_fault[(r/2)*4+r%2]||row_fault[(r/2)*4+r%2+2];
            end
        // Put the OR inside each kept module. Identical relays must survive
        // synthesis/ABC; a single merged OR/register restores the long veto.
        wire [1:0] global_fault;
        for(p=0;p<2;p=p+1) begin : g_global
            if(MARGIN) begin : g_k
                ot_hdc_v41_fh_fault_relay u_global
                    (.clk(clk),.rst_n(rst_n),.d(quadrant_fault),.q(global_fault[p]));
            end else begin : g_n
                assign global_fault[p]=1'b0;
            end
        end
        for(p=0;p<16;p=p+1) begin : g_relay
            ot_hdc_v41_fh_fault_relay u_relay
                (.clk(clk),.rst_n(rst_n),.d(MARGIN?{4{global_fault[p/8]}}:quadrant_fault),.q(relay_fault[p]));
        end
        for(l=0;l<64;l=l+1) begin : g_lane
            ot_hdc_v41_fh_fault_copy u_copy
                (.clk(clk),.rst_n(rst_n),.d(relay_fault[l/4]),.q(lane_veto[l]));
        end
        for(g=0;g<4;g=g+1) begin : g_write
            ot_hdc_v41_fh_fault_copy u_copy
                (.clk(clk),.rst_n(rst_n),.d(relay_fault[4*g]),.q(write_veto[g]));
        end
        ot_hdc_v41_fh_fault_copy u_status
            (.clk(clk),.rst_n(rst_n),.d(relay_fault[0]),.q(fault));
        assign retired_v=valid_pipe[DEPTH-1];
        assign retired_packet=packet_pipe[DEPTH-1];
        assign busy=|valid_pipe;
    end endgenerate
endmodule

(* keep_hierarchy *)
module ot_hdc_v41_fh_fault_relay(input wire clk,rst_n,input wire [3:0] d,output reg q);
    always @(posedge clk or negedge rst_n)
        if(!rst_n) q<=0;else q<=|d;
endmodule

(* keep_hierarchy *)
module ot_hdc_v41_fh_fault_copy(input wire clk,rst_n,d,output reg q);
    always @(posedge clk or negedge rst_n)
        if(!rst_n) q<=0;else q<=d;
endmodule
