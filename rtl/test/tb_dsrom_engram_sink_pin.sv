`timescale 1ns/1ps
module tb_dsrom_engram_sink_pin;
    parameter integer OVERFLOW_MUTANT=0;
    reg ck=0; always #5 ck=~ck;
    reg rst_n=0;
    reg [3:0] iv=0,stv=0,stbad=0;
    wire [3:0] ir;
    reg [19:0] col=0;
    reg [11:0] beat=0,slots=0,stslots=0;
    reg [1055:0] data=0;
    wire we;wire [10:0] wa;wire [511:0] wd;
    wire [7:0] ready,poison;
    reg rel=0;reg [2:0] relslot=0;
    integer sent[0:3];integer src,k,tick,total=0,phase=0;
    reg [1535:0] seen=0;
    integer compact;
    reg [15:0] expected;
    dsfd_engram_sink #(.PIN_CAPTURE(1)) dut(.ck(ck),.rst_n(rst_n),.in_v(iv),.in_r(ir),
        .in_col(col),.in_beat(beat),.in_slot(slots),.in_d(data),.st_v(stv),.st_slot(stslots),.st_bad(stbad),
        .wr_en(we),.wr_addr(wa),.wr_data(wd),.rdy(ready),.perr(poison),.rel_v(rel),.rel_slot(relslot));
    always @(posedge ck) if(rst_n) begin
        for(src=0;src<4;src=src+1) if(iv[src]&&ir[src]) sent[src]=sent[src]+1;
        if(phase==1 && we) begin
            if(wa[7:3]>=24) $fatal(1,"tag bounds");
            compact=wa[10:8]*192+wa[7:0];
            if(seen[compact]) $fatal(1,"duplicate accepted beat");
            seen[compact]=1;total=total+1;
            expected=wa[0] ? 16'h4000 : 16'h3f80;
            for(k=0;k<32;k=k+1) if(wd[k*16+:16]!==expected) $fatal(1,"payload mismatch");
        end
    end
    task reset;
        begin @(negedge ck);rst_n=0;iv=0;stv=0;repeat(4) @(negedge ck);
            for(src=0;src<4;src=src+1) sent[src]=0;
            rst_n=1;
        end
    endtask
    task drive(input integer limit);
        begin
            tick=0;
            while(sent[0]+sent[1]+sent[2]+sent[3]<limit*4) begin
                @(negedge ck);tick=tick+1;
                if(tick>10000) $fatal(1,"bounded queue failed to drain");
                for(src=0;src<4;src=src+1) begin
                    // Hold payload while stalled; long concurrent bursts and
                    // independent gaps exercise all four reservation domains.
                    iv[src]=(sent[src]<limit) && ((tick+src)%13!=0);
                    col[src*5+:5]=src*6+(sent[src]%48)/8;
                    beat[src*3+:3]=sent[src]%8;
                    slots[src*3+:3]=sent[src]/48;
                    data[src*264+:264]={8'd127,{32{sent[src]%2 ? 8'h40 : 8'h38}}};
                end
            end
            @(negedge ck);iv=0;
        end
    endtask
    initial begin
        for(src=0;src<4;src=src+1) sent[src]=0;
        reset;drive(5);reset;phase=1;drive(384);
        repeat(20) @(negedge ck);
        if(total!=1536 || seen!={1536{1'b1}} || ready!=0) $fatal(1,"fullshape acceptance/ready mismatch");
        for(tick=0;tick<48;tick=tick+1) begin
            @(negedge ck);stv=15;
            for(src=0;src<4;src=src+1) stslots[src*3+:3]=tick/6;
        end
        @(negedge ck);stv=0;
        repeat(10) @(negedge ck);
        if(ready!=255 || poison!=0) $fatal(1,"statuses not drained");
        for(tick=0;tick<8;tick=tick+1) begin
            @(negedge ck);rel=1;relslot=tick;
        end
        @(negedge ck);rel=0;repeat(5) @(negedge ck);
        if(ready!=0) $fatal(1,"release stale slot");
        $display("ENGRAM_SINK_PIN PASS words=1536 sources=4 slots=8 burst=1 reset=1 payload=1 tags=1 release=1");$finish;
    end
endmodule
