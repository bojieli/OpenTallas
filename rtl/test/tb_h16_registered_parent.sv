// Boundary mechanism surrogate: every input bit contributes; no leaf exact credit.
module ot_attn_hgrp_m6h1 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    gid,
    input  wire          ld_v,
    input  wire          ld_mode,
    input  wire [2:0]    ld_bank,
    input  wire [7:0]    ld_grp,
    input  wire [1023:0] ld_w,
    input  wire          ld_w2v,
    input  wire          iv,
    input  wire [2:0]    ibank,
    input  wire [575:0]  ib,
    output wire          ov,
    output wire [31:0]   oy,
    output wire [0:0]    oflt
);
reg qv,qf; reg [31:0] qy;
wire [1617:0] p={ld_v,ld_mode,ld_bank,ld_grp,ld_w,ld_w2v,iv,ibank,ib};
reg [31:0] hash; integer k;
always @* begin
    hash={24'b0,gid};
    for(k=0;k<1618;k=k+1) hash[k%32]=hash[k%32]^p[k];
end
always @(posedge clk or negedge rst_n)
    if(!rst_n) begin qv<=0;qf<=0;qy<=0;end
    else begin qv<=iv;qf<=ld_v^ld_w2v;qy<=hash;end
assign ov=qv;assign oy=qy;assign oflt=qf;
endmodule

module ot_attn_tile_m6h1 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          ld_v,
    input  wire          ld_mode,
    input  wire [2:0]    ld_bank,
    input  wire [7:0]    ld_grp,
    input  wire [1023:0] ld_w,
    input  wire          ld_w2v,
    input  wire          iv,
    input  wire [2:0]    ibank,
    input  wire [575:0]  ib,
    output wire          ov,
    output wire [511:0]  oy,
    output wire [15:0]   oflt
);
    wire [15:0] gov;
    genvar g;
    generate
        for (g = 0; g < 16; g = g + 1) begin : g_g
            ot_attn_hgrp_m6h1 u_g (
                .clk(clk), .rst_n(rst_n), .gid(g[7:0]), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank),
                .ld_grp(ld_grp), .ld_w(ld_w), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(gov[g]),
                .oy(oy[g*32 +: 32]), .oflt(oflt[g*1 +: 1]));
        end
    endgenerate
    assign ov = gov[0];
endmodule

module tb_h16_registered_parent;
reg clk=0; always #5 clk=~clk;
reg rst_n=0;
reg [1617:0] packet=0;
wire lv,lmode,lw2v,v;wire[2:0]bank,operand_bank;wire[7:0]group_id;
wire[1023:0]weight;wire[575:0]operand;
assign {lv,lmode,bank,group_id,weight,lw2v,v,operand_bank,operand}=packet;
wire rv,dv,legacy_v;wire[511:0]ry,dy,legacy_y;wire[15:0]rf,df,legacy_f;
`define PORTS .clk(clk),.rst_n(rst_n),.ld_v(lv),.ld_mode(lmode),.ld_bank(bank),.ld_grp(group_id),.ld_w(weight),.ld_w2v(lw2v),.iv(v),.ibank(operand_bank),.ib(operand)
ot_attn_tile_m6h1 reference (`PORTS,.ov(rv),.oy(ry),.oflt(rf));
ot_attn_tile_registered_parent #(.REGISTER_PARENT(1)) dut (`PORTS,.ov(dv),.oy(dy),.oflt(df));
ot_attn_tile_registered_parent default_off (`PORTS,.ov(legacy_v),.oy(legacy_y),.oflt(legacy_f));
reg[528:0] history[0:2];reg[1617:0] packet_history[0:1];
integer age=0,cycles=0,checks=0,j;
generate for(genvar r=0;r<4;r=r+1) begin:rows
    for(genvar c=0;c<4;c=c+1) begin:heads
        always @(posedge clk) if(rst_n && age>10)
            if(dut.registered_parent.row[r].head[c].macro_launch !== packet_history[1])
                $fatal(1,"head packet/order mismatch row%0d col%0d cycle%0d",r,c,cycles);
    end
end endgenerate
always @(posedge clk) begin
    cycles=cycles+1;
    if(!rst_n) begin age=0;for(j=0;j<3;j=j+1)history[j]=0;packet_history[0]=0;packet_history[1]=0;end
    else begin
        age=age+1;
        #1;
        if({legacy_v,legacy_f,legacy_y} !== {rv,rf,ry}) $fatal(1,"default OFF differs");
        if(age>10) begin
            if({dv,df,dy} !== history[2]) $fatal(1,"three-cycle output association mismatch cycle%0d",cycles);
            checks=checks+1;
        end
        history[2]=history[1];history[1]=history[0];history[0]={rv,rf,ry};
        packet_history[1]=packet_history[0];packet_history[0]=packet;
    end
end
initial begin
    repeat(3) @(negedge clk);#1 rst_n=1;
    for(integer n=0;n<2400;n=n+1) begin
        @(negedge clk);#1;
        for(integer i=0;i<51;i=i+1) begin
            if(i<50)packet[i*32+:32]=$random;else packet[1617:1600]=$random;
        end
        if(n%7==0)begin packet[1617]=0;packet[579]=0;end
        if(n==799 || n==1599)begin rst_n=0;#2;packet=0;repeat(3)@(negedge clk);#1 rst_n=1;end
    end
    repeat(6)@(negedge clk);
    $display("PASS boundary cycles=%0d checked=%0d H16 all-packet/all-output/default-OFF/POR",cycles,checks);$finish;
end
endmodule
