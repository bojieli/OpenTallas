`timescale 1ns/1ps
`default_nettype none
// Compiler-fixed 3-sector read per HC position,24 edges apart. Request pins
// are functions of captured control state; far-HC tap samples launch+1.
// Its registered return is launch+19; this reader captures and emits word0
// at launch+20, downstream engine samples launch+21. No queues/ready/stalls.
// RESP_PHASE (H-NETLIST 2026-10-15): edge of the fixed 24-edge period at which the
// return is captured; 19 = direct tap connection (default, unchanged). A parent that
// adds pin/leaf register edges on the request and return paths adds them here.
// HUB-SAFE2 2026-10-20 (kit hnx_hcq_hub_safe2_1020, SAFE-DESIGN item 3; zero added edges, outputs bit-identical):
//  * bank routing: the sector -> bank selects are KEPT one-hot registers loaded with the NEXT issue / return sector
//    (isel per (sector j, bank b); rsel per (j, b, 32-bit lane group g)), so local_rq / arrived are one AND-OR level of
//    <= 32-load copies (census safe1019: return_sector[2:0] drove 1,098..2,067 loads through the 8:1 sector muxes);
//  * the 23-row stream leaves a SHIFT register (landing >> 32 a row) instead of landing[next_row*32 +: 32]
//    (next_row[1:0] drove 389..772 loads); the response load of the landing uses KEPT copies resp_c of the response
//    slot, registered one edge ahead (phase RESP_PHASE-1: response_slot(t+1) == active && phase == RESP_PHASE-1 &&
//    returned < positions at t, since phase steps every active edge, returned / positions change only on a response
//    or an idle launch, and active falls only with returned == positions).
module ot_hnx_hgi_hc_gathered_mix_reader #(parameter integer RESP_PHASE=19)(
    input wire clk,rst_n,launch,
    input wire [3:0] npos,
    input wire [15:0] base_sector,position_stride_sector,
    output reg [135:0] local_rq,
    output reg [7:0] local_read,
    input wire [2055:0] local_rr,
    output reg gathered_mix_v,
    output reg [4:0] gathered_mix_row,
    output reg [2:0] gathered_mix_pos,
    output reg [31:0] gathered_mix_data,
    output reg done,fault
);
    reg active,streaming;
    initial if(RESP_PHASE<1||RESP_PHASE>23)$fatal(1,"RESP_PHASE must lie inside the 24-edge period");
    reg [15:0] issue_sector,return_sector,stride;
    reg [3:0] positions,issued,returned;
    reg [4:0] phase,next_row;
    reg [2:0] output_pos;
    wire request_slot=active&&phase==0&&issued<positions;
    wire response_slot=active&&phase==5'(RESP_PHASE)&&returned<positions;
    wire [32:0] last_sector={17'd0,base_sector}+(npos-1)*{17'd0,position_stride_sector}+2;
    wire bounds_ok=npos>=1&&npos<=8&&!base_sector[15]&&last_sector<32768&&last_sector[14:13]==base_sector[14:13];
    wire start=launch&&!active&&bounds_ok;
    // next issue / return sectors (exactly the register updates below)
    wire [15:0] is_n=start?base_sector:(request_slot?issue_sector+stride:issue_sector);
    wire [15:0] rs_n=start?base_sector:(response_slot?return_sector+stride:return_sector);
    wire resp_n=active&&phase==5'(RESP_PHASE-1)&&returned<positions;
    // ---- kept routing copies
    wire [3*8-1:0] isel;          // [j*8+b]
    wire [3*8*8-1:0] rsel;        // [(j*8+b)*8+g]
    for(genvar j=0;j<3;j=j+1)begin:g_j
        wire [15:0] qn=is_n+16'(j), rn=rs_n+16'(j);
        for(genvar b=0;b<8;b=b+1)begin:g_b
            (* keep = "true", dont_touch = "true" *) reg is_c;
            (* keep = "true", dont_touch = "true" *) reg [7:0] rs_c;
            always @(posedge clk)begin is_c<=qn[2:0]==3'(b);rs_c<={8{rn[2:0]==3'(b)}};end
            assign isel[j*8+b]=is_c;
            assign rsel[(j*8+b)*8+:8]=rs_c;
        end
    end
    (* keep = "true", dont_touch = "true" *) reg [23:0] resp_c;   // copies of response_slot, one per landing row group
    reg [7:0] expected_valid,actual_valid;
    reg [767:0] arrived;
    always @*begin
        local_rq=0;local_read=0;expected_valid=0;actual_valid=0;arrived=0;
        for(integer b=0;b<8;b=b+1)actual_valid[b]=local_rr[b*257+256];
        for(integer j=0;j<3;j=j+1)begin:sector
            reg [15:0] q;
            q=issue_sector+16'(j);
            for(integer b=0;b<8;b=b+1)begin
                local_rq[b*17+:17]=local_rq[b*17+:17]|({17{isel[j*8+b]}}&{request_slot,q});
                local_read[b]=local_read[b]|(isel[j*8+b]&request_slot);
                expected_valid[b]=expected_valid[b]|(rsel[(j*8+b)*8]&response_slot);
                for(integer g=0;g<8;g=g+1)
                    arrived[j*256+g*32+:32]=arrived[j*256+g*32+:32]|({32{rsel[(j*8+b)*8+g]}}&local_rr[b*257+g*32+:32]);
            end
        end
    end
    // ---- the 23 streamed rows: landing[r] = row r + 1 of the last response, shifted down one row an edge
    reg [23*32-1:0] landing;
    for(genvar r=0;r<23;r=r+1)begin:g_l
        wire [31:0] nxt=(r==22)?32'd0:landing[(r+1)*32+:32];
        always @(posedge clk)landing[r*32+:32]<=resp_c[r]?arrived[(r+1)*32+:32]:nxt;
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            active<=0;streaming<=0;phase<=0;issue_sector<=0;return_sector<=0;stride<=0;
            positions<=0;issued<=0;returned<=0;next_row<=0;output_pos<=0;resp_c<=0;
            gathered_mix_v<=0;gathered_mix_row<=0;gathered_mix_pos<=0;gathered_mix_data<=0;done<=0;fault<=0;
        end else begin
            gathered_mix_v<=0;done<=0;
            resp_c<={24{resp_n}};
            if(actual_valid!==expected_valid)fault<=1;
            if(active)begin
                phase<=phase==23?5'd0:phase+5'd1;
                if(request_slot)begin issue_sector<=issue_sector+stride;issued<=issued+1'b1;end
                if(response_slot)begin
                    returned<=returned+1'b1;return_sector<=return_sector+stride;
                    gathered_mix_v<=1;gathered_mix_row<=0;gathered_mix_pos<=returned[2:0];gathered_mix_data<=arrived[31:0];
                    streaming<=1;next_row<=1;output_pos<=returned[2:0];
                end else if(streaming)begin
                    gathered_mix_v<=1;gathered_mix_row<=next_row;gathered_mix_pos<=output_pos;
                    gathered_mix_data<=landing[31:0];
                    next_row<=next_row+1'b1;
                    if(next_row==23)begin
                        streaming<=0;
                        if(returned==positions)begin active<=0;done<=1;end
                    end
                end
            end
            if(launch)begin
                if(active||!bounds_ok)fault<=1;
                else begin
                    active<=1;streaming<=0;phase<=0;issue_sector<=base_sector;return_sector<=base_sector;
                    stride<=position_stride_sector;positions<=npos;issued<=0;returned<=0;next_row<=0;output_pos<=0;
                end
            end
        end
    end
endmodule
`default_nettype wire
