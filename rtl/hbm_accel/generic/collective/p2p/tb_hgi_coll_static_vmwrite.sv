`timescale 1ns/1ps
module tb_hgi_coll_static_vmwrite;
    parameter integer MUT=0;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0; reg [1:0] sid=0;
    reg [3:0] rv=0;
    reg [159:0] ra=0;
    reg [2047:0] rd=0;
    reg tv=0;
    reg [567:0] td=0;
    reg [4:0] islot=0;
    reg [7:0] slots=0;
    reg [31:0] owners=0;
    wire [2247:0] kq;
    wire [4:0] done;
    wire fault;
    ot_hgi_coll_static_vmwrite #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.sid(sid),
        .rgx_v(rv),.rgx_addr(ra),.rgx_data(rd),.rgx_vm(1'b1),.tkw_v(tv),.tkw_d(td),
        .ingress_slot(islot),.slot_valid(slots),.slot_owner(owners),.kq(kq),.launch_done(done),.fault(fault));
    reg [4:0] pv=0, ppv=0;
    reg [199:0] pa=0, ppa=0;
    reg [2559:0] pd=0, ppd=0;
    reg [79:0] pm=0, ppm=0;
    reg [2247:0] expected;
    reg [7:0] used;
    integer checked=0,full_cycles=0;
    task tick(input [4:0] valid, input integer seq, input integer mode);
        reg [15:0] sec;
        reg [199:0] aa;
        reg [2559:0] dd;
        reg [79:0] mm;
        integer lane,half,bank,word;
        begin
            @(negedge clk);
            aa=0; dd=0; mm={16'h5aa5,64'hffffffffffffffff};
            for(lane=0;lane<5;lane=lane+1) begin
                // Four lanes sustain eight distinct bank sectors each cycle.
                // TKW uses first bank1; the full five-lane burst is isolated.
                sec=16'((seq*16)+(lane==4 ? 1 : 2*lane));
                if(mode==2) sec=16'(seq*16);
                if(mode==7) sec=16'd1;
                if(mode==4) sec=sec | 16'h2000;
                if(mode==5) sec=sec | 16'h8000;
                aa[lane*40 +:40]=40'(sec)<<3;
                for(word=0;word<16;word=word+1) dd[lane*512+word*32 +:32]=32'(seq*65536+lane*256+word);
            end
            rv=valid[3:0];tv=valid[4];ra=aa[159:0];rd=dd[2047:0];td={aa[199:160],mm[79:64],dd[2559:2048]};
            islot=valid;slots=0;owners=0;expected=0;used=0;
            for(half=0;half<2;half=half+1) for(lane=0;lane<5;lane=lane+1) begin
                if((half==0 ? pv[lane] : ppv[lane])) begin
                    sec=half==0 ? pa[lane*40+3 +:16] : ppa[lane*40+3 +:16]+16'd1;
                    bank=int'(sec[2:0]); used[bank]=1;
                    slots[bank]=1;owners[bank*4 +:4]=4'(lane+5*half);
                    expected[bank*281 +:281]=expected[bank*281 +:281] | {1'b1,sec,
                        (half==0 ? pd[lane*512 +:256] : ppd[lane*512+256 +:256]),
                        (half==0 ? pm[lane*16 +:8] : ppm[lane*16+8 +:8])};
                end
            end
            if(mode==1) slots=slots ^ 8'b1;
            if(mode==3) islot=valid ^ 5'b1;
            if(mode==6) islot=valid | 5'b1;
            @(posedge clk); #1;
            // Only valid payload has meaning. Check every emitted sector bit.
            for(bank=0;bank<8;bank=bank+1) begin
                if(kq[bank*281+280] !== used[bank]) $fatal(1,"valid timing bank %0d",bank);
                if(used[bank] && kq[bank*281 +:281] !== expected[bank*281 +:281]) $fatal(1,"payload/latency bank %0d",bank);
            end
            if(done !== ppv) $fatal(1,"launch_done latency");
            if(used==8'hff) full_cycles=full_cycles+1;
            checked=checked+1;
            ppv=pv;ppa=pa;ppd=pd;ppm=pm;pv=valid;pa=aa;pd=dd;pm=mm;
        end
    endtask
    // Exact exception timing: a violation presented at edge C raises the
    // sticky fault at C+1 (pin-captured checks), never at C, never at C+2.
    integer fault_checks=0;
    task fault_next(input [8*48-1:0] what);
        begin
            if(fault) $fatal(1,"fault at C (expected C+1): %0s",what);
            tick(0,90,0);
            if(!fault) $fatal(1,"%0s undetected at C+1",what);
            fault_checks=fault_checks+1;
        end
    endtask
    task reset;
        begin
            @(negedge clk);rst_n=0;rv=0;tv=0;islot=0;slots=0;owners=0;
            pv=0;ppv=0;pa=0;ppa=0;pd=0;ppd=0;pm=0;ppm=0;
            repeat(3) @(negedge clk);
            rst_n=1;
        end
    endtask
    initial begin
        reset();
        for(integer n=0;n<24;n=n+1) tick(5'b01111,n,0);
        tick(0,24,0);tick(0,25,0);tick(0,26,0);
        for(integer n=30;n<60;n=n+3) begin tick(5'b11111,n,0);tick(0,n+1,0);tick(0,n+2,0); end
        if(fault || full_cycles<20) $fatal(1,"legal production schedule fault or insufficient load");
        reset();tick(0,0,1);fault_next("extra reserved resource");
        reset();tick(1,0,3);fault_next("ingress slot overflow");
        reset();tick(5'b00011,0,2);tick(0,1,0);fault_next("same bank conflict");
        reset();tick(1,0,0);tick(0,1,0);tick(1,2,0);tick(0,3,0);
        if(fault) $fatal(1,"reset failed to clear diagnostic fault");
        reset();tick(1,0,0);tick(1,1,7);tick(0,2,0);
        fault_next("high/low bank conflict");
        // Continue legal transfers under sticky fault: tick checks exact payload
        // and launch timing at every edge, so the fault cannot shift execution.
        tick(0,3,0);tick(1,4,0);tick(0,5,0);tick(0,6,0);
        if(!fault) $fatal(1,"fault failed to remain sticky");
        reset();tick(1,0,4);fault_next("wrong sid");
        reset();tick(0,0,6);fault_next("missing reserved ingress");
        reset();sid=2;tick(1,0,5);tick(0,1,0);tick(0,2,0);
        if(fault) $fatal(1,"mirror window must use sector sid zero independent of local sid");
        sid=0;
        $display("STATIC VMWRITE PASS checked=%0d full_bank_cycles=%0d fault_timing_checks=%0d RGX=4x512 TKW=568 low=C+1 high=C+2 fault=C+1",checked,full_cycles,fault_checks);
        $finish;
    end
endmodule
