`timescale 1ns/1ps
`default_nettype none
// U-only layer-boundary selector and autonomous static event store. No ready/credits.
// cfg writes occur while idle. Store rows: {last, cycle[31:0], unit_mask[15:0], record_id[31:0]}.
// Event cycles are relative to the edge sampling union_v. Minimum event spacing = 3.
// record_id is a compiler record reference; a native descriptor dispatcher is a separate integration boundary.
module ot_hnx_union_calendar #(
    parameter integer AW=14, parameter integer MUT=0
)(
    input wire clk, rst_n,
    input wire cfg_we, input wire [AW-1:0] cfg_addr, input wire [80:0] cfg_data,
    input wire union_v, input wire [9:0] union_count,
    input wire [4:0] n_rows, input wire [3:0] topk,
    input wire [AW-1:0] bank_base, input wire [4:0] bank_shift,
    output reg busy, output reg fault, output reg done,
    output reg selected_v, output reg [9:0] selected_u,
    output reg [AW-1:0] selected_base,
    output reg launch_v, output reg [15:0] launch_mask, output reg [31:0] launch_record
);
    reg [80:0] mem [0:(1<<AW)-1];
    reg [80:0] rd, event_q;
    reg [AW-1:0] pc, limit_q;
    reg [31:0] age;
    reg [2:0] st;
    localparam IDLE=0, READ=1, CAP=2, WAIT=3;
    wire [31:0] u_pick = (MUT == 1 && union_count > {28'd0,topk}) ? {22'd0,union_count}-1 : {22'd0,union_count};
    wire [31:0] stride = 32'd1 << bank_shift;
    wire [31:0] first = { {(32-AW){1'b0}},bank_base } + ((u_pick-{28'd0,topk}) << bank_shift);
    wire [31:0] bound = first + stride;
    wire legal = n_rows >= 1 && n_rows <= 16 && topk >= 1 && topk <= 8 &&
        union_count >= {6'd0,topk} && union_count <= 10'(int'(n_rows)*int'(topk)) &&
        bank_shift <= AW && first < (32'd1<<AW) && bound <= (32'd1<<AW);
    always @(posedge clk) begin
        if (cfg_we && !busy) mem[cfg_addr] <= cfg_data;
        if (st == READ) rd <= mem[pc];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy<=0; fault<=0; done<=0; selected_v<=0; launch_v<=0; st<=IDLE; age<=0;
        end else begin
            fault<=0; done<=0; selected_v<=0; launch_v<=0;
            if (busy) age<=age+1;
            if ((cfg_we || union_v) && busy) begin
                busy<=0; fault<=1; st<=IDLE;
            end else case(st)
                IDLE: if (union_v) begin
                    if (!legal || cfg_we) fault<=1;
                    else begin
                        selected_v<=1; selected_u<=10'(u_pick); selected_base<=AW'(first);
                        pc<=AW'(first); limit_q<=AW'(bound-1); age<=1; busy<=1; st<=READ;
                    end
                end
                READ: st<=CAP;
                CAP: begin event_q<=rd; st<=WAIT; end
                WAIT: if (event_q[79:48] < age) begin
                    busy<=0; fault<=1; st<=IDLE; // late or non-monotonic calendar: fail, never stall
                end else if (event_q[79:48] == age) begin
                    launch_v<=!event_q[80]; launch_mask<=event_q[47:32]; launch_record<=event_q[31:0];
                    if (event_q[80]) begin busy<=0; done<=1; st<=IDLE; end
                    else if (pc == limit_q) begin busy<=0; fault<=1; launch_v<=0; st<=IDLE; end
                    else begin pc<=pc+1'b1; st<=READ; end
                end
                default: begin st<=IDLE; busy<=0; fault<=1; end
            endcase
        end
    end
endmodule
`default_nettype wire
