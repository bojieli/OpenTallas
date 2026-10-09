`timescale 1ns/1ps
module tb_hc_mean_capture;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,cmd_valid=0,in_valid=0,out_ready=0;
    reg [1:0] cmd_capture=0;
    reg [9:0] cmd_user=10'd513;
    reg [20:0] cmd_position=21'd1048575;
    reg [3:0] cmd_epoch=4'd13;
    reg [7:0] in_beat=0;
    reg [511:0] in_residuals=0;
    wire cmd_ready,in_ready,out_valid,busy,fault,out_last,out_corrected;
    wire [511:0] out_data;
    wire [9:0] out_user;wire [20:0] out_position;wire [3:0] out_epoch;
    wire [1:0] out_capture;wire [5:0] out_frame;
`ifdef HC_MUT_TREE
    localparam integer MT=1;
`else
    localparam integer MT=0;
`endif
`ifdef HC_MUT_ALIAS
    localparam integer MA=1;
`else
    localparam integer MA=0;
`endif
`ifdef HC_INJECT_CE
    localparam [71:0] INJ=72'd1;
`elsif HC_INJECT_UE
    localparam [71:0] INJ=72'd3;
`else
    localparam [71:0] INJ=72'd0;
`endif
    ot_dsrom_hc_mean_capture #(.MUT_TREE(MT),.MUT_LAYER_ALIAS(MA),.READ_INJECT(INJ)) u(.*);
    reg [511:0] inputs[0:479],expected[0:119];
    string idir;
    integer bad=0,phase,cap,beat,nout=0,cycles=0,corrected=0;
    reg [511:0] held;reg stalled=0;
    initial begin
        if(!$value$plusargs("vectors=%s",idir)) $fatal(1,"missing vectors");
        if($value$plusargs("bad=%d",bad)) begin end
        $readmemh({idir,"/input.hex"},inputs);
        $readmemh({idir,"/expected.hex"},expected);
        repeat(5) @(negedge clk);rst_n=1;
        for(phase=0;phase<3;phase=phase+1) begin
            cap=(phase==0)?2:(phase==1)?0:1;
            @(negedge clk);while(!cmd_ready) @(negedge clk);
            cmd_capture=(bad==4 && phase==0)?3:cap;
            if(bad==1 && phase==1) cmd_epoch=12;
            if(bad==3 && phase==1) cmd_capture=2;
            cmd_valid=1;
            @(negedge clk);cmd_valid=0;
            if((bad==4 && phase==0)||((bad==1||bad==3)&&phase==1)) begin
                repeat(5) @(negedge clk);
                if(!fault||out_valid||!busy && bad!=4) $fatal(1,"bad command escaped");
                $display("PASS negative command %0d retained prior ownership",bad);$finish;
            end
            for(beat=0;beat<160;beat=beat+1) begin
                while(!in_ready) @(negedge clk);
                in_beat=(bad==2 && beat==1)?3:beat;
                in_residuals=inputs[cap*160+beat];
                if(bad==5 && beat==0) in_residuals[15:0]=16'h7fc0;
                in_valid=1;
                @(negedge clk);in_valid=0;
                if((bad==2 && beat==1)||(bad==5 && beat==0)) begin
                    repeat(20) @(negedge clk);
                    if(!fault||out_valid||!busy) $fatal(1,"bad beat escaped");
                    $display("PASS negative beat %0d retained ownership",bad);$finish;
                end
            end
        end
        while(nout<120) @(negedge clk);
        repeat(3) @(negedge clk);
        if(fault||busy||!cmd_ready) $fatal(1,"final ownership failed to drain");
`ifdef HC_INJECT_CE
        if(corrected!=120) $fatal(1,"correction count");
`endif
        $display("PASS full shape 3x1280 BF16 means 120 flits cycles=%0d CE=%0d",cycles,corrected);
        $finish;
    end
    always @(negedge clk) begin
        cycles=cycles+1;
        if(cycles>40000) $fatal(1,"finite test inventory exhausted");
        out_ready=(cycles%7!=0)&&(cycles%11!=0);
`ifdef HC_INJECT_UE
        if(fault) begin
            if(nout!=0||!busy||out_valid) $fatal(1,"UE disclosed data or lost ownership");
            $display("PASS UE retained ownership and delivered no data");$finish;
        end
`else
        if(fault && bad==0) $fatal(1,"unexpected fault");
`endif
    end
    always @(posedge clk) if(rst_n) begin
        if(stalled && (!out_valid || out_data!==held)) $fatal(1,"output changed under backpressure");
        stalled=out_valid&&!out_ready;held=out_data;
        if(out_valid&&out_ready) begin
            if(out_capture!==nout/40 || out_frame!==nout%40 ||
               out_user!==10'd513 || out_position!==21'd1048575 || out_epoch!==4'd13 ||
               out_last!==(nout==119) || out_data!==expected[nout])
                $fatal(1,"mean/identity/order mismatch frame %0d got=%h expected=%h",nout,out_data,expected[nout]);
            nout=nout+1;corrected=corrected+out_corrected;
        end
    end
endmodule
