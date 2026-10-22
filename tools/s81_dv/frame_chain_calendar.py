#!/usr/bin/env python3
# TOKc-S81b 10-22: usage frame_chain_calendar.py <slice_top.sv>  (one line per chained frame: R0, upstream gate, needed delay)
# chained-frame calendar check: frame lanes clocked by an upstream frame's xok start when the upstream frame's own
# hop-0 gates open; report needed reset delay d = max(G_up_eff) - G_own_eff for each chained frame.
import re,sys,json
t=open(sys.argv[1]).read()
drv={}
for m in re.finditer(r'dsfd_rly_1_\w+ \S+ \(\.ck\(([\w\[\]]+)\), \.rs\((\w+)\), \.i\((\w+)\), \.o\((\w+)\)\);',t): drv[m.group(4)]=m.group(3)
asg={m.group(1):m.group(2) for m in re.finditer(r'assign (\w+) = (\w+);',t)}
def depth(n):
    d=0
    while True:
        if n in drv: n=drv[n]; d+=1
        elif n in asg: n=asg[n]
        else: return d
icg={m.group(4):(m.group(2),m.group(3)) for m in re.finditer(r'ICGx4_ASAP7_75t_R (\w+) \(\.CLK\(([\w\[\]]+)\), \.ENA\((\w+)\), \.SE\(\S+\), \.GCLK\((\w+)\[0\]\)\);',t)}
fr={}
for m in re.finditer(r'col_\w+ #\(\.INSTANCE\("(\w+)"\)\) \w+ \((.*?)\);',t):
    inst,body=m.groups(); rst=re.search(r'\.rst_n\((\w+)\)',body).group(1)
    xk=[s.strip() for s in re.search(r'\.xk\(\{([^}]*)\}\)',body).group(1).split(',')]
    lanes=[]
    for e in xk:
        mm=re.match(r'(\w+)\[(\d+)\]',e)
        if not mm:  # flight wire: find dv_flight ck_in
            f=re.search(r'\(\.ck_in\((\w+)\[(\d+)\]\), [^;]*\.ck_out\(%s\)'%e,t); mm=f
        base,N=mm.group(1),int(mm.group(2)); ck,ena=icg[base]
        lanes.append((N,depth(ena),ck))
    fr[inst]=dict(R=depth(rst),rst=rst,lanes=lanes)
out={}
for i,f in fr.items():
    ups={re.match(r'(u_f_\w+?)_xok',ck).group(1) for N,g,ck in f['lanes'] if '_xok' in ck}
    if not ups: continue
    up=ups.pop(); u=fr.get(up)
    if not u: print(i,'upstream',up,'not in cut'); continue
    g_up=max(g+N%2 for N,g,ck in u['lanes']); g_own=max(g+N%2 for N,g,ck in f['lanes'])
    r0=f['R']+4
    d=max(0,g_up-r0)
    out[i]=dict(upstream=up,R0=r0,G_own=g_own,G_up=g_up,delay=d,rst=f['rst'])
    print(i,out[i])
