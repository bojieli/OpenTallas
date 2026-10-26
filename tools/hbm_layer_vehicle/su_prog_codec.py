#!/usr/bin/env python3
"""TOK-HBM-SU 2026-10-26: decode the su_prog configuration drives of a slice replay into the SU quarter command
lines (ot_hbm_su_programme_pslice_c5 column image, su_programme_compile.lower_columns), optionally re-time a field,
re-encode with the SAME lower_columns code, and rewrite the drives.  Round-trip (no change) must reproduce the
original drive stream bit-exactly (checked)."""
import argparse, json, sys, tempfile, hashlib
from pathlib import Path
P_BANK, P_DATA, P_LEN, P_ROW, P_START, P_WE = 141, 142, 143, 144, 145, 146
SB, NCOL = 2470, 10
VMW_LO, VMW_W = 128, 312

def rd(d):
    H=[int(l,16) for l in (d/'hdr.mem').read_text().split()]
    V=[int(l,16) for l in (d/'val.mem').read_text().split()]
    M=[int(l,16) for l in (d/'msk.mem').read_text().split()]
    return H,V,M

def fields(h): return dict(t=h>>62,dom=(h>>60)&3,port=(h>>44)&0xffff,rec=((h>>32)&0xfff)-1,cyc=h&0xffffffff)

def mkh(t,dom,port,rec,cyc): return (t<<62)|(dom<<60)|(port<<44)|((rec+1)<<32)|cyc

def decode(H,V):
    ev=[(i,fields(h)) for i,h in enumerate(H)]
    pr=[(i,f) for i,f in ev if f['t']==1 and f['port'] in range(141,147)]
    assert pr and all(f['dom']==1 for _,f in pr)
    cyc0=min(f['cyc'] for _,f in pr); cyc1=max(f['cyc'] for _,f in pr)
    st={p:0 for p in range(141,147)}; byc={}
    for i,f in pr: byc.setdefault(f['cyc'],[]).append((f['port'],V[i]))
    writes=[]; start=[]; length=None
    for c in range(cyc0,cyc1+1):
        for p,v in byc.get(c,[]): st[p]=v
        if st[P_WE]&1: writes.append((c,st[P_BANK]&0xffff,st[P_ROW]&0x7f,st[P_DATA]&((1<<256)-1)))
        if st[P_START]&1: start.append(c); length=st[P_LEN]&0xffff
    return pr,writes,start,length

def lines_from(writes,N):
    lines=[0]*N; meta=[]
    for c in range(NCOL):
        w=[(b-32*c,r,d) for _,b,r,d in writes if 32*c<=b<32*c+32]
        loc=sorted({b for b,_,_ in w})
        nidx=(N+15)//16; image_ib=(nidx+127)//128
        idxb=set(range(image_ib)); dbase=min(b for b in loc if b not in idxb)
        idx={}; dic={}
        for b,r,d in w:
            if b<image_ib: idx[b*128+r]=d
            else: dic[(b-dbase)*128+r]=d
        for e in range(N):
            k=(idx[e//16]>>(16*(e%16)))&0xffff
            lines[e]|=dic[k]<<(256*c)
        meta.append(dict(col=c,dbase=dbase,image_ib=image_ib,dict=len(dic)))
    return lines,meta

def encode(lines,meta,tools):
    sys.path.insert(0,str(tools))
    import su_programme_compile as S
    with tempfile.TemporaryDirectory() as t:
        t=Path(t); (t/'src.mem').write_text(''.join(f'{x:0{(SB+3)//4}x}\n' for x in lines))
        ib=meta[0]['dbase']; res=(ib-1)*2048+1 if ib>1 else None
        m=S.lower_columns(t/'src.mem',t/'o',line_bits=SB,resident_edges=res if res and res>=len(lines) else None)
        cfg=[(int(l[:4],16),int(l[4:6],16),int(l[6:],16)) for l in (t/'o'/'config.mem').read_text().split()]
    return cfg,m

def vmw(x): return (x>>VMW_LO)&((1<<VMW_W)-1)

def main():
    a=argparse.ArgumentParser(); a.add_argument('replay',type=Path); a.add_argument('--tools',type=Path,required=True)
    a.add_argument('--vmw-shift',type=int,default=0,help='extra drain (vmw) edges: die PIN_REG 1 lane write +4')
    a.add_argument('--issue-shift',type=int,default=0,help='all non-fill fields (control/vmw/rf/red/tree) +D edges; checks +D')
    a.add_argument('--out',type=Path)
    a=a.parse_args()
    H,V,M=rd(a.replay); pr,writes,start,N=decode(H,V)
    lines,meta=lines_from(writes,N)
    rt,_=encode(lines,meta,a.tools)
    same=[(b,r,d) for _,b,r,d in writes]==rt
    nd=sum(1 for x in lines for p in range(8) if (vmw(x)>>(39*p+38))&1)
    de=[e for e,x in enumerate(lines) if any((vmw(x)>>(39*p+38))&1 for p in range(8))]
    vr=[e for e,x in enumerate(lines) if any(((x>>440)>>(30*p+29))&1 for p in range(8))]
    rep=dict(writes=len(writes),write_cycles=[writes[0][0],writes[-1][0]],start=start,length=N,meta=meta,
             roundtrip_exact=same,drains=nd,drain_edges=[de[0],de[-1]] if de else None,fill_edges=[vr[0],vr[-1]] if vr else None)
    if a.out:
        assert same, 'decode does not round-trip; refuse'
        s=a.vmw_shift; D=a.issue_shift; assert s>=0 and D>=0
        N2=max(N+D, (de[-1]+D+s+1) if de else N)
        mask=((1<<VMW_W)-1)<<VMW_LO; fmask=((1<<240)-1)<<440; full=(1<<SB)-1; omask=full&~fmask&~mask
        L=lambda e: lines[e] if 0<=e<N else 0
        new=[(L(e)&fmask)|(L(e-D)&omask)|(L(e-D-s)&mask) for e in range(N2)]
        cfg,man=encode(new,meta,a.tools)
        # drives: same last-write cycle (start fixed), one write per cycle, writes earlier if more
        st_c=start[0]; last_w=writes[-1][0]; c0=last_w-len(cfg)+1
        assert all(writes[i+1][0]==writes[i][0]+1 for i in range(len(writes)-1)), 'original writes not one per cycle'
        keep=[(i,f) for i,f in enumerate(fields(h) for h in H)]
        prset={i for i,_ in pr}
        ev=[]
        lst={}
        def put(c,p,v):
            if lst.get(p)!=v: ev.append((c,p,v)); lst[p]=v
        # replay original non-config prog drives (start/len) relative; regenerate we/bank/row/data
        first_c=min(c0,pr[0][1]['cyc'])
        for k,(b,r,d) in enumerate(cfg):
            c=c0+k; put(c,P_WE,1); put(c,P_BANK,b); put(c,P_ROW,r); put(c,P_DATA,d)
        put(last_w+1,P_WE,0)
        for i,f in pr:
            if f['port'] in (P_START,): ev.append((f['cyc'],f['port'],V[i]))
            if f['port']==P_LEN: ev.append((f['cyc'],f['port'],N2 if V[i]==N else V[i]))
        ev.sort(key=lambda x:x[0])
        # rebuild: domain blocks contiguous and cycle sorted; replace the prog drives inside dom1 block
        out_h,out_v,out_m=[],[],[]
        rec_ck={f['rec'] for i,f in keep if f['dom']==1 and f['t']==2}
        assert len(rec_ck)==1, rec_ck
        Hs=list(H)
        for i,f in keep:
            if f['dom']==1 and f['t']==2: Hs[i]=mkh(2,1,f['port'],f['rec'],f['cyc']+D)
        H=Hs
        dom1=[(fields(H[i])['cyc'],0,i) for i,f in keep if f['dom']==1 and f['t'] in (1,2) and i not in prset]
        dom1+= [(c,1,(p,v)) for c,p,v in ev]
        dom1.sort(key=lambda x:(x[0],x[1]))
        blocks={0:[],1:[],2:[]}
        for i,f in keep:
            if f['t'] in (1,2) and f['dom']!=1: blocks[f['dom']].append(i)
        order=[]
        for d in (0,1,2):
            if d==1:
                for c,kind,x in dom1:
                    if kind==0: out_h.append(H[x]); out_v.append(V[x]); out_m.append(M[x])
                    else: out_h.append(mkh(1,1,x[0],-1,c)); out_v.append(x[1]); out_m.append(0)
            else:
                for i in blocks[d]: out_h.append(H[i]); out_v.append(V[i]); out_m.append(M[i])
        # keep any type-3 tail
        out_h+= [h for h in H if (h>>62)==3]; out_v+=[0]*(len(out_h)-len(out_v)); out_m+=[0]*(len(out_h)-len(out_m))
        a.out.mkdir(parents=True,exist_ok=True)
        W=1024
        (a.out/'hdr.mem').write_text(''.join(f'{h:016x}\n' for h in out_h))
        (a.out/'val.mem').write_text(''.join(f'{v:0{W}x}\n' for v in out_v))
        (a.out/'msk.mem').write_text(''.join(f'{m:0{W}x}\n' for m in out_m))
        for fn in ('vm_pre.txt',):
            (a.out/fn).write_bytes((a.replay/fn).read_bytes())
        idx=json.loads((a.replay/'index.json').read_text())
        idx['events']=len(out_h); idx['drives']=sum(1 for h in out_h if h>>62==1); idx['checks']=sum(1 for h in out_h if h>>62==2)
        idx.setdefault('diagnostic',{})['su_programme_retime']=dict(tool='tools/hbm_layer_vehicle/su_prog_codec.py',
            vmw_shift=s,issue_shift=D,reason='die binds pgslice_lg PIN_REG 1 (leaf split): lane write/first output +4 (leaf_split_latency su_write); '
            'programme was lowered for PIN_REG 0, so every drain (vmw) command moves +4 edges (checks already +4); '
            'issue_shift: lane write-backs (all 32 store banks, single bank write port) must not land on a fill-return write '
            '(pgslice st_conflict fw&&lw); every issue group is delayed until the last fill of the record has landed',
            lines_before=N,lines_after=N2,config_writes_before=len(writes),config_writes_after=len(cfg),
            first_write_cycle=c0,source_replay_sha256=hashlib.sha256((a.replay/'hdr.mem').read_bytes()).hexdigest())
        (a.out/'index.json').write_text(json.dumps(idx,indent=1)+'\n')
        rep.update(out=str(a.out),lines_after=N2,writes_after=len(cfg),first_write=c0,events=len(out_h))
    print(json.dumps(rep,indent=1))

if __name__=='__main__': main()
