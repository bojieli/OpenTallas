// Minimum LOADED register-to-ETM-to-register physical vehicle.
// Producer is a kept sequential endpoint fixture, not an enclosing engine.
// There are no primary payload ports with fictional zero-network clocks.
// Actual tile source, macro ETMs, reset distribution and all34/head receivers
// are timed. No arithmetic correctness or enclosing-engine claim from this fixture.
module ot_attn_registered_parent_phys(input wire clk,input wire rst_n);
    (* keep="true",dont_touch="true" *) reg [1617:0] producer;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) producer <= {{1617{1'b0}},1'b1};
        else producer <= {producer[1616:0],producer[1617]^producer[127]^1'b1};
    wire lv,lmode,lw2v,v;
    wire [2:0] bank,operand_bank;
    wire [7:0] group_id;
    wire [1023:0] weight;
    wire [575:0] operand;
    assign {lv,lmode,bank,group_id,weight,lw2v,v,operand_bank,operand}=producer;
    (* keep="true" *) wire ov;
    (* keep="true" *) wire [511:0] oy;
    (* keep="true" *) wire [15:0] oflt;
    (* keep_hierarchy="true",dont_touch="true" *)
    ot_attn_tile_registered_parent #(.REGISTER_PARENT(1)) u_tile (
        .clk(clk),.rst_n(rst_n),.ld_v(lv),.ld_mode(lmode),.ld_bank(bank),
        .ld_grp(group_id),.ld_w(weight),.ld_w2v(lw2v),.iv(v),.ibank(operand_bank),
        .ib(operand),.ov(ov),.oy(oy),.oflt(oflt));
endmodule
