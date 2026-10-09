// Functional local reset release. Preserve this module as an actual boundary;
// each bucket has one clock-local retained release register, not control mirrors.
(* keep_hierarchy = "yes" *)
module ot_hfd_loader_reset_leaf(input wire clk, parent_reset_n, output wire reset_n);
    (* keep = "true", dont_touch = "true" *) reg released;
    always @(posedge clk or negedge parent_reset_n)
        if (!parent_reset_n) released <= 1'b0;
        else released <= 1'b1;
    assign reset_n = released;
endmodule
