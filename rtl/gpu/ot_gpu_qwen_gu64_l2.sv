`timescale 1ns/1ps
// Sized by GU_pipeline_before_RTL.json. An AR column; physical SM has16.
// No elastic MAC input: reserve a pair first, then pulse step_v only at the
// actual clock phase for that slot. The phase advances through all bubbles.
// One addressed16-entry FIFO holds raw/scaled/sent data, never host epilogues.
module ot_gpu_qwen_gu64_l2 #(
    parameter integer ENABLE_GU64_L2=0,
    parameter integer ROWW=18
) (
    input wire clk,rst_n,
    output wire [2:0] issue_phase,
    input wire reserve_v,output wire reserve_ready,
    input wire [2:0] reserve_slot,
    input wire [2*ROWW-1:0] reserve_rows,
    input wire [31:0] reserve_scales_bf16,
    input wire [15:0] reserve_epoch,
    input wire step_v,output wire step_ready,
    input wire [2:0] step_slot,
    input wire [1023:0] weights_i8,x_bf16,
    output wire l2_v,input wire l2_ready,
    output wire [3:0] l2_id,
    output wire [ROWW-1:0] l2_row,
    output wire [15:0] l2_epoch,
    output wire [31:0] l2_data,
    input wire commit_v,input wire [3:0] commit_id,
    input wire [ROWW-1:0] commit_row,
    input wire [15:0] commit_epoch,
    output wire [4:0] free_row_credits,
    output reg fault
);
    localparam FREE=0,RESERVED=1,RAW=2,MULTIPLYING=3,READY=4,SENT=5,COMMITTED=6;
    reg [2:0] phase;
    reg [7:0] reserved;
    reg [6:0] products[0:7];
    reg [2:0] state[0:15];
    reg [31:0] data[0:15];
    reg [15:0] scale[0:15],epoch[0:15];
    reg [ROWW-1:0] row[0:15];
    reg [3:0] raw_cursor,out_cursor,out_id;
    reg out_hold;
    reg raw_found,out_found;
    reg [3:0] raw_id,selected_id;
    reg [4:0] credits;
    integer j,k;
    always @* begin
        raw_found=0;out_found=0;raw_id=0;selected_id=0;credits=0;
        for(j=0;j<8;j=j+1) if(!reserved[j]) credits=credits+2;
        for(j=0;j<16;j=j+1) begin
            k=(raw_cursor+j)&15;
            if(!raw_found && state[k]==RAW) begin raw_found=1;raw_id=k;end
            k=(out_cursor+j)&15;
            if(!out_found && state[k]==READY) begin out_found=1;selected_id=k;end
        end
        if(out_hold) begin selected_id=out_id;out_found=state[out_id]==READY;end
    end
    assign free_row_credits=credits;
    assign issue_phase=phase;
    assign reserve_ready=ENABLE_GU64_L2 && !fault && !reserved[reserve_slot];
    assign step_ready=ENABLE_GU64_L2 && !fault && step_slot==phase &&
        reserved[step_slot] && products[step_slot]<64;
    wire accepted=step_v && step_ready;
    wire [3:0] pair_id={step_slot,1'b0};
    wire [1:0] pv;
    wire [63:0] ps;
    wire [2*ROWW-1:0] pr;
    wire [5:0] pt;
    wire pf;
    ot_gpu_qwen_gu64_pair #(.ENABLE_GU64(ENABLE_GU64_L2),.ROWW(ROWW)) u_gu(
        .clk(clk),.rst_n(rst_n),.v(accepted),
        .first(products[step_slot]==0),.last(products[step_slot]==63),
        .weights_i8(weights_i8),.x_bf16(x_bf16),
        .global_rows({row[pair_id+1],row[pair_id]}),.slots({step_slot,step_slot}),
        .ov(pv),.sums(ps),.result_rows(pr),.result_slots(pt),.fault(pf));
    wire mul_v,mul_fault;
    wire [31:0] mul_y;
    wire [3:0] mul_id;
    wire [7:0] mv;
    ot_gpu_fmul #(.LAT(7)) u_scale(.clk(clk),.rst_n(rst_n),
        .v(raw_found),.a(data[raw_id]),.b({scale[raw_id],16'd0}),
        .y(mul_y),.fault(mul_fault));
    ot_hdc_vline #(.D(7)) u_mv(.clk(clk),.rst_n(rst_n),.v(raw_found),.vd(mv));
    ot_hdc_delay #(.W(4),.D(7)) u_mid(.clk(clk),.rst_n(rst_n),.d(raw_id),.q(mul_id));
    assign mul_v=mv[7];
    assign l2_v=ENABLE_GU64_L2 && out_found;
    assign l2_id=selected_id;
    assign l2_row=row[selected_id];assign l2_epoch=epoch[selected_id];
    assign l2_data=data[selected_id];
    wire send=l2_v && l2_ready;
    wire commit_identity=commit_epoch==epoch[commit_id] && commit_row==row[commit_id];
    wire commit_allowed=state[commit_id]==SENT ||
        (send && selected_id==commit_id && state[commit_id]==READY);
    integer i,r;
    reg [3:0] idx;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            phase<=0;reserved<=0;fault<=0;raw_cursor<=0;out_cursor<=0;
            out_id<=0;out_hold<=0;
            for(i=0;i<8;i=i+1) products[i]<=0;
            for(i=0;i<16;i=i+1) begin
                state[i]<=FREE;row[i]<=0;epoch[i]<=0;scale[i]<=0;data[i]<=0;
            end
        end else begin
            phase<=phase+1'b1;
            if(pf || mul_fault) fault<=1;
            if(step_v && !step_ready) fault<=1;
            if(reserve_v && !reserve_ready) fault<=1;
            if(reserve_v && reserve_ready) begin
                if(reserve_rows[ROWW-1:0]==reserve_rows[2*ROWW-1:ROWW]) fault<=1;
                else begin
                    reserved[reserve_slot]<=1;products[reserve_slot]<=0;
                    for(r=0;r<2;r=r+1) begin
                        idx={reserve_slot,1'b0}+r;
                        state[idx]<=RESERVED;row[idx]<=reserve_rows[r*ROWW+:ROWW];
                        epoch[idx]<=reserve_epoch;scale[idx]<=reserve_scales_bf16[r*16+:16];
                    end
                end
            end
            if(accepted) products[step_slot]<=products[step_slot]+1'b1;
            if(pv!=0) begin
                if(pv!=3 || pt[2:0]!=pt[5:3]) fault<=1;
                for(r=0;r<2;r=r+1) if(pv[r]) begin
                    idx={pt[r*3+:3],1'b0}+r;
                    if(state[idx]!=RESERVED || products[idx[3:1]]!=64 ||
                       row[idx]!=pr[r*ROWW+:ROWW]) fault<=1;
                    else begin data[idx]<=ps[r*32+:32];state[idx]<=RAW;end
                end
            end
            if(raw_found) begin state[raw_id]<=MULTIPLYING;raw_cursor<=raw_id+1'b1;end
            if(mul_v) begin
                if(state[mul_id]!=MULTIPLYING) fault<=1;
                else begin data[mul_id]<=mul_y;state[mul_id]<=READY;end
            end
            if(l2_v && !l2_ready) begin out_hold<=1;out_id<=selected_id;end
            if(send) begin state[selected_id]<=SENT;out_hold<=0;out_cursor<=selected_id+1'b1;end
            if(commit_v) begin
                if(!commit_identity || !commit_allowed) fault<=1;
                else begin
                    state[commit_id]<=COMMITTED;
                    if(state[commit_id^1]==COMMITTED) begin
                        state[commit_id]<=FREE;state[commit_id^1]<=FREE;
                        reserved[commit_id[3:1]]<=0;
                    end
                end
            end
        end
    end
endmodule
