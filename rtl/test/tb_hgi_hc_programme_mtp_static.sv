`timescale 1ns/1ps
module tb_hgi_hc_programme_mtp_static(input wire clk);
    reg rst_n=0;
    integer cycle=0,errors=0,seen=0,words=1420;
    reg [255:0] image[0:2047];
    string filename;
    wire cfgwe=cycle>=5&&cycle<5+words;
    wire [10:0] address=11'(cycle-5);
    wire mutate=$test$plusargs("MUTANT");
    wire [255:0] data=image[address]^((mutate&&address==1024)?(256'd1<<233):256'd0);
    wire clear,launch,pop,slot,tl,sl,sc,active,done,fault;
    wire [4:0] row;
    wire [3:0] npos;
    wire [2:0] position;
    wire [31:0] eps;
    wire [50:0] c={position,npos,eps,sc,sl,tl,row,slot,pop,launch,clear};
    initial begin
        if($value$plusargs("WORDS=%d",words))begin end
        if(!$value$plusargs("IMAGE=%s",filename))filename="programme.mem";
        $readmemh(filename,image,0,words-1);
    end
    ot_hgi_hc_programme_mtp_static dut(.clk(clk),.rst_n(rst_n),.cfg_we(cfgwe),.cfg_addr(address),.cfg_data(data),
        .start_v(cycle==2048),.start_base(11'd0),.start_limit(12'(words)),.start_loops(16'd1),
        .clear(clear),.row_launch(launch),.row_raw_read(pop),.row_weight_slot(slot),.row_id(row),
        .tail_launch(tl),.sink_launch(sl),.sink_capture(sc),.norm_eps(eps),.row_npos(npos),.tail_position(position),
        .active(active),.done(done),.fault(fault));
    always @(posedge clk)begin
        cycle<=cycle+1;
        if(cycle==4)rst_n<=1;
        if(cycle>=2053&&cycle<2053+words)begin
            seen<=seen+1;
            if(c!==image[cycle-2053][50:0])begin errors=errors+1;$display("MTP_PROGRAMME_MISMATCH cycle%0d",cycle);end
        end
        if(fault)errors=errors+1;
        if(cycle==2053+words+4)begin
            $display("HC_MTP_PROGRAMME_DONE seen=%0d errors=%0d firstconsumer2053",seen,errors);
            if(seen!=words||errors)$fatal(1,"programme mismatch");
            $finish;
        end
    end
endmodule
