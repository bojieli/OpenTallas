`timescale 1ps/1fs
// Minimum full-depth mutable landing ring, actual 833.333/1024 ps clocks.
// This is a component fault/debt gate, not the 128-PC exact or physical gate.
module tb_qwen_s4_protected_r9_read;
    localparam integer WIDTH=281, DEPTH=64, KIND=0;
    localparam integer P=$clog2(DEPTH)+1;
    import ot_gpu_w6_secded_pkg::*;
    reg wc=0,rc=0,por=0,allow_new=1,wv=0,ready=0;
    always #512 wc=~wc;
    always begin #416.666 rc=1; #416.667 rc=0; end
    reg [WIDTH-1:0] data=0;
    wire wr,valid,wfault,rfault;
    wire [WIDTH-1:0] out;
    wire [P-1:0] occupied,owner,retired;
    integer received=0, expected=0, checks=0;
    reg compare_enable=1;
    wire gold_wr,gold_valid,gold_wfault,gold_rfault;
    wire [WIDTH-1:0] gold_data;wire [P-1:0] gold_owner;
    ot_qwen_s4_protected_ring #(.WIDTH(WIDTH),.DEPTH(DEPTH),.KIND(KIND)) gold(
        .wr_clk(wc),.rd_clk(rc),.por_n(por),.allow_new(allow_new),
        .wr_valid(wv),.wr_ready(gold_wr),.wr_data(data),.wr_fault(gold_wfault),
        .rd_valid(gold_valid),.rd_ready(ready),.rd_data(gold_data),.rd_owner(gold_owner),
        .retire(gold_valid&&ready),.rd_fault(gold_rfault));
    always @(negedge rc) if(por&&compare_enable)begin
        if(valid!==gold_valid || wr!==gold_wr || wfault!==gold_wfault || rfault!==gold_rfault)
            $fatal(1,"r9 changed valid/ready/fault edge vs golden protected cuts");
        if(valid && (out!==gold_data || owner!==gold_owner))
            $fatal(1,"r9 changed held coded payload/owner vs golden");
    end
    reg score=1;
    function automatic [WIDTH-1:0] payload(input integer id);
        payload={(WIDTH/32+1){32'(id*1234567+17)}};
    endfunction
    ot_qwen_s4_protected_ring #(.WIDTH(WIDTH),.DEPTH(DEPTH),.KIND(KIND),.READ_RSEL(1)) dut(.wr_clk(wc),.rd_clk(rc),.por_n(por),
        .allow_new(allow_new),.wr_valid(wv),.wr_ready(wr),.wr_data(data),
        .wr_occupancy(occupied),.wr_fault(wfault),.rd_valid(valid),
        .rd_ready(ready),.rd_data(out),.rd_owner(owner),
        .retire(valid&&ready),.retired(retired),.rd_fault(rfault));
    always @(posedge rc) if(por&&valid&&ready)begin
        if(score && out!==payload(expected)) $fatal(1,"golden payload/order expected %0d",expected);
        expected=expected+1;received=received+1;
    end
    task cold;
        begin
            @(negedge wc);por=0;wv=0;ready=0;allow_new=1;
            repeat(4)@(negedge wc);
            expected=0;received=0;por=1;
            repeat(4)@(negedge wc);
        end
    endtask
    task put(input integer id);
        begin
            @(negedge wc);data=payload(id);wv=1;
            do @(posedge wc); while(!wr);
            @(negedge wc);wv=0;
        end
    endtask
    task drain(input integer count);
        begin
            @(negedge rc);ready=1;
            repeat(80)@(negedge rc);
            if(received!=count || wfault || rfault)$fatal(1,"drain %0d/%0d faults %b%b",received,count,wfault,rfault);
            repeat(4)@(negedge wc);
            if(occupied!=0)$fatal(1,"debt not retired");
            checks=checks+1;
        end
    endtask
    reg [P-1:0] held_retired;
    reg [WIDTH-1:0] held_payload;
    reg [65:0] dec;
    reg [63:0] raw;
    initial begin
        cold();ready=1;
        for(integer n=0;n<180;n=n+1)put(n);
        drain(180); // wraps both identity phases and physical slots
        cold();
        for(integer n=0;n<DEPTH;n=n+1)put(n);
        repeat(12)@(negedge wc);
        if(wr||occupied!=DEPTH)$fatal(1,"full ring admitted overwrite");
        if(!valid)$fatal(1,"full ring lacks checked held output");
        held_payload=out;held_retired=retired;
        allow_new=0; // warm reset: admission pause, never cold POR
        repeat(20)@(negedge rc);
        if(!valid||out!==held_payload||retired!=held_retired||occupied!=DEPTH)
            $fatal(1,"warm reset erased/replayed held debt");
        drain(DEPTH);allow_new=1;
        compare_enable=0;
        // Single-bit payload, parity, and overall-parity correction.
        for(integer bitn=0;bitn<3;bitn=bitn+1)begin
            cold();put(0);wait(dut.publish_bin==1);
            @(negedge wc);
            dut.mem[0][bitn==0?10:bitn==1?0:71]=~dut.mem[0][bitn==0?10:bitn==1?0:71];
            drain(1);
        end
        // SECDED UE must hold owner and source debt; no fabricated completion.
        cold();put(0);wait(dut.publish_bin==1);@(negedge wc);
        dut.mem[0][10]=~dut.mem[0][10];dut.mem[0][11]=~dut.mem[0][11];
        ready=1;repeat(24)@(negedge rc);
        if(!rfault||valid||received!=0||retired!=0||occupied!=1)$fatal(1,"UE escaped debt quarantine");
        allow_new=0;repeat(24)@(negedge rc);
        if(!rfault||retired!=0||occupied!=1)$fatal(1,"warm reset cleared UE debt");
        checks=checks+1;
        // A valid codeword from another PC must fail transaction seal.
        cold();put(0);wait(dut.publish_bin==1);@(negedge wc);
        dec=decode64(dut.mem[0][0+:72]);raw=dec[63:0];raw[44]=~raw[44];
        dut.mem[0][0+:72]=encode64(raw);
        ready=1;repeat(24)@(negedge rc);
        if(!rfault||valid||retired!=0||occupied!=1)$fatal(1,"wrong PC seal escaped");
        checks=checks+1;
        // Pointer upset: stored complementary crossing must disagree too.
        cold();put(0);wait(dut.publish_bin==1);@(negedge wc);
        dut.u_ws.primary[2*P]=~dut.u_ws.primary[2*P];
        repeat(6)@(negedge rc);
        if(!wfault||wr||dut.ww_ok)$fatal(1,"pointer upset created coherent false crossing");
        if(retired!=0)$fatal(1,"fault retired unconsumed debt");
        checks=checks+1;
        // A protected selector upset must never read a different PC slot.
        cold();put(0);wait(dut.publish_bin==1);@(negedge rc);
        dut.r9_read.column[0].u_sel.primary[0]=~dut.r9_read.column[0].u_sel.primary[0];
        ready=1;repeat(24)@(negedge rc);
        if(!rfault||valid||retired!=0||occupied!=1)$fatal(1,"r9 selector fault released owned debt");
        allow_new=0;repeat(24)@(negedge rc);
        if(!rfault||retired!=0||occupied!=1)$fatal(1,"warm erased r9 selector fault/debt");
        checks=checks+1;
        // A coherently wrong selector is not authority merely because its
        // rails agree: it must still match the protected current fetch PC.
        cold();put(0);wait(dut.publish_bin==1);@(negedge rc);
        dut.r9_read.column[0].u_sel.primary=dut.r9_read.column[0].u_sel.primary^64'h3;
        dut.r9_read.column[0].u_sel.inverse=dut.r9_read.column[0].u_sel.inverse^64'h3;
        ready=1;repeat(24)@(negedge rc);
        if(!rfault||valid||retired!=0||occupied!=1)$fatal(1,"r9 wrong coherent selector accepted another source slot");
        checks=checks+1;
        $display("PASS r9 full-depth%0dx%0d ring ordered180 full warm-held CE3 UE seal pointer checks=%0d",WIDTH,DEPTH,checks);
        $finish;
    end
endmodule
