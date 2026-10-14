`timescale 1ns/1ps
// Same-edge metadata of the *selected* original source. No state, ownership,
// special-value reinterpretation, or feedback: both data sources remain real.
module ot_hdc_bf16_capture_split (
    input wire [31:0] vm_word, kr_word,
    input wire select_kr,
    output wire [15:0] high_increment,
    output wire round_up
);
    wire [15:0] vm_inc, kr_inc;
    wire vm_carry, kr_carry;
    ot_hdc_inc_k #(.W(16)) u_vm (.a(vm_word[31:16]), .inc(1'b1), .y(vm_inc), .co(vm_carry));
    ot_hdc_inc_k #(.W(16)) u_kr (.a(kr_word[31:16]), .inc(1'b1), .y(kr_inc), .co(kr_carry));
    // Exactly bits [14:0] plus bit16, as the existing BF16 RNE decision.
    (* keep *) wire [3:0] vm_groups = {
        |{vm_word[16],vm_word[14:12]}, |vm_word[11:8],
        |vm_word[7:4], |vm_word[3:0]};
    (* keep *) wire [3:0] kr_groups = {
        |{kr_word[16],kr_word[14:12]}, |kr_word[11:8],
        |kr_word[7:4], |kr_word[3:0]};
    wire vm_up = vm_word[15] & (|vm_groups);
    wire kr_up = kr_word[15] & (|kr_groups);
    assign high_increment = select_kr ? kr_inc : vm_inc;
    assign round_up = select_kr ? kr_up : vm_up;
endmodule
