`timescale 1ns/1ps
module tb_hbm_smh_csnk_ne;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, sv=0, ready=0;
    reg [41:0] sd=0;
    wire sr, iv, ret0, ret1, v0, v1;
    wire [41:0] id, d0, d1;
    ot_hbm_accel_smh_csrc #(.W(42),.PS(2),.PR(1),.DEPTH(9)) src
        (.clk(clk),.rst_n(rst_n),.s_valid(sv),.s_ready(sr),.s_data(sd),.o_v(iv),.o_d(id),.i_ret(ret0));
    ot_hbm_accel_smh_csnk #(.W(42),.PK(1),.PRK(2),.DEPTH(9)) ref_fifo
        (.clk(clk),.rst_n(rst_n),.i_v(iv),.i_d(id),.o_ret(ret0),.m_valid(v0),.m_ready(ready),.m_data(d0));
    ot_hbm_accel_smh_csnk_ne #(.W(42),.PK(1),.PRK(2),.DEPTH(9)) dut
        (.clk(clk),.rst_n(rst_n),.i_v(iv),.i_d(id),.o_ret(ret1),.m_valid(v1),.m_ready(ready),.m_data(d1));
    reg [41:0] scoreboard[0:20000];
    integer wr=0,rd=0,cycles=0,accepted=0,delivered=0;
    integer empty=0,full=0,both=0,last_pop=0,wrap=0,resets=0;
    integer seed=314159,t;
    reg [31:0] rnd;
    always @(posedge clk) begin
        if (!rst_n) begin wr=0; rd=0; end
        else begin
            cycles=cycles+1;
            if (v0 !== v1 || ret0 !== ret1 || (v0 && d0 !== d1))
                $fatal(1,"equivalence failure cycle=%0d valid=%b/%b credit=%b/%b data=%h/%h",cycles,v0,v1,ret0,ret1,d0,d1);
            if (dut.nonempty !== (dut.cnt != 0))
                $fatal(1,"cached occupancy invariant failure cycle=%0d cnt=%0d",cycles,dut.cnt);
            if (sv && sr) begin scoreboard[wr]=sd; wr=wr+1; accepted=accepted+1; end
            if (v1 && ready) begin
                if (rd>=wr || d1 !== scoreboard[rd]) $fatal(1,"independent order/data failure at %0d",rd);
                rd=rd+1; delivered=delivered+1;
            end
            if (ref_fifo.cnt==0) empty=empty+1;
            if (ref_fifo.cnt==9) full=full+1;
            if (ref_fifo.f_v && ref_fifo.pop) both=both+1;
            if (ref_fifo.cnt==1 && ref_fifo.pop && !ref_fifo.f_v) last_pop=last_pop+1;
            if (ref_fifo.wp==8 && ref_fifo.f_v) wrap=wrap+1;
        end
    end
    initial begin
        repeat(3) @(negedge clk);
        rst_n=1;
        for(t=0;t<10000;t=t+1) begin
            @(negedge clk);
            if(t==4000) begin rst_n=0; sv=0; ready=0; resets=resets+1; end
            else if(t==4003) rst_n=1;
            if(rst_n) begin
                rnd=$random(seed);
                sd={rnd[9:0],32'(t)};
                if(t%512<100) begin sv=1;ready=0;end
                else if(t%512<180) begin sv=0;ready=1;end
                else if(t%512<300) begin sv=1;ready=1;end
                else begin sv=rnd[0];ready=rnd[1];end
            end
        end
        @(negedge clk);sv=0;ready=1;
        repeat(40) @(negedge clk);
        if(wr!=rd || !empty || !full || !both || !last_pop || !wrap || !resets)
            $fatal(1,"coverage/drain failure wr=%0d rd=%0d empty=%0d full=%0d both=%0d last=%0d wrap=%0d resets=%0d",wr,rd,empty,full,both,last_pop,wrap,resets);
        $display("PASS cycles=%0d accepted=%0d delivered=%0d empty=%0d full=%0d simultaneous=%0d last_pop=%0d wrap=%0d resets=%0d",cycles,accepted,delivered,empty,full,both,last_pop,wrap,resets);
        $finish;
    end
endmodule
