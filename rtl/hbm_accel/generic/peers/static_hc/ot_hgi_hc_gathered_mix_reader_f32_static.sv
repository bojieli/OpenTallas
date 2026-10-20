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
module ot_hgi_hc_gathered_mix_reader_f32_static #(parameter integer RESP_PHASE=23, parameter integer GL=11,
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
    initial if(GL!=11)$fatal(1,"f32 reader: GL 11 launch copies");
    reg active,streaming;
    reg [15:0] issue_sector,return_sector,stride;
    (* keep = "true", dont_touch = "true" *) reg [3*RSC-1:0] rs_c;
    reg [3:0] positions,issued,returned;
    reg [4:0] phase,next_row;
    reg [2:0] output_pos;
    wire bounds_ok=bounds_i;
    // launch accept, one per group: 0 issue_sector, 1 return_sector, 2 stride, 3..7 rs_c (15 b each), 8 phase/positions/
    // issued, 9 returned/next_row/output_pos/active/streaming/gathered_mix_*/streaming copies, 10 request prediction
    wire [GL-1:0] la;
    for(genvar k=0;k<GL;k=k+1)begin:g_la
        assign la[k]=launch_c[k]&&!active&&bounds_ok;
    end
    // ---- response prediction (two edges early) and copies
    wire pred2=active&&phase==5'(RP-2)&&returned<positions;
    (* keep = "true", dont_touch = "true" *) reg [1:0] ld1;
    // ld2 copies: 0..45 landing rows 1..23 (2 x 16 b), 46..50 rs_c groups, 51 return_sector, 52/53 output data halves,
    // 54 row-select state, 55 row-select copies, 56 control A (returned, gathered_mix_*), 57 control B (streaming, next_row)
    localparam integer NLD=58;
    (* keep = "true", dont_touch = "true" *) reg [NLD-1:0] ld2;
    reg pred_late; always @(posedge clk) pred_late<=ld1[0];
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin ld1<=0;ld2<=0;end
        else begin
            ld1<={2{pred2}};
            for(integer k=0;k<NLD;k=k+1)ld2[k]<=(MUT==1)?pred_late:ld1[k/32];
        end
    wire response_slot=ld2[56];
    // ---- request prediction (one edge early)
    (* keep = "true", dont_touch = "true" *) reg [1:0] rq;
    wire rq_d=(la[10]&&npos!=4'd0)||(active&&phase==5'd23&&issued<positions);
    always @(posedge clk or negedge rst_n) if(!rst_n)rq<=0; else rq<={2{rq_d}};
    wire request_slot=rq[1];
    // ---- streaming copies (same next state as streaming)
    (* keep = "true", dont_touch = "true" *) reg [5:0] st_c;
    // ---- RSC return selects (as the RSC 24 reader: copy j*8+c selects chunk c of return sector j)
    wire [767:0] arr;
    for(genvar j=0;j<3;j=j+1)begin:g_j
        for(genvar c=0;c<8;c=c+1)begin:g_c
            wire [2:0] rk=rs_c[(j*8+c)*3+:3]+3'(j);
            reg [31:0] v;
            always @*begin
                v=32'd0;
                for(integer b=0;b<8;b=b+1)v=v|({32{rk==3'(b)}}&local_rr[b*257+c*32+:32]);
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
            reg [15:0] q,r;
            q=issue_sector+16'(j);r=return_sector+16'(j);
            local_rq[q[2:0]*17+:17]={request_slot,q};local_read[q[2:0]]=request_slot;
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
    wire sh0=st_c[0]&&!ld2[54], sh1=st_c[1]&&!ld2[55], sh2=st_c[2]&&!ld2[52], sh3=st_c[3]&&!ld2[53];
    always @(posedge clk)begin
        if(ld2[54])rsel<=23'd1; else if(sh0)rsel<={rsel[22:1],1'b0};
        if(ld2[55])begin rsel_a<=23'd1;rsel_b<=23'd1;end else if(sh1)begin rsel_a<={rsel[22:1],1'b0};rsel_b<={rsel[22:1],1'b0};end
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
            if(ld2[52])gathered_mix_data[15:0]<=arr[15:0]; else if(sh2)gathered_mix_data[15:0]<=sel[15:0];
            if(ld2[53])gathered_mix_data[31:16]<=arr[31:16]; else if(sh3)gathered_mix_data[31:16]<=sel[31:16];
        end
    // ---- control (same next state as the reader; response / request / streaming imply active)
    wire respA=ld2[56], respB=ld2[57];
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            active<=0;phase<=0;positions<=0;issued<=0;returned<=0;
            gathered_mix_v<=0;gathered_mix_row<=0;gathered_mix_pos<=0;done<=0;fault<=0;
        end else begin
            gathered_mix_v<=0;done<=0;
            if(actual_valid!==expected_valid)fault<=1;
            if(active)phase<=phase==23?5'd0:phase+5'd1;
            if(request_slot)issued<=issued+1'b1;
            if(respA)begin
                returned<=returned+1'b1;
                gathered_mix_v<=1;gathered_mix_row<=0;gathered_mix_pos<=returned[2:0];
            end else if(st_c[4])begin
                gathered_mix_v<=1;gathered_mix_row<=next_row;gathered_mix_pos<=output_pos;
                if(next_row==23&&returned==positions)begin active<=0;done<=1;end
            end
            if(launch&&(active||!bounds_ok))fault<=1;
            if(la[8])begin phase<=0;positions<=npos;issued<=0;end
            if(la[9])begin active<=1;returned<=0;end
        end
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin streaming<=0;st_c<=0;next_row<=0;output_pos<=0;end
        else begin
            if(respB)begin
                streaming<=1;st_c<=6'h3f;next_row<=1;output_pos<=returned[2:0];
            end else if(st_c[5])begin
                next_row<=next_row+1'b1;
                if(next_row==23)begin streaming<=0;st_c<=6'h0;end
            end
            if(la[9])begin streaming<=0;st_c<=6'h0;next_row<=0;output_pos<=0;end
        end
    end
    // sector registers: per-group launch accept, response / request from their copies
    always @(posedge clk or negedge rst_n)
        if(!rst_n)issue_sector<=0;
        else if(la[0])issue_sector<=base_sector;
        else if(rq[0])issue_sector<=issue_sector+stride;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)return_sector<=0;
        else if(la[1])return_sector<=base_sector;
        else if(ld2[51])return_sector<=return_sector+stride;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)stride<=0;
        else if(la[2])stride<=position_stride_sector;
    wire [15:0] rs_next=return_sector+stride;
    for(genvar g=0;g<5;g=g+1)begin:g_rs
        localparam integer LO=g*15, HI=(g==4)?3*RSC:(g+1)*15;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)rs_c[HI-1:LO]<=0;
            else if(la[3+g])begin for(integer i=LO;i<HI;i=i+1)rs_c[i]<=base_sector[i%3]; end
            else if(ld2[46+g])begin for(integer i=LO;i<HI;i=i+1)rs_c[i]<=rs_next[i%3]; end
    end
endmodule
`default_nettype wire
