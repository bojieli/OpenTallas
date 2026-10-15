"""io_tcl (place_pin) for the three Q per-mac containers: seams on M4 at identical y both sides (0.048 grid,
offset 0.012), die-facing pins on M5/M3: ctl S face (operands from the S bank), mac N face (p* results to the N bank)."""
import json,math
NETS=json.load(open('port_nets.json'))
H=216.0; WC=49.68; WM=214.272
C,M0,M1='ot_s81_q_ctl_native_graph','ot_s81_q_mac0_native_graph','ot_s81_q_mac1_native_graph'
def idx(mod,ports):
    out={}
    for p in ports:
        for i,n in enumerate(NETS[mod].get(p,[])): out.setdefault(n,[]).append((p,i))
    return out
def seam(ctl_ports,mac,mac_ports):
    ci=idx(C,ctl_ports); mi=idx(mac,mac_ports)
    nets=sorted(set(ci)|set(mi)); assert set(ci)==set(mi),(len(set(ci)-set(mi)),len(set(mi)-set(ci)))
    t0=math.ceil((10.8-0.012)/0.048); t1=math.floor((H-10.8-0.012)/0.048); n=len(nets); step=(t1-t0)/(n-1)
    return {nt:round(0.012+(t0+round(k*step))*0.048,3) for k,nt in enumerate(nets)},ci,mi,n/(t1-t0+1)
L={C:[],M0:[],M1:[]}
def pp(mod,pin,layer,x,y): 
    sz='{0.192 0.024}' if layer=='M4' else ('{0.024 0.192}' if layer=='M5' else '{0.018 0.144}')
    L[mod].append(f'place_pin -pin_name {{{pin}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} -pin_size {sz} -force_to_die_boundary')
dens={}
for face,mac,cp,mp,cx,mx in (('W',M0,['w_i','w_o'],['e_i','e_o'],0.0,WM),('E',M1,['e_i','e_o'],['w_i','w_o'],WC,0.0)):
    Y,ci,mi,r=seam(cp,mac,mp); dens[face]=round(r,4)
    for nt,y in Y.items():
        for p,i in ci[nt]: pp(C,f'{p}[{i}]','M4',cx,y)
        for p,i in mi[nt]: pp(mac,f'{p}[{i}]','M4',mx,y)
def row(mod,pins,w,yface):
    # alternate M5 (0.048, offset 0.024) and M3 (0.036, offset 0.018) tracks across the face, centred
    n=len(pins); span=min(w-4.32,n*0.06); x=(w-span)/2
    for k,p in enumerate(pins):
        lay='M5' if k%2==0 else 'M3'; pit,off=(0.048,0.024) if lay=='M5' else (0.036,0.018)
        xx=x+k*span/max(1,n-1); xx=off+round((xx-off)/pit)*pit
        pp(mod,p,lay,xx,yface)
row(C,['clock_0']+[f'{p}[{i}]' for p in ('s_i','s_o') for i in range(len(NETS[C].get(p,[])))],WC,0.0)
for mac in (M0,M1):
    row(mac,['clock_0']+[f'{p}[{i}]' for p in ('s_i','s_o') for i in range(len(NETS[mac].get(p,[])))],WM,H)
for mod,l in L.items(): open(f'{mod}_pins.tcl','w').write('# S81 Q per-mac container pins (die lead 10-14): seams M4 same y both sides\n'+'\n'.join(l)+'\n')
print(dens,{m:len(l) for m,l in L.items()})
