// FLATTEN variant (qwen-missing 2026-10-07): the parent's ingress cell qfd_embed_ingress_code bound to the SAME RTL
// the hardened child view was routed from (ot_qwen_embedding_ingress_numeric, AW 12, keep / dont_touch capture
// registers and 150 retained pad buffers), synthesised and placed inside the parent instead of as a hard macro.
// Values and cycles are identical to the macro binding (same module); only the hierarchy is flattened.
module qfd_embed_ingress_code(
 input clk,rst_n,input [12-1:0] address,input valid,credit,
 output [12-1:0] address_q,address_n,output valid_q,valid_n,credit_q,credit_n);
    ot_qwen_embedding_ingress_numeric #(.AW(12)) u_island (.clk(clk), .rst_n(rst_n), .address(address), .valid(valid),
        .credit(credit), .address_q(address_q), .address_n(address_n), .valid_q(valid_q), .valid_n(valid_n),
        .credit_q(credit_q), .credit_n(credit_n));
endmodule
