`timescale 1ns/1ps
// Sparse fixed issue calendar consumer.  Synchronous calendar ROM has EXACT
// one-edge read latency.  Two records are fetched before production starts;
// every issue launches the read two records ahead.  Adjacent issues use the
// actual ROM response as a bypass, not a readiness-dependent wait.
//
// row[46] last; row[45:44] unit; row[43:32] actual PC; row[31:0] issue cycle.
// Candidate signals come from the actual source decoder (including DYN,
// embedding and full-vocabulary argmax state).  They are checked but NEVER
// gate issue.  Parent must replace its issue/fin equations with issue_v/end_v,
// and retain source command packing, arithmetic, and numeric folding state.
module ot_qwen_fixed_issue #(
    parameter integer ROW_AW=12,
    parameter integer OWN=1
)(
    input wire clk, input wire rst_n,
    input wire start, input wire [31:0] stop_cycle,
    output wire slot_re, output wire [ROW_AW-1:0] slot_addr,
    input wire [46:0] slot_q,
    input wire candidate_v, input wire [11:0] candidate_pc,
    input wire [1:0] candidate_unit,
    input wire available, input wire end_ok, input wire cp_available,
    output wire issue_v, output wire end_v, output wire cp_v, output reg[1:0]cp_index,
    output wire [11:0] issue_pc, output wire [1:0] issue_unit,
    output reg active, output reg done,
    output reg [31:0] cycle,
    output reg fault
);
    reg [31:0] stop_q;
    reg [46:0] head, tail;
    reg head_v, tail_v;
    reg [ROW_AW-1:0] index;
    reg pending;
    reg [ROW_AW-1:0] pending_index;
    reg second_read;
    wire scheduled=active && head_v && cycle==head[31:0];
    assign issue_unit=head[45:44];
    assign issue_pc=head[43:32];
    assign issue_v=scheduled && head[45:44]==OWN;
    assign end_v=scheduled && head[45:44]==0;
    assign cp_v=scheduled && OWN==1 && head[45:44]==3;
    wire next_from_rom=pending && pending_index==index+1'b1;
    wire next_present=tail_v || next_from_rom;
    wire [46:0] next_row=next_from_rom ? slot_q : tail;
    assign slot_re=(start && !active) || (active && second_read) || (scheduled && !head[46] && !(next_present && next_row[46]));
    assign slot_addr=(start && !active) ? {ROW_AW{1'b0}} :
                     second_read ? {{(ROW_AW-1){1'b0}},1'b1} : index+2'd2;
    always @(posedge clk or negedge rst_n) begin
      if(!rst_n) begin
        active<=0;done<=0;cycle<=0;fault<=0;stop_q<=0;
        head<=0;tail<=0;head_v<=0;tail_v<=0;index<=0;
        pending<=0;pending_index<=0;second_read<=0;cp_index<=0;
      end else begin
        done<=0;
        pending<=slot_re;
        if(slot_re) pending_index<=slot_addr;
        if(start && active) fault<=1;
        if(start && !active) begin
          active<=1;cycle<=0;stop_q<=stop_cycle;fault<=0;
          head_v<=0;tail_v<=0;index<=0;second_read<=1;cp_index<=0;
        end else if(active) begin
          cycle<=cycle+1'b1;
          if(second_read) second_read<=0;
          if(pending) begin
            if(pending_index==index) begin head<=slot_q;head_v<=1;end
            else if(pending_index==index+1'b1 && !scheduled) begin tail<=slot_q;tail_v<=1;end
            else if(pending_index!=index+1'b1) fault<=1;
          end
          if(head_v && cycle>head[31:0]) fault<=1;
          if(scheduled) begin
            if(!candidate_v || candidate_pc!=head[43:32] || candidate_unit!=(head[45:44]==3?2'd1:head[45:44])) fault<=1;
            if(head[45:44]==0 ? !end_ok : head[45:44]==3 ? !cp_available : !available) fault<=1;
            if(cp_v)begin cp_index<=cp_index+1'b1;if(cp_index==3)fault<=1;end
            if(head[45:44]!=0 && head[45:44]!=OWN && !(OWN==1&&head[45:44]==3)) fault<=1;
            if(head[46]) begin
              if(head[45:44]!=0 || cycle!=stop_q) fault<=1;
              active<=0;done<=1;head_v<=0;tail_v<=0;
            end else begin
              if(!next_present || next_row[31:0]<=cycle) fault<=1;
              head<=next_row;head_v<=next_present;tail_v<=0;index<=index+1'b1;
              if(&index) fault<=1;
            end
          end
          if(cycle==stop_q) begin
            active<=0;done<=1;
            if(!head_v || head[31:0]!=stop_q || !head[46] || head[45:44]!=0) fault<=1;
          end
          if(&cycle) begin fault<=1;active<=0;done<=1;end
        end
      end
    end
endmodule
