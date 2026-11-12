// HBM-CORES-B 11-12: EQ_CYCLE_SHIFTED miter, ot_hbm_sm_pv_merge RDREG 1 (dut) vs RDREG 0 (ref), same free inputs.
// While neither side has faulted: pv_v / pv_y / pv_tag equal in the same cycle; DUT publication = ref one edge later.
// Real 64x512 stack on both sides; both use the same adder stub (stub_fadd.v). RDMUT 1/2/3 = negative controls.
module miter #(parameter integer RDMUT=0, parameter integer LV=2) (
    input wire clk, input wire ev, input wire [511:0] sum, input wire [15:0] tag_d,
    input wire pub_start, input wire [2:0] pub_slot, input wire fold_start, input wire [2:0] fold_a, input wire [2:0] fold_b);
    wire rst_n = 1'b1;                                 // -set-init-zero: every register starts in its reset value
    wire r_pv_v,r_pub_v,r_fault,d_pv_v,d_pub_v,d_fault;
    wire [511:0] r_pv_y,d_pv_y;
    wire [15:0] r_pv_tag,d_pv_tag,r_pub_tag,d_pub_tag;
    wire [31:0] r_pub_data,d_pub_data;
    wire [3:0] r_pub_word,d_pub_word;
    wire [2:0] r_pub_out_slot,d_pub_out_slot;
    ot_hbm_sm_pv_merge #(.PUBLISH(1),.LV(LV),.RDREG(0)) u_ref(.clk(clk),.rst_n(rst_n),.ev(ev),.sum(sum),.tag_d(tag_d),.pv_v(r_pv_v),.pv_y(r_pv_y),
        .pv_tag(r_pv_tag),.fault(r_fault),.pub_start(pub_start),.pub_slot(pub_slot),.pub_v(r_pub_v),.pub_data(r_pub_data),.pub_word(r_pub_word),
        .pub_out_slot(r_pub_out_slot),.pub_tag(r_pub_tag),.fold_start(fold_start),.fold_a(fold_a),.fold_b(fold_b));
    ot_hbm_sm_pv_merge #(.PUBLISH(1),.LV(LV),.RDREG(1),.RDMUT(RDMUT)) u_dut(.clk(clk),.rst_n(rst_n),.ev(ev),.sum(sum),.tag_d(tag_d),.pv_v(d_pv_v),.pv_y(d_pv_y),
        .pv_tag(d_pv_tag),.fault(d_fault),.pub_start(pub_start),.pub_slot(pub_slot),.pub_v(d_pub_v),.pub_data(d_pub_data),.pub_word(d_pub_word),
        .pub_out_slot(d_pub_out_slot),.pub_tag(d_pub_tag),.fold_start(fold_start),.fold_a(fold_a),.fold_b(fold_b));
    reg q_v=0,q_f=0; reg [31:0] q_data=0; reg [3:0] q_word=0; reg [2:0] q_slot=0; reg [15:0] q_tag=0;
    always @(posedge clk) begin q_v<=r_pub_v;q_data<=r_pub_data;q_word<=r_pub_word;q_slot<=r_pub_out_slot;q_tag<=r_pub_tag;q_f<=r_fault; end
    wire ok = !r_fault && !d_fault;
    always @* begin
        if (ok) assert(d_pv_v == r_pv_v);
        if (ok && r_pv_v) assert(d_pv_y == r_pv_y && d_pv_tag == r_pv_tag);
        if (!q_f && !d_fault) assert(d_pub_v == q_v);
        if (!q_f && !d_fault && q_v) assert(d_pub_data == q_data && d_pub_word == q_word && d_pub_out_slot == q_slot && d_pub_tag == q_tag);
    end
endmodule
