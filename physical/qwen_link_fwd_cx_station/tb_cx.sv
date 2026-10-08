`timescale 1ns/1ps
// Exact bench of the centre-aligned forwarded-clock link (two stations, both directions).
// Inputs launch on the rising edge (the upstream station's falling edge); s0 captures on the falling edge of the
// received clock, s1 on the falling edge of ~clk (= rising edge of clk). Checks every bit after every capture edge,
// clock ownership/polarity of both hops, cold-reset control clear, and TMR majority under single-rail faults:
// a rail stuck at 1 through reset must not release (rejects an OR vote), a rail stuck at 0 after release must not
// clear (rejects an AND vote). NEG=1 drives clk_ba from clk_ab (wrong clock ownership) and must fail.
module tb_qwen_link_fwd_cx;
    parameter integer NEG=0;
    localparam W=528;
    reg rst_n=1;
    reg [1:0] clk=0;
    reg [W-1:0] a=0,b=0;
    wire [W-1:0] a2,b2;
    wire c_ab2,c_ba2;
    reg checking=1;
    ot_qwen_link_fwd_cx_pair dut(.rst_n(rst_n),.clk_ab(clk[0]),.clk_ba(NEG==1?clk[0]:clk[1]),
      .a_i(a),.b_i(b),.a_o(a2),.b_o(b2),.clk_ab_o(c_ab2),.clk_ba_o(c_ba2));
    wire [1:0] c1={dut.ba_mid,dut.ab_mid}, c2={c_ba2,c_ab2};
    wire [W-1:0] out1_ab=dut.ab_data, out1_ba=dut.ba_data;
    integer checks[0:1];
    genvar g;
    generate for(g=0;g<2;g=g+1) begin: stream
        integer count=0,j,n0=0,n1=0;
        reg [W-1:0] m1=0,m2=0;          // model of station-0 and station-1 capture registers
        wire [W-1:0] inp =(g==0)?a:b;
        wire [W-1:0] out1=(g==0)?out1_ab:out1_ba;
        wire [W-1:0] out2=(g==0)?b2:a2;
        initial begin checks[g]=0; #(1+g*0.7); forever #5 clk[g]=~clk[g]; end
        always @(clk[g] or c1[g] or c2[g]) begin
            #0.1;
            if(c1[g]!==~clk[g] || c2[g]!==clk[g]) $fatal(1,"clock ownership/polarity mismatch stream=%0d",g);
        end
        // upstream launch on the rising edge: independent, changing bits
        always @(posedge clk[g]) begin
            count=count+1;
            for(j=0;j<W;j=j+1)
                if(g==0) a[j]=((count*53+j*17)>>(j%9))&1;
                else     b[j]=((count*97+43+j*19)>>(j%7))&1;
        end
        // reset model: a cold reset clears release chains; control clears until the third own capture edge
        always @(negedge rst_n) begin n0=0;n1=0;m1[15:0]=0;m2[15:0]=0; end
        always @(negedge clk[g]) begin          // station 0 capture edge
            m1[W-1:16]=inp[W-1:16];
            m1[15:0]=(rst_n && n0>=2)?inp[15:0]:16'd0;
            if(rst_n) n0=n0+1;
            #0.1;
            if(checking && count>1) begin
                if(out1!==m1) $fatal(1,"hop1 exact mismatch stream=%0d edge=%0d",g,n0);
                checks[g]=checks[g]+1;
            end
        end
        always @(posedge clk[g]) begin          // station 1 capture edge (falling edge of the forwarded ~clk)
            m2[W-1:16]=m1[W-1:16];
            m2[15:0]=(rst_n && n1>=2)?m1[15:0]:16'd0;
            if(rst_n) n1=n1+1;
            #0.1;
            if(checking && count>2) begin
                if(out2!==m2) $fatal(1,"hop2 exact mismatch stream=%0d edge=%0d",g,n1);
                checks[g]=checks[g]+1;
            end
        end
    end endgenerate
    integer k,total;
    initial begin
        #0.2 rst_n=0;
        #12.1;
        if(out1_ab[15:0]!==0 || out1_ba[15:0]!==0 || a2[15:0]!==0 || b2[15:0]!==0) $fatal(1,"cold reset controls");
        #3.4 rst_n=1;
        #3000;
        // single rail stuck at 0 after release: the 2-of-3 vote keeps the link released (AND vote would clear)
        force dut.s0.ab.release1=3'b011;
        force dut.s1.ba.release1=3'b101;
        #3000;
        if(out1_ab[15:0]===0 && a2[15:0]===0) $fatal(1,"degenerate stream controls");
        release dut.s0.ab.release1; release dut.s1.ba.release1;
        // single rail stuck at 1 through a cold reset: the vote must hold the controls cleared (OR vote would leak)
        checking=0;
        @(posedge clk[0]); #0.3;
        force dut.s0.ab.release1=3'b010;
        force dut.s1.ab.release1=3'b100;
        rst_n=0;
        for(k=0;k<20;k=k+1) begin
            @(negedge clk[0]); #0.2;
            if(out1_ab[15:0]!==0 || b2[15:0]!==0) $fatal(1,"TMR vote leaked control under reset with one stuck rail");
        end
        release dut.s0.ab.release1; release dut.s1.ab.release1;
        total=checks[0]+checks[1];
        if(total<1000) $fatal(1,"too few checks %0d",total);
        $display("PASS cx two-hop exact checks=%0d centre-aligned capture, inverted forward, TMR 2-of-3 under stuck rails",total);
        $finish;
    end
endmodule
