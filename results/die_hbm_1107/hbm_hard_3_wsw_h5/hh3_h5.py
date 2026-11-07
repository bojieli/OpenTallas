import sys,re
src,dst=sys.argv[1],sys.argv[2]
s=open(src).read()
a="parameter integer HREG=0, parameter integer GIN=0)("
assert s.count(a)==1; s=s.replace(a,"parameter integer HREG=0, parameter integer GIN=0, parameter integer SEL16=0)(")
a="""   for(ps=0;ps<((HREG>=4)?7:6);ps=ps+1)begin:g_s
    localparam integer LO=(HREG>=4&&ps==6)?256:48*ps,W=(HREG>=4)?((ps==6)?30:(ps==5)?16:48):((ps==5)?286-240:48);"""
b="""   // SEL16 (HBM-HARD-3 11-07, default 0 = unchanged): one sel_q set per 16-bit slice, so each select flop drives
   // at most 16 AND legs (vH4 routed: 54 slew nets, all one sel_q bit through one buffer to 48 legs). Same cycle.
   for(ps=0;ps<((SEL16!=0)?18:(HREG>=4)?7:6);ps=ps+1)begin:g_s
    localparam integer LO=(SEL16!=0)?16*ps:(HREG>=4&&ps==6)?256:48*ps,
                       W=(SEL16!=0)?((ps==17)?14:16):(HREG>=4)?((ps==6)?30:(ps==5)?16:48):((ps==5)?286-240:48);"""
assert s.count(a)==1; s=s.replace(a,b)
a="sel_q<=((KMUT==2&&pi==5&&ps==2)||(KMUT==7&&pi==5&&ps==6))?sel_q2:grant;"
b="sel_q<=((KMUT==2&&pi==5&&ps==2)||(KMUT==7&&pi==5&&ps==6)||(KMUT==9&&pi==5&&ps==11))?sel_q2:grant;"
assert s.count(a)==1; s=s.replace(a,b)
open(dst,'w').write(s)
