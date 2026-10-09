`timescale 1ns/1ps
module tb_dsrom_engram_boot_dispatch;
    reg ck=0; always #5 ck=~ck;
    reg rst_n=0, iv=0;
    reg [31:0] ia=0;
    reg [255:0] id=0;
    wire ic, ready, fault;
    wire [1:0] wv;
    wire [28:0] wa;
    wire [2:0] wt;
    wire [255:0] wd;
    reg [1:0] dv=0;
    reg [5:0] dt=0;
    integer mode=0, n, atom, issued=0, credits=8;
    reg [2:0] tags [0:7];
    reg [7:0] seen=0;
    reg [31:0] checksum=0;
    ot_dsrom_engram_boot_dispatch #(.EXPECT_SECTORS(8)) dut(
        .ck(ck),.rst_n(rst_n),.i_v(iv),.i_addr(ia),.i_d(id),.i_cred(ic),
        .w_v(wv),.w_atom(wa),.w_tag(wt),.w_d(wd),.done_v(dv),.done_tag(dt),.ready(ready),.fault(fault));
    always @(negedge ck) if(rst_n) begin
        if(ic) credits=credits+1;
        if(wv!=0) begin
            if(wv==3) $fatal(1,"two stack dispatches");
            atom=wa*2+(wv==2);
            if(atom>7 || seen[atom]) $fatal(1,"duplicate/bad atom");
            if(wd[31:0] !== (atom*atom+7) || wd[255:32]!==0) $fatal(1,"write payload changed");
            tags[atom]=wt; seen[atom]=1; issued=issued+1;
        end
    end
    task send(input [31:0] addr,input [255:0] data);
        begin
            @(posedge ck); #1;
            if(credits<=0) $fatal(1,"sender exhausted credits");
            credits=credits-1; ia=addr;id=data;iv=1;
            @(posedge ck); #1;iv=0;
        end
    endtask
    task complete(input integer a);
        begin
            @(posedge ck);#1; dv=(a%2)?2:1;dt=0;
            if(a%2) dt[5:3]=tags[a]; else dt[2:0]=tags[a];
            @(posedge ck);#1;dv=0;
        end
    endtask
    initial begin
        if($value$plusargs("MODE=%d",mode)) begin end
        repeat(3) @(posedge ck);#1;rst_n=1;
        for(n=0;n<8;n=n+1) begin
            checksum=checksum^(n*n+7)^n;
            send((mode==2 && n==2)?32'h80000002:(32'hc0000000+n), n*n+7);
        end
        repeat(8) @(posedge ck);
        if(mode==2) begin
            if(!fault || ready) $fatal(1,"swapped RoPE class was accepted");
            $display("ENGRAM_BOOT NEG swappedclass caught"); $finish;
        end
        if(issued!=8) $fatal(1,"writes not all dispatched");
        // Complete in a deliberately different order; one stack is stalled.
        complete(1);complete(0);
        repeat(4) @(posedge ck);
        send(32'hffffffff,{190'd0,2'b11,(mode==3)?(checksum^32'h1):checksum,(mode==1)?32'd7:32'd8});
        for(n=6;n>=2;n=n-1) complete(n);
        repeat(8) @(posedge ck);
        if(ready) $fatal(1,"published before last stack drained");
        complete(7);repeat(8) @(posedge ck);
        if(mode==1 || mode==3) begin
            if(!fault || ready) $fatal(1,"stale marker accepted");
            $display("ENGRAM_BOOT NEG marker mode%0d caught",mode);
        end else if(mode==4) begin
            if(!ready || fault) $fatal(1,"positive setup failed");
            complete(7);repeat(5) @(posedge ck);
            if(!fault || ready) $fatal(1,"duplicate completion accepted");
            $display("ENGRAM_BOOT NEG duplicate completion caught");
        end else begin
            if(!ready || fault) $fatal(1,"complete boot failed");
            if(credits!=8) $fatal(1,"credit leak %0d",credits);
            $display("ENGRAM_BOOT PASS sectors=8 outorder=1 stalled_stack=1 credits=8");
        end
        $finish;
    end
endmodule
