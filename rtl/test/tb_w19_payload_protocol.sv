`timescale 1ns/1ps
module tb_w19_payload_protocol;
    reg clk=0,rst=0; always #0.5 clk=~clk;
    reg cv=0; wire cr; reg [23:0] n=40; reg [15:0] epoch=7;
    reg [3:0] sv=0; wire [3:0] sr; reg [95:0] si=0; reg [63:0] se=0; reg [1023:0] sd=0;
    reg qv=0; wire qr; reg [31:0] qa=0; reg [9:0] qt=0;
    wire rv; reg rr=0; wire [9:0] rt; wire [1087:0] rd; wire idle,fault;
    ot_gpu_payload_assemble #(.ENABLE(1)) dut(.clk(clk),.rst_n(rst),.cfg_valid(cv),.cfg_ready(cr),
        .cfg_payloads(n),.cfg_req_base(32'd0),.cfg_epoch(epoch),.sector_valid(sv),.sector_ready(sr),
        .sector_index(si),.sector_epoch(se),.sector_data(sd),.req_valid(qv),.req_ready(qr),.req_addr(qa),.req_tag(qt),
        .rsp_valid(rv),.rsp_ready(rr),.rsp_tag(rt),.rsp_data(rd),.idle(idle),.fault(fault));
    wire offcr,offqr,offrv,offidle,offfault;wire [3:0] offsr;
    ot_gpu_payload_assemble off(.clk(clk),.rst_n(rst),.cfg_valid(cv),.cfg_ready(offcr),.cfg_payloads(n),
        .cfg_req_base(32'd0),.cfg_epoch(epoch),.sector_valid(sv),.sector_ready(offsr),.sector_index(si),
        .sector_epoch(se),.sector_data(sd),.req_valid(qv),.req_ready(offqr),.req_addr(qa),.req_tag(qt),
        .rsp_valid(offrv),.rsp_ready(rr),.rsp_tag(),.rsp_data(),.idle(offidle),.fault(offfault));
    integer cyc=0,out=0,checks=0,i,j,k,line,physical;
    reg monitor=0, held=0;reg [1097:0] previous;
    always @(posedge clk) begin
        cyc<=cyc+1;
        if (offcr || offqr || offrv || offsr || !offidle || offfault) $fatal(1,"default not off");
        if (monitor) begin
            if (fault) $fatal(1,"unexpected fault");
            if (held && (!rv || {rt,rd}!==previous)) $fatal(1,"response changed under stall");
            held=rv&&!rr;previous={rt,rd};
            if (rv && rr) begin
                if (rt !== (out%32)) $fatal(1,"response tag/order");
                for (j=0;j<136;j=j+1)
                    if (rd[j*8 +:8] !== (((out*136+j)*17+epoch)&255)) $fatal(1,"payload/exp byte %0d row %0d",j,out);
                out=out+1;
            end
        end else held=0;
    end
    task reset;
        begin @(negedge clk);rst=0;sv=0;qv=0;cv=0;rr=0;monitor=0;
            repeat(3) @(negedge clk);rst=1;out=0;
        end
    endtask
    task configure;
        begin @(negedge clk);cv=1;@(negedge clk);cv=0;if(!cr && !idle) begin end end
    endtask
    task sector(input integer number,input integer ep);
        begin @(negedge clk);sv=1;si[23:0]=number;se[15:0]=ep;sd=0;
            @(negedge clk);sv=0;
        end
    endtask
    task expect_fault;
        begin @(negedge clk);if(!fault || rv || qr || sr) $fatal(1,"fault not fail-closed");checks=checks+1;end
    endtask
    task normal(input integer count,input integer ep);
        begin if(count==40) reset(); else begin @(negedge clk);out=0;end
            n=count;epoch=ep;configure();monitor=1;
            fork
                begin
                    for(i=0;i<count;i=i+1) begin
                        @(negedge clk);qv=1;qa=i;qt=i%32;
                        @(posedge clk);while(!qr) @(posedge clk);
                        @(negedge clk);qv=0;
                    end
                end
                begin
                    for(line=0;line<(count*136+127)/128;line=line+1) begin
                        @(negedge clk);sv=15;physical=(count==40 && line<4)?3-line:line;
                        for(k=0;k<4;k=k+1) begin
                            si[k*24 +:24]=physical*4+3-k;se[k*16 +:16]=ep;
                            for(j=0;j<32;j=j+1)sd[k*256+j*8 +:8]=((physical*128+(3-k)*32+j)*17+ep)&255;
                        end
                        while(sv!=0) begin
                            @(posedge clk);
                            // Remember partial sector handshakes at the sampling
                            // edge, then change valid only on the falling edge.
                            begin : g_mask
                                reg [3:0] remaining;
                                remaining=sv & ~sr;
                                @(negedge clk);sv=remaining;
                            end
                        end
                    end
                end
                begin
                    while(out<count) begin @(negedge clk);rr=(cyc%11>=5);end
                    @(negedge clk);rr=1;
                end
            join
            wait(idle);@(negedge clk);if(out!=count) $fatal(1,"missing outputs");monitor=0;checks=checks+1;
        end
    endtask
    initial begin
        normal(40,7);normal(3,8);
        reset();n=2;epoch=9;configure();sector(0,9);sector(0,9);expect_fault(); // landed duplicate
        reset();configure();@(negedge clk);sv=3;si=0;se={4{epoch}};@(negedge clk);sv=0;expect_fault();
        reset();configure();sector(0,10);expect_fault(); // stale epoch
        reset();configure();@(negedge clk);qv=1;qa=0;qt=0;@(negedge clk);qa=1;qt=0;
        @(negedge clk);qv=0;expect_fault(); // live tag collision
        reset();configure();@(negedge clk);qv=1;qa=1;@(negedge clk);qv=0;expect_fault(); // row/ordinal skip
        reset();n=0;configure();expect_fault();
        $display("PROTO PASS checks=%0d default_off=1 response_hold=1 epochs=1 duplicate_sector=1 duplicate_tag=1 row_order=1",checks);$finish;
    end
    initial begin #20000;$fatal(1,"protocol timeout");end
endmodule
