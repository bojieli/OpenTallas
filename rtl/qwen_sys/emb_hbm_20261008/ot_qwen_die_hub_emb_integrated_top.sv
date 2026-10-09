// Additive real-port wrapper; original hub remains unchanged.
module ot_qwen_die_hub_emb_integrated_top #(
    parameter integer BOOT_MERGE=0,
    parameter integer CR = 128, parameter integer OD = 8, parameter integer XS = 8, parameter integer ARC = 4,
    parameter integer RQD = 32, parameter integer MUT = 0
) (
    input  wire         ck,
    input  wire         rst_n,
    input  wire         fck0, input wire fck1, input wire fck2, input wire fck3,
    input  wire [527:0] l0_i, output wire [527:0] l0_o,
    input  wire [527:0] l1_i, output wire [527:0] l1_o,
    input  wire [527:0] l2_i, output wire [527:0] l2_o,
    input  wire [527:0] l3_i, output wire [527:0] l3_o,
    input  wire         x3_v, input wire [511:0] x3_d, input wire [10:0] x3_tag, output wire x3_cr,
    output wire         ar_v, output wire [511:0] ar_d, input wire ar_cr,
    output wire         fault,
    output wire [5:0]   fault_cause,
    input  wire         ea_v, input wire ea_kind, input wire [23:0] ea_addr, output wire ea_cr,
    output wire         eq_v, output wire [511:0] eq_d,
    input wire host_v, input wire host_we, input wire [31:0] host_addr, input wire [255:0] host_d,
    output wire host_boot_credit, output wire host_boot_accept, output wire host_runtime_v, output wire merge_fault,
    output wire         emb_ready, output wire emb_fault, output wire [7:0] emb_fault_code
);
    generate if (BOOT_MERGE != 0) begin: enabled
    ot_qwen_die_hub_emb_integrated_impl #(.NL(4),.LW(528),.CR(CR),.OD(OD),.XS(XS),.ARC(ARC),.RQD(RQD),.MUT(MUT)) u (.ck(ck), .rst_n(rst_n), .fck({fck3,fck2,fck1,fck0}),
        .l_i({l3_i,l2_i,l1_i,l0_i}), .l_o({l3_o,l2_o,l1_o,l0_o}),
        .x3_v(x3_v), .x3_d(x3_d), .x3_tag(x3_tag), .x3_cr(x3_cr),
        .ar_v(ar_v), .ar_d(ar_d), .ar_cr(ar_cr), .fault(fault), .fault_cause(fault_cause),
        .ea_v(ea_v), .ea_kind(ea_kind), .ea_addr(ea_addr), .ea_cr(ea_cr),
        .eq_v(eq_v), .eq_d(eq_d), .emb_ready(emb_ready), .emb_fault(emb_fault), .emb_fault_code(emb_fault_code),
        .host_v(host_v),.host_we(host_we),.host_addr(host_addr),.host_d(host_d),
        .host_boot_credit(host_boot_credit),.host_boot_accept(host_boot_accept),.host_runtime_v(host_runtime_v),.merge_fault(merge_fault));
    end else begin: disabled
    ot_qwen_die_hub_emb #(.NL(4),.LW(528),.CR(CR),.OD(OD),.XS(XS),.ARC(ARC),.RQD(RQD),.MUT(MUT)) u (.ck(ck), .rst_n(rst_n), .fck({fck3,fck2,fck1,fck0}),
        .l_i({l3_i,l2_i,l1_i,l0_i}), .l_o({l3_o,l2_o,l1_o,l0_o}),
        .x3_v(x3_v), .x3_d(x3_d), .x3_tag(x3_tag), .x3_cr(x3_cr),
        .ar_v(ar_v), .ar_d(ar_d), .ar_cr(ar_cr), .fault(fault), .fault_cause(fault_cause),
        .ea_v(ea_v), .ea_kind(ea_kind), .ea_addr(ea_addr), .ea_cr(ea_cr),
        .eq_v(eq_v), .eq_d(eq_d), .emb_ready(emb_ready), .emb_fault(emb_fault), .emb_fault_code(emb_fault_code));
    assign host_boot_credit=0;assign host_boot_accept=0;assign merge_fault=0;
    assign host_runtime_v=host_v && !host_addr[31];
    end endgenerate
endmodule
