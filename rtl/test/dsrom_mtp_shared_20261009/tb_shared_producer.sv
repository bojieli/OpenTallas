`timescale 1ns/1ps
module tb_shared_producer;
    reg clk=0;always #0.416667 clk=~clk;
    reg rst_n=0,cmd_valid=0,in_valid=0,out_ready=0;
    reg [73:0] cmd_context=0,in_context=0;
    reg [511:0] in_data=0;reg [6:0] in_word=0;
    reg in_last=0,in_fmt_fp32=0,in_error=0;
    wire cmd_ready,in_ready,out_valid,out_last,out_corrected,busy,fault;
    wire [511:0] out_data;wire [73:0] out_context;wire [6:0] out_word;
`ifdef SHARED_CE
    localparam [71:0] INJECT=72'd1;
`elsif SHARED_UE
    localparam [71:0] INJECT=72'd3;
`else
    localparam [71:0] INJECT=72'd0;
`endif
    ot_dsrom_mtp_shared_producer #(.READ_INJECT(INJECT)) dut(.*);
    integer frame=0,received=0,total=0,cyc=0,bad=0,start=0;
    reg [73:0] expected_context;
    function automatic [15:0] value(input integer row,f);
        value={((row+f)%2)!=0,8'(110+(row%30)),7'((row*17+f*31)%128)};
    endfunction
    always @(negedge clk)out_ready=(cyc%7!=2)&&(cyc%11!=4);
    always @(posedge clk)begin
        cyc<=cyc+1;
        if(out_valid&&out_ready)begin
            if(bad!=0)$fatal(1,"negative delivered output");
            if(out_context!==expected_context||out_word!==7'(received)||out_last!==(received==79))$fatal(1,"shared identity/order mismatch");
            for(integer j=0;j<16;j=j+1)
                if(out_data[32*j+:32]!=={value(16*received+j,frame),16'd0})$fatal(1,"shared widened value mismatch");
`ifdef SHARED_CE
            if(!out_corrected)$fatal(1,"CE not reported");
`endif
            received<=received+1;total<=total+1;
        end
    end
    initial begin
        if($value$plusargs("bad=%d",bad))begin end
        repeat(8)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);start=cyc;
        for(frame=0;frame<6;frame=frame+1)begin
            received=0;
            expected_context={3'(frame),2'(frame%4),2'(frame%3),4'(frame),21'(1048575-frame),10'(frame==5?865:frame),32'(100+frame)};
            wait(cmd_ready);@(negedge clk);cmd_valid=1;cmd_context=expected_context;
            @(negedge clk);cmd_valid=0;
            for(integer w=0;w<80;w=w+1)begin
                wait(in_ready);@(negedge clk);in_valid=1;in_context=expected_context;
                in_word=w;in_last=(w==79);
                for(integer j=0;j<16;j=j+1)in_data[32*j+:32]={value(16*w+j,frame),16'd0};
                if(w==17)begin
                    case(bad)
                        1:in_context[0]=~in_context[0];
                        2:in_word=16;
                        3:in_last=1;
                        4:in_fmt_fp32=1;
                        5:in_data[31:0]=32'h7f800000;
                        6:in_error=1;
                        8:in_data[0]=1;
                        7:force dut.context_n=74'd0;
                    endcase
                end
                @(negedge clk);in_valid=0;
                if(bad&&w==17)begin
                    repeat(8)@(negedge clk);
                    if(!fault||out_valid||cmd_ready||in_ready)$fatal(1,"negative escaped");
                    $display("SHARED_NEGATIVE PASS bad=%0d",bad);$finish;
                end
            end
`ifdef SHARED_UE
            repeat(12)@(negedge clk);
            if(!fault||out_valid)$fatal(1,"UE escaped");
            $display("SHARED_UE PASS");$finish;
`endif
            wait(received==80);@(negedge clk);
            if(fault||busy)$fatal(1,"shared retire fault");
        end
        $display("SHARED_PRODUCER PASS rows=1280 contexts=6 total_flits=%0d elapsed_cycles=%0d",total,cyc-start);$finish;
    end
endmodule
