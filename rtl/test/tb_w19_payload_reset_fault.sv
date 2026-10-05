// Reset/fault coverage on unchanged production 136-byte sector/tag adapter.
`timescale 1ns/1ps
module tb_w19_payload_reset_fault;
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
    integer i;
    always @(posedge clk)
        if (offcr || offqr || offrv || offsr || !offidle || offfault)
            $fatal(1,"default not off");
    task reset;
        begin @(negedge clk);rst=0;sv=0;qv=0;cv=0;rr=0;
            repeat(3) @(negedge clk);rst=1;
        end
    endtask
    task configure;
        begin @(negedge clk);cv=1;@(posedge clk);if(!cr && n!=0)$fatal(1,"configuration refused");@(negedge clk);cv=0;end
    endtask
    task expect_fault;
        begin @(negedge clk);if(!fault || rv || qr || sr) $fatal(1,"fault not fail-closed");end
    endtask
    reg bs=0,bv=0;wire br;reg [3:0] bsr=0;wire [3:0] bsv;
    wire [95:0] bsi;wire [63:0] bse;wire [1023:0] bsd;
    ot_gpu_payload_line_bridge bridge(.clk(clk),.rst_n(rst),.start(bs),.epoch(epoch),
        .line_valid(bv),.line_ready(br),.line_data({32{32'h89abcdef}}),.sector_valid(bsv),
        .sector_ready(bsr),.sector_index(bsi),.sector_epoch(bse),.sector_data(bsd));
    task fresh(input integer count,input integer ep);
        begin n=count;epoch=ep;configure();end
    endtask
    task request(input integer address,input integer tag);
        begin @(negedge clk);qv=1;qa=address;qt=tag;
            @(posedge clk);if(!qr)$fatal(1,"request refused");@(negedge clk);qv=0;end
    endtask
    task batch(input integer first,input integer ep);
        integer p,k,b;
        begin @(negedge clk);sv=15;
            for(p=0;p<4;p=p+1)begin
                k=first+3-p;si[p*24 +:24]=k;se[p*16 +:16]=ep;
                for(b=0;b<32;b=b+1)sd[p*256+b*8 +:8]=((k*32+b)*17+ep)&255;
            end
            @(posedge clk);if(sr!==15)$fatal(1,"batch refused");@(negedge clk);sv=0;
        end
    endtask
    task check_payload(input integer ep,input integer tag);
        integer b;
        begin if(!rv || rt!==tag)$fatal(1,"response tag");
            for(b=0;b<136;b=b+1)if(rd[b*8 +:8]!==((b*17+ep)&255))$fatal(1,"weight/exponent byte %0d",b);
        end
    endtask
    task retire(input integer ep,input integer tag);
        reg [1097:0] saved;
        begin wait(rv);@(negedge clk);check_payload(ep,tag);saved={rt,rd};
            repeat(5)begin @(negedge clk);if(!rv || {rt,rd}!==saved)$fatal(1,"response stall");end
            rr=1;@(negedge clk);rr=0;repeat(2)@(negedge clk);
            if(!idle || rv || fault)$fatal(1,"drain failed");
        end
    endtask
    task flush;
        begin @(posedge clk);#0.2;rst=0;#0.05;
            if(rv || !idle || fault || !cr)$fatal(1,"async reset flush");
            sv=0;qv=0;cv=0;rr=0;bv=0;bsr=0;bs=0;
            @(negedge clk);rst=1;@(negedge clk);
        end
    endtask
    task sticky;
        begin expect_fault();cv=1;repeat(3)@(negedge clk);
            if(!fault || cr || rv)$fatal(1,"config cleared sticky fault");cv=0;
        end
    endtask
    task receipt(input [511:0] name);
        begin $display("CASE %0s PASS",name);end
    endtask
    initial begin
        reset();fresh(1,7);request(0,5);
        @(negedge clk);sv=3;si[23:0]=0;si[47:24]=1;se={4{epoch}};
        @(negedge clk);sv=0;if(rv)$fatal(1,"incomplete release");flush();
        fresh(1,8);request(0,5);batch(4,8);batch(0,8);retire(8,5);receipt("reset_partial_record_tag_reuse");
        reset();fresh(1,9);request(0,9);batch(0,9);batch(4,9);wait(rv);
        @(negedge clk);check_payload(9,9);flush();fresh(1,10);request(0,9);
        batch(0,10);batch(4,10);retire(10,9);receipt("reset_stalled_response");
        reset();fresh(24,11);for(i=0;i<16;i=i+1)request(i,i);
        @(negedge clk);qv=1;qa=16;qt=16;
        repeat(3)begin @(negedge clk);if(qr || fault || rv)$fatal(1,"credit bound");end
        flush();fresh(1,12);request(0,0);batch(0,12);batch(4,12);retire(12,0);receipt("reset_full_tag_credits");
        reset();fresh(8,13);@(negedge clk);sv=1;si[23:0]=16;se[15:0]=13;
        repeat(4)begin @(negedge clk);if(sr[0] || fault)$fatal(1,"future sector window");end
        flush();receipt("finite_sector_window_backpressure");
        reset();fresh(1,14);@(negedge clk);sv=1;si[23:0]=8;se[15:0]=14;
        @(negedge clk);sv=0;sticky();receipt("sector_out_of_descriptor");
        reset();fresh(2,15);request(0,31);batch(0,15);batch(4,15);wait(rv);
        @(negedge clk);rr=1;@(negedge clk);rr=0;sv=1;si[23:0]=0;se[15:0]=15;
        @(negedge clk);sv=0;sticky();receipt("duplicate_consumed_sector");
        reset();fresh(1,16);@(negedge clk);sv=3;si=0;se={4{epoch}};
        @(negedge clk);sv=0;sticky();receipt("duplicate_simultaneous_sector");
        reset();fresh(1,17);@(negedge clk);sv=1;si[23:0]=0;se[15:0]=16;
        @(negedge clk);sv=0;sticky();receipt("stale_epoch_after_reset");
        reset();fresh(2,18);request(0,5);@(negedge clk);qv=1;qa=1;qt=5;
        @(negedge clk);qv=0;sticky();receipt("duplicate_live_request_tag");
        reset();fresh(1,19);@(negedge clk);qv=1;qa=1;qt=6;
        @(negedge clk);qv=0;sticky();receipt("request_ordinal_skip");
        reset();fresh(0,20);sticky();receipt("zero_length_descriptor");
        reset();epoch=21;@(negedge clk);bv=1;bsr=3;
        @(negedge clk);if(bsv!==12 || br || bsi[23:0]!==0)$fatal(1,"partial bridge");
        flush();epoch=22;@(negedge clk);bv=1;bsr=0;
        #0.01;if(bsv!==15 || bsi[23:0]!==0 || bse[15:0]!==22)$fatal(1,"bridge reset");
        bsr=15;@(negedge clk);bsr=0;if(bsi[23:0]!==4)$fatal(1,"bridge ordinal");
        bs=1;@(negedge clk);bs=0;if(bsv!==15 || bsi[23:0]!==0)$fatal(1,"bridge descriptor restart");
        bv=0;receipt("reset_partial_line_bridge");
        $display("RESET_FAULT PASS cases=12 default_off=1 tightly_packed_bytes=136");$finish;
    end
    initial begin #20000;$fatal(1,"protocol timeout");end
endmodule
