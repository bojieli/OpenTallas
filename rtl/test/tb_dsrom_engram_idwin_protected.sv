`timescale 1ns/1ps
module tb_dsrom_engram_idwin_protected(input wire clk);
    reg rst_n=0,tv=0,first=0,dead=0,rv=0;
    reg [5:0] user=0,ru=0;reg [16:0] cid=0;reg [20:0] pos=0;reg [2:0] rn=0;
    wire ov,od,fault,ce;wire [67:0] ids;
    ot_dsrom_engram_idwin_protected d(.clk(clk),.rst_n(rst_n),.t_valid(tv),.t_user(user),.t_cid(cid),
        .t_pos(pos),.t_first(first),.t_dead(dead),.rb_valid(rv),.rb_user(ru),.rb_n(rn),
        .win_valid(ov),.win_ids(ids),.win_dead(od),.fault(fault),.corrected(ce));
    reg [16:0] hist[0:63][0:255];reg hdead[0:63][0:255];integer count[0:63];
    integer mode=0,cy=0,u,n,k,b,a,ce_count=0;reg [71:0] saved;reg [67:0] want;reg blocked;
    always @(posedge clk) begin cy<=cy+1;if(cy>100000) $fatal(1,"timeout");end
    task step;begin @(negedge clk);end endtask
    task reset_state;begin rst_n=0;tv=0;rv=0;repeat(2) step();rst_n=1;step();for(k=0;k<64;k=k+1)count[k]=0;end endtask
    task send(input integer who,input integer value,input bit fresh,input bit death,input bit expect_ce);
        integer seq,j;
        begin
            seq=fresh?0:count[who];user=who;cid=value;pos=seq;first=fresh;dead=death;tv=1;
            blocked=death;want[16:0]=death?17'd2:17'(value);
            for(j=1;j<4;j=j+1) begin
                blocked=blocked || seq<j;
                if(seq>=j) blocked=blocked || hdead[who][seq-j];
                want[17*j +:17]=blocked?17'd2:hist[who][seq-j];
            end
            step();tv=0;
            if(fault || !ov || ids!==want || od!=death || (expect_ce && !ce)) $fatal(1,"protected mismatch u%0d pos%0d ids%h want%h ce%0d",who,seq,ids,want,ce);
            if(ce) ce_count=ce_count+1;
            hist[who][seq]=value;hdead[who][seq]=death;count[who]=seq+1;
            step();if(ov) $fatal(1,"window repeated");
        end
    endtask
    task rewind(input integer who,input integer number);
        begin ru=who;rn=number;rv=1;step();rv=0;if(fault || ov) $fatal(1,"rewindfault");count[who]=count[who]-number;step();end
    endtask
    initial begin
        if(!$value$plusargs("MODE=%d",mode)) mode=0;
        reset_state();
        if(mode==0) begin
            for(n=0;n<200;n=n+1) for(u=0;u<64;u=u+1) begin
                if(n>=8 && n<80) begin
                    b=n-8;a=u*8+((count[u]-1)&7);saved=d.hist[a];d.hist[a]=saved^(72'b1<<b);
                    send(u,(n*431+u*197)%99092,0,0,1);d.hist[a]=saved;
                end else if(n>=80 && n<152) begin
                    d.meta[u]=d.meta[u]^(72'b1<<(n-80));send(u,(n*431+u*197)%99092,0,0,1);
                end else send(u,(n*431+u*197)%99092,n==0,(n==3 || n==171) && u%3==0,0);
            end
            for(u=0;u<64;u=u+1) begin rewind(u,5);send(u,19,0,0,0);end
            if(ce_count!=9216) $fatal(1,"singlefault coverage%0d",ce_count);
            reset_state();send(63,99091,1,0,0);
            $display("ENGRAM_PROTECTED PASS users64 history8 windows12865 singlehistory4608 singlemeta4608 dead rewind5 reset");$finish;
        end
        for(u=0;u<64;u=u+1) begin
            reset_state();
            for(n=0;n<(mode==3?12:4);n=n+1) send(u,n+10,n==0,0,0);
            user=u;pos=count[u];cid=44;first=0;dead=0;
            case(mode)
                1: begin a=u*8+((count[u]-1)&7);d.hist[a]=d.hist[a]^72'd5;tv=1;end
                2: begin d.meta[u]=d.meta[u]^72'd5;tv=1;end
                3: begin rewind(u,5);ru=u;rn=1;rv=1;end
                4: begin tv=1;ru=u;rn=1;rv=1;end
                5: begin pos=count[u]+1;tv=1;end
                6: begin cid=99092;tv=1;end
                7: begin ru=u;rn=0;rv=1;end
                8: begin ru=u;rn=6;rv=1;end
                default:$fatal(1,"mode");
            endcase
            step();tv=0;rv=0;
            if(!fault || ov) $fatal(1,"negative uncaught mode%0d user%0d",mode,u);
        end
        $display("ENGRAM_PROTECTED NEG mode%0d all64 caught",mode);$finish;
    end
endmodule
