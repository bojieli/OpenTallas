// Same local two-input fault OR as the former top-level expression; no state/cycles.
(* keep_hierarchy *)
module qkd_kv_ctx_fault_merge (
    input wire base_fault,
    input wire ctx_fault,
    output wire fault
);
    assign fault = base_fault & ctx_fault;
endmodule
module miter(input base_fault, input ctx_fault, output same);
wire actual;
qkd_kv_ctx_fault_merge dut(base_fault,ctx_fault,actual);
assign same = (actual == (base_fault | ctx_fault));
endmodule
