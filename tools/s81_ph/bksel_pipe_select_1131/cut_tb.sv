`timescale 1ps/1fs
module cut_tb;
    parameter integer QW=11, MODE=0;
    localparam integer XW=21, OW=4+XW+QW+4+1;
    reg clk=0;
    always #416.5 clk=~clk;
    reg [16*XW-1:0] u=0;
    reg [QW-1:0] q=0;
    reg [XW-1:0] acc=0;
    reg [3:0] tag=0;
    wire [3:0] sel[0:3], date[0:3];
    wire [XW-1:0] above[0:3];
    wire [QW-1:0] quota[0:3];
    wire valid[0:3];
    wire [OW-1:0] obs[0:3];
    cut_ref #(.QW(QW)) r0(.clk(clk),.u(u),.q(q),.acc(acc),.tag(tag),.sel(sel[0]),.above(above[0]),.quota(quota[0]),.date(date[0]),.valid(valid[0]));
    cut_r1 #(.QW(QW)) r1(.clk(clk),.u(u),.q(q),.acc(acc),.tag(tag),.sel(sel[1]),.above(above[1]),.quota(quota[1]),.date(date[1]),.valid(valid[1]));
    cut_r2 #(.QW(QW)) r2(.clk(clk),.u(u),.q(q),.acc(acc),.tag(tag),.sel(sel[2]),.above(above[2]),.quota(quota[2]),.date(date[2]),.valid(valid[2]));
    cut_mut #(.QW(QW)) rm(.clk(clk),.u(u),.q(q),.acc(acc),.tag(tag),.sel(sel[3]),.above(above[3]),.quota(quota[3]),.date(date[3]),.valid(valid[3]));
    for(genvar k=0;k<4;k=k+1)assign obs[k]={sel[k],above[k],quota[k],date[k],valid[k]};
    reg [31:0] seed=32'hc6a172e5;
    function automatic [31:0] next_seed(input [31:0] z);
        reg [31:0] x;
        begin x=z^(z<<13);x=x^(x>>17);next_seed=x^(x<<5);end
    endfunction
    function automatic [3:0] highest(input [15:0] m);
        integer k;begin highest=0;for(k=0;k<16;k=k+1)if(m[k])highest=k;end
    endfunction
    reg [65535:0] seen=0;
    reg [15:0] mask, last_mask=16'hffff;
    reg [16*XW-1:0] last_u=0;
    reg [QW-1:0] last_q=0;
    reg [XW-1:0] last_acc=0, expected_above;
    reg [3:0] last_tag=0, expected_sel;
    integer i,j,iv,qv,errors=0,checks=0,mutants=0,seen_count=0,none_count=0;
    initial begin
        repeat(4)@(negedge clk);
        for(i=0;i<65538;i=i+1)begin
            mask=i*32'd40503+32'd19;seed=next_seed(seed);qv=31+(seed%((1<<QW)-63));q=qv;
            for(j=0;j<16;j=j+1)begin
                seed=next_seed(seed);
                if(mask[j])iv=qv+1+(seed%((1<<XW)-qv-1));else iv=seed%qv;
                u[XW*j+:XW]=iv;
            end
            seed=next_seed(seed);acc=seed;tag=i[3:0];
            @(posedge clk);#1;
            expected_sel=highest(last_mask);
            expected_above=(expected_sel==15)?((MODE==0)?0:last_acc):last_u[XW*(expected_sel+1)+:XW];
            if(sel[0]!==expected_sel || above[0]!==expected_above ||
               (MODE==0 && quota[0]!==last_q) || (MODE==1 && date[0]!==last_tag) ||
               (MODE==1 && valid[0]!== (|last_mask)))begin
                if(errors<4)$display("CUT_ORACLE_FAIL mode=%0d qw=%0d edge=%0d mask=%h sel=%h expected=%h above=%h expected=%h",MODE,QW,i,last_mask,sel[0],expected_sel,above[0],expected_above);
                errors=errors+1;
            end
            checks=checks+2;
            if(obs[1]!==obs[0] || obs[2]!==obs[0])begin
                if(errors<4)$display("CUT_MISMATCH mode=%0d qw=%0d edge=%0d ref=%h r1=%h r2=%h",MODE,QW,i,obs[0],obs[1],obs[2]);
                errors=errors+1;
            end
            if(obs[3]!==obs[0])begin
                if(mutants==0)$display("CUT_MUTANT_CAUGHT mode=%0d qw=%0d edge=%0d mask=%h ref=%h stale=%h",MODE,QW,i,last_mask,obs[0],obs[3]);
                mutants=mutants+1;
            end
            if(!seen[last_mask])begin seen[last_mask]=1;seen_count=seen_count+1;end
            if(last_mask==0)none_count=none_count+1;
            last_mask=mask;last_u=u;last_q=q;last_acc=acc;last_tag=tag;
            @(negedge clk);
        end
        $display("CUT_RESULT mode=%0d qw=%0d xw=21 edges=65538 checks=%0d errors=%0d masks=%0d mutant_errors=%0d no_qualify=%0d clock_ps=833",MODE,QW,checks,errors,seen_count,mutants,none_count);
        if(errors!=0 || seen_count!=65536 || mutants==0 || none_count==0)$fatal(1,"selector cut gate failed");
        $display("BKSEL_SELECTOR_CUT_PASS");$finish;
    end
endmodule
