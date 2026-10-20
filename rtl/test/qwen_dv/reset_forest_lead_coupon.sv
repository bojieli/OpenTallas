// Every consumed early reset output feeds a distinct kept rq flop.
// The scalar child boundary consumes only scalar_q. All are observable.
module reset_forest_lead_coupon #(parameter integer DEPTH=2, LEAVES=1024)(
    input wire ck,rst_n, output wire [LEAVES-1:0] observed);
    wire [LEAVES-1:0] early;
    ot_pl_land_reset_forest_lead #(.DEPTH(DEPTH),.LEAVES(LEAVES),.ROOT_LOADS(32)) u_forest(
        .ck(ck),.d(rst_n),.q(early),.scalar_q(observed[0]));
    generate for(genvar c=1;c<LEAVES;c=c+1) begin:g_consumer
        (* keep_hierarchy="yes" *) ot_pl_land_field_copy_bit #(.ID(8192+c)) u_rq(
            .ck(ck),.d(early[c]),.q(observed[c]));
    end endgenerate
endmodule
