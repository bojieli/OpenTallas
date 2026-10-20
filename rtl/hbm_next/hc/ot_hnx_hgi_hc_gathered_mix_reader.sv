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
// HUB-SAFE3 2026-10-20 (kit hnx_hcq_hub_safe3_1020, census safe2; zero added edges, mixes bit-identical):
//  * the launch is accepted through 4 KEPT copies of the calendar's gather_launch (launch_c) and of active (act_c), one
//    per register group (start: 121 loads); the bound check multiplies by the 3-bit (npos - 1) only (npos is 1..8
//    whenever bounds_ok can be true, so bounds_ok is unchanged);
//  * the response slot reaches its consumers only through kept copies registered one edge ahead (resp_n, split over 2
//    kept phase copies): 48 landing copies (16-b groups), 4 control copies; streaming has 2 kept data-half copies;
//  * the issue sectors of the 3 sectors are registered (q_j = next issue sector + j); request addresses are no longer
//    zeroed while the request valid is 0 (don't-care), the valid bits are; rsel has a 9th copy for expected_valid.
module ot_hnx_hgi_hc_gathered_mix_reader #(parameter integer RESP_PHASE=19)(
    input wire clk,rst_n,launch,
    input wire [5:0] launch_c,        // KEPT copies of launch (same edge)
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
    (* keep = "true", dont_touch = "true" *) reg [5:0] act_c;        // = active
    (* keep = "true", dont_touch = "true" *) reg [3:0] str_c;        // = streaming (one per data byte)
    (* keep = "true", dont_touch = "true" *) reg [9:0] ph_c;         // 2 x phase
    (* keep = "true", dont_touch = "true" *) reg [3:0] rsp_o;        // = response_slot: data lo, data hi, row/pos/stream, return
    (* keep = "true", dont_touch = "true" *) reg [47:0] resp_c;      // = response_slot, one per 16-b landing group
    wire request_slot=active&&phase==0&&issued<positions;
    wire [3:0] nm1=npos-4'd1;
    wire [18:0] span=({19{nm1[0]}}&{3'd0,position_stride_sector})|({19{nm1[1]}}&{2'd0,position_stride_sector,1'b0})|
                     ({19{nm1[2]}}&{1'd0,position_stride_sector,2'b0});
    wire [32:0] last_sector={17'd0,base_sector}+{14'd0,span}+33'd2;
    wire bounds_ok=npos>=1&&npos<=8&&!base_sector[15]&&last_sector<32768&&last_sector[14:13]==base_sector[14:13];
    wire [5:0] st;                    // launch accepted, per register group ([4]: issue bank decode, [5]: q_r)
    for(genvar k=0;k<6;k=k+1)begin:g_st assign st[k]=launch_c[k]&&!act_c[k]&&bounds_ok; end
    // next issue / return sectors (exactly the register updates below)
    wire [15:0] is_n=st[0]?base_sector:(request_slot?issue_sector+stride:issue_sector);
    wire [15:0] q_n=st[5]?base_sector:(request_slot?issue_sector+stride:issue_sector);                       // = is_n
    wire [2:0] is3_n=st[4]?base_sector[2:0]:(request_slot?issue_sector[2:0]+stride[2:0]:issue_sector[2:0]);   // = is_n[2:0]
    wire [15:0] rs_n=st[1]?base_sector:(rsp_o[3]?return_sector+stride:return_sector);
    wire [1:0] resp_n;
    for(genvar k=0;k<2;k=k+1)begin:g_rn assign resp_n[k]=act_c[2+k]&&ph_c[k*5+:5]==5'(RESP_PHASE-1)&&returned<positions; end
    // ---- kept routing copies
    wire [3*8-1:0] isel;          // [j*8+b]
    wire [3*8*9-1:0] rsel;        // [(j*8+b)*9+g], g 8 = expected_valid
    reg [15:0] q_r [0:2];
    for(genvar j=0;j<3;j=j+1)begin:g_j
        wire [2:0] qn=is3_n+3'(j), rn=rs_n[2:0]+3'(j);
        always @(posedge clk)q_r[j]<=q_n+16'(j);
        for(genvar b=0;b<8;b=b+1)begin:g_b
            (* keep = "true", dont_touch = "true" *) reg is_c;
            (* keep = "true", dont_touch = "true" *) reg [8:0] rs_c;
            always @(posedge clk)begin is_c<=qn==3'(b);rs_c<={9{rn==3'(b)}};end
            assign isel[j*8+b]=is_c;
            assign rsel[(j*8+b)*9+:9]=rs_c;
        end
    end
    reg [7:0] expected_valid,actual_valid;
    reg [767:0] arrived;
    always @*begin
        local_rq=0;local_read=0;expected_valid=0;actual_valid=0;arrived=0;
        for(integer b=0;b<8;b=b+1)actual_valid[b]=local_rr[b*257+256];
        for(integer j=0;j<3;j=j+1)begin
            for(integer b=0;b<8;b=b+1)begin
                local_rq[b*17+:16]=local_rq[b*17+:16]|({16{isel[j*8+b]}}&q_r[j]);
                local_rq[b*17+16]=local_rq[b*17+16]|(isel[j*8+b]&request_slot);
                local_read[b]=local_read[b]|(isel[j*8+b]&request_slot);
                expected_valid[b]=expected_valid[b]|(rsel[(j*8+b)*9+8]&rsp_o[3]);
                for(integer g=0;g<8;g=g+1)
                    arrived[j*256+g*32+:32]=arrived[j*256+g*32+:32]|({32{rsel[(j*8+b)*9+g]}}&local_rr[b*257+g*32+:32]);
            end
        end
    end
    // ---- the 23 streamed rows: landing[r] = row r + 1 of the last response, shifted down one row an edge
    reg [23*32-1:0] landing;
    for(genvar r=0;r<23;r=r+1)begin:g_l
        wire [31:0] nxt=(r==22)?32'd0:landing[(r+1)*32+:32];
        always @(posedge clk)begin
            landing[r*32+:16]<=resp_c[2*r]?arrived[(r+1)*32+:16]:nxt[15:0];
            landing[r*32+16+:16]<=resp_c[2*r+1]?arrived[(r+1)*32+16+:16]:nxt[31:16];
        end
    end
    // ---- outputs: the data halves through their own copies
    always @(posedge clk or negedge rst_n)
        if(!rst_n)gathered_mix_data<=0;
        else begin
            // rsp_o implies active; streaming implies active (it is set only under active and falls with it)
            for(integer y=0;y<4;y=y+1)
                if(rsp_o[y/2])gathered_mix_data[y*8+:8]<=arrived[y*8+:8];
                else if(str_c[y])gathered_mix_data[y*8+:8]<=landing[y*8+:8];
        end
    always @(posedge clk)begin issue_sector<=is_n;return_sector<=rs_n; end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            active<=0;streaming<=0;phase<=0;stride<=0;act_c<=0;str_c<=0;ph_c<=0;rsp_o<=0;
            positions<=0;issued<=0;returned<=0;next_row<=0;output_pos<=0;resp_c<=0;
            gathered_mix_v<=0;gathered_mix_row<=0;gathered_mix_pos<=0;done<=0;fault<=0;
        end else begin
            gathered_mix_v<=0;done<=0;
            resp_c<={24{resp_n[1],resp_n[0]}};
            rsp_o<={resp_n[1],resp_n[1],resp_n[0],resp_n[0]};
            if(actual_valid!==expected_valid)fault<=1;
            if(active)begin
                phase<=phase==23?5'd0:phase+5'd1;
                ph_c<={2{phase==23?5'd0:phase+5'd1}};
                if(request_slot)issued<=issued+1'b1;
                if(rsp_o[3])returned<=returned+1'b1;
                if(rsp_o[2])begin
                    gathered_mix_v<=1;gathered_mix_row<=0;gathered_mix_pos<=returned[2:0];
                    streaming<=1;str_c<=4'hf;next_row<=1;output_pos<=returned[2:0];
                end else if(streaming)begin
                    gathered_mix_v<=1;gathered_mix_row<=next_row;gathered_mix_pos<=output_pos;
                    next_row<=next_row+1'b1;
                    if(next_row==23)begin
                        streaming<=0;str_c<=4'h0;
                        if(returned==positions)begin active<=0;act_c<=6'd0;done<=1;end
                    end
                end
            end
            if(launch&&(active||!bounds_ok))fault<=1;
            if(st[2])begin stride<=position_stride_sector;positions<=npos;issued<=0;end
            if(st[3])begin
                active<=1;act_c<=6'h3f;streaming<=0;str_c<=4'h0;phase<=0;ph_c<=0;
                returned<=0;next_row<=0;output_pos<=0;
            end
        end
    end
endmodule
`default_nettype wire
