`timescale 1ns/1ps
// Full TR16/TW17/PW32/NG4 component, common input trace, different output latencies.
module tb_hist_pipeline_latency;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,n_set=0,tw_v=0,rd_v=0;
    reg [31:0] n_val=0,tw_pos=0,rd_pos=0;
    reg [16:0] tw_tok=0;
    wire ro,rp,vo,vp,po,pp,lo,lp,eo,ep;
    wire [16:0] to,tp;
    ot_mtp_hist_ring old_dut(.clk(clk),.rst_n(rst_n),.n_set(n_set),.n_val(n_val),.tw_v(tw_v),.tw_pos(tw_pos),.tw_tok(tw_tok),.rd_v(rd_v),.rd_ready(ro),.rd_pos(rd_pos),.h_v(vo),.h_tok(to),.h_pad(po),.h_last(lo),.err(eo));
    ot_mtp_hist_ring_p new_dut(.clk(clk),.rst_n(rst_n),.n_set(n_set),.n_val(n_val),.tw_v(tw_v),.tw_pos(tw_pos),.tw_tok(tw_tok),.rd_v(rd_v),.rd_ready(rp),.rd_pos(rd_pos),.h_v(vp),.h_tok(tp),.h_pad(pp),.h_last(lp),.err(ep));
    function automatic [16:0] token(input integer pos);token=(pos*31337)^17'h1a36f;endfunction
    integer cycles=0,accepted=0,current=0,oc=0,pc=0,ol=0,pl=0,i;
    always @(posedge clk) begin
        cycles=cycles+1;
        if(rst_n && rd_v) begin
            if(!(ro&&rp)) $fatal(1,"read offered before both ready");
            accepted=cycles;
        end
        #1;
        if(rst_n && vo) begin
            if(oc==0) begin ol=cycles-accepted;if(ol!=1)$fatal(1,"old first latency %0d",ol);end
            if(po !== (current<oc) || to !== ((current<oc)?17'b0:token(current-oc)) || lo !== (oc==3))$fatal(1,"old stream p%0d k%0d",current,oc);
            oc=oc+1;
        end
        if(rst_n && vp) begin
            if(pc==0) begin pl=cycles-accepted;if(pl!=3)$fatal(1,"new first latency %0d",pl);end
            if(pp !== (current<pc) || tp !== ((current<pc)?17'b0:token(current-pc)) || lp !== (pc==3))$fatal(1,"new stream p%0d k%0d",current,pc);
            pc=pc+1;
        end
        if(rst_n && (eo||ep))$fatal(1,"unexpected sticky error");
    end
    initial begin
        repeat(3)@(negedge clk);rst_n=1;
        for(i=0;i<40;i=i+1)begin
            @(negedge clk);n_set=1;n_val=i;tw_v=1;tw_pos=i;tw_tok=token(i);
            @(negedge clk);n_set=0;tw_v=0;rd_v=1;rd_pos=i;current=i;oc=0;pc=0;
            @(negedge clk);rd_v=0;
            while(oc<4||pc<4)@(negedge clk);
        end
        $display("RESULT PASS positions=40 outputs_per_dut=160 old_first_cycles=%0d new_first_cycles=%0d added_read_cycles=%0d",ol,pl,pl-ol);
        $finish;
    end
endmodule
