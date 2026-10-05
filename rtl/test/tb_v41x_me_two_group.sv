`timescale 1ns/1ps
// Full-shape TP4 rank-0 wo_a activation contract: two independent 4096-term
// groups, one ME descriptor per group.  This tests the activation-store
// sequence, not the multiplier/reduction engine or whole-layer execution.
module tb_v41x_me_two_group;
    localparam MG=8, MP=1, G=4, KMAX=5120, NBW=14, EW=13, LANES=64, K=4096;
    reg clk=0;
    always #5 clk=~clk;
    reg wr_v=0;
    reg [$clog2(MP+1)-1:0] wr_p=0;
    reg [EW-1:0] wr_e=0;
    reg [G*16-1:0] wr_d=0;
    reg pre_v=0;
    reg [$clog2(MP+1)-1:0] pre_p=0;
    reg [EW-1:0] pre_e=0;
    reg [LANES*16-1:0] pre_d=0;
    reg [1:0] rd_rot=0;
    reg [7:0] rq_v=0;
    reg [8*NBW-1:0] rq_q=0;
    reg [8*4-1:0] rq_plg=0;
    wire [LANES*MP*16-1:0] rd_x;
    reg [15:0] input_data [0:2*K-1];
    reg [1023:0] data_path;
    integer group,e,w,q,c,l,errors=0,load_cycles=0,read_values=0;
    ot_hdc_v41x_me_xbank #(.MG(MG),.MP(MP),.G(G),.KMAX(KMAX),.NBW(NBW),.EW(EW)) dut(.*);
    initial begin
        if (!$value$plusargs("DATA=%s",data_path)) $fatal(1,"missing +DATA=fixture");
        $readmemh(data_path,input_data);
        for(group=0;group<2;group=group+1) begin
            // The same bank capacity is reused for the second output group.
            for(e=0;e<K;e=e+G) begin
                @(negedge clk); wr_v=1; wr_e=e;
                for(w=0;w<G;w=w+1) wr_d[w*16 +:16]=input_data[group*K+e+w];
                load_cycles=load_cycles+1;
            end
            @(negedge clk);wr_v=0;
            rq_v=8'hff;
            for(c=0;c<8;c=c+1) rq_plg[c*4 +:4]=3;
            for(q=0;q<K/LANES;q=q+1) begin
                @(negedge clk);
                for(c=0;c<8;c=c+1) rq_q[c*NBW +:NBW]=q;
                @(posedge clk);#1;
                for(l=0;l<LANES;l=l+1) begin
                    if(rd_x[l*16 +:16] !== input_data[group*K+q*LANES+l]) begin
                        if(errors<8) $display("ERR group=%0d q=%0d lane=%0d got=%h expected=%h",
                                             group,q,l,rd_x[l*16 +:16],input_data[group*K+q*LANES+l]);
                        errors=errors+1;
                    end
                    read_values=read_values+1;
                end
            end
            @(negedge clk);rq_v=0;
        end
        if(errors || load_cycles!=2048 || read_values!=8192)
            $fatal(1,"ME two-group failed errors=%0d load=%0d reads=%0d",errors,load_cycles,read_values);
        $display("ME_TWO_GROUP_PASS load_cycles=%0d reads=%0d errors=0",load_cycles,read_values);
        $finish;
    end
endmodule
