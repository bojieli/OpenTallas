`timescale 1ns/1ps
module tb_qwen_link_forwarded_tmr_pair;
    parameter integer NL=1, NEG=0;
    localparam W=528;
    reg rst_n=1;
    reg [2*NL-1:0] clk=0;
    wire [2*NL-1:0] c1,c2;
    reg [NL*W-1:0] a=0,b=0;
    wire [NL*W-1:0] a1,b1,a2,b2,off_a,off_b;
    wire [NL-1:0] off_ab,off_ba;
    wire [NL-1:0] ab_clock=(NEG==1)?{NL{clk[0]}}:clk[NL-1:0];
    wire [NL*W-1:0] stage_a=(NEG==2)?b:a;
    ot_qwen_link_forwarded_tmr_pair dut(.rst_n(rst_n),.clk_ab(clk[0]),.clk_ba(NEG==1?clk[0]:clk[1]),
      .a_i(a),.b_i(b),.a_o(a2),.b_o(b2),.clk_ab_o(c2[0]),.clk_ba_o(c2[1]));
    assign c1={dut.ba_mid,dut.ab_mid};
    assign a1=dut.ba_data;assign b1=dut.ab_data;
    ot_qwen_die_link_fwd_full_tmr #(.NL(NL)) off(
      .rst_n(rst_n),.fclk_ab_i(clk[NL-1:0]),.fclk_ba_i(clk[2*NL-1:NL]),
      .fclk_ab_o(off_ab),.fclk_ba_o(off_ba),
      .a_i(a),.b_i(b),.a_o(off_a),.b_o(off_b));
    integer checks[0:2*NL-1];
    genvar g;
    generate for(g=0;g<2*NL;g=g+1) begin: stream
        integer count=0, j, edges=0;
        reg [W-1:0] expected1=0,expected2=0,sampled;
        wire [W-1:0] inp=(g<NL)?a[(g%NL)*W+:W]:b[(g%NL)*W+:W];
        wire [W-1:0] out1=(g<NL)?b1[(g%NL)*W+:W]:a1[(g%NL)*W+:W];
        wire [W-1:0] out2=(g<NL)?b2[(g%NL)*W+:W]:a2[(g%NL)*W+:W];
        initial begin checks[g]=0; #(1+g*0.7); forever #5 clk[g]=~clk[g]; end
        always @(clk[g] or c1[g] or c2[g]) begin
            #0.1;
            if(c1[g]!==clk[g] || c2[g]!==clk[g]) $fatal(1,"clock ownership mismatch");
        end
        always @(negedge clk[g]) begin
            count=count+1;
            // Independent, changing all bits; explicit final partial chunk.
            for(j=0;j<W;j=j+1)
                if(g<NL) a[(g%NL)*W+j]=((count*53+g*71+j*17)>>(j%9))&1;
                else b[(g%NL)*W+j]=((count*97+g*43+j*19)>>(j%7))&1;
        end
        always @(negedge rst_n) begin edges=0; expected1[15:0]=0; expected2[15:0]=0; end
        always @(posedge clk[g]) begin
            sampled=inp;
            expected2=expected1;
            expected1=sampled;
            if(!rst_n || edges<2) begin expected1[15:0]=0;expected2[15:0]=0;end
            if(rst_n) edges=edges+1;
            #0.1;
            if(out1[15:0]!==expected1[15:0] || out2[15:0]!==expected2[15:0])
                $fatal(1,"exact mismatch control reset/release stream=%0d edge=%0d",g,edges);
            if(count>1 && (out1!==expected1 || out2!==expected2))
                $fatal(1,"stream=%0d edge=%0d exact mismatch NEG=%0d",g,edges,NEG);
            if(c1[g]!==clk[g] || c2[g]!==clk[g]) $fatal(1,"clock ownership mismatch");
            checks[g]=checks[g]+1;
        end
    end endgenerate
    integer k,total;
    initial begin
        #0.2 rst_n=0;
        #12.1;
        for(k=0;k<NL;k=k+1)
            if(a1[k*W+:16]!==0 || b1[k*W+:16]!==0 || a2[k*W+:16]!==0 || b2[k*W+:16]!==0)
                $fatal(1,"cold reset controls");
        #3.4 rst_n=1;
        #10020;
        if(off_a!==0 || off_b!==0 || off_ab!==0 || off_ba!==0) $fatal(1,"default off");
        total=0;for(k=0;k<2*NL;k=k+1)total=total+checks[k];
        $display("PASS NL=%0d two-hop per-stream checks=%0d cold-reset release default-off",NL,total);
        $finish;
    end
endmodule
