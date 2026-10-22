// Private opt-in component. Each copy captures on the unchanged local_r edge.
// This file does not change shared LP generation or certify parent fanout.
`default_nettype none
(* keep_hierarchy = "yes" *)
module ot_pl_land_field_copy_bit #(parameter integer ID=0)(
    input wire ck, d, output wire q
);
    (* keep = 1 *) reg value;
    always @(posedge ck) value <= d;
    assign q = value;
endmodule

(* keep_hierarchy = "yes" *)
module ot_pl_land_field_copy_group #(
    parameter integer COPIES=24, D=4, K=2, ID=0,
    parameter integer AW=(D<=2)?1:$clog2(D)
)(
    input wire ck, rsi,
    input wire [D-1:0] bank, vld,
    input wire [D*(AW+1)-1:0] epo,
    output wire [COPIES-1:0] o
);
    reg rq, warm;
    reg [AW:0] rc;
    (* keep = 1 *) reg [D-1:0] read_oh;
    wire [AW:0] expected_epoch=rc-(AW+1)'(K);
    wire selected=|(bank & read_oh);
    wire selected_valid=|(vld & read_oh);
    wire captured=warm && selected_valid && selected;
    always @(posedge ck) rq <= rsi;
    always @(posedge ck)
        if (!rq) begin
            rc<=0; warm<=0;
            for (integer s=0;s<D;s=s+1) read_oh[s]<=(s==((D-K)%D));
        end else begin
            rc<=rc+1'b1;
            if (rc==K-1) warm<=1;
            read_oh<={read_oh[D-2:0],read_oh[D-1]};
        end
    generate for(genvar c=0;c<COPIES;c=c+1) begin:g_copy
        (* keep_hierarchy = "yes" *) ot_pl_land_field_copy_bit #(.ID(ID*24+c)) u_ff(
            .ck(ck),.d(captured),.q(o[c]));
    end endgenerate
`ifndef SYNTHESIS
    reg fault=0;
    always @(posedge ck) if(warm && selected_valid && !fault)
        for(integer j=0;j<D;j=j+1) if(read_oh[j] && epo[j*(AW+1)+:AW+1]!=expected_epoch) begin
            fault<=1;
            $error("LAND_FIELD_FAULT %m: slot%0d epoch%0d expected%0d",j,epo[j*(AW+1)+:AW+1],expected_epoch);
        end
    initial if(COPIES<1 || COPIES>24) $fatal(1,"field group COPIES must be 1..24");
`endif
endmodule

module ot_pl_land_field_copies #(
    parameter integer COPIES=3, D=4, K=2,
    parameter integer AW=(D<=2)?1:$clog2(D)
)(
    input wire ck, rsi,
    input wire [D-1:0] bank, vld,
    input wire [D*(AW+1)-1:0] epo,
    output wire [COPIES-1:0] o
);
    generate for(genvar g=0;g<(COPIES+23)/24;g=g+1) begin:g_group
        localparam integer CW=(COPIES-g*24<24)?COPIES-g*24:24;
        (* keep_hierarchy = "yes" *) ot_pl_land_field_copy_group #(.COPIES(CW),.D(D),.K(K),.ID(g)) u_group(
            .ck(ck),.rsi(rsi),.bank(bank),.vld(vld),.epo(epo),.o(o[g*24+:CW]));
    end endgenerate
`ifndef SYNTHESIS
    initial begin
        if(COPIES<1 || COPIES>744) $fatal(1,"field COPIES must be 1..744");
        if(D<2 || (D & (D-1))!=0) $fatal(1,"field D must be power of two >=2");
        if(K<1 || K>D-1) $fatal(1,"field K must be 1..D-1");
    end
`endif
endmodule
`default_nettype wire
