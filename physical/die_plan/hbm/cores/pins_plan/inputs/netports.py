import re,sys,json,collections
# extract module ports (name,dir,width) from a yosys netlist
mods={};cur=None
rx_m=re.compile(r'^\s*module\s+(\S+)\s*\(');rx_p=re.compile(r'^\s*(input|output|inout)\s+(?:wire\s+)?(?:\[(\d+):(\d+)\]\s*)?(\S+?)\s*;')
for line in open(sys.argv[1]):
    m=rx_m.match(line)
    if m: cur=m.group(1).lstrip('\\'); mods[cur]=[]; continue
    if cur is None: continue
    if line.strip().startswith('endmodule'): cur=None; continue
    m=rx_p.match(line)
    if m:
        d,a,b,n=m.groups();w=abs(int(a)-int(b))+1 if a else 1
        mods[cur].append([n.lstrip('\\'),d,w,int(b) if b else 0])
base=lambda s: re.sub(r'^\$paramod\$[0-9a-f]+\\','',re.sub(r'^\$paramod\\([^\\]+)\\.*$',r'\1',s))
out=collections.defaultdict(dict)
for k,v in mods.items(): out[base(k)][k]=v
json.dump(out,open(sys.argv[2],'w'))
for b,vs in sorted(out.items()):
    print(b,len(vs),[sum(p[2] for p in v) for v in vs.values()][:4])
