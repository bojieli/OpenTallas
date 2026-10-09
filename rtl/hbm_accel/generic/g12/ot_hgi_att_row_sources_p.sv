`timescale 1ns/1ps
// Physical/exactness vehicle for the opt-in G12 frontend. The legacy engine is
// unchanged and selects this vehicle only after its gates pass.
module ot_hgi_att_row_sources_p #(
    parameter integer MUT_RING_ZERO=0, MUT_DROP_C=0, MUT_C_REVERSE=0
)(
    input wire clk,rst_n,cmd_v,ring,
    output wire cmd_r,
    input wire [20:0] pos1,b_n,b_m,c_n,
    input wire c_id_v,output wire c_id_r,input wire [31:0] c_id,
    output wire row_v,input wire row_r,
    output wire row_source,row_last,
    output wire [19:0] row_index,
    output wire [20:0] row_ordinal,
    output wire busy,done,fault
);
    // Command station and two-word selected-ID FIFO: every data input lands
    // in a flop, and returned ready never depends combinationally on row_r.
    reg command_full, ring_q;
    reg [20:0] pos1_q,b_n_q,b_m_q,c_n_q;
    reg [31:0] id_fifo [0:1];
    reg wr_ptr,rd_ptr; reg [1:0] id_count;
    wire inner_cmd_r,inner_id_r,inner_busy;
    wire push_id=c_id_v && c_id_r;
    wire pop_id=(id_count!=0) && inner_id_r;
    assign cmd_r=!command_full;
    assign c_id_r=(id_count<2);
    assign busy=inner_busy || command_full;
    always @(posedge clk) begin
        if(!rst_n) begin
            command_full<=0;ring_q<=0;pos1_q<=0;b_n_q<=0;b_m_q<=0;c_n_q<=0;
            wr_ptr<=0;rd_ptr<=0;id_count<=0;id_fifo[0]<=0;id_fifo[1]<=0;
        end else begin
            if(command_full && inner_cmd_r) command_full<=0;
            if(cmd_v && cmd_r) begin
                command_full<=1;ring_q<=ring;pos1_q<=pos1;b_n_q<=b_n;b_m_q<=b_m;c_n_q<=c_n;
            end
            if(push_id) begin id_fifo[wr_ptr]<=c_id;wr_ptr<=~wr_ptr;end
            if(pop_id) rd_ptr<=~rd_ptr;
            case({push_id,pop_id})
                2'b10:id_count<=id_count+1'b1;
                2'b01:id_count<=id_count-1'b1;
                default:id_count<=id_count;
            endcase
        end
    end
    ot_hgi_att_row_sources #(.ENABLE_G12(1),.MUT_RING_ZERO(MUT_RING_ZERO),.MUT_DROP_C(MUT_DROP_C),.MUT_C_REVERSE(MUT_C_REVERSE)) u_rows(
        .clk(clk),.rst_n(rst_n),.cmd_v(command_full),.cmd_r(inner_cmd_r),.ring(ring_q),.pos1(pos1_q),.b_n(b_n_q),.b_m(b_m_q),.c_n(c_n_q),
        .c_id_v(id_count!=0),.c_id_r(inner_id_r),.c_id(id_fifo[rd_ptr]),
        .legacy_v(1'b0),.legacy_r(),.legacy_source(1'b0),.legacy_last(1'b0),.legacy_row(20'b0),.legacy_ordinal(21'b0),
        .row_v(row_v),.row_r(row_r),.row_source(row_source),.row_last(row_last),.row_index(row_index),.row_ordinal(row_ordinal),
        .busy(inner_busy),.done(done),.fault(fault));
endmodule
