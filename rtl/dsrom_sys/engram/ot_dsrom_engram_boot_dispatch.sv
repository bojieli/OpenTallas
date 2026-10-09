`timescale 1ns/1ps
// Engram class-11 boot sectors only. RoPE class 10 must be dispatched to the
// existing boot_seq by the caller; this block rejects a swapped class.
// Eight upstream credits reserve eight tagged sector slots. Downstream must
// reserve eight write-queue entries per stack; completions acknowledge actual
// writes, never mere queue acceptance. Inputs/outputs have pin registers.
// Marker: addr ffffffff, data[65:64]=3, [63:32]=XOR fingerprint,
// [31:0]=expected sectors. Fingerprint XORs each little-endian data word and
// the region-local atom. ready stays low until all tagged writes complete.
module ot_dsrom_engram_boot_dispatch #(
    parameter integer ROWSTRIPE = 0,
    parameter integer EXPECT_SECTORS = 1
) (
    input wire ck, rst_n,
    input wire i_v,
    input wire [31:0] i_addr,
    input wire [255:0] i_d,
    output reg i_cred,
    output reg [1:0] w_v,
    output reg [28:0] w_atom,
    output reg [2:0] w_tag,
    output reg [255:0] w_d,
    input wire [1:0] done_v,
    input wire [5:0] done_tag,
    output wire ready,
    output reg fault
);
    reg iv_q;
    reg [31:0] ia_q;
    reg [255:0] id_q;
    reg [1:0] dv_q;
    reg [5:0] dt_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin iv_q<=0; dv_q<=0; end
        else begin iv_q<=i_v; dv_q<=done_v; end
    always @(posedge ck) begin ia_q<=i_addr; id_q<=i_d; dt_q<=done_tag; end

    reg [1:0] state [0:7]; // 0 free, 1 queued, 2 controller completion outstanding
    reg [29:0] addr [0:7];
    reg [255:0] data [0:7];
    reg [31:0] received, fingerprint, mark_count, mark_crc;
    reg marker, loaded;
    reg [4:0] pending_credits;
    integer j, k, free_slot, queued_slot, completed;
    reg empty;
    reg [31:0] sector_xor;
    always @(*) begin
        free_slot=-1; queued_slot=-1; empty=1;
        for (j=7;j>=0;j=j-1) begin
            if (state[j]==0) free_slot=j;
            else empty=0;
            if (state[j]==1) queued_slot=j;
        end
        sector_xor={2'b0,ia_q[29:0]};
        for (k=0;k<8;k=k+1) sector_xor=sector_xor^id_q[32*k+:32];
    end
    assign ready=loaded && !fault;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            for (j=0;j<8;j=j+1) state[j]<=0;
            received<=0; fingerprint<=0; marker<=0; loaded<=0; fault<=0;
            mark_count<=0; mark_crc<=0; pending_credits<=0; i_cred<=0; w_v<=0;
            w_atom<=0; w_tag<=0; w_d<=0;
        end else begin
            i_cred<=0; w_v<=0;
            completed=0;
            for (j=0;j<2;j=j+1) if (dv_q[j]) begin
                if (state[dt_q[3*j+:3]]!=2 || (ROWSTRIPE ? ((addr[dt_q[3*j+:3]]/9)%2) : addr[dt_q[3*j+:3]][0])!=j[0]) fault<=1;
                else begin
                    state[dt_q[3*j+:3]]<=0;
                    completed=completed+1;
                end
            end
            // Return one credit per cycle even when both controllers complete.
            if (pending_credits!=0) begin
                i_cred<=1;
                pending_credits<=pending_credits-5'd1+completed[4:0];
            end else pending_credits<=completed[4:0];
            if (!fault) begin
                if (queued_slot>=0) begin
                    state[queued_slot]<=2;
                    w_v<=(ROWSTRIPE ? ((addr[queued_slot]/9)%2) : addr[queued_slot][0]) ? 2'b10 : 2'b01;
                    w_atom<=ROWSTRIPE ? ((addr[queued_slot]/9)/2)*9+addr[queued_slot]%9 : addr[queued_slot][29:1]; w_tag<=queued_slot[2:0]; w_d<=data[queued_slot];
                end
                if (iv_q) begin
                    if (marker || loaded) fault<=1;
                    else if (ia_q==32'hffffffff) begin
                        if (id_q[65:64]!=2'b11 || id_q[255:66]!=0) fault<=1;
                        else begin
                            marker<=1; mark_count<=id_q[31:0]; mark_crc<=id_q[63:32];
                        end
                    end else if (ia_q[31:30]!=2'b11 || free_slot<0 ||
                                 ia_q[29:0]!=received[29:0] || received>=EXPECT_SECTORS) fault<=1;
                    else begin
                        state[free_slot]<=1; addr[free_slot]<=ia_q[29:0]; data[free_slot]<=id_q;
                        received<=received+1; fingerprint<=fingerprint^sector_xor;
                    end
                end
                if (marker && empty && !loaded) begin
                    if (received!=EXPECT_SECTORS || mark_count!=received || mark_crc!=fingerprint) fault<=1;
                    else begin
                        loaded<=1;
                        // Marker consumed one upstream credit too.
                        pending_credits<=pending_credits-((pending_credits!=0)?5'd1:5'd0)+completed[4:0]+5'd1;
                    end
                end
            end
        end
    end
endmodule
