`timescale 1ns/1ps
module tb_v41x_me_xbank;
    localparam MG=8, MP=2, G=4, KMAX=5120, NBW=14, EW=13, LANES=8*MG;
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
    ot_hdc_v41x_me_xbank #(.MG(MG),.MP(MP),.G(G),.KMAX(KMAX),.NBW(NBW),.EW(EW)) dut(.*);
    integer p,e,w,c,l,t,plg,q,k,errors=0;
    reg [15:0] expected_data;
    reg [15:0] real_data [0:MP*KMAX-1];
    reg [1023:0] real_path;
    reg use_real=0;
    function automatic [15:0] datum(input integer pos,input integer idx);
        datum=use_real ? real_data[pos*KMAX+idx] : ((idx*137+pos*2789) & 16'hffff);
    endfunction
    initial begin
        if ($value$plusargs("ME_DATA=%s",real_path)) begin
            $readmemh(real_path,real_data);
            use_real=1;
        end
        // Fill both real full-shape activation vectors, four VM elements/cycle.
        for (p=0;p<MP;p=p+1)
            for (e=0;e<KMAX;e=e+G) begin
                @(negedge clk);
                wr_v=1; wr_p=p; wr_e=e;
                for(w=0;w<G;w=w+1) wr_d[w*16 +:16]=datum(p,e+w);
            end
        @(negedge clk); wr_v=0;
        // Mixed plg and beat values on the eight skewed request buses.
        for (t=0;t<1000;t=t+1) begin
            @(negedge clk);
            rq_v=8'hff;
            for(c=0;c<8;c=c+1) begin
                plg=1+((t+c)%3);
                q=(t*17+c*23)%(KMAX/(8<<plg));
                rq_plg[c*4 +:4]=plg;
                rq_q[c*NBW +:NBW]=q;
            end
            @(posedge clk); #1;
            for(l=0;l<LANES;l=l+1) begin
                c=l%8;
                plg=rq_plg[c*4 +:4]; q=rq_q[c*NBW +:NBW];
                k=q*(8<<plg)+(l&((8<<plg)-1));
                for(p=0;p<MP;p=p+1) begin
                    expected_data=datum(p,k);
                    if(rd_x[(l*MP+p)*16 +:16] !== expected_data) begin
                        if (errors < 8)
                        $display("ERR t=%0d lane=%0d p=%0d k=%0d got=%h exp=%h",t,l,p,k,
                                 rd_x[(l*MP+p)*16 +:16],expected_data);
                        errors=errors+1;
                    end
                end
            end
        end
        if(errors) $fatal(1,"ME xbank errors=%0d",errors);
        $display("ME_XBANK_PASS kmax=%0d lanes=%0d mp=%0d reads=%0d errors=0",KMAX,LANES,MP,1000*LANES*MP);
        $finish;
    end
endmodule
