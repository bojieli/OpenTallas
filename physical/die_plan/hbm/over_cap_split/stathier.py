"""Parse a mapped yosys .stat (stat -liberty, hierarchical): per module local cells, submodule instance counts,
totals incl. submodules.  usage: stathier.py STAT [maxdepth] [mincells]"""
import re,sys
def short(n): return re.sub(r'[$]paramod[$]?[0-9a-f]*\\?','',n).replace("s32'",'')
def parse(path):
    t=open(path).read(); t=t[:t.find('=== design hierarchy ===')]
    secs=re.split(r'(?m)^=== (.+) ===\s*$',t)[1:]
    mods={}
    for name,body in zip(secs[0::2],secs[1::2]):
        types=[]
        for line in body.split('Chip area')[0].splitlines():
            m=re.match(r'^\s+(\d+)\s+(?:\S+\s+)?(\S+)\s*$',line)
            if m and m.group(2) not in ('wires','bits','ports','cells','submodules','memories','processes') and not m.group(2).endswith('bits'):
                types.append((int(m.group(1)),m.group(2)))
        mods[name.strip()]=types
    loc={};sub={};mac={}
    for n,ty in mods.items():
        sub[n]=[(c,x) for c,x in ty if x in mods]; loc[n]=sum(c for c,x in ty if 'ASAP7' in x); mac[n]=[(c,x) for c,x in ty if x.startswith('ot_sram') or x.startswith('fakeram')]
    tot={}
    def T(n):
        if n not in tot: tot[n]=loc[n]+sum(c*T(x) for c,x in sub[n])
        return tot[n]
    for n in mods: T(n)
    tops=[n for n in mods if not any(n==x for v in sub.values() for _,x in v)]
    parse.mac=mac
    return mods,loc,sub,tot,tops
def show(path,md=4,mn=5000):
    mods,loc,sub,tot,tops=parse(path)
    def rec(n,d,mult):
        print('  '*d+'%9d x%-3d local %8d  %s'%(tot[n],mult,loc[n],short(n)[:100]))
        if d<md:
            for c,x in sorted(sub[n],key=lambda a:-a[0]*tot[a[1]]):
                if tot[x]*c>=mn: rec(x,d+1,c)
    for t in tops: rec(t,0,1)
if __name__=='__main__':
    show(sys.argv[1],int(sys.argv[2]) if len(sys.argv)>2 else 4,int(sys.argv[3]) if len(sys.argv)>3 else 5000)
