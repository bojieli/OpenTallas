`timescale 1ns/1ps
// Four-stack key-image write arbiter for the simulation HBM controllers.
// A bounded record FIFO accepts the writer's 128-dimensional key image. Each
// record becomes two full code-sector writes and one four-byte scale update
// on every stack. Later reads wait until all twelve writes have committed.
module ot_hdc_v41x_idx_pool_hbm_bridge #(
    parameter integer NPC=32, AW=28, TAGW=16, LENW=4, BEATW=4
) (
    input wire clk, rst_n,
    input wire w_v,
    output wire w_rdy,
    input wire [3:0] w_stack_mask,
    input wire [AW-1:0] w_csec,
    input wire [511:0] w_codes,
    input wire [AW-1:0] w_ssec,
    input wire [2:0] w_sslot,
    input wire [31:0] w_scales,
    input wire [4*NPC-1:0] r_v,
    output wire [4*NPC-1:0] r_rdy,
    input wire [4*NPC*AW-1:0] r_addr,
    input wire [4*NPC*LENW-1:0] r_len,
    input wire [4*NPC*TAGW-1:0] r_tag,
    output wire [4*NPC-1:0] h_v,
    input wire [4*NPC-1:0] h_rdy,
    output wire [4*NPC*AW-1:0] h_addr,
    output wire [4*NPC*LENW-1:0] h_len,
    output wire [4*NPC*TAGW-1:0] h_tag,
    output wire [4*NPC-1:0] h_we,
    output wire [4*NPC*256-1:0] h_wdata,
    output wire [4*NPC*32-1:0] h_wstrb,
    input wire [4*NPC-1:0] h_wr_done,
    output wire busy,
    output reg [31:0] dbg_records,
    output reg [31:0] dbg_writes,
    output reg [31:0] dbg_fifo_highwater,
    output reg [31:0] dbg_read_stalls,
    output reg [31:0] dbg_writer_stalls
);
    localparam integer LPC=$clog2(NPC);
    // Four records are enough to decouple the vector writer from HBM's
    // refresh and queue stalls. The writer holds valid when this FIFO fills.
    reg [606:0] fifo[0:3]; // {stack mask, code sector, codes, scale sector, slot, scales}
    reg [1:0] rp,wp,phase;
    reg [2:0] count;
    reg [3:0] issued,acked;
    wire active=count!=0;
    // The incoming write wins over a read presented on the same edge.
    wire hold_reads=active || w_v;
    assign busy=active;
    assign w_rdy=count<4;
    wire push=w_v && w_rdy;
    wire pop=active && phase==2 && ((acked | ~head_mask)==4'hf);
    wire [3:0] head_mask;
    wire [AW-1:0] head_csec,head_ssec;
    wire [511:0] head_codes;
    wire [2:0] head_slot;
    wire [31:0] head_scales;
    assign {head_mask,head_csec,head_codes,head_ssec,head_slot,head_scales}=fifo[rp];
    wire [AW-1:0] wa=phase==0 ? head_csec : phase==1 ? head_csec+1'b1 : head_ssec;
    wire [255:0] wd=phase==0 ? head_codes[255:0] :
                    phase==1 ? head_codes[511:256] : ({224'd0,head_scales} << (32*head_slot));
    wire [31:0] ws=phase==2 ? (32'hf << (4*head_slot)) : 32'hffff_ffff;
    function automatic [LPC-1:0] pc_of(input [AW-1:0] sec);
        pc_of=((sec>>2) ^ (sec>>(2+LPC)) ^ (sec>>(2+2*LPC))) & (NPC-1);
    endfunction
    wire [LPC-1:0] wpc=pc_of(wa);
    wire [3:0] accept,commit;
    genvar s,p;
    generate for(s=0;s<4;s=s+1) begin : g_stack
        assign accept[s]=active && head_mask[s] && !issued[s] && h_rdy[s*NPC+wpc];
        assign commit[s]=active && head_mask[s] && issued[s] && h_wr_done[s*NPC+wpc];
        for(p=0;p<NPC;p=p+1) begin : g_pc
            localparam integer I=s*NPC+p;
            wire sel=active && head_mask[s] && !issued[s] && wpc==p;
            assign r_rdy[I]=!hold_reads && h_rdy[I];
            assign h_v[I]=active ? sel : (w_v ? 1'b0 : r_v[I]);
            assign h_addr[I*AW +: AW]=active ? wa : r_addr[I*AW +: AW];
            assign h_len[I*LENW +: LENW]=active ? LENW'(1) : r_len[I*LENW +: LENW];
            assign h_tag[I*TAGW +: TAGW]=active ? '0 : r_tag[I*TAGW +: TAGW];
            assign h_we[I]=sel;
            assign h_wdata[I*256 +: 256]=wd;
            assign h_wstrb[I*32 +: 32]=ws;
        end
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            rp<=0;wp<=0;count<=0;phase<=0;issued<=0;acked<=0;
            dbg_records<=0;dbg_writes<=0;dbg_fifo_highwater<=0;
            dbg_read_stalls<=0;dbg_writer_stalls<=0;
        end else begin
            if(count>dbg_fifo_highwater) dbg_fifo_highwater<=count;
            if(|(r_v & {4*NPC{hold_reads}})) dbg_read_stalls<=dbg_read_stalls+1'b1;
            if(w_v && !w_rdy) dbg_writer_stalls<=dbg_writer_stalls+1'b1;
            if(push) begin
                fifo[wp]<={w_stack_mask,w_csec,w_codes,w_ssec,w_sslot,w_scales};
                wp<=wp+1'b1;
            end
            if(pop) rp<=rp+1'b1;
            case({push,pop})
                2'b10: count<=count+1'b1;
                2'b01: count<=count-1'b1;
                default: count<=count;
            endcase
            if(pop) dbg_records<=dbg_records+1'b1;
            dbg_writes<=dbg_writes+{31'd0,commit[0]}+{31'd0,commit[1]}+
                        {31'd0,commit[2]}+{31'd0,commit[3]};
            for(integer q=0;q<4;q=q+1) begin
                if(accept[q]) issued[q]<=1'b1;
                if(commit[q]) acked[q]<=1'b1;
            end
            if(active && ((acked | ~head_mask)==4'hf)) begin
                phase<=phase==2 ? 0 : phase+1'b1;
                issued<=0;acked<=0;
            end
        end
    end
endmodule
