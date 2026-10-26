import re,sys,collections
T=open(sys.argv[1]).read()
inst=re.findall(r'^\s*(\w+)\s+(?:#\(.*?\)\s*)?(\w+)\s*\((.*?)\);\s*$',T,re.M)
def pins(s): return dict(re.findall(r'\.(\w+)\(([^()]*?)\)',s))
rel={}  # net -> release cycle relative to rst_n release (cycle index of first ck edge with o=1)
drv={}
for m,n,p in inst:
    if m.startswith('dsfd_rly_1_'):
        P=pins(p); drv[P['o'].strip()]=(P['i'].strip(),P['ck'].strip(),n)
def R(net,depth=0):
    net=net.strip()
    if net in rel: return rel[net]
    if net=='rst_n': return 0
    if net not in drv: return None
    i,ck,n=drv[net]; r=R(i)
    rel[net]=None if r is None else r+1
    return rel[net]
lands=[]
for m,n,p in inst:
    if m.startswith('dsfd_dvland'):
        P=pins(p); lands.append((n,P))
# map ckf_d -> flight -> fck chain -> ICG
flight={}
for m,n,p in inst:
    if m=='dv_flight_sim' or 'dv_flight_sim' in m:
        pass
for mm in re.finditer(r'dv_flight_sim #\(\.W\((\d+)\), \.F\((\d+)\)\) (\w+)__flight \((.*?)\);',T):
    P=pins(mm.group(4)); flight[mm.group(3)]=(int(mm.group(2)),P['ck_in'].strip())
icg={}
for m,n,p in inst:
    if m.startswith('ICGx'):
        P=pins(p); icg[P['GCLK'].strip()]=(P['ENA'].strip(),P['CLK'].strip(),n)
stations={}
for m,n,p in inst:
    if m.startswith('dsfd_dvrlyh_') or m.startswith('dsfd_dvrly_'):
        P=pins(p); stations[P['ck_o'].strip()]=(P['ck'].strip(),m)
for n,P in lands:
    k=int(re.search(r"'[dh](\w+)",P['k']).group(1)); 
    F,ck=flight.get(n,(0,P['ck_f'].strip()))
    N=0; c=ck
    while c in stations: c=stations[c][0]; N+=1
    if c in icg: ena,clk,gn=icg[c]; G=R(ena)
    else: ena=clk=None; G='?'
    R0=R(P['rs'])
    ok='?'
    if isinstance(G,int) and isinstance(R0,int):
        d=R0-G
        ok = 'OK' if (k+d-4 <= F <= k+d-1) else 'BAD'
    print(f"{n:28s} K={k} F={F} N={N} G={G} R0={R0} R0-G={(R0-G) if isinstance(G,int) and isinstance(R0,int) else '?'} srcclk={clk} {ok}")

print('--- binder-belief vs netlist')
def base(net):
    n=0
    while net.startswith('rsg_'): net=drv[net][0]; n+=1
    return net,n
for n,P in lands:
    F,ck=flight.get(n,(0,P['ck_f'].strip())); N=0; c=ck
    while c in stations: c=stations[c][0]; N+=1
    ena=icg[c][0]; sl,ns=base(ena); rl,nr=base(P['rs'].strip())
    h=N%2; believed = (ns+h) if ns else (h-nr)  # binder's dr_-ds_
    print(f"{n:24s} sleaf={sl}({R(sl)}) +{ns}  rleaf={rl}({R(rl)}) +{nr} N%2={h} binder dr-ds={believed} netlist dr-ds={R(rl)-R(sl)} diff={R(rl)-R(sl)-believed}")
