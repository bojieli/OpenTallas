`timescale 1ns/1ps
// Minimum full-shape mechanism: 24 columns, 192 beats, eight slots. Complete
// all data before delivering any status, then delay the final poison status.
module tb_dsrom_engram_status_order;
    reg ck=0; always #5 ck=~ck;
    reg rst_n=0;
    reg [3:0] iv=0, sv=0, sb=0;
    wire [3:0] ir;
    reg [19:0] col=0;
    reg [11:0] beat=0, slot=0, ss=0;
    reg [1055:0] data=0;
    wire we; wire [10:0] wa; wire [511:0] wd;
    wire [7:0] ready, poison;
    reg rel=0; integer n,writes=0,cycles=0;
    ot_dsrom_engram_rowsink #(.NSRC(4),.NC(24),.NSLOT(8)) dut(
        .clk(ck),.rst_n(rst_n),.in_valid(iv),.in_ready(ir),.in_col(col),.in_beat(beat),.in_slot(slot),.in_data(data),
        .st_valid(sv),.st_slot(ss),.st_bad(sb),.wr_en(we),.wr_addr(wa),.wr_data(wd),.rdy(ready),.perr(poison),
        .rel_valid(rel),.rel_slot(3'd0));
    always @(negedge ck) if(rst_n) begin
        cycles=cycles+1;
        if(cycles>2000) $fatal(1,"status-order component did not drain");
        if(we) begin
            if(wa!==writes || wd!==0) $fatal(1,"wrong write address/data");
            writes=writes+1;
        end
    end
    initial begin
        repeat(3) @(negedge ck);rst_n=1;
        for(n=0;n<192;n=n+1) begin
            @(posedge ck);#1;
            while(!ir[0]) begin @(posedge ck);#1;end
            col[4:0]=n/8;beat[2:0]=n%8; data[263:256]=127;iv=1;
            @(posedge ck);#1;iv=0;
        end
        repeat(8) @(posedge ck);
        if(writes!=192) $fatal(1,"not all beats written");
        if(ready[0]) $fatal(1,"premature ready before delayed statuses");
        for(n=0;n<23;n=n+1) begin
            @(posedge ck);#1;sv=1;
            @(posedge ck);#1;sv=0;
        end
        repeat(8) @(posedge ck);
        if(ready[0]) $fatal(1,"premature ready before final status");
        @(posedge ck);#1;sv=1;sb=1;
        @(posedge ck);#1;sv=0;sb=0;
        repeat(4) @(posedge ck);
        if(!ready[0] || !poison[0]) $fatal(1,"late poison status not visible");
        @(posedge ck);#1;rel=1;
        @(posedge ck);#1;rel=0;
        repeat(3) @(posedge ck);
        if(ready[0] || poison[0]) $fatal(1,"release did not clear slot");
        $display("ENGRAM_STATUS PASS beats=192 statuses=24 delayed=1 poison=1 release=1");$finish;
    end
endmodule
