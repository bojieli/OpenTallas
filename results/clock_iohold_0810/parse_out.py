import re,sys,statistics as st
t=open(sys.argv[1]).read().split("Startpoint:")[1:]
L=[];H=[]
for b in t:
    lines=b.splitlines()
    # launch clock arrival at the startpoint CLK pin = time on the line ending with "/CLK (...)" before data
    clk=None;arr=None
    for ln in lines:
        m=re.match(r"\s.*?(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+[\^v]\s+\S+/CLK\s",ln)
        if m and arr is None: clk=float(m.group(2))
        m=re.match(r"\s+(-?\d+\.\d+)\s+data arrival time",ln)
        if m: arr=float(m.group(1)); break
    if clk is None or arr is None: continue
    L.append(clk);H.append(arr-clk)
q=lambda v,p: sorted(v)[int(p*(len(v)-1))]
print(f"n {len(H)} launch_ins mean {st.mean(L):.1f} min {min(L):.1f} max {max(L):.1f} | cq+dtx min {min(H):.2f} p10 {q(H,.1):.2f} p50 {q(H,.5):.2f}")
m=st.mean(L)
for Hc in (0,10,15,20):
    pad=[max(0,(m-l)+12.5+Hc-h) for l,h in zip(L,H)]
    print(f"H {Hc}: outputs needing pad {sum(p>0 for p in pad)} max {max(pad):.1f} sum {sum(pad):.0f}")
