`timescale 1ns/1ps
module tb_hbm_su_ctl_c13_primitives;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;
    reg [15:0] a;
    reg [23:0] b;
    wire [23:0] product;
    reg [23:0] expected0,expected1;
    reg [189:0] data;
    reg valid;
    reg [6:0] select;
    wire [189:0] old_q,new_q;
    wire old_v,new_v,old_c,new_c,old_busy,new_busy;
    wire [189:0] old_delay,new_delay;
    localparam [111:0] DEPTHS={16'd152,16'd276,16'd35,16'd68,16'd121,16'd94,16'd0};
    ot_hdc_su_ctl_mul16 mul(.clk(clk),.a(a),.b(b),.y(product));
    ot_hdc_su_ctl_insert #(.LOCAL(0),.W(190),.K(7),.DEPTHS(DEPTHS),.DMAX(276)) old_insert(
        .clk(clk),.rst_n(rst_n),.v(valid),.sel(select),.d(data),.q(old_q),.vo(old_v),.coll(old_c),.busy(old_busy));
    ot_hdc_su_ctl_insert #(.LOCAL(1),.W(190),.K(7),.DEPTHS(DEPTHS),.DMAX(276)) new_insert(
        .clk(clk),.rst_n(rst_n),.v(valid),.sel(select),.d(data),.q(new_q),.vo(new_v),.coll(new_c),.busy(new_busy));
    ot_hdc_su_ctl_delay #(.LOCAL(0),.W(190),.D(8)) old_pipe(.clk(clk),.rst_n(rst_n),.d(data),.q(old_delay));
    ot_hdc_su_ctl_delay #(.LOCAL(1),.W(190),.D(8)) new_pipe(.clk(clk),.rst_n(rst_n),.d(data),.q(new_delay));
    integer i,j,checks=0;reg [31:0] rng=32'h913027af;
    function [31:0] next_random(input [31:0] x);
        reg[31:0] y;begin y=x^(x<<13);y=y^(y>>17);next_random=y^(y<<5);end
    endfunction
    initial begin
        a=0;b=0;data=0;valid=0;select=0;expected0=0;expected1=0;
        for(i=0;i<2400;i=i+1) begin
            @(negedge clk);
            rst_n=(i>2 && i!=800 && i!=1600);
            rng=next_random(rng);a=rng[15:0];rng=next_random(rng);b=rng[23:0];
            if(i<16)begin a=16'h1<<i;b=24'hffffff;end
            if(i==16)begin a=16'hffff;b=24'hffffff;end
            for(j=0;j<5;j=j+1)begin rng=next_random(rng);data[j*32+:32]=rng;end
            rng=next_random(rng);data[160+:30]=rng[29:0];
            rng=next_random(rng);valid=rng[0];select=7'b1<<(rng%7);
            expected1=expected0;expected0=a*b;
            @(posedge clk);#1;
            if(i>1 && product!==expected1)$fatal(1,"mul mismatch cycle %0d got %h want %h",i,product,expected1);
            if({old_v,old_c,old_busy}!={new_v,new_c,new_busy})$fatal(1,"identity mismatch cycle %0d",i);
            if(i>280 && old_q!==new_q)$fatal(1,"control data mismatch cycle %0d",i);
            if(i>8 && old_delay!==new_delay)$fatal(1,"return mismatch cycle %0d",i);
            checks=checks+1;
        end
        $display("PASS_C13_PRIMITIVES cycles=%0d W190 depth276 return8 modulo24 identity_collision_busy_reset_exact",checks);$finish;
    end
endmodule
