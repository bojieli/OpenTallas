import re,glob,os,collections,sys
LINE = re.compile(r"^\s*(?:(\d+)\s+([\d.]+)\s+)?(-?[\d.]+)\s+(-?[\d.]+)\s+([\^v])\s+(\S+)\s+\((\S+)\)")
for f in sorted(glob.glob('/tmp/setup-triage-local/*/paths.log')):
    job=f.split('/')[-2]; t=open(f).read()
    if 'TRI_FULL_BEGIN' not in t: continue
    full=t.split('TRI_FULL_BEGIN',1)[1].split('TRI_LOC_BEGIN',1)[0]
    c=collections.Counter(); wd=0
    for blk in re.split(r"\n(?=Startpoint: )", full):
        if not blk.startswith('Startpoint'): continue
        st=re.search(r"Startpoint: (\S+)",blk)[1]; en=re.search(r"Endpoint: (\S+)",blk)[1]
        for part,stop in ((blk.split('data arrival time')[0],st),(blk.split('data arrival time')[-1],en)):
            for l in part.splitlines():
                m=LINE.match(l)
                if not m: continue
                inst=m[6].rsplit('/',1)[0]
                if inst==stop or m[6]==stop: break
                pre=re.match(r"[a-z_]+",inst)
                k=pre[0] if pre else inst[:8]
                if k not in ('clkbuf_','delaybuf_','clkload','clk','ck','core_clk'): c[k]+=1
                if k in ('wire','rebuffer','split','place','max_length'): wd+=float(m[3])
    if c: print(f"{job:45s} {dict(c.most_common(6))} nonCTS_ps_sum={wd:.0f}")
