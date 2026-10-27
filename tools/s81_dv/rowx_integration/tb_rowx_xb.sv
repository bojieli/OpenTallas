`timescale 1ps/1fs
module tb #(parameter integer MUT=0);
    reg clk=0; always #416.5 clk=~clk;
    reg rst_n=0,tx_book=1,rx_book=1,tx_v=0; reg [1023:0] tx_d=0; reg [7:0] tx_index=0;
    reg manual=0,manual_v=0; reg [1103:0] manual_d=0;
    wire ring_v,rx_v,pass_v,fault;wire[1103:0]ring_d,pass_d;wire[1023:0]rx_d;
    wire ml_v=manual?manual_v:ring_v;wire[1103:0]ml_d=manual?manual_d:ring_d;
    dsdv_rowx_xb #(.MUT(MUT)) u(.clk(clk),.rst_n(rst_n),.tx_book(tx_book),.sid(4'd7),.user_id(10'd37),
        .position(21'd1234567),.tx_v(tx_v),.tx_d(tx_d),.tx_index(tx_index),.ring_v(ring_v),.ring_d(ring_d),
        .rx_book(rx_book),.ml_v(ml_v),.ml_d(ml_d),.rx_v(rx_v),.rx_d(rx_d),.pass_v(pass_v),.pass_d(pass_d),.fault(fault));
    integer ntx=0,nrx=0,c=0;
    reg et,er;reg[1103:0]expected;reg[1023:0]expected_rx;
    always @(posedge clk) if(rst_n) begin
        c=c+1;et=tx_v&&tx_book;er=ml_v&&rx_book;expected_rx=ml_d[1044:21];
        expected={26'd0,21'd1234567,10'd37,1'b1,1'b1,tx_d,tx_index,4'd7,5'd0,3'd2,1'b1};
        #0.001;
        if(ring_v!==et || rx_v!==er)$fatal(1,"VALID edge%0d",c);
        if(et)begin if(ring_d!==expected)$fatal(1,"TX payload/identity edge%0d",c);ntx=ntx+1;end
        if(er)begin if(rx_d!==expected_rx)$fatal(1,"RX payload edge%0d",c);nrx=nrx+1;end
    end
    initial begin
        repeat(3)@(negedge clk);rst_n=1;
        for(int n=0;n<1120;n++)begin
            @(negedge clk);tx_v=1;tx_index=8'(n);
            for(int k=0;k<32;k++)tx_d[32*k+:32]=$urandom;
            @(negedge clk);tx_v=0;
        end
        repeat(3)@(negedge clk);
        if(fault || ntx!=1120 || nrx!=1120)$fatal(1,"positive counts tx%0d rx%0d fault%b",ntx,nrx,fault);
        manual=1;rx_book=0;manual_v=1;
        for(int n=0;n<64;n++)begin
            for(int k=0;k<34;k++)manual_d[32*k+:32]=$urandom;manual_d[1103:1088]=16'($urandom);
            #0.001;if(!pass_v || pass_d!==manual_d)$fatal(1,"normal MU pass");@(negedge clk);
        end
        manual_v=0;@(negedge clk);rx_book=1;
        manual_d={26'd0,21'd1234567,10'd36,1'b1,1'b1,1024'd0,8'd0,4'd7,5'd0,3'd2,1'b1};
        manual_v=1;@(negedge clk);manual_v=0;
        if(!fault)$fatal(1,"bad receive identity not caught");
        rst_n=0;@(negedge clk);rst_n=1;manual=0;tx_book=0;tx_v=1;
        @(negedge clk);tx_v=0;if(!fault)$fatal(1,"out of booked TX window not caught");
        $display("ROWX_XB_GATE PASS tx1120 rx1120 normal64 identity_negative window_negative TX1edge RX1edge");$finish;
    end
endmodule
