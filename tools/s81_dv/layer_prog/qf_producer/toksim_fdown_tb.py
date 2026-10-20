#!/usr/bin/env python3
"""TOKSIM-S81B/FDOWN 10-19: derive tb_fdown_trace.sv from the TOK2 fullsix TB (tb_fullsix_trace.sv, L16/E24 build).

Vehicle change only (no RTL change): the slice x buffer ot_s81sl_xs receives the ffn.down x vectors (bf16(route_w) of
each expert, FP8 q family, 36 beats of 64 elements, K 2304) as gathered beats at its own g pins -- the production
all-gather boundary -- instead of the private raw-qnorm VP/VS/VQ/RSTOP producer.  One beat per edge from source 0, the
k-th gather window (xs.o_gw) delivers expert k's beats starting 4 edges after the window opens.  Every other DUT
(XR issuer path, XS, the six real sid6 frames of selected_fullsix_cone, frame-root relay, CAP) is the fullsix one.
Horizon / epoch count are plusargs (+T, default 30000).  usage: toksim_fdown_tb.py IN.sv OUT.sv
"""
import sys
src = open(sys.argv[1]).read()
NB, NW, CTLN = 36, 7, 40000


def sub(old, new, cnt=1):
    global src
    assert src.count(old) == cnt, (old, src.count(old))
    src = src.replace(old, new)


sub('module tb_fullsix_trace;', 'module tb_fullsix_trace; // TOKSIM-S81B/FDOWN derivative (toksim_fdown_tb.py)')
sub('reg [185:0] ctl[0:12000];reg [12000:0] ctlv=0;reg [531:0] gold[0:19];',
    f'reg [185:0] ctl[0:{CTLN}];reg [{CTLN}:0] ctlv=0;reg [531:0] gold[0:{NB*NW-1}];integer T=30000,gwin=-1,gstart=-1,nrd=0;'
    f'reg[2:0]tg_v=0;reg[20:0]tg_i=0;reg[3071:0]tg_d=0;')
sub('ot_s81sl_xs xs(.clk(clk),.rst_n(rst_n),.g_v(gv),.g_fam(gfam),.g_idx(gi),.g_d(gd),',
    'ot_s81sl_xs xs(.clk(clk),.rst_n(rst_n),.g_v(tg_v),.g_fam(3\'d0),.g_idx(tg_i),.g_d(tg_d),')
sub('integer reads[0:14];reg[31:0]expected_reads[0:14];', 'integer reads[0:63];reg[31:0]expected_reads[0:63];')
sub(' qword=gold[blk/2]>>(266*(blk%2));', f' qword=gold[{NB}*(gwin<0?0:gwin)+blk/2]>>(266*(blk%2));')
sub(' qexp=gold[blk/2]>>(256+266*(blk%2));', f' qexp=gold[{NB}*(gwin<0?0:gwin)+blk/2]>>(256+266*(blk%2));')
sub(' for(integer e=0;e<15;e++)reads[e]=0;', ' for(integer e=0;e<64;e++)reads[e]=0;\n rc=$value$plusargs("T=%d",T);')
sub(' for(integer j=0;j<12001;j++)ctl[j]=0;', f' for(integer j=0;j<{CTLN+1};j++)ctl[j]=0;')
sub('n+1<=ORIGIN+11984', f'n+1<=ORIGIN+{CTLN-16}')
sub('if(current_epoch<0||current_epoch>14)err++;', 'if(current_epoch<0||current_epoch>63)err++;')
sub('bi0>=40', f'bi0>={2*NB}')
sub('bi1>=40', f'bi1>={2*NB}')
sub(' if(n>=ORIGIN && n<ORIGIN+11900)begin', ' if(n>=ORIGIN && n<ORIGIN+T)begin', 2)
# gathered beats at the xs pins: window k (k-th o_gw) -> expert k's 36 beats, one per edge from 4 edges after the window
sub('always @(negedge clk)begin\n if(n==8)rst_n=1;',
    'always @(posedge clk)if(xs.o_gw)begin gwin=gwin+1;gstart=n+4;$display("FDOWN_WINDOW t=%0d window=%0d",n-ORIGIN,gwin);end\n'
    'always @(negedge clk)begin\n'
    f' tg_v=0;tg_i=0;tg_d=0;\n if(gwin>=0 && gwin<{NW} && n+1>=gstart && n+1<gstart+{NB})begin tg_v=3\'d1;tg_i=21\'(n+1-gstart);'
    f'tg_d={{2540\'d0,gold[{NB}*gwin+n+1-gstart]}};end\n'
    '\nend\nalways @(negedge clk)begin\n if(n==8)rst_n=1;')
old_end = src[src.index(' if(n==ORIGIN+11900)begin'):src.index('generate for(genvar m=0;m<8;m++)begin:mon_macro')]
new_end = (' if(n==ORIGIN+T)begin\n'
           '  if(fx||fs||fq||fr||fxs)begin err++;$display("FDOWN_FAULTS xr%b vs%b vq%b rstop%b xs%b",fx,fs,fq,fr,fxs);end\n'
           '  for(integer e=0;e<64;e++)if(reads[e]||expected_reads[e])begin\n'
           '   $display("EPOCH_READ_COUNTS epoch=%0d actual=%0d expected=%0d",e,reads[e],expected_reads[e]);\n'
           '   if(reads[e]!=expected_reads[e])err++;\n  end\n'
           '  $display("FDOWN_CONTROL gos%0d ends%0d gws%0d macwrites%0d lastcommit%0d windows%0d",gos,ends,gws,writes,lastcommit,gwin+1);\n'
           '  $display("FULLSIX_SOURCE_CHECK errors=%0d rawwrites=%0d gathers=%0d epochs=%0d",err,nw,nq,gos);\n'
           '  $display("FULLSIX_PREPARATORY_TRACE_END CAPfault=%b landfaults=%b otherVPfaults=%b",cap_fault,return_landing_fault,other_vp_fault);\n'
           '  $finish;\n end\nend\n\n')
src = src.replace(old_end, new_end)
sub('   wd=gold[beat]>>(266*half);', f'   wd=gold[{NB}*gwin+beat]>>(266*half);')
sub('if(beat>=20||addr!=40', f'if(beat>={NB}||addr!=40')
open(sys.argv[2], 'w').write(src)
print('FDOWN_TB_WRITTEN', sys.argv[2])
