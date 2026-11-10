# HBM-CORES-B q3bc CF2 bench: tb.sv re-baselined for the +1 at scan end.  Only in the one cycle after gold init_busy falls may
# gate configured/init_busy/fault differ (scan end only: init_busy also falls after every row drain, which does not move): gate must show gold's previous configured/fault and init_busy=1. All else exact.
import re
s=open('tb.sv').read()
def rep(a,b):
    global s
    assert s.count(a)==1,(a,s.count(a)); s=s.replace(a,b)
m=re.search(r'wire \[382:0\] gall=\{go0,go1,go2,go3,',s); assert m
rep('wire [382:0] gall={go0,go1,go2,go3,','wire g_end=scan&&p_ib&&!go2&&live!=0;\n wire [382:0] gall={go0,g_end?p_cfg:go1,g_end?1\'b1:go2,g_end?p_flt:go3,')
rep(' reg p_cfg=0, p_flt=0;',' reg p_cfg=0, p_flt=0, p_ib=0, scan=0;')
rep('p_cfg=g_cfg; p_flt=g_flt;','if(g_end) scan=0; if(desc_v) scan=1; p_cfg=go1; p_flt=go3; p_ib=go2; if(u_gate._hcbr_clr) nclr=nclr+1; if(u_gate._hcbr_p1 || u_gate._hcbr_p2) begin nkill=nkill+1; errs=errs+1; $display("ASSERT restart-kill reached cyc %0d", cyc); end')
rep('  $display("LOCKSTEP','  $display("RESTART_COVER clr %0d kill_reached %0d", nclr, nkill);\n  $display("LOCKSTEP')
rep('nrow=1+($urandom%10); base=$urandom%(256-nrow); bad=($urandom%4)==0;',
    'nrow=1+($urandom%10); base=$urandom%(256-nrow); bad=($urandom%4)==0; top=($urandom%3)==0; if(top) begin base=256-nrow; bad=($urandom%2)==0; end if(sweep!=0) begin bad=0; top=0; end')
rep('if(bad && r==base+nrow/2)','if(bad && r==(top?base+nrow-1:base+nrow/2))')
rep(' integer live=0,',' integer nclr=0, nkill=0, sweep=0, lgap=256, top=0, off=0, live=0,')
rep('  if(!$value$plusargs("seed=%d", seed)) seed=1;','  if(!$value$plusargs("seed=%d", seed)) seed=1; void\'($value$plusargs("sweep=%d", sweep)); void\'($value$plusargs("lgap=%d", lgap));')
rep('extra=$urandom%4; repeat(256+extra) step;','''extra=$urandom%4;
   if(sweep!=0) begin off=sweep+(t%8); repeat(off) step; cfgw({8'd255,3'd0}, 256'd1); repeat(8) step; $display("SWEEP off %0d gold_fault %b gate_fault %b", off, go3, to3); end
   else repeat(lgap+extra) step;''')
open('tb_cf2.sv','w').write(s)
