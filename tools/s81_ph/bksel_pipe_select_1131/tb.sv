`timescale 1ps/1fs
module tb;
    parameter integer QW=11, XR=6;
    localparam integer Q=4, CB=11, GW=15, XW=21, OBS=4+8+XW+1+Q*CB;
    reg clk=0;
    always #416.5 clk=~clk;
    reg [Q*16*GW-1:0] gs=0;
    reg [Q*16*CB-1:0] bs=0;
    reg [QW-1:0] q=0;
    wire [3:0] go[0:3];
    wire [7:0] rb[0:3];
    wire [XW-1:0] ra[0:3];
    wire ro[0:3];
    wire [Q*CB-1:0] re[0:3];
    wire [OBS-1:0] obs[0:3];
    su_original #(.Q(Q),.CB(CB),.QW(QW),.XR(XR)) u0
      (.clk(clk),.gs(gs),.bs(bs),.q(q),.g_out(go[0]),.res_b(rb[0]),.res_above(ra[0]),.res_ok(ro[0]),.res_eq(re[0]));
    su_r1 #(.Q(Q),.CB(CB),.QW(QW),.XR(XR)) u1
      (.clk(clk),.gs(gs),.bs(bs),.q(q),.g_out(go[1]),.res_b(rb[1]),.res_above(ra[1]),.res_ok(ro[1]),.res_eq(re[1]));
    su_r2 #(.Q(Q),.CB(CB),.QW(QW),.XR(XR)) u2
      (.clk(clk),.gs(gs),.bs(bs),.q(q),.g_out(go[2]),.res_b(rb[2]),.res_above(ra[2]),.res_ok(ro[2]),.res_eq(re[2]));
    su_mutant #(.Q(Q),.CB(CB),.QW(QW),.XR(XR)) um
      (.clk(clk),.gs(gs),.bs(bs),.q(q),.g_out(go[3]),.res_b(rb[3]),.res_above(ra[3]),.res_ok(ro[3]),.res_eq(re[3]));
    for (genvar j=0;j<4;j=j+1) begin
        assign obs[j]={go[j],rb[j],ra[j],ro[j],re[j]};
    end
    reg [31:0] seed=32'h672af50d;
    function automatic [31:0] advance(input [31:0] x0);
        reg [31:0] x;
        begin x=x0^(x0<<13);x=x^(x>>17);advance=x^(x<<5);end
    endfunction
    integer edge_id,j,s,k,b,errors=0,checks=0,mutant_errors=0,none_seen=0;
    reg [15:0] bucket_seen=0;
    initial begin
        // No reset exists in this module. Flush its real datapath, including XR, before comparing.
        repeat(64) @(negedge clk);
        for(edge_id=0;edge_id<4096;edge_id=edge_id+1) begin
            gs=0;bs=0;q=1;
            if(edge_id<512) begin
                // A new search every edge: visit every bucket with nonzero, distinct counts.
                b=(edge_id%2==0)?15:((edge_id/2)%15);
                for(s=0;s<Q;s=s+1) bs[CB*(16*s+b)+:CB]=s+1;
            end else if(edge_id<640) begin
                // No qualifying bucket, zero quota, high quota and full-width counters.
                case(edge_id%4)
                  0:begin gs=0;bs={Q*16*CB{1'b1}};q=0;end
                  1:begin gs=0;bs=0;q={QW{1'b1}};end
                  2:begin gs={Q*16*GW{1'b1}};bs={Q*16*CB{1'b1}};q={QW{1'b1}};end
                  3:begin gs=0;bs=0;q=0;end
                endcase
            end else begin
                // Independently changing actual gs/bs/quota interfaces; no forced internal state.
                for(j=0;j<Q*16;j=j+1) begin
                    seed=advance(seed);gs[GW*j+:GW]=seed&127;
                    seed=advance(seed);bs[CB*j+:CB]=seed&63;
                end
                seed=advance(seed);q=seed%4096;
            end
            @(posedge clk);#1;
            checks=checks+2;
            if((^obs[0])===1'bx) begin
                $display("FAIL reference unknown edge=%0d QW=%0d XR=%0d",edge_id,QW,XR);errors=errors+1;
            end
            if(obs[1]!==obs[0] || obs[2]!==obs[0]) begin
                if(errors<4)$display("FAIL edge=%0d QW=%0d ref=%h R1=%h R2=%h",edge_id,QW,obs[0],obs[1],obs[2]);
                errors=errors+1;
            end
            if(obs[3]!==obs[0]) begin
                if(mutant_errors==0)$display("MUTANT_CAUGHT edge=%0d QW=%0d bucket=%h above_ref=%h above_stale=%h",edge_id,QW,rb[0],ra[0],ra[3]);
                mutant_errors=mutant_errors+1;
            end
            if(ro[0])bucket_seen[rb[0][3:0]]=1'b1;else none_seen=none_seen+1;
            @(negedge clk);
        end
        $display("RESULT QW=%0d XR=%0d edges=4096 checks=%0d errors=%0d mutant_errors=%0d buckets=%h no_qualify=%0d clock_ps=833",QW,XR,checks,errors,mutant_errors,bucket_seen,none_seen);
        if(errors!=0 || mutant_errors==0 || bucket_seen!==16'hffff || none_seen==0)$fatal(1,"mechanism gate failed");
        $display("BKSEL_PIPE_LOCKSTEP_PASS");$finish;
    end
endmodule
