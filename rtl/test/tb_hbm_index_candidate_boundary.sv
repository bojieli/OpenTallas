`timescale 1ns/1ps
module tb_hbm_index_candidate_boundary;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, held_valid=0;
    reg [6:0] rank=0;
    reg [3:0] iv=0, il=0;
    reg [63:0] lv=0;
    reg [1023:0] val=0;
    reg [1279:0] idx=0;
    wire [3:0] ready, ov, ol, we, re;
    wire [7:0] olv;
    wire [135:0] oblk;
    wire [127:0] oval;
    wire [39:0] wa,ra;
    wire [271:0] wd;
    reg [271:0] rd=0;
    wire rep, overflow, busy;
    wire [131:0] stats;
    wire [31:0] job; wire [3:0] gen; wire [19:0] pos; wire [6:0] out_rank;
    reg [67:0] memory[0:4095];
    integer q,j;
    always @(posedge clk) for(integer t=0;t<4;t=t+1) begin
        if(we[t]) memory[t*1024+wa[10*t+:10]] <= wd[68*t+:68];
        if(re[t]) rd[68*t+:68] <= memory[t*1024+ra[10*t+:10]];
    end
    ot_hbm_accel_index_candidate #(.ENABLE(1)) dut(
        .clk(clk),.rst_n(rst_n),.held_valid(held_valid),.held_job(32'hfedc1234),
        .held_gen(4'hd),.held_pos(20'hfffff),.held_rank(rank),
        .out_job(job),.out_gen(gen),.out_pos(pos),.out_rank(out_rank),
        .in_valid(iv),.in_ready(ready),.in_last(il),.in_lv(lv),.in_val(val),.in_idx(idx),.in_k(12'd2048),
        .out_valid(ov),.out_ready(4'hf),.out_last(ol),.out_lv(olv),.out_blk(oblk),.out_val(oval),
        .mem_we(we),.mem_waddr(wa),.mem_wdata(wd),.mem_re(re),.mem_raddr(ra),.mem_rdata(rd),
        .rep_req(rep),.ovf(overflow),.busy(busy),.stats(stats));
    wire [3:0] disabled_ready, disabled_valid, disabled_we, disabled_re;
    wire disabled_busy;
    ot_hbm_accel_index_candidate disabled(
        .clk(clk),.rst_n(rst_n),.held_valid(1'b1),.held_job(32'h1),.held_gen(4'h1),.held_pos(20'hfffff),.held_rank(rank),
        .in_valid(4'hf),.in_last(4'hf),.in_lv(lv),.in_val(val),.in_idx(idx),.in_k(12'd2048),
        .in_ready(disabled_ready),.out_valid(disabled_valid),.out_ready(4'hf),.busy(disabled_busy),
        .mem_we(disabled_we),.mem_re(disabled_re),.mem_rdata(rd));
    task automatic run_case(input integer owner, input integer block_id, input bit empty, input integer expected);
        integer cycles, count; reg [3:0] sent, finished;
        begin
            @(negedge clk); rst_n=0; held_valid=0; iv=0; il=0;
            repeat(4) @(negedge clk);
            rank=owner; rst_n=1;
            if(ready!==0) $fatal(1,"score acceptance without actual held frame");
            @(negedge clk); held_valid=1; lv=0; val={64{16'hff80}}; idx=0;
            if(!empty) for(integer lane=0;lane<8;lane=lane+1) begin
                lv[48+lane]=1; idx[20*(48+lane)+:20]=block_id*8+lane;
            end
            sent=0; finished=0; count=0; cycles=0;
            while(finished!=4'hf) begin
                iv=~sent; il=4'hf;
                @(posedge clk);
                sent=sent|(iv&ready);
                for(integer quarter=0;quarter<4;quarter=quarter+1) if(ov[quarter]) begin
                    if(ol[quarter]) finished[quarter]=1;
                    for(integer lane=0;lane<2;lane=lane+1) if(olv[2*quarter+lane]) begin
                        count=count+1;
                        if(oblk[17*(2*quarter+lane)+:17]!==17'd131071)
                            $fatal(1,"candidate output lost literal global newest ID");
                        if(oval[16*(2*quarter+lane)+:16]!==16'h7f80)
                            $fatal(1,"candidate collective did not receive actual pinned maximum");
                    end
                end
                if(rep||overflow) $fatal(1,"unexpected retained-input replay/overflow");
                if(job!==32'hfedc1234||gen!==4'hd||pos!==20'hfffff||out_rank!==rank)
                    $fatal(1,"actual held tuple truncation");
                if(disabled_ready||disabled_valid||disabled_we||disabled_re||disabled_busy)
                    $fatal(1,"default-off accepted/driven transaction");
                cycles=cycles+1;
                if(cycles>4096) $fatal(1,"single-beat four-quarter publication failed to drain");
                @(negedge clk);
            end
            iv=0; il=0;
            if(count!=expected) $fatal(1,"rank%0d false/absent newest pin: got%0d expected%0d",owner,count,expected);
            $display("CANDIDATE_BOUNDARY rank=%0d empty=%0d cycles=%0d published=%0d",owner,empty,cycles,count);
        end
    endtask
    initial begin
        run_case(0,130944,0,0);
        run_case(31,131071,0,1);
        run_case(0,0,1,0);
        $display("PASS_HBM_INDEX_CANDIDATE_BOUNDARY"); $finish;
    end
endmodule
