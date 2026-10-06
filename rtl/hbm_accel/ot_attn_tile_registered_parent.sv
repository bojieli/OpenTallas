// Retained instances prevent identical physical row/head banks being merged.
(* keep_hierarchy="true" *)
module ot_attn_parent_row_bank(input wire clk,input wire por_n,
    input wire [1617:0] d,output reg [1617:0] q);
    always @(posedge clk or negedge por_n)
        if(!por_n) q<=0; else q<=d;
endmodule

(* keep_hierarchy="true" *)
module ot_attn_parent_head_bank(input wire clk,input wire por_n,
    input wire [1617:0] d,output wire [1617:0] q,output reg local_por_n);
    // The native FF has QN. Keep the complement in state so the macro
    // receives the exact packet directly from QN rather than a loaded INV.
    reg [1617:0] q_n;
    reg data_por_n;
    // Release falling-edge data FFs from the opposite clock phase. Macro
    // and positive-edge output receivers retain their falling-edge release.
    always @(posedge clk or negedge por_n)
        if(!por_n) data_por_n<=0;else data_por_n<=1;
    always @(negedge clk or negedge por_n)
        if(!por_n) local_por_n<=0;else local_por_n<=1;
    always @(negedge clk or negedge data_por_n)
        if(!data_por_n) q_n<={1618{1'b1}};else q_n<=~d;
    assign q=~q_n;
endmodule

// Mandatory parent endpoint repair; canonical hardened head remains unchanged.
// Model: hbm_attn_registered_parent_model; REGISTER_PARENT is off by default.
module ot_attn_tile_registered_parent #(parameter REGISTER_PARENT=0) (
    input wire clk, input wire rst_n,
    input wire ld_v, input wire ld_mode, input wire [2:0] ld_bank,
    input wire [7:0] ld_grp, input wire [1023:0] ld_w,
    input wire ld_w2v, input wire iv, input wire [2:0] ibank,
    input wire [575:0] ib,
    output wire ov, output wire [511:0] oy, output wire [15:0] oflt
);
wire [1617:0] packet = {ld_v,ld_mode,ld_bank,ld_grp,ld_w,ld_w2v,iv,ibank,ib};
wire [15:0] gov;
generate if (!REGISTER_PARENT) begin : legacy
    ot_attn_tile_m6h1 u_tile (.clk(clk),.rst_n(rst_n),.ld_v(ld_v),.ld_mode(ld_mode),
        .ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_w2v(ld_w2v),
        .iv(iv),.ibank(ibank),.ib(ib),.ov(ov),.oy(oy),.oflt(oflt));
end else begin : registered_parent
    // Only root POR clears this boundary; CP warm reset must drain accepted work.
    (* async_reg="true", keep="true" *) reg [1:0] por_release;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) por_release <= 0;
        else por_release <= {por_release[0],1'b1};
    (* keep="true" *) reg [1617:0] launch;
    always @(posedge clk or negedge por_release[1])
        if (!por_release[1]) launch <= 0;
        else launch <= packet;
    for (genvar r=0;r<4;r=r+1) begin : row
        // Keep the four physical row branches, even though beats are identical.
        wire [1617:0] row_launch;
        (* keep="true",dont_touch="true",keep_hierarchy="true" *)
        ot_attn_parent_row_bank u_row_launch (.clk(clk),.por_n(por_release[1]),
            .d(launch),.q(row_launch));
        for (genvar c=0;c<4;c=c+1) begin : head
            localparam integer G=r*4+c;
            wire local_por_n;
            wire [1617:0] macro_launch;
            (* keep="true",dont_touch="true",keep_hierarchy="true" *)
            ot_attn_parent_head_bank u_macro_launch (.clk(clk),.por_n(por_release[1]),
                .d(row_launch),.q(macro_launch),.local_por_n(local_por_n));
            wire lv,lmode,lw2v,v;
            wire [2:0] bank,operand_bank;
            wire [7:0] group_id;
            wire [1023:0] weight;
            wire [575:0] operand;
            assign {lv,lmode,bank,group_id,weight,lw2v,v,operand_bank,operand}=macro_launch;
            wire hv,hf;
            wire [31:0] hy;
            ot_attn_hgrp_m6h1 u_g (.clk(clk),.rst_n(local_por_n),.gid(G[7:0]),
                .ld_v(lv),.ld_mode(lmode),.ld_bank(bank),.ld_grp(group_id),
                .ld_w(weight),.ld_w2v(lw2v),.iv(v),.ibank(operand_bank),.ib(operand),
                .ov(hv),.oy(hy),.oflt(hf));
            (* keep="true", dont_touch="true" *) reg [33:0] capture;
            always @(posedge clk or negedge local_por_n)
                if (!local_por_n) capture <= 0;
                else capture <= {hv,hf,hy};
            assign {gov[G],oflt[G],oy[G*32+:32]}=capture;
        end
    end
    assign ov=gov[0];
end endgenerate
endmodule
