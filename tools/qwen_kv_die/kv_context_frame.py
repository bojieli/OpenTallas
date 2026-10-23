"""Literal, source-bound diagnostic geometry for the recurring OVL context."""
from collections import Counter
from functools import lru_cache
import json,os,re
from pathlib import Path
import kv_source_frame

# SQC-KDIE4 10-22 (OT_KV_KVNC_VIEW=1, needs OT_KV_ROPE_OVL=1): the same literal pin geometry, read from the CLOSED view of
# OT_KV_KVNC_KIT (physical/ref_tile/<kit>/views/qkd_kvn_ctx_ovl_rope, e.g. cm4 / cf4 CLOSED 10-22) instead of a diagnostic
# source frame: no NOT_A_DIE_RESULT marker; the view's kit spec must name the selected source file and production params.
VIEW_TOP='qkd_kvn_ctx_ovl_rope'

def active():
    return bool(os.environ.get('OT_KV_KVNC_SOURCE_FRAME')) or os.environ.get('OT_KV_KVNC_VIEW','0')=='1'

def _load_view(root):
    import hashlib
    kit=os.environ.get('OT_KV_KVNC_KIT','')
    if not kit:raise ValueError('OT_KV_KVNC_VIEW=1 needs OT_KV_KVNC_KIT (a CLOSED qkd_kvn_ctx_ovl_rope kit)')
    kd=Path(root)/'physical/ref_tile'/kit
    spec=json.loads((kd/'spec.json').read_text())
    lef=kd/'views'/VIEW_TOP/(VIEW_TOP+'.lef')
    if spec.get('top')!=VIEW_TOP or not lef.is_file():raise ValueError('OT_KV_KVNC_VIEW: no closed '+VIEW_TOP+' view in '+str(kd))
    text=lef.read_text()
    m=re.search(r'MACRO\s+'+VIEW_TOP+r'\b.*?SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text,re.S)
    srcs=[s for s in spec['sources'] if s.endswith(VIEW_TOP+'.sv')]
    receipt=dict(top=VIEW_TOP,params=spec.get('params',{}),outline=[float(m[1]),float(m[2])],kit=kit,view=str(lef.relative_to(root)),
                 source_sha256={s:hashlib.sha256((Path(root)/s).read_bytes()).hexdigest() for s in srcs},qualification='CLOSED_VIEW')
    return lef,receipt

@lru_cache(None)
def load(root):
    manifest=os.environ.get('OT_KV_KVNC_SOURCE_FRAME','')
    if not manifest and os.environ.get('OT_KV_KVNC_VIEW','0')=='1':
        lef,receipt=_load_view(root)
        if receipt['params']!={'MUT_USER':0,'MUT_STALE':0}:
            raise ValueError('context view must bind the selected production mutation parameters')
        text=lef.read_text();w,h=receipt['outline'];raw={}
        for m in re.finditer(r'\bPIN\s+(\S+)(.*?)\bEND\s+\1\s',text,re.S):
            if m[1] in ('VDD','VSS'):continue
            rs=re.findall(r'LAYER\s+(\w+)\s*;\s*RECT\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s*;',m[2])
            if not rs:raise ValueError('context view pin lacks literal geometry '+m[1])
            raw[m[1]]=(m[0],[(lay,*map(float,v)) for lay,*v in rs])
        return dict(receipt=receipt,lef=lef,text=text,w=float(w),h=float(h),raw=raw)
    if not manifest:return None
    kit=os.environ.get('OT_KV_KVNC_KIT','')
    lef,receipt=kv_source_frame.load(root,manifest,kit,'qkd_kvn_ctx_ovl_rope')
    if receipt['params']!={'MUT_USER':0,'MUT_STALE':0}:
        raise ValueError('context frame must bind the selected production mutation parameters')
    text=lef.read_text();w,h=receipt['outline'];raw={}
    for m in re.finditer(r'\bPIN\s+(\S+)(.*?)\bEND\s+\1\s',text,re.S):
        rs=re.findall(r'LAYER\s+(\w+)\s*;\s*RECT\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s*;',m[2])
        if not rs:raise ValueError('context frame pin lacks literal geometry '+m[1])
        raw[m[1]]=(m[0],[(lay,*map(float,v)) for lay,*v in rs])
    return dict(receipt=receipt,lef=lef,text=text,w=float(w),h=float(h),raw=raw)

_groups_cache={};_points_cache={};_anchor_cache={}

def groups(root,binding):
    key=(str(root),id(binding))
    if key in _groups_cache:return _groups_cache[key]
    r=load(str(root))
    if r is None:return None
    if binding['module']!=r['receipt']['top'] or binding['parameters']!=r['receipt']['params']:
        raise ValueError('context frame binding differs from selected source')
    if set(r['receipt']['source_sha256'])!={binding['file']}:
        raise ValueError('context frame source differs from selected context leaf')
    raw=r['raw'];out={};used=set()
    for p,names in binding['ports'].items():
        pins=[]
        for n in names:
            part=([n] if n in raw else sorted((x for x in raw if re.fullmatch(re.escape(n)+r'\[\d+\]',x)),key=lambda x:int(x[x.rindex('[')+1:-1])))
            if not part:raise ValueError('context frame missing binding port '+n)
            pins+=part
        out[p]=pins;used.update(pins)
    if used!=set(raw):raise ValueError('context frame/binding pin sets differ')
    _groups_cache[key]=out
    return out

def points(root,binding,port):
    key=(str(root),id(binding),port)
    if key in _points_cache:return _points_cache[key]
    r=load(str(root));g=groups(root,binding)
    if r is None:return None
    pins=g[port.lstrip('*').split('[')[0]]
    _points_cache[key]=[(r['w'],r['h'],(x0+x1)/2,(y0+y1)/2,lay) for pin in pins for lay,x0,y0,x1,y1 in r['raw'][pin][1]]
    return _points_cache[key]

def anchor(root,binding,port):
    key=(str(root),id(binding),port)
    if key in _anchor_cache:return _anchor_cache[key]
    pts=points(root,binding,port)
    if pts is None:return None
    def face(p):
        w,h,x,y,_=p;return min((('W',x),('E',w-x),('S',y),('N',h-y)),key=lambda t:t[1])[0]
    f=Counter(face(p) for p in pts).most_common(1)[0][0];side=[p for p in pts if face(p)==f]
    c=sum(p[3] if f in 'EW' else p[2] for p in side)/len(side)
    w,h=pts[0][:2];x,y=dict(W=(0,c),E=(w,c),S=(c,0),N=(c,h))[f]
    _anchor_cache[key]=(x,y,f,c,side[0][4])
    return _anchor_cache[key]

def world(it,p):
    w,h,x,y,_=p
    if it.orient in ('MY','R180'):x=w-x
    if it.orient in ('MX','R180'):y=h-y
    return it.x+x,it.y+y

def xy(root,binding,it,port):
    a=anchor(root,binding,port)
    if a is None:return None
    r=load(str(root));return world(it,(r['w'],r['h'],a[0],a[1],a[4]))

def far(root,binding,it,port,pt):
    ps=points(root,binding,port)
    if ps is None:return None
    return max(abs(pt[0]-x)+abs(pt[1]-y) for x,y in (world(it,p) for p in ps))

def install_case(root,binding,work):
    r=load(str(root))
    if r is None:return
    g=groups(root,binding);mapping={}
    for p,pins in g.items():
        for i,n in enumerate(pins):mapping[n]=p if len(pins)==1 else f'{p}[{i}]'
    text=r['text']
    for n,new in mapping.items():
        text=re.sub(r'(?m)^(\s*(?:PIN|END)\s+)'+re.escape(n)+r'\s*$',lambda m:m[1]+new,text)
    top=r['receipt']['top'];text=re.sub(r'(?m)^(MACRO|END)\s+'+re.escape(top)+r'\s*$',r'\1 qkd_kvnc',text)
    macro=re.search(r'(?ms)^MACRO qkd_kvnc\b.*?^END qkd_kvnc\s*$',text).group(0)
    p=Path(work)/'elements.lef';old=p.read_text();old,n=re.subn(r'(?ms)^MACRO qkd_kvnc\b.*?^END qkd_kvnc\s*$',lambda m:macro,old)
    if n!=1:raise ValueError('context case must replace exactly one generic macro')
    p.write_text(old);(Path(work)/'context_source_frame.json').write_text(json.dumps(r['receipt'],indent=2)+'\n')
    if r['receipt'].get('qualification')=='CLOSED_VIEW':return
    for d in (Path(work),Path(work).parent):
        with (d/'NOT_A_DIE_RESULT').open('a') as f:f.write('CONTEXT_SOURCE_FRAME_DIAGNOSTIC_ONLY; closed leaf qualification pending\n')
