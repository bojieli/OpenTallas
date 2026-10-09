`timescale 1ns/1ps
module tb_dsrom_engram_lead(input wire clk);
    reg rst_n=0;
    reg mv=0;reg [20:0] mt=0;wire mo,mf;wire [16:0] mc;
    ot_dsrom_engram_token_map m(.clk(clk),.rst_n(rst_n),.in_v(mv),.in_tok(mt),.out_v(mo),.out_cid(mc),.fault(mf));
    reg tv=0,first=0,dead=0,slot=0,rv=0,oready=0;
    reg [11:0] user=0,ru=0;reg [20:0] pos=0,tok=0;reg [2:0] rn=0;
    wire ready,rr,ov,od,os,fault;wire [67:0] ids;wire [11:0] ou;wire [20:0] op,ot;
    ot_dsrom_engram_lead_producer p(.clk(clk),.rst_n(rst_n),.t_v(tv),.t_ready(ready),.t_user(user),
        .t_pos(pos),.t_tok(tok),.t_first(first),.t_dead(dead),.t_slot(slot),.rb_v(rv),.rb_user(ru),.rb_n(rn),
        .rb_ready(rr),.out_v(ov),.out_ready(oready),.out_ids(ids),.out_dead(od),.out_slot(os),
        .out_user(ou),.out_pos(op),.out_tok(ot),.fault(fault));
    reg [16:0] expected[0:129279];
    reg [16:0] hist[0:63][0:31];reg hd[0:63][0:31];integer count[0:63];
    integer mode=0,cy=0,seen=0,i,j,u,n,tid;reg [67:0] want;reg blocked;
    reg [8191:0] dir;
    always @(posedge clk) begin
        cy<=cy+1;if(cy>300000) $fatal(1,"timeout");
    end
    task step; begin @(negedge clk); end endtask
    task send(input integer who,input integer raw,input bit fresh,input bit death);
        integer k,seq;reg [67:0] hold;
        begin
            while(!ready) step();user=who;tok=raw;first=fresh;dead=death;slot=who&1;
            seq=fresh?0:count[who];pos=seq;tv=1;step();tv=0;
            blocked=death;want[16:0]=death?17'd2:expected[raw];
            for(k=1;k<4;k=k+1) begin
                blocked=blocked || seq<k;
                if(seq>=k) blocked=blocked || hd[who][seq-k];
                want[17*k +:17]=blocked?17'd2:hist[who][seq-k];
            end
            hist[who][seq]=expected[raw];hd[who][seq]=death;count[who]=seq+1;
            while(!ov && !fault) step();
            if(fault || ids!==want || ou!=who || op!=seq || ot!=raw || od!=death || os!=(who&1)) $fatal(1,"lead mismatch user%0d seq%0d raw%0d ids%h want%h",who,seq,raw,ids,want);
            hold=ids;
            repeat(3) begin step();if(!ov || ids!==hold || ready) $fatal(1,"stalled lead changed");end
            oready=1;step();oready=0;
        end
    endtask
    initial begin
        if(!$value$plusargs("OT_ROM_DIR=%s",dir)) $fatal(1,"missing images");
        $readmemh({dir,"/expected.hex"},expected);
        if(!$value$plusargs("MODE=%d",mode)) mode=0;
        for(i=0;i<64;i=i+1) count[i]=0;
        repeat(4) step();rst_n=1;step();
        if(mode!=0) begin
            if(mode==3) begin ru=0;rn=1;rv=1;step();rv=0;end
            else begin tv=1;first=1;user=mode==2?64:0;tok=mode==1?129280:3;pos=mode==4?1:0;step();tv=0;end
            repeat(12) step();if(!fault || ov) $fatal(1,"negative accepted");
            $display("ENGRAM_LEAD NEG mode%0d caught",mode);$finish;
        end
        // Exhaustive released map, one token/cycle and both ends of every bank.
        fork
            begin for(i=0;i<129280;i=i+1) begin mv=1;mt=i;step();end mv=0;end
            begin while(seen<129280) begin step();if(mo) begin if(mc!==expected[seen]) $fatal(1,"map at%0d",seen);seen=seen+1;end end end
        join
        if(mf) $fatal(1,"map fault");
        // Every user, explicit reset, DEAD blocking, normalization aliases,
        // raw IDs above17-bit truncation threshold are prohibited by geometry.
        for(n=0;n<16;n=n+1) for(u=0;u<64;u=u+1) begin
            tid=(n*7919+u*2039)%129280;
            send(u,tid,n==0,(n==4 || n==11) && (u%3==0));
        end
        for(u=0;u<64;u=u+1) begin
            while(!rr) step();ru=u;rn=5;rv=1;step();rv=0;count[u]=count[u]-5;
            send(u,128799,0,0);
        end
        // A reset discards all inflight/context/history visibility.
        rst_n=0;step();rst_n=1;step();send(63,129279,1,0);
        $display("ENGRAM_LEAD PASS map129280 users64 tokens1089 stalls rollback5 dead reset");$finish;
    end
endmodule
