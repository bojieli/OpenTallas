`timescale 1ns/1ps
module tb_qwen_xline_delivery;
    parameter integer MUT=0;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, load_v=0, exec_v=0;
    reg [8:0] load_id=0;
    reg [127:0] load_x=0;
    reg [378:0] exec_ib=0;
    wire [507:0] root;
    ot_qwen_xline_pack enc(load_v,load_id,load_x,exec_v,exec_ib,root);
    function automatic [127:0] pattern(input integer epoch,input integer line);
        pattern={32'h1234a987 ^ line, 32'hffeeddcc ^ epoch, 32'ha55aa55a ^ (line*32'd7919),32'h13572468 ^ (epoch*32'd811+line)};
    endfunction
    integer epoch=0, edge_count=0, checks=0;
    integer errors=0;
    integer launch_edge=0;
    always @(posedge clk) edge_count <= edge_count+1;
    genvar t,d;
    wire [507:0] pipe[0:31]; assign pipe[0]=root;
    generate for(d=0;d<31;d=d+1) begin:g_path
        ot_qwen_die_station #(.TAP(0)) st(.clk(clk),.rst_n(rst_n),.a_d(pipe[d]),.a_r(),.b_d(pipe[d+1]),.b_r(1'b1),.t_d(),.t_r(1'b1),.c_d(),.c_r(1'b1));
    end
    for(t=0;t<768;t=t+1) begin:g_tile
        // All 768 tile IDs observe real station paths; equal-depth tiles share
        // the path model to avoid duplicating identical wire/station behavior.
        localparam integer DEP=1+t%31;
        wire go,f; wire [127:0] xl; wire [378:0] ib;
        ot_qwen_xline_capture #(.MUT_IGNORE_ID(MUT)) cap(.clk(clk),.rst_n(rst_n),.tile_id(16'(t)),.word(pipe[DEP]),.ib_go(go),.ib(ib),.xl(xl),.fault(f));
        always @(posedge clk) if(rst_n && go) begin
            if(xl !== pattern(epoch,t%512)) $fatal(1,"wrong distinct line t=%0d got=%h wanted=%h",t,xl,pattern(epoch,t%512));
            if(ib !== exec_ib) $fatal(1,"instruction corruption t=%0d",t);
            if(edge_count-launch_edge !== DEP+512) $fatal(1,"cycle mismatch t=%0d latency=%0d expected=%0d",t,edge_count-launch_edge,DEP+512);
            if(f) $fatal(1,"unexpected capture fault t=%0d",t);
            checks=checks+1;
        end
    end endgenerate
    // Dedicated endpoint exercises missing / malformed line, reset, consumption.
    reg [507:0] badword=0;
    wire badgo,badfault;
    ot_qwen_xline_capture errcap(.clk(clk),.rst_n(rst_n),.tile_id(16'd37),.word(badword),.ib_go(badgo),.ib(),.xl(),.fault(badfault));
    integer k, e;
    initial begin
        repeat(3) @(negedge clk); rst_n=1;
        badword=508'b1; @(negedge clk);
        if(badgo || !badfault) $fatal(1,"missing line not rejected");
        rst_n=0; badword=0; @(negedge clk); rst_n=1;
        badword[379]=1; badword[10]=1; @(negedge clk);
        if(!badfault) $fatal(1,"noncanonical load not rejected");
        rst_n=0; badword=0; @(negedge clk); rst_n=1;
        for(e=1;e<=2;e=e+1) begin
            epoch=e; exec_ib={379{1'b1}} ^ e;
            launch_edge=edge_count;
            for(k=0;k<512;k=k+1) begin
                load_v=1; load_id=k; load_x=pattern(e,k);
                @(negedge clk);
            end
            load_v=0; exec_v=1; @(negedge clk); exec_v=0;
            repeat(34) @(negedge clk);
            if(checks!=768*e) $fatal(1,"missing executions got=%0d wanted=%0d",checks,768*e);
        end
        // Replay EXEC without loading: each endpoint must reject stale x.
        exec_v=1; @(negedge clk); exec_v=0;
        repeat(34) @(negedge clk);
        if(checks!=1536) $fatal(1,"stale x consumed");
        $display("PASS distinct-lines=512 tiles=768 epochs=2 executions=%0d stream_edges=512 capture_extra_edges=0 paths=1..31 tail_latency_edges=543",checks);
        $finish;
    end
endmodule
