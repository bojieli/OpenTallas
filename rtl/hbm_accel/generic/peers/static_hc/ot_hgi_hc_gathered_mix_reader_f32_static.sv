`timescale 1ns/1ps
`default_nettype none
// HBM-HCBANK6 10-20 (QHUB SAFE 2, native32 census): ot_hgi_hc_gathered_mix_reader_static #(RESP_PHASE, EXTB 1, RSC 24)
// rebuilt so that every mapped driver has <= 32 loads, with the SAME ports, edges and output values on every edge:
//   launch   GL kept launch copies (launch_c, from the programme calendar register, ot_hbm_hc_qcal_static FAN32 gl): one
//            accept select per loaded register group, so no single accept node fans out to the ~160 loaded bits;
//   response the response edge LD(t) = active && phase == RP && returned < positions is PREDICTED two edges early
//            (phase only counts while active; a launch restarts at phase 0 so RP >= 2 cannot be reached in two edges;
//            returned / positions do not change on phase RP-2 / RP-1 edges; the end-of-stream drop happens on a phase
//            RP-1 edge with returned == positions, where the prediction is already false): pred2 -> ld1 (2 kept) ->
//            ld2 (kept copies, one per <= 16 loaded bits);
//   request  request_slot(t) is predicted one edge early (rq copies): a launch, or phase 23 -> 0 with issued < positions;
//   landing  load-only rows 1..23 (row 0 leaves on the response edge itself); the streamed row is picked by a ONE-HOT row
//            register (2 kept copies per row, 16 AND loads each) instead of a 24:1 next_row mux; streaming has kept copies.
// MUT (bench): 1 = response prediction one edge late (ld from pred one edge after LD; must FAIL).
module ot_hgi_hc_gathered_mix_reader_f32_static #(parameter integer RESP_PHASE=23, parameter integer GL=16,
                                                   parameter integer MUT=0)(
    input wire clk,rst_n,launch,
    input wire [GL-1:0] launch_c,
    input wire [3:0] npos,
    input wire [15:0] base_sector,position_stride_sector,
    input wire bounds_i,
    output reg [135:0] local_rq,
    output reg [7:0] local_read,
    input wire [2055:0] local_rr,
    output reg gathered_mix_v,
    output reg [4:0] gathered_mix_row,
    output reg [2:0] gathered_mix_pos,
    output reg [31:0] gathered_mix_data,
    output reg done,fault
);
    localparam integer RP=RESP_PHASE, RSC=24;
    initial if(RP<2||RP>23)$fatal(1,"f32 reader: RESP_PHASE 2..23 (two-edge response prediction)");
    initial if(GL!=16)$fatal(1,"f32 reader: GL 16 launch copies");
    reg active,streaming;
    reg [15:0] return_sector,stride;
    // HBM-HC7-QHUB 10-20 (native32 census: issue_sector[k] 39, request_slot 35 loads): two KEPT issue-sector copies (own
    // next state each: copy 0 drives request lanes 0..3, copy 1 lanes 4..7) and four request-slot copies (see rq)
    (* keep = "true", dont_touch = "true" *) reg [15:0] is_c0, is_c1;
    // Native census c1r: binary selectors reached 191 mapped loads despite kept decode wires.
    // Register the eight-way decode on the SAME sector-update edge. Each kept select
    // drives sixteen data bits plus its hold feedback (native max17 expected).
    // Each chunk owns two kept copies and one independent sixteen-flop load copy.
    (* keep = "true", dont_touch = "true" *) reg [16*RSC-1:0] rs_oh;
    (* keep = "true", dont_touch = "true" *) reg [3*RSC-1:0] rs_c;
    reg [3:0] positions,issued,returned;
    reg [4:0] phase,next_row;
    reg [2:0] output_pos;
    wire bounds_ok=bounds_i;
    // launch accept, one per group: 0 issue_sector, 1 return_sector, 2 stride, 3..7 rs_c (15 b each), 8 phase/positions/
    // issued, 9 returned/next_row/output_pos/active/streaming/gathered_mix_*/streaming copies, 10 request prediction
    (* keep = "true", dont_touch = "true" *) reg [1:0] act_c;           // copies of active (same D)
    wire [GL-1:0] la;
    for(genvar k=0;k<GL;k=k+1)begin:g_la
        (* keep = "true" *) wire w=launch_c[k]&&!act_c[k%2]&&bounds_ok;   // kept: an ABC boundary per group select
        assign la[k]=w;
    end
    // ---- response prediction (two edges early) and copies
    wire pred2=active&&phase==5'(RP-2)&&returned<positions;
    (* keep = "true", dont_touch = "true" *) reg [2:0] ld1;
    // ld2 copies: 0..45 landing rows 1..23 (2 x 16 b), 46..50 rs_c groups, 51 return_sector, 52..54 output data thirds,
    // 55/60 row-select state halves, 56/61 copy a halves, 57/62 copy b halves, 58 control A (returned, gathered_mix_*),
    // 59 control B (streaming)
    localparam integer NLD=66;
    (* keep = "true", dont_touch = "true" *) reg [NLD-1:0] ld2;
    reg pred_late; always @(posedge clk) pred_late<=ld1[0];
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin ld1<=0;ld2<=0;end
        else begin
            ld1<={3{pred2}};
            for(integer k=0;k<NLD;k=k+1)ld2[k]<=(MUT==1)?pred_late:ld1[k/30];
        end
    wire response_slot=ld2[58];
    // ---- request prediction (one edge early)
    (* keep = "true", dont_touch = "true" *) reg [3:0] rq;   // 0 is_c0 + issued, 1 lanes 0..3, 2 lanes 4..7, 3 is_c1
    wire rq_d=(la[10]&&npos!=4'd0)||(active&&phase==5'd23&&issued<positions);
    always @(posedge clk or negedge rst_n) if(!rst_n)rq<=0; else rq<={4{rq_d}};
    wire request_slot=rq[0];
    // ---- streaming copies (same next state as streaming)
    (* keep = "true", dont_touch = "true" *) reg [10:0] st_c;   // 0/8 rsel, 1/9 and 2/10 rsel copies, 3..5 data, 6 ctl A, 7 ctl B
    // ---- RSC return selects (as the RSC 24 reader: copy j*8+c selects chunk c of return sector j)
    wire [767:0] arr;
    for(genvar j=0;j<3;j=j+1)begin:g_j
        for(genvar c=0;c<8;c=c+1)begin:g_c
            wire [7:0] oh0=rs_oh[(j*8+c)*16+:8], oh1=rs_oh[(j*8+c)*16+8+:8];
            reg [31:0] v;
            always @*begin
                v=32'd0;
                for(integer b=0;b<8;b=b+1)begin
                    v[15:0]=v[15:0]|({16{oh0[b]}}&local_rr[b*257+c*32+:16]);
                    v[31:16]=v[31:16]|({16{oh1[b]}}&local_rr[b*257+c*32+16+:16]);
                end
            end
            assign arr[j*256+c*32+:32]=v;
        end
    end
    // ---- requests / expected valids (as the reader)
    reg [7:0] expected_valid,actual_valid;
    always @*begin
        local_rq=0;local_read=0;expected_valid=0;actual_valid=0;
        for(integer b=0;b<8;b=b+1)actual_valid[b]=local_rr[b*257+256];
        for(integer j=0;j<3;j=j+1)begin:sector
            reg [15:0] q0,q1,r;
            q0=is_c0+16'(j);q1=is_c1+16'(j);r=return_sector+16'(j);
            // the three sectors map to three distinct lanes (j = 0..2 mod 8): per-lane selects, lanes 0..3 from copy 0
            for(integer b=0;b<8;b=b+1)
                if(b<4 && q0[2:0]==3'(b))begin local_rq[b*17+:17]={rq[1],q0};local_read[b]=rq[1];end
                else if(b>=4 && q1[2:0]==3'(b))begin local_rq[b*17+:17]={rq[2],q1};local_read[b]=rq[2];end
            expected_valid[r[2:0]]=response_slot;
        end
    end
    // ---- landing rows 1..23, one-hot row select (2 kept copies per row), output data
    reg [767:32] landing;
    for(genvar k=1;k<24;k=k+1)begin:g_land
        always @(posedge clk) if(ld2[(k-1)*2+((0)%2)])landing[k*32+:16]<=arr[k*32+:16];
        always @(posedge clk) if(ld2[(k-1)*2+1])landing[k*32+16+:16]<=arr[k*32+16+:16];
    end
    reg [23:1] rsel;                                          // state: one-hot of next_row while streaming
    (* keep = "true", dont_touch = "true" *) reg [23:1] rsel_a,rsel_b;   // copies: 16 output bits each
    // shift selects (kept wires, <= 12 bits each): 0/6 state halves, 1/7 copy a halves, 2/8 copy b halves, 3..5 data thirds
    wire [8:0] sh;
    for(genvar k=0;k<9;k=k+1)begin:g_sh
        localparam integer SC=(k<6)?k:(k-6)+8, LC=(k==0)?55:(k==1)?56:(k==2)?57:(k==3)?52:(k==4)?53:(k==5)?54:(k==6)?60:(k==7)?61:62;
        (* keep = "true" *) wire w=st_c[SC]&&!ld2[LC];
        assign sh[k]=w;
    end
    always @(posedge clk)begin
        if(ld2[55])rsel[11:1]<=11'd1; else if(sh[0])rsel[11:1]<={rsel[10:1],1'b0};
        if(ld2[60])rsel[23:12]<=12'd0; else if(sh[6])rsel[23:12]<=rsel[22:11];
        if(ld2[56])rsel_a[11:1]<=11'd1; else if(sh[1])rsel_a[11:1]<={rsel[10:1],1'b0};
        if(ld2[61])rsel_a[23:12]<=12'd0; else if(sh[7])rsel_a[23:12]<=rsel[22:11];
        if(ld2[57])rsel_b[11:1]<=11'd1; else if(sh[2])rsel_b[11:1]<={rsel[10:1],1'b0};
        if(ld2[62])rsel_b[23:12]<=12'd0; else if(sh[8])rsel_b[23:12]<=rsel[22:11];
    end
    reg [31:0] sel;
    always @*begin
        sel=32'd0;
        for(integer k=1;k<24;k=k+1)begin
            sel[15:0]=sel[15:0]|({16{rsel_a[k]}}&landing[k*32+:16]);
            sel[31:16]=sel[31:16]|({16{rsel_b[k]}}&landing[k*32+16+:16]);
        end
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)gathered_mix_data<=0;
        else begin
            if(ld2[52])gathered_mix_data[10:0]<=arr[10:0]; else if(sh[3])gathered_mix_data[10:0]<=sel[10:0];
            if(ld2[53])gathered_mix_data[21:11]<=arr[21:11]; else if(sh[4])gathered_mix_data[21:11]<=sel[21:11];
            if(ld2[54])gathered_mix_data[31:22]<=arr[31:22]; else if(sh[5])gathered_mix_data[31:22]<=sel[31:22];
        end
    // ---- control (same next state as the reader; response / request / streaming imply active)
    wire respA=ld2[58], respB=ld2[59];
    wire active_n=la[9]?1'b1:(!respA && st_c[6] && next_row==23 && returned==positions)?1'b0:active;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            active<=0;act_c<=0;phase<=0;positions<=0;issued<=0;returned<=0;
            gathered_mix_v<=0;gathered_mix_row<=0;gathered_mix_pos<=0;done<=0;fault<=0;
        end else begin
            gathered_mix_v<=0;done<=0;
            active<=active_n;act_c<={2{active_n}};
            if(actual_valid!==expected_valid)fault<=1;
            if(active)phase<=phase==23?5'd0:phase+5'd1;
            if(request_slot)issued<=issued+1'b1;
            if(respA)begin
                returned<=returned+1'b1;
                gathered_mix_v<=1;gathered_mix_row<=0;gathered_mix_pos<=returned[2:0];
            end else if(st_c[6])begin
                gathered_mix_v<=1;gathered_mix_row<=next_row;gathered_mix_pos<=output_pos;
                if(next_row==23&&returned==positions)done<=1;
            end
            if(launch&&(active||!bounds_ok))fault<=1;
            if(la[8])begin phase<=0;positions<=npos;issued<=0;end
            if(la[9])returned<=0;
        end
    end
    // streaming and its copies: one next-state node
    wire stream_n=la[9]?1'b0:respB?1'b1:(st_c[7] && next_row==23)?1'b0:streaming;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin streaming<=0;st_c<=0;next_row<=0;output_pos<=0;end
        else begin
            streaming<=stream_n;st_c<={11{stream_n}};
            if(respB)begin next_row<=1;output_pos<=returned[2:0];end
            else if(st_c[7])next_row<=next_row+1'b1;
            if(la[9])begin next_row<=0;output_pos<=0;end
        end
    end
    // sector registers: per-group launch accept, response / request from their copies
    always @(posedge clk or negedge rst_n)
        if(!rst_n)is_c0<=0;
        else if(la[0])is_c0<=base_sector;
        else if(rq[0])is_c0<=is_c0+stride;
    wire [15:0] is_c1_next=is_c1+stride;
    // Eight-bit load groups keep both mux polarities below native32.
    for(genvar h=0;h<2;h=h+1)begin:g_is1
        always @(posedge clk or negedge rst_n)
            if(!rst_n)is_c1[h*8+:8]<=0;
            else if(la[14+h])is_c1[h*8+:8]<=base_sector[h*8+:8];
            else if(rq[3])is_c1[h*8+:8]<=is_c1_next[h*8+:8];
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)return_sector<=0;
        else if(la[1])return_sector<=base_sector;
        else if(ld2[51])return_sector<=return_sector+stride;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)stride<=0;
        else if(la[2])stride<=position_stride_sector;
    wire [15:0] rs_next=return_sector+stride;
    // Binary sector copies update on the original launch/response edge. The
    // following unconditional decode rung is ready one edge later, before phase
    // RP (RP>=2) and before the next response 24 edges later. No interface edge
    // changes; separate binary state prevents ABC merging 48 decode D loads.
    for(genvar g=0;g<8;g=g+1)begin:g_rs
        localparam integer LA=(g<5)?3+g:6+g, LD=(g<5)?46+g:58+g;
        always @(posedge clk)
            if(la[LA])rs_c[g*9+:9]<={3{3'(base_sector)}};
            else if(ld2[LD])rs_c[g*9+:9]<={3{3'(rs_next)}};
    end
    for(genvar k=0;k<24;k=k+1)begin:g_decode
        for(genvar h=0;h<2;h=h+1)begin:g_half
            always @(posedge clk)rs_oh[k*16+h*8+:8]<=8'b1 << (rs_c[k*3+:3]+3'(k/8));
        end
    end
endmodule
`default_nettype wire
