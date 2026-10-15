`timescale 1ns/1ps
// Two clocks (2ns writer/4ns reader, distinct phases), 4096 words, fixed
// four-ns reservations. Compiler table: write first index at wcycle17 and
// every2 writercycles; read at rcycle18 and every readercycle. Queue occupancy
// bounded11<64; read-at-r0 -> output-at-r3 exactly, including every wrap.
module tb_qfd_static_transport;
 parameter integer MUT=0,N=4096;
 reg wck=0,rck=0,rst_n=0;
 always #1 wck=~wck;always #2 rck=~rck;
 reg ws=0,rs=0,iv=0,wv=0,rv=0;
 reg [5:0] wa=0,ra=0;reg [545:0] wd=0;
 wire ov,wf,rf;wire [545:0] od;
 qfd_static_ch546 dut(.wck(wck),.rck(rck),.rst_n(rst_n),
 .w_slot(ws),.w_addr(wa),.w_version(wv),.i_valid(iv),.i_data(wd),
 .r_slot(rs),.r_addr(ra),.r_version(rv),.o_valid(ov),.o_data(od),.w_fault(wf),.r_fault(rf));
 integer wc=0,rc=0,wi=0,ri=0,got=0,bad=0,bad_timing=0,checked=0,k;
 reg [3:0] ev=0;integer ix[0:3];
 function [545:0] payload(input integer i);
 integer b;begin for(b=0;b<546;b=b+1) payload[b]=((i*17+b*63)>>(b%13))&1;end endfunction
 always @(negedge wck) if(rst_n) begin
 wc=wc+1;ws=0;iv=0;
 if(wc>=16 && (wc-16)%2==0 && wi<N) begin
 ws=1;wa=wi%64;wv=!((wi/64)%2);iv=!(MUT==1 && wi==123);wd=payload(wi);wi=wi+1;
 end
 end
 always @(negedge rck) if(rst_n) begin
 rc=rc+1;rs=0;
 if(rc>=17 && ri<N) begin rs=1;ra=ri%64;rv=!((ri/64)%2);if(MUT==2 && ri==123) rv=!rv;ri=ri+1;end
 end
 // Observe after NBA: every reserved output edge must occur irrespective of
 // fault inputs. Faults are not allowed to stretch this compiled timeline.
 always @(posedge rck) if(rst_n) begin
 for(k=3;k>0;k=k-1) ix[k]=ix[k-1];ix[0]=ri-1;
 ev={ev[2:0],rs};#0.1;checked=checked+1;
 if(ov!==ev[3]) bad_timing=bad_timing+1;
 if(ov) begin if(od!==payload(ix[3])) bad=bad+1;got=got+1;end
 end
 initial begin
 #20 rst_n=1;
 wait(got==N);repeat(4)@(posedge rck);#0.2;
 if(bad==0 && bad_timing==0 && !wf && !rf)
 $display("PASS static_transport words=%0d exact_read_latency=3rck checked=%0d faults=0 no_runtime_credit_or_backpressure",got,checked);
 else $display("FAIL static_transport MUT=%0d words=%0d data=%0d timing=%0d faults=%0d/%0d",MUT,got,bad,bad_timing,wf,rf);
 $finish;
 end
 initial begin #100000;$display("FAIL static_transport timeout got=%0d",got);$finish;end
endmodule
