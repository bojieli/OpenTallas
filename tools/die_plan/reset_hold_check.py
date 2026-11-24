"""RESET-HOLD (QC-RSTCNT 11-24, COORD): needed reset hold of a bound die vs the hold it gets, per wavefront core reset pin.

A reset-less line (stations, delay lines, landings, plain 1-flop d/q modules) carries garbage from a core output until that
core has been held in reset long enough; a consumer core released before the garbage has flushed latches it.  For every
wavefront-reset core input pin: arrival = longest reset-less transport (cycles) from any core output (released at its
partition's published release R[src]) to the pin; needed hold = arrival - R[cons] (the ported RESET-HOLD-SWEEP flush4
--gen measurement, epyc11 RESET-HOLD-SWEEP/flush4.py 11-24 01:51: hard cores black-boxed, 1-flop ck/d/q modules and
native muxes counted, rs reset pins resetting).

The hold a die GETS = reset.source root counter (reset_tree.lock_stages: PLL lock or the tied reset.source.hold counter,
host-independent) + the host boot contract (rst_n low with clocks running, --host-contract).  Release offsets shift by
the counter uniformly, so the NEED does not change with the counter; it is compared with the provided hold.

  reset_hold_check.py BINDDIR --top TOP.sv [--plan PLAN] [--host-contract N] [--enforce] [--json OUT]
BINDDIR holds rtl/ and bind_reset.json (a bind --out dir).  Verdict PASS / SHORT; exit 1 on SHORT only with --enforce
(report-only by default; COORD: failing from S81 c9)."""
import argparse
import collections
import json
import os
import re
import sys
from pathlib import Path



def measure(RTL, TOPF, RESET, H=0, GEN=True, RING=4, A_SPINE=25, SPINE_RE="", START_RE="", log=print):
    """-> rows [{arr, inst, type, pin, cls, rel, need_hold, why}] (flush4 --gen semantics; need_hold at hold H)."""

    CTRL = ('ot_dp_rrelay','ot_dp_rgate','ot_dp_rsync','ot_dp_rtail','ot_dp_landing_','ot_dp_lockq','ot_dp_reset','ot_dp_rst')
    INST = re.compile(r"(?m)^[ \t]*(?:\(\*.*?\*\)\s*)?([A-Za-z_]\w*)\s+(#\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\)\s*)?([A-Za-z_][\w$]*)\s*\(\s*\.")
    KW = {'module','input','output','inout','wire','reg','assign','always','if','else','begin','end','case','for','generate','genvar','initial','function','task','localparam','parameter','return'}
    IDB = re.compile(r"\b([A-Za-z_][\w$]*)\b(?:\s*\[\s*(\d+)\s*\])?")
    def strip(t):
        t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
        return re.sub(r"//[^\n]*", "", t)
    def close(t,i):
        d=0
        while True:
            c=t[i]
            if c=='(':d+=1
            elif c==')':
                d-=1
                if d==0:return i
            i+=1
    def conns(s):
        out={};i=0
        for m in re.finditer(r"\.([A-Za-z_]\w*)\s*\(", s):
            if m.start()<i: continue
            e=close(s,m.end()-1); out[m.group(1)]=s[m.end():e]; i=e
        return out
    def ids(e):
        e=re.sub(r"\d+'[bhd][0-9a-fA-FxzXZ_]+","",e)
        return {(m.group(1), m.group(2) if m.group(2) is not None else None) for m in IDB.finditer(e)}
    def parse(f):
        t=strip(open(f).read())
        m=re.search(r"\bmodule\s+(\w+)",t); mod=m.group(1)
        hend=t.index(');',m.end()); hdr=t[m.end():hend]
        inp=re.findall(r"\binput\s+wire\s*(?:\[[^\]]*\]\s*)?(\w+)",hdr); outp=re.findall(r"\boutput\s+(?:wire|reg)?\s*(?:\[[^\]]*\]\s*)?(\w+)",hdr)
        body=t[hend:]
        E=[]; cores=[]; kinds=collections.Counter()
        pos=0
        for m in INST.finditer(body):
            mt,par,nm=m.group(1),m.group(2) or '',m.group(3)
            if mt in KW or m.start()<pos: continue
            lp=body.index('(',m.end(3)-0 if body[m.end(3):].lstrip().startswith('(') else m.end(3))
            e=close(body,lp); pos=e; cs=conns(body[lp+1:e]); kinds[mt]+=1
            if mt.startswith(CTRL): continue
            def P(k,d=1):
                x=re.search(r"\.%s\(\s*(\d+)"%k,par); return int(x.group(1)) if x else d
            if mt.startswith('ot_dp_dly'): w=P('D')
            elif mt=='ot_dp_st': w=1
            elif mt.startswith('ot_dp_clk_landing') or mt.startswith('ot_dp_landing'): w=RING
            elif mt.startswith('ot_dp_lk'): w=0
            elif mt.startswith('ot_dp_'): w=1
            elif GEN and mt.startswith('ot_bind_native_'): w=0
            elif GEN and set(k.lower() for k in cs) <= {'ck','clk','d','q'} and {'d','q'} <= set(k.lower() for k in cs): w=1
            else: w=None
            if w is None: cores.append((mt,nm,cs)); continue
            dst=set();src=set()
            for k,x in cs.items():
                k=k.lower() if GEN else k
                if k in('q','eq','y','qx','o'): dst|=ids(x)
                elif k in('clk','rst_n','fclk','t_rst_n','a_clk','strap_k','rst_xn','en') or 'rst' in k or 'start' in k or 'strap' in k: pass
                elif k in('d','ea','a','b','i') or (GEN and k=='s'): src|=ids(x)
            # ot_dp_st: d->q and ea->eq are separate; merged = conservative only by names
            for s in src:
                for d in dst: E.append((s,d,w,nm if mt.startswith('ot_dp_dly_ram') else None))
        for m in re.finditer(r"\bassign\s+([^=;]+)=([^;]+);",body):
            for s in ids(m.group(2)):
                for d in ids(m.group(1)): E.append((s,d,0,None))
        for m in re.finditer(r"\bwire\b[^;=\n]*?(\w+)\s*=\s*([^;]+);",body):
            for s in ids(m.group(2)): E.append((s,(m.group(1),None),0,None))
        return mod,inp,outp,E,cores,kinds
    RSK=('rs','rsi','rse','rs_n','rs_s')
    T={};
    _tt=strip(open(os.path.join(RTL,TOPF)).read())
    _used={m.group(1) for m in INST.finditer(_tt[_tt.index(');'):])}
    _mf={}
    for f in sorted(os.listdir(RTL)):
        if f.endswith('.sv') and f!=TOPF:
            try:
                _m=re.search(r"\bmodule\s+(\w+)",strip(open(os.path.join(RTL,f)).read()))
                if _m: _mf.setdefault(_m.group(1),f)
            except Exception: pass
    log('PARTITION MODULES in top',len(_used & set(_mf)))
    for f in sorted(set(_mf[m] for m in _used if m in _mf)):
        if True: 
            try: r=parse(os.path.join(RTL,f)); T[r[0]]=r
            except Exception as ex: log('PARSE_FAIL',f,repr(ex))
    # per type: longest from each input bus / from cores to each output bus and each core input
    def rclass(cs):
        nets=[x for k,x in cs.items() if ('rst' in k.lower() or (GEN and k in RSK)) and k not in('t_rst_n','first','first_i','frst')]
        if not nets: return 'noreset'
        n=' '.join(nets)
        if SPINE_RE and re.search(SPINE_RE,n): return 'spine'
        if START_RE and re.search(START_RE,n): return 'start'
        return 'wave'
    def dfs_type(r):
        mod,inp,outp,E,cores,kinds=r
        adj=collections.defaultdict(list); bits=collections.defaultdict(set)
        nodes=set()
        for s,d,w,_ in E: nodes.add(s);nodes.add(d)
        core_in=[];core_out={};CLS={}
        # declared direction of leaf pins unknown: an ident driven by an E-dst or port input is an input to the core; else output
        driven={d for _,d,_,_ in E}
        drvname={d[0] for d in driven}|set(inp)
        for mt,nm,cs in cores:
            c=rclass(cs); CLS[nm]=c
            for k,x in cs.items():
                if 'rst' in k.lower() or k.startswith(('clk','ck')) or (GEN and k in RSK): continue
                for i in ids(x):
                    nodes.add(i)
                    if i[0] in drvname: core_in.append((i,mt,nm,k))
                    else: core_out[i]=c if core_out.get(i) in (None,'noreset') else core_out[i]
        for n in nodes: bits[n[0]].add(n[1])
        for s,d,w,_ in E: adj[s].append((d,w))
        for nm,bs in bits.items():
            if None in bs:
                for b in bs:
                    if b is not None:
                        adj[(nm,None)].append(((nm,b),0)); adj[(nm,b)].append(((nm,None),0))
        # SCC condensation: whole-vector <-> bit zero loops; report positive cycles
        idx={};low={};st=[];on=set();comp={};C=[0];cnt=[0]
        def scc(v0):
            work=[(v0,iter(adj[v0]))]; idx[v0]=low[v0]=cnt[0];cnt[0]+=1;st.append(v0);on.add(v0)
            while work:
                v,it=work[-1]
                for (u,w) in it:
                    if u not in idx:
                        idx[u]=low[u]=cnt[0];cnt[0]+=1;st.append(u);on.add(u);work.append((u,iter(adj[u])));break
                    elif u in on: low[v]=min(low[v],idx[u])
                else:
                    work.pop()
                    if work: low[work[-1][0]]=min(low[work[-1][0]],low[v])
                    if low[v]==idx[v]:
                        while True:
                            u=st.pop();on.discard(u);comp[u]=C[0]
                            if u==v:break
                        C[0]+=1
        allv=set(nodes)
        for nm in inp+outp: allv.add((nm,None)); 
        for nm in inp+outp:
            for b in bits.get(nm,()):
                if b is not None: 
                    adj[(nm,None)].append(((nm,b),0)); adj[(nm,b)].append(((nm,None),0))
        for v in list(allv):
            if v not in idx: scc(v)
        # inside an SCC charge the sum of positive internal edges once, flag
        cad=collections.defaultdict(list); inner=collections.Counter()
        for s in list(adj):
            for d,w in adj[s]:
                if comp[s]==comp[d]:
                    if w>0: inner[comp[s]]+=w
                else: cad[comp[s]].append((comp[d],w))
        order=sorted(set(comp.values()),reverse=True)  # tarjan: comp ids are reverse topological -> high id first
        def longest(srcs):
            if not isinstance(srcs,dict): srcs={x:0 for x in srcs}
            D={}
            for s0,v in srcs.items():
                if s0 in comp and D.get(comp[s0],-10**9)<v: D[comp[s0]]=v
            for c in order:
                if c in D:
                    b=D[c]
                    for d,w in cad[c]:
                        if D.get(d,-1)<b+w: D[d]=b+w
            return D
        res=dict(inner={c:v for c,v in inner.items()},ports={},core={})
        res['cyc_names']=sorted({v[0] for v in comp if comp[v] in inner})[:20]
        def collect(D):
            o={p:D[comp[(p,None)]] for p in outp if (p,None) in comp and comp[(p,None)] in D}
            k={}
            for i,mt,nm,pin in core_in:
                c=comp.get(i)
                if c in D:
                    key=nm+'.'+pin
                    if D[c]>k.get(key,-1): k[key]=D[c]
            return o,k
        res['cls']=CLS
        res['from_wf']=collect(longest({n:-H for n,c in core_out.items() if c!='spine'}))
        res['from_sp']=collect(longest({n:A_SPINE for n,c in core_out.items() if c=='spine'}))
        for p in inp:
            if (not GEN and not p.startswith(('i_','ft','s_'))) or (GEN and re.match(r'(clk|fclk|arst|rst|strap|cland|start|run)',p)): continue
            o,k=collect(longest([(p,None)]))
            res['ports'][p]=(o,k)
        return res
    R={}
    for mod,r in T.items():
        R[mod]=dfs_type(r)
        if R[mod]['inner']: log('CYC',mod,len(R[mod]['inner']),max(R[mod]['inner'].values()),R[mod]['cyc_names'][:6])
    # top
    t=_tt
    hend=t.index(');'); body=t[hend:]
    drv=collections.defaultdict(list); snk=collections.defaultdict(list); par={}
    pos=0
    for m in INST.finditer(body):
        mt,nm=m.group(1),m.group(3)
        if mt not in T or m.start()<pos: continue
        lp=body.index('(',m.end(3)); e=close(body,lp); pos=e; par[nm]=mt
        _,inp,outp,*_=T[mt]; inp=set(inp);outp=set(outp)
        for k,x in conns(body[lp+1:e]).items():
            for i in ids(x):
                (drv if k in outp else snk)[i[0]].append((nm,k))
    asg=collections.defaultdict(set)
    for m in re.finditer(r"\bassign\s+([^=;]+)=([^;]+);",body):
        for s in ids(m.group(2)):
            for d in ids(m.group(1)): asg[d[0]].add(s[0])
    def drivers(n,seen=()):
        out=list(drv.get(n,()))
        for s in asg.get(n,()):
            if s not in seen: out+=drivers(s,seen+(n,))
        return out
    inst_in=collections.defaultdict(list)
    for n,l in snk.items():
        for dp in drivers(n):
            for sp in l: inst_in[sp].append(dp)
    A={}; state={}; LOOP=[]
    # arrival at an instance output bus
    rev=collections.defaultdict(list)
    for mod in T:
        for p,(o,k) in R[mod]['ports'].items():
            for q,w in o.items(): rev[(mod,q)].append((p,w))
    def out_arr(inst,q):
        key=(inst,q)
        if key in A: return A[key]
        if state.get(key)==1: LOOP.append(key); return (0,('LOOP',))
        state[key]=1; mod=par[inst]
        cands=[]
        if q in R[mod]['from_wf'][0]: cands.append((RP[inst]+R[mod]['from_wf'][0][q],('core_wf',inst,q)))
        if q in R[mod]['from_sp'][0]: cands.append((R[mod]['from_sp'][0][q],('core_sp',inst,q)))
        best=max(cands) if cands else (-10**9,('none',))
        for p,w in rev[(mod,q)]:
            a=in_arr(inst,p)
            if a[0]+w>best[0]: best=(a[0]+w,('via',inst,p,q,w)+(a[1],))
        state[key]=2; A[key]=best; return best
    def in_arr(inst,p):
        best=(-10**9,('src',inst,p))
        for d in inst_in.get((inst,p),()):
            a=out_arr(*d)
            if a[0]>best[0]: best=a
        return best
    RB=json.load(open(RESET))['parts']
    RP={i:RB[i]["release"] for i in par if i in RB}
    for i in par: RP.setdefault(i,0)
    A.clear(); state.clear()
    rows=[]
    for inst,mod in par.items():
        k={}
        for src in ('from_wf','from_sp'):
            for x,v in R[mod][src][1].items():
                vv=v+(RP[inst] if src=='from_wf' else 0)
                if vv>k.get(x,(-10**9,))[0]: k[x]=(vv,(src,inst))
        for p,(o,kk) in R[mod]['ports'].items():
            if not kk: continue
            a=in_arr(inst,p)
            for x,v in kk.items():
                if a[0]+v>k.get(x,(-10**9,))[0]: k[x]=(a[0]+v,('in',p,v,a[1]))
        for x,(v,why) in k.items():
            c=R[mod]['cls'].get(x.split('.')[0],'?')
            rel=RP[inst]+1 if c=='wave' else None
            rows.append(dict(arr=v,inst=inst,type=mod,pin=x,cls=c,rel=rel,need_hold=(v+H-rel) if rel is not None else None,why=why))
    return rows


def summary(rows, top=15):
    wave = [r for r in rows if r["cls"] == "wave"]
    worst = sorted(wave, key=lambda r: -(r["need_hold"] or 0))
    return dict(pins=len(wave), parts=len({r["inst"] for r in wave}), need=max([r["need_hold"] for r in wave] or [0]),
                worst=[dict(inst=r["inst"], type=r["type"], pin=r["pin"], need=r["need_hold"], arr=r["arr"], rel=r["rel"])
                       for r in worst[:top]])


def short_at(rows, hold):
    """wavefront pins / parts / types still short at a provided hold."""
    bad = [r for r in rows if r["cls"] == "wave" and r["need_hold"] is not None and r["need_hold"] > hold]
    return dict(hold=hold, pins=len(bad), parts=len({r["inst"] for r in bad}), types=sorted({r["type"] for r in bad}))


def provided(plan_path=None, host_contract=0):
    """the hold a die gets: root counter stages (reset_tree.lock_stages) + host contract."""
    counter = 0
    if plan_path:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import reset_tree as RT
        import schema
        counter = RT.lock_stages(schema.Plan(schema.load(plan_path), plan_path))
    return dict(counter=counter, host_contract=int(host_contract), total=counter + int(host_contract))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bind_dir")
    ap.add_argument("--top", required=True)
    ap.add_argument("--plan")
    ap.add_argument("--host-contract", type=int, default=0)
    ap.add_argument("--counter", type=int, help="override the counter stages (else from --plan)")
    ap.add_argument("--enforce", action="store_true")
    ap.add_argument("--json")
    ap.add_argument("--rows")
    ap.add_argument("--spine-re", default="")
    ap.add_argument("--start-re", default="")
    a = ap.parse_args(argv)
    sys.setrecursionlimit(10 ** 7)
    bd = Path(a.bind_dir)
    rows = measure(str(bd / "rtl"), a.top, str(bd / "bind_reset.json"), H=0, SPINE_RE=a.spine_re, START_RE=a.start_re)
    s = summary(rows)
    pv = provided(a.plan, a.host_contract)
    if a.counter is not None:
        pv = dict(counter=a.counter, host_contract=a.host_contract, total=a.counter + a.host_contract)
    sh = short_at(rows, pv["total"])
    verdict = "PASS" if sh["pins"] == 0 else "SHORT"
    out = dict(verdict=verdict, need=s["need"], provided=pv, short=sh, pins=s["pins"], parts=s["parts"], worst=s["worst"],
               enforce=a.enforce, bind_dir=str(bd))
    print(f"RESET-HOLD {verdict}: need {s['need']} clk, provided {pv['total']} (counter {pv['counter']} + host "
          f"{pv['host_contract']}); short {sh['pins']} pins / {sh['parts']} parts / {len(sh['types'])} types; "
          f"{s['pins']} wavefront core reset pins in {s['parts']} parts")
    for w in s["worst"][:5]:
        print(f"  need {w['need']} {w['inst']} {w['type']} {w['pin']} (arr {w['arr']}, rel {w['rel']})")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1) + "\n")
    if a.rows:
        Path(a.rows).write_text(json.dumps(rows) + "\n")
    return 1 if (a.enforce and verdict != "PASS") else 0


if __name__ == "__main__":
    sys.exit(main())
