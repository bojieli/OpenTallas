`timescale 1ns/1ps
module tb_hc_seed_join;
`ifdef HC_ECC_PIPE
    localparam integer EP=1;
`else
    localparam integer EP=0;
`endif
`ifdef HC_MACRO_CAP
    localparam integer MC=1;
`else
    localparam integer MC=0;
`endif
`ifdef HC_IN_SKID
    localparam integer IS=1;
`else
    localparam integer IS=0;
`endif
`ifdef HC_PLAIN_ROWS
    localparam integer PR=1;
`else
    localparam integer PR=0;
`endif
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,in_valid=0,out_ready=0;
    reg [511:0] in_data=0;reg [9:0] in_user=513;
    reg [20:0] in_position=1048575;reg [3:0] in_epoch=13;
    reg [1:0] in_capture=0;reg [5:0] in_frame=0;reg in_last=0;
    wire in_ready,out_valid,busy,fault,out_last,out_corrected;
    wire [511:0] out_data;wire [9:0] out_user;wire [20:0] out_position;
    wire [3:0] out_epoch;wire [1:0] out_capture;wire [5:0] out_frame;
`ifdef HC_INJECT_CE
    localparam [71:0] INJ=72'd1;
`elsif HC_INJECT_UE
    localparam [71:0] INJ=72'd3;
`else
    localparam [71:0] INJ=72'd0;
`endif
    ot_dsrom_hc_seed_join #(.ECC_PIPE(EP),.MACRO_CAP(MC),.IN_SKID(IS),.READ_INJECT(INJ)) u(.*);
    reg [511:0] expected[0:119];string idir;
    integer bad=0,reset_test=0,reset_done=0,phase,cap,f,nout=0,cycles=0,corrected=0;
    reg stalled=0;reg [511:0] held;
    initial begin
        if(!$value$plusargs("vectors=%s",idir)) $fatal(1,"missing vectors");
        if($value$plusargs("bad=%d",bad)) begin end
        if($value$plusargs("reset=%d",reset_test)) begin end
        $readmemh({idir,"/expected.hex"},expected);
        repeat(5) @(negedge clk);rst_n=1;
        for(phase=0;phase<3;phase=phase+1) begin
            cap=(phase==0)?2:(phase==1)?0:1;
            for(f=0;f<40;f=f+1) begin
                while(!in_ready) @(negedge clk);
                in_capture=(bad==1 && phase==0)?3:(bad==3&&phase==1)?2:cap;
                in_frame=(bad==2&&phase==0&&f==0)?1:f;
                in_last=(bad==5&&f==0)?1:(bad==6&&f==39)?0:f==39;
                in_data=expected[cap*40+f];
                if(bad==4&&phase==1) in_epoch=12;
                if(bad==7) in_position=1048576;
                in_valid=1;
                @(negedge clk);in_valid=0;
                if((bad==1||bad==2||bad==5||bad==7) ||
                   (bad==6&&f==39)||((bad==3||bad==4)&&phase==1)) begin
                    repeat(3) @(negedge clk);
                    if(!fault||out_valid||(phase==1&&!busy)) $fatal(1,"invalid joined frame escaped");
                    $display("PASS join negative %0d",bad);$finish;
                end
            end
            if(reset_test&&!reset_done) begin
                repeat(3) @(negedge clk);rst_n=0;
                repeat(3) @(negedge clk);
                if(busy||fault||out_valid||!in_ready) $fatal(1,"reset retained old validity");
                rst_n=1;in_epoch=14;reset_done=1;phase=-1;
            end
        end
        while(nout<120) @(negedge clk);
        repeat(3) @(negedge clk);
        if(fault||busy||!in_ready) $fatal(1,"joined ownership not retired");
`ifdef HC_INJECT_CE
        if(corrected!=120) $fatal(1,"join CE count");
`endif
        $display("PASS join120frames cycles=%0d CE=%0d reset=%0d",cycles,corrected,reset_test);$finish;
    end
    always @(negedge clk) begin
        cycles=cycles+1;out_ready=cycles%7!=0&&cycles%13!=0;
        if(cycles>4000) $fatal(1,"finite frame inventory exhausted");
`ifdef HC_INJECT_UE
        if(fault) begin
            if(nout||!busy||out_valid) $fatal(1,"join UE disclosed or lost ownership");
            $display("PASS join UE no disclosure retained ownership");$finish;
        end
`else
        if(fault&&bad==0) $fatal(1,"unexpected join fault");
`endif
    end
    always @(posedge clk) if(rst_n) begin
        if(stalled&&(!out_valid||out_data!==held)) $fatal(1,"join backpressure corrupted output");
        stalled=out_valid&&!out_ready;held=out_data;
        if(out_valid&&out_ready) begin
            if(out_data!==expected[nout] || out_capture!==nout/40 || out_frame!==nout%40 ||
               out_user!==513 || out_position!==1048575 || out_epoch!==in_epoch || out_last!==(nout==119))
                $fatal(1,"joined data/identity/order mismatch %0d",nout);
            nout=nout+1;corrected=corrected+out_corrected;
        end
    end
endmodule
