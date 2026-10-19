"""Physical static ASTK expansion. Every emitted cell needs its own native view.

The 328.32 um envelope holds two actual 162 um EP columns and a 4.32 um
channel. Placement uses actual LEF outlines. No parent or legacy view qualifies
this composition; reset relays and registered fault join are separate masters.
"""
import hashlib
import re
from pathlib import Path

SR='rtl/qwen_sys/split_20261014'
PHYS=f'{SR}/qkd_astk_phys.sv'
LEAVES={'qkd_astk_ctl_s':f'{SR}/qkd_astk_static_leaves.sv',
        'qkd_astk_ep_s':f'{SR}/qkd_astk_static_leaves.sv',
        'qkd_astk_ex_s':f'{SR}/qkd_astk_static_leaves.sv',
        'qkd_astk_zn':'rtl/qwen_sys/kv_die_20261009/qkd_astk_leaves.sv',
        'qkd_rlys_296':'rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv',
        'qkd_astk_rly_296':PHYS,'qkd_astk_fault_join':PHYS,
        'qkd_astk_er_owner_st':f'{SR}/qkd_astk_er_owner_st.sv'}


def configure(K, views, rtl, sublevels):
    if not K.KSD.ON:
        raise ValueError('physical ASTK expansion requires the static source graph')
    import kv_static_die as S
    import os
    if os.environ.get('OT_KV_ASTK_EXPAND','0')!='1':
        raise ValueError('physical ASTK source requires OT_KV_ASTK_EXPAND=1')
    if not S.ASTK_ST:
        raise ValueError('physical ASTK expansion requires OT_KV_ASTK_ST')
    for m,p in LEAVES.items():
        views[m]=f'physical/ref_tile/{m}/views/{m}'
        rtl[m]=p
    sublevels['qkd_astk_strip_er_die']=tuple((p,m) for p,m in (
        (f'{SR}/qkd_astk_strip_er_st.sv','qkd_astk_strip_er_st'),
        (f'{SR}/qkd_astk_strip_st.sv','qkd_astk_strip_st'),
        (f'{SR}/qkd_astk_er_chain_st.sv','qkd_astk_er_chain_st'),
        (PHYS,'qkd_astk_delay'),(PHYS,'qkd_astk_delay_nrst')))
    # RL3 is measured against the calendar Z=1016 by AD-KV-ASTK.
    # No width reservation can silently retain the RL1 parent profile.
    for m in ('qkd_astk','qkd_astk_n'):
        K.BINDINGS[m]['parameters']=dict(RL=getattr(S,'ASTK_RL',3),Z_STRIDE=4,DISTRIBUTED_ER=1)
    return {m:dict(plan=None,prepare=prepare,straps=lambda inst:{})
            for m in ('qkd_astk','qkd_astk_n')}


def prepare(J, leaf, fw, fh):
    if fw < 328.27:
        raise ValueError('static ASTK needs the actual 328.32 um envelope')
    cells={n.lstrip('\\'):dict(c,type=(c['type'].split('\\')[1] if c['type'].startswith('$paramod') else c['type'].lstrip('\\'))) for n,c in J['cells'].items()}
    placed={}
    rectangles=[]
    def put(n,x,y):
        typ=cells[n]['type'].lstrip('\\')
        if typ not in leaf:
            raise ValueError(f'{n}: missing native closed leaf {typ}')
        w,h=leaf[typ]['size'];rect=(x,y,x+w,y+h)
        if min(x,y)<0 or rect[2]>fw+.05 or rect[3]>fh+.05:
            return False
        if any(min(rect[2],b[2])-max(rect[0],b[0])>.001 and
               min(rect[3],b[3])-max(rect[1],b[1])>.001 for b in rectangles):
            return False
        rectangles.append(rect);placed[n]=(round(x,3),round(y,3),'R0');return True
    # Stagger successive EP owners between columns, preserving logical order.
    # This reduces each chain's y step to half an engine row.
    pitch=(fh-237.6)/8
    def center(e):return pitch*(e+.5)
    pending=[]
    for n,c in cells.items():
        t=c['type'].lstrip('\\');w,h=leaf[t]['size'] if t in leaf else (0,0)
        e=re.search(r'g_ep\[(\d+)\]',n)
        z=re.search(r'g_zn\[(\d+)\]',n)
        if t=='qkd_astk_ep_s' and e:
            k=int(e[1]); x=(k%2)*166.32;y=center(k)-h/2
        elif t=='qkd_astk_ex_s' and e:
            k=int(e[1]);j=int(re.search(r'g_ex\[(\d+)\]',n)[1]);x=(k%2)*166.32
            y=center(k)-172.8-(2-j)*153.36 if j<2 else center(k)+172.8+(j-2)*153.36+4.32
        elif t=='qkd_astk_ctl_s':x=0;y=fh-h
        elif t=='qkd_astk_zn' and z:
            k=int(z[1]);x=(k%2)*166.32;y=fh-237.6+(k//2)*90.72
        else:
            pending.append(n);continue
        if not put(n,x,y):raise ValueError(f'{n}: actual functional leaf does not fit ASTK envelope')
    # Place all actual relay/tap/glue rectangles in remaining slots. Anchor
    # each to its source owner, then choose the nearest legal lattice position.
    # This is geometry only: measured pin reach/clock/STA remains a die gate.
    for n in sorted(pending):
        t=cells[n]['type'].lstrip('\\')
        if t not in leaf:raise ValueError(f'{n}: missing native closed leaf {t}')
        w,h=leaf[t]['size'];e=re.search(r'g_(?:ep|owner)\[(\d+)\]',n)
        anchor=center(int(e[1])) if e else fh-237.6
        candidates=((abs(y+h/2-anchor),x,y)
                    for y in (i*54.0 for i in range(int(fh/54)))
                    for x in (i*27.0 for i in range(int(fw/27))))
        if not any(put(n,x,y) for _,x,y in sorted(candidates)):
            raise ValueError(f'{n}: no legal slot for actual native leaf outline {w}x{h}')
    return lambda cell,fw,fh:placed[cell]


def provenance(root):
    paths=sorted(set(LEAVES.values())|{f'{SR}/qkd_astk_strip_er_die.sv',
        f'{SR}/qkd_astk_strip_er_st.sv',f'{SR}/qkd_astk_strip_st.sv',
        f'{SR}/qkd_astk_er_chain_st.sv'})
    return {p:hashlib.sha256((Path(root)/p).read_bytes()).hexdigest() for p in paths}


def view_readiness(root):
    """Use the existing immutable gate snapshot and exact export hashes.

    A changed shared RTL file is deliberately not inferred equivalent here.
    A source-pinned module-equivalence record can be consumed by the existing
    native binding workflow before the successor is admitted.
    """
    import json
    root=Path(root);out={}
    for m,src in LEAVES.items():
        if m=='qkd_rlys_296':continue  # unused by the all-reset first profile
        vd=root/f'physical/ref_tile/{m}/views/{m}'
        reasons=[];required=[vd/f'{m}.lef',vd/'insertion.json',vd/'abstract.json']
        required += [vd/f'{m}_{c}.lib' for c in ('tt','ff','ss')]
        for p in required:
            if not p.exists():reasons.append(f'missing {p.relative_to(root)}')
        gp=root/f'physical/ref_tile/{m}/gate_result.json'
        if gp.exists():
            g=json.loads(gp.read_text())
            if g.get('verdict') not in ('PASS','WARN'):reasons.append('physical gate not accepted')
            if any(i.get('severity')=='FAIL' for i in g.get('items',[])):reasons.append('physical gate contains failures')
            snap={i['path']:i.get('sha256') for i in g.get('source_binding',{}).get('files',[]) if 'path' in i}
            bound=(root/src).exists() and snap.get(src)==hashlib.sha256((root/src).read_bytes()).hexdigest()
            # Shared source files also contain unrelated masters. Reuse only
            # after recovering the exact snapshotted blob and comparing the
            # selected module bytes, never by master name or shape alone.
            if not bound and (root/src).exists():
                import subprocess
                rev=g.get('source_binding',{}).get('start_commit')
                old=subprocess.run(['git','-C',str(root),'show',f'{rev}:{src}'],capture_output=True)
                if old.returncode==0 and hashlib.sha256(old.stdout).hexdigest()==snap.get(src):
                    pat=rf'^\s*module\s+{re.escape(m)}\b.*?^\s*endmodule\b'
                    a=re.search(pat,old.stdout.decode(),re.M|re.S)
                    b=re.search(pat,(root/src).read_text(),re.M|re.S)
                    bound=bool(a and b and a.group()==b.group())
            if not bound:
                reasons.append(f'exact selected source not bound by gate snapshot: {src}')
        else:reasons.append('missing physical gate result')
        if (vd/'abstract.json').exists():
            a=json.loads((vd/'abstract.json').read_text())
            for fn,sha in a.get('files',{}).items():
                p=vd/fn
                if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:
                    reasons.append(f'export hash mismatch {fn}')
        out[m]=dict(ready=not reasons,reasons=reasons)
    return out


def require_views(root):
    r=view_readiness(root)
    bad={m:v['reasons'] for m,v in r.items() if not v['ready']}
    if bad:raise ValueError(f'actual static ASTK leaf bindings not ready: {bad}')
    return r


def source_graph(root, K, E):
    """Audit the exact expanded RTL even while new physical leaves are open.

    Missing outlines come from explicit kit specs and are labelled estimates.
    They can never be used by kv_expand's production view binder.
    """
    import json,subprocess,tempfile
    from collections import Counter
    root=Path(root)
    fr=configure(K,E.VIEWS,E.RTL,E.SUBLEVELS)
    leaf={};headers=[]
    for m,p in LEAVES.items():
        if m=='qkd_rlys_296':continue
        t=re.sub(r'//[^\n]*','',E.module_text(root/p,m))
        headers.append(t[:re.search(r'\)\s*;',t).end()]+'\nendmodule\n')
    with tempfile.TemporaryDirectory() as td:
        td=Path(td);(td/'ports.sv').write_text(''.join(headers))
        r=subprocess.run(['yosys','-q','-p',f'read_verilog -lib -sv {td}/ports.sv; write_json {td}/ports.json'],capture_output=True,text=True)
        if r.returncode:raise ValueError(r.stderr)
        j=json.loads((td/'ports.json').read_text())['modules']
    for m in j:
        vd=root/f'physical/ref_tile/{m}/views/{m}'
        ports={p:dict(dir=v['direction'],w=len(v['bits']),bits=set(range(len(v['bits']))) if len(v['bits'])>1 else {None}) for p,v in j[m]['ports'].items()}
        if (vd/f'{m}.lef').exists():
            _,blk,size,actual=E.lef_macro(vd/f'{m}.lef')
            for p,r in actual.items():r['w']=1 if r['bits']=={None} else max(r['bits'])+1
            if {p:(r['dir'],r['w']) for p,r in actual.items()}!={p:(r['dir'],r['w']) for p,r in ports.items()}:
                raise ValueError(f'{m}: actual LEF vs selected source ports differ')
            leaf[m]=dict(ports=actual,size=size,outline_basis='actual_LEF')
        else:
            sp=root/f'physical/ref_tile/{m}/spec.json'
            if not sp.exists():sp=root/f'tools/ref_tile/specs_rtlbkv_1018/{m}.json'
            if not sp.exists():raise ValueError(f'missing explicit kit outline {m}')
            outline=json.loads(sp.read_text())['outline']
            leaf[m]=dict(ports=ports,size=(outline['w'],outline['h']),outline_basis='unclosed_kit_spec')
    b=K.BINDINGS['qkd_astk'];J=E.elaborate(b['module'],b['file'],leaf,b['parameters'])
    fw=328.32;fh=4*(K.ENG_H+K.GY)+237.6
    plan=prepare(J,leaf,fw,fh)
    cells=[]
    for n,c in J['cells'].items():
        m=E.base_type(c['type']);n=n.lstrip('\\');x,y,o=plan(n,fw,fh)
        cells.append(dict(name=n,master=m,x=x,y=y,orient=o,outline=list(leaf[m]['size']),
            outline_basis=leaf[m]['outline_basis'],connections=c['connections']))
    return dict(schema='opentallas.static_astk_source_graph.v1',physical_qualified=False,
        profile=dict(RL=3,Z_STRIDE=4,DISTRIBUTED_ER=1,fault_join_edges=1),
        outline=[fw,fh],counts=dict(Counter(c['master'] for c in cells)),
        ports=J['ports'],cells=cells,source_sha256=provenance(root))


if __name__=='__main__':
    import argparse,json
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--source-graph',action='store_true')
    a=ap.parse_args();root=Path(__file__).resolve().parents[2]
    if a.source_graph:
        import kv_expand as E
        E.K._set_geometry(True,reserve_native_astk=True)
        r=source_graph(root,E.K,E)
        a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n')
        print(json.dumps(r['counts']));raise SystemExit(0)
    r=dict(schema='opentallas.static_astk_readiness.v1',profile=dict(RL=3,Z_start_age=1016,fault_join_edges=1),
           leaves=view_readiness(root),source_sha256=provenance(root))
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({m:v['ready'] for m,v in r['leaves'].items()}))
    raise SystemExit(0 if all(v['ready'] for v in r['leaves'].values()) else 1)
