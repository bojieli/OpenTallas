`timescale 1ns/1ps
// Two corrected TP4 wo_a groups through a 64-element BF16 prefetch ingress.
// The test supplies already rounded data, so VM four-bank selection and the
// FP32-to-BF16 converter are separate integration gates.
module tb_v41x_me_two_group_wide_inreg;
    localparam MG=8,MP=1,G=4,KMAX=5120,NBW=14,EW=13,LANES=64,K=4096;
    reg clk=0;
    always #5 clk=~clk;
    reg wr_v=0,pre_v=0;
    reg [$clog2(MP+1)-1:0] wr_p=0,pre_p=0;
    reg [EW-1:0] wr_e=0,pre_e=0;
    reg [G*16-1:0] wr_d=0;
    reg [LANES*16-1:0] pre_d=0;
    reg [1:0] rd_rot=2;
    reg [7:0] rq_v=0;
    reg [8*NBW-1:0] rq_q=0;
    reg [8*4-1:0] rq_plg=0;
    wire [LANES*MP*16-1:0] rd_x;
    reg [15:0] input_data [0:2*K-1];
    reg [1023:0] data_path;
    integer group,e,l,q,c,errors=0,preload_cycles=0,read_values=0;
    ot_hdc_v41x_me_xbank_macro_inreg #(.MG(MG),.MP(MP),.G(G),.KMAX(KMAX),.NBW(NBW),.EW(EW)) dut(.*);
    initial begin
        if (!$value$plusargs("DATA=%s",data_path)) $fatal(1,"missing +DATA=fixture");
        $readmemh(data_path,input_data);
        for(group=0;group<2;group=group+1) begin
            for(e=0;e<K;e=e+LANES) begin
                @(negedge clk);pre_v=1;pre_e=e;
                for(l=0;l<LANES;l=l+1)
                    pre_d[l*16 +:16]=input_data[group*K+e+((((l/16)-rd_rot)&3)*16)+(l%16)];
                preload_cycles=preload_cycles+1;
            end
            @(negedge clk);pre_v=0;rq_v=8'hff;
            for(c=0;c<8;c=c+1) rq_plg[c*4 +:4]=3;
            for(q=0;q<K/LANES;q=q+1) begin
                @(negedge clk);
                for(c=0;c<8;c=c+1) rq_q[c*NBW +:NBW]=q;
                @(posedge clk);#1;
                if (q>0)
                    for(l=0;l<LANES;l=l+1) begin
                        if(rd_x[l*16 +:16] !== input_data[group*K+(q-1)*LANES+l]) begin
                            if(errors<8) $display("ERR group=%0d q=%0d lane=%0d",group,q-1,l);
                            errors=errors+1;
                        end
                        read_values=read_values+1;
                    end
            end
            @(posedge clk);#1;
            for(l=0;l<LANES;l=l+1) begin
                if(rd_x[l*16 +:16] !== input_data[group*K+(K/LANES-1)*LANES+l]) begin
                    if(errors<8) $display("ERR group=%0d q=63 lane=%0d",group,l);
                    errors=errors+1;
                end
                read_values=read_values+1;
            end
            @(negedge clk);rq_v=0;
        end
        if(errors || preload_cycles!=128 || read_values!=8192)
            $fatal(1,"ME two-group wide failed errors=%0d preload=%0d reads=%0d",
                   errors,preload_cycles,read_values);
        $display("ME_TWO_GROUP_WIDE_INREG_PASS preload_cycles=%0d reads=%0d errors=0",preload_cycles,read_values);
        $finish;
    end
endmodule
