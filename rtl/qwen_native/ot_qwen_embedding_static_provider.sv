`timescale 1ns/1ps
// Balanced registered binary distribution/gather. Every leaf has the same
// fixed latency, including unused leaves. No FIFOs, credits, ready or arbiter.
// LEVEL=12 reserves the complete 2374 code + 3 scale bank inventory.
module ot_qwen_embedding_static_tree #(
    parameter integer LEVEL=12,
    parameter integer BASE=0
)(input wire clk,rst_n,i_v,
  input wire [11:0] i_bank,
  input wire [23:0] i_addr,
  output wire o_v,
  output wire [23:0] o_addr,
  output wire [511:0] o_data,
  output wire fault);
    generate if(LEVEL==0) begin:g_leaf
        if(BASE<2377) begin:g_present
            ot_qwen_embedding_static_bank #(.BANK_ID(BASE<2374?BASE:BASE-2374),.SCALE(BASE>=2374))
                u_bank(.clk(clk),.rst_n(rst_n),.i_v(i_v),.i_addr(i_addr),
                       .o_v(o_v),.o_addr(o_addr),.o_data(o_data),.fault(fault));
        end else begin:g_absent
            reg [4:0] vp;
            reg bad;
            always @(posedge clk or negedge rst_n)
                if(!rst_n) begin vp<=0;bad<=0;end
                else begin vp<={vp[3:0],i_v};if(i_v) bad<=1;end
            assign o_v=vp[4];assign o_data=0;assign o_addr=0;assign fault=bad;
        end
    end else begin:g_node
        reg lv,rv;
        reg [11:0] bank_q;
        reg [23:0] addr_q;
        wire [1:0] valid,child_fault;
        wire [47:0] address;
        wire [1023:0] data;
        reg valid_q, fault_q;
        reg [23:0] out_addr;
        reg [511:0] out_data;
        always @(posedge clk or negedge rst_n)
            if(!rst_n) begin lv<=0;rv<=0;valid_q<=0;fault_q<=0;end
            else begin
                lv<=i_v && !i_bank[LEVEL-1];
                rv<=i_v && i_bank[LEVEL-1];
                valid_q<=|valid;
                if((&valid)||(|child_fault)) fault_q<=1;
            end
        always @(posedge clk) begin
            bank_q<=i_bank;addr_q<=i_addr;
            out_addr <= valid[1]?address[47:24]:address[23:0];
            out_data <= valid[1]?data[1023:512]:data[511:0];
        end
        ot_qwen_embedding_static_tree #(.LEVEL(LEVEL-1),.BASE(BASE)) u_left(
            .clk(clk),.rst_n(rst_n),.i_v(lv),.i_bank(bank_q),.i_addr(addr_q),
            .o_v(valid[0]),.o_addr(address[23:0]),.o_data(data[511:0]),.fault(child_fault[0]));
        ot_qwen_embedding_static_tree #(.LEVEL(LEVEL-1),.BASE(BASE+(1<<(LEVEL-1)))) u_right(
            .clk(clk),.rst_n(rst_n),.i_v(rv),.i_bank(bank_q),.i_addr(addr_q),
            .o_v(valid[1]),.o_addr(address[47:24]),.o_data(data[1023:512]),.fault(child_fault[1]));
        assign o_v=valid_q;assign o_addr=out_addr;assign o_data=out_data;assign fault=fault_q;
    end endgenerate
endmodule

// i_kind=0: global 512-bit code-word address token*64+chunk.
// i_kind=1: token row, response low16=BF16 scale. All addresses are echoed.
// Input sampled E -> response E+28. Root imposes compiler cadence >=2 edges.
module ot_qwen_embedding_static_provider(
    input wire clk,rst_n,i_v,i_kind,
    input wire [23:0] i_addr,
    output wire o_v,o_kind,
    output wire [23:0] o_addr,
    output wire [511:0] o_data,
    output wire fault
);
    wire [11:0] bank = i_kind ? (2374+(i_addr>>16)) : (i_addr>>12);
    wire tree_fault;
    reg bad,previous;
    reg [28:0] kinds;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin bad<=0;previous<=0;kinds<=0;end
        else begin
            previous<=i_v;
            kinds<={kinds[27:0],i_kind};
            if(i_v && (previous || (i_kind ? i_addr>=151936 : i_addr>=9723904))) bad<=1;
        end
    ot_qwen_embedding_static_tree u_tree(.clk(clk),.rst_n(rst_n),.i_v(i_v),
        .i_bank(bank),.i_addr(i_addr),.o_v(o_v),.o_addr(o_addr),.o_data(o_data),.fault(tree_fault));
    assign o_kind=kinds[28];
    assign fault=bad|tree_fault;
endmodule
