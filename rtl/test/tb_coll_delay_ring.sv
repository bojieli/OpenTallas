`timescale 1ns/1ps
module tb_coll_delay_ring;
    reg clk=0;
    always #0.416666 clk=~clk;
    reg rs_n=0,d=0;
    reg[31:0]rng=32'h3456bcde;
    integer cyc=0;
    wire[15:0]bad;
    localparam integer DEPTHS[0:15]='{0,1,2,3,4,5,16,17,18,31,32,33,65,351,371,378};
    for(genvar i=0;i<16;i=i+1)begin:g_depth
        wire ref_q,safe_q;
        ot_coll_dly1 #(.N(DEPTHS[i]))u_ref(.clk(clk),.rs_n(rs_n),.d(d),.q(ref_q));
        ot_coll_dly1 #(.N(DEPTHS[i]),.SAFE_RING(1))u_safe(.clk(clk),.rs_n(rs_n),.d(d),.q(safe_q));
        assign bad[i]=ref_q!==safe_q;
    end
    always @(negedge clk)begin
        rng<=rng^(rng<<13)^(rng>>17)^(rng<<5);
        d<=rng[0];
        rs_n<=!(cyc<4 || cyc==113 || cyc==114 || cyc==777 || cyc==1789 || cyc==1790);
    end
    always @(posedge clk)begin
        cyc=cyc+1;
        #0.001;
        if(cyc>1 && |bad)begin
            $display("COLL_DELAY_RING FAIL cycle %0d depths_bad %h",cyc,bad);
            $finish;
        end
        if(cyc==4096)begin
            $display("COLL_DELAY_RING PASS depths16 edges4096 repeated_reset exact");
            $finish;
        end
    end
endmodule
