`timescale 1ns/1ps
module tb_dsrom_engram_boot_ctrl_map;
    reg ck=0;always #5 ck=~ck;
    reg rst_n=0;
    reg [1:0] iv=0;
    reg [28:0] ia=0;
    reg [2:0] it=0;
    reg [255:0] id=0;
    wire [64*341-1:0] rq;
    reg [63:0] wd=0;
    wire [1:0] done;
    wire [5:0] tags;
    wire fault;
    integer p,writes=0,acks=0,mode=0;
    reg [7:0] seen=0;
    reg [340:0] word;
    ot_dsrom_engram_boot_ctrl_map dut(.ck(ck),.rst_n(rst_n),.i_v(iv),.i_atom(ia),.i_tag(it),.i_d(id),
        .rq(rq),.wd(wd),.done_v(done),.done_tag(tags),.fault(fault));
    always @(negedge ck) if(rst_n) begin
        for(p=0;p<64;p=p+1) begin
            word=rq[p*341+:341];
            if(word[0]) begin
                if(p!=0 && p!=32) $fatal(1,"wrong controller PC");
                if(word[1]!=1 || word[35:32]!=0 || word[84:53]!=32'hffffffff) $fatal(1,"bad rq write fields");
                if(word[52:36]>2 || seen[word[38:36]]) $fatal(1,"bad request tag");
                if((word[52:36]==1) && word[31:2]!=1) $fatal(1,"wrong PC-local atom");
                if((word[52:36]!=1) && word[31:2]!=0) $fatal(1,"wrong first PC atom");
                if(word[340:85]!=word[52:36]+100) $fatal(1,"wrong payload");
                if(p==32 && word[52:36]!=2) $fatal(1,"wrong stack");
                seen[word[38:36]]=1;writes=writes+1;
            end
        end
        if(done[0]) acks=acks+1;
        if(done[1]) acks=acks+1;
    end
    task send(input [1:0] v,input [28:0] a,input [2:0] t);
        begin
            @(posedge ck);#1;iv=v;ia=a;it=t;id=t+100;
            @(posedge ck);#1;iv=0;
        end
    endtask
    task complete(input integer pc);
        begin
            @(posedge ck);#1;wd=64'b1<<pc;
            @(posedge ck);#1;wd=0;
        end
    endtask
    initial begin
        if($value$plusargs("MODE=%d",mode)) begin end
        repeat(3) @(posedge ck);#1;rst_n=1;
        send(1,0,0);send(1,32,1);send(2,0,2);
        repeat(8) @(posedge ck);
        if(writes!=2 || acks!=0) $fatal(1,"same PC queue did not wait for actual wd");
        complete(32);repeat(6) @(posedge ck);
        if(acks!=1 || writes!=2) $fatal(1,"SE completion released unrelated SW PC");
        if(mode==1) begin
            complete(32);repeat(5) @(posedge ck);
            if(!fault) $fatal(1,"duplicate untagged PC completion accepted");
            $display("ENGRAM_MAP NEG duplicate PC completion caught");$finish;
        end
        complete(0);repeat(8) @(posedge ck);
        if(writes!=3 || acks!=2) $fatal(1,"queued repeated PC not issued");
        complete(0);repeat(8) @(posedge ck);
        if(acks!=3 || fault || seen!=7) $fatal(1,"map completion accounting failed");
        $display("ENGRAM_MAP PASS sectors=3 repeated_pc=1 controller_fields=1 completions=3");$finish;
    end
endmodule
