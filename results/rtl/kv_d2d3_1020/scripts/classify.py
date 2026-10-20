import re,sys,json,collections
net_txt=open(sys.argv[1]).read(); rep=json.load(open(sys.argv[2]))
cells={}  # inst -> (master, {pin:net})
for m in re.finditer(r'\n\s*([A-Za-z_][\w$]*)\s+((?:\\\S+)|[\w$.\[\]]+)\s*\((.*?)\);',net_txt,re.S):
    master,inst,body=m.groups()
    if master in('module','input','output','wire','assign'): continue
    pins=dict((p,n.strip()) for p,n in re.findall(r'\.(\w+)\(([^()]*)\)',body))
    cells[inst.lstrip('\\').strip()]=(master,pins)
loads=collections.defaultdict(list); drv={}
OUT={'Y','QN','Q','H','L','CON','SN','dout','rd_data'}
for i,(ms,p) in cells.items():
    for pin,n in p.items():
        if pin in('Y','QN','Q','H','L','CON','SN') or ms.startswith('d2d_sram') and pin.startswith(('rd','dout','Q')): drv[n]=(i,pin)
        else: loads[n].append((i,pin))
def isff(i): return 'DFF' in cells[i][0] or 'DHL' in cells[i][0] or 'DLL' in cells[i][0]
def fwd_ffs(net,depth=6):
    seen=set();out=collections.Counter();front=[net]
    for _ in range(depth):
        nf=[]
        for n in front:
            for i,p in loads.get(n,[]):
                if i in seen: continue
                seen.add(i)
                if isff(i) or cells[i][0].startswith('d2d_sram'): out[re.sub(r'\[\d+\]','[]',i.split('$')[0])]+=1
                else:
                    for pp,nn in cells[i][1].items():
                        if pp=='Y': nf.append(nn)
        front=nf
    return out
def back_ffs(net,depth=8):
    seen=set();out=collections.Counter();front=[net]
    for _ in range(depth):
        nf=[]
        for n in front:
            if n not in drv: out['PORT:'+n]+=1; continue
            i,p=drv[n]
            if i in seen: continue
            seen.add(i)
            if isff(i): out[re.sub(r'\[\d+\]','[]',i.split('$')[0])]+=1
            else: nf+= [nn for pp,nn in cells[i][1].items() if pp!='Y']
        front=nf
    return out
for v in sorted(rep['violations'],key=lambda v:-v['loads']):
    n=v['net']; print(v['loads'],v['driver'][:70],'\n   FROM',dict(back_ffs(n).most_common(4)),'\n   TO',dict(fwd_ffs(n).most_common(3)))
