#!/usr/bin/env python3
"""Strict source-selected instance snapshot gate; no hook installation.

Restricted compiler LEF RECT grammar, R0/MX/MY/R180 only. Every signal/CLOCK
RECT centre must meet its layer's preferred-axis track at the SAME supplied
instance origin, and that origin must lie on the supplied finite row/site grid.
This is not DRC, via, PG, row legality of the whole macro, or SS/FF signoff.
"""
import argparse
from decimal import Decimal,InvalidOperation
import hashlib,json,re
from pathlib import Path
import check_macro_track_alignment as frozen

FROZEN_SHA='21f4957b432b14b142598ee334b9cdb9ef18f09efbbcaa0d2cbd629582ff8a84'
SCHEMA='OT_STRICT_MACRO_INSTANCE_TRACKS_V1'

class Refuse(ValueError):pass

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(condition,message):
    if not condition:raise Refuse(message)
def integer(v):return type(v) is int

def nm(v):
    try:n=Decimal(v)*1000
    except InvalidOperation:raise Refuse('invalid LEF/track coordinate')
    require(n.is_finite() and n==n.to_integral_value(),'non-integer nanometre coordinate unsupported')
    return int(n)

def pinned(root,entry):
    require(isinstance(entry,dict) and set(entry)=={'path','sha256'},'exact path/SHA entry required')
    p=(root/entry['path']).resolve()
    require(p.is_file() and sha(p)==entry['sha256'],'missing or changed source '+str(p))
    return p

def strict_tracks(text):
    result={}
    pattern=r'make_tracks\s+(\w+)\s+-x_offset\s+(\S+)\s+-x_pitch\s+(\S+)\s+-y_offset\s+(\S+)\s+-y_pitch\s+(\S+)'
    for raw in text.splitlines():
        line=raw.split('#',1)[0].strip()
        if not line:continue
        m=re.fullmatch(pattern,line);require(m is not None,'unsupported track Tcl syntax')
        layer=m[1];require(layer in frozen.ASAP7_LAYERS or layer=='Pad','unknown track layer '+layer)
        grid=tuple(nm(m[i]) for i in range(2,6));require(grid[1]>0 and grid[3]>0,'nonpositive track pitch')
        result.setdefault(layer,[]).append(grid)
    require(any(k!='Pad' for k in result),'empty routing tracks')
    return result

def strict_lef(text):
    """Validate supported syntax completely before using frozen RECT parser."""
    macro=None;pin=None;port=False;obs=False;props=False;ended=False
    names=set();pins=set();size=False;rects=0;port_rects=0;layer=None;pin_attrs=set();macro_attrs=set()
    for number,raw in enumerate(text.splitlines(),1):
        s=raw.split('#',1)[0].strip()
        if not s:continue
        t=s.replace(';',' ').split();key=t[0]
        def check(c,msg):require(c,f'LEF line {number}: '+msg)
        if props:
            if t==['END','PROPERTYDEFINITIONS']:props=False
            else:check(re.fullmatch(r'MACRO\s+\w+\s+INTEGER\s*;',s) is not None,'unsupported property definition')
            continue
        if key=='END':
            if t==['END','LIBRARY']:
                check(macro is None and not ended,'unexpected library END');ended=True
            elif t==['END']:
                check(port or obs,'unexpected bare END')
                if port:check(port_rects>0,'empty PORT');port=False
                else:obs=False
                layer=None
            elif pin and t==['END',pin]:check(not port,'unclosed PORT');pin=None
            elif macro and t==['END',macro]:
                check(pin is None and not obs and size and pins,'incomplete macro');macro=None
            else:raise Refuse(f'LEF line {number}: invalid END')
            continue
        check(not ended,'tokens after END LIBRARY')
        check(s.endswith(';') or key in ('MACRO','PIN','PORT','OBS','PROPERTYDEFINITIONS'),'missing semicolon')
        if macro is None:
            if key=='MACRO':
                check(len(t)==2 and t[1] not in names,'duplicate/malformed MACRO');macro=t[1];names.add(macro);pins=set();size=False;macro_attrs=set()
            elif key=='PROPERTYDEFINITIONS':check(len(t)==1,'malformed properties');props=True
            elif key=='VERSION':check(len(t)==2 and t[1] in ('5.7','5.8'),'unsupported version')
            elif key in ('BUSBITCHARS','DIVIDERCHAR'):check(len(t)==2,'malformed header')
            else:raise Refuse(f'LEF line {number}: unsupported library statement {key}')
            continue
        if key=='PIN':
            check(pin is None and not obs and len(t)==2 and t[1] not in pins,'duplicate/malformed PIN');pin=t[1];pins.add(pin);pin_attrs=set()
        elif key=='PORT':check(pin is not None and not port and not obs and len(t)==1,'invalid PORT');port=True;port_rects=0;layer=None
        elif key=='OBS':check(pin is None and not obs and len(t)==1,'invalid OBS');obs=True;layer=None
        elif key=='LAYER':
            check((port or obs) and len(t)==2 and t[1] in frozen.ASAP7_LAYERS,'unsupported/missing geometry layer');layer=t[1]
        elif key=='RECT':
            check((port or obs) and layer is not None and len(t)==5,'unsupported RECT syntax')
            a,b,c,d=map(nm,t[1:]);check(0<=a<c and 0<=b<d,'inverted/degenerate/negative RECT')
            rects+=1
            if port:port_rects+=1
        elif key in ('DIRECTION','USE','SHAPE'):
            check(key not in pin_attrs,'duplicate pin attribute');pin_attrs.add(key)
            allowed={'DIRECTION':('INPUT','OUTPUT','INOUT'),'USE':('SIGNAL','CLOCK','POWER','GROUND'),'SHAPE':('ABUTMENT',)}
            check(pin is not None and not port and len(t)==2 and t[1] in allowed[key],'unsupported pin attribute')
        else:
            check(pin is None and not obs,'unsupported pin/geometry statement '+key)
            check(key not in macro_attrs,'duplicate macro attribute');macro_attrs.add(key) if key!='PROPERTY' else None
            if key=='SIZE':check(len(t)==4 and t[2]=='BY' and not size and nm(t[1])>0 and nm(t[3])>0,'bad SIZE');size=True
            elif key=='SYMMETRY':check(len(t)>1 and all(x in ('X','Y','R90') for x in t[1:]),'bad SYMMETRY')
            elif key=='CLASS':check(t==['CLASS','BLOCK'],'only BLOCK macros supported')
            elif key=='PROPERTY':check(len(t)==3 and t[1] in ('width','depth','banks') and t[2].isdigit(),'unsupported macro property')
            elif key=='FOREIGN':check(len(t)==4 and t[1]==macro and nm(t[2])==nm(t[3])==0,'unsupported FOREIGN translation')
            elif key=='ORIGIN':check(len(t)==3 and nm(t[1])==nm(t[2])==0,'nonzero ORIGIN unsupported')
            else:raise Refuse(f'LEF line {number}: unsupported macro statement {key}')
    require(macro is None and pin is None and not props and not port and not obs and ended and names and rects,'incomplete/empty LEF')
    macros=frozen.parse_lef(text)
    for m in macros:
        require(m['class']=='BLOCK','missing BLOCK CLASS')
        signal=[p for p in m['pins'] if p['use'] not in ('POWER','GROUND')]
        require(signal and all(p['rects'] for p in signal),'empty signal pin geometry')
        for p in m['pins']:
            for layer,(a,b,c,d) in p['rects']:require(c<=m['W'] and d<=m['H'],'RECT outside macro bounds')
    return {m['name']:m for m in macros}

def preflight(manifest,root):
    root=Path(root)
    require(sha(Path(frozen.__file__))==FROZEN_SHA,'frozen checker bytes changed')
    require(isinstance(manifest,dict) and set(manifest)=={'schema','frozen_checker_sha256','tracks','row_site','instances'},'exact manifest fields required')
    require(manifest.get('schema')==SCHEMA and manifest.get('frozen_checker_sha256')==FROZEN_SHA,'explicit schema/frozen source required')
    tracks_path=pinned(root,manifest['tracks']);tracks=strict_tracks(tracks_path.read_text())
    require(isinstance(manifest.get('instances'),list) and manifest['instances'],'empty instance snapshot')
    rows=manifest.get('row_site');keys={'x_origin_nm','y_origin_nm','site_pitch_nm','row_pitch_nm','site_count','row_count'}
    require(isinstance(rows,dict) and set(rows)==keys and all(integer(v) for v in rows.values()),'exact integer row/site origin/pitch/count required')
    require(all(rows[k]>0 for k in ('site_pitch_nm','row_pitch_nm','site_count','row_count')),'nonpositive finite row/site grid')
    results=[];names=set()
    for i in manifest['instances']:
        require(set(i)=={'name','macro','lef','orientation','x_nm','y_nm'},'exact instance fields required')
        require(isinstance(i['name'],str) and i['name'] and i['name'] not in names,'duplicate/empty instance');names.add(i['name'])
        require(integer(i['x_nm']) and integer(i['y_nm']),'integer instance nanometres required')
        lef=pinned(root,i['lef']);macros=strict_lef(lef.read_text());require(i['macro'] in macros,'unknown macro')
        m=macros[i['macro']];o=i['orientation']
        require(o in frozen.MIRROR_SET,'unsupported rotation/orientation; restricted four-orientation gate')
        require(o in frozen.allowed_orients(m['symmetry']),'orientation not declared by LEF symmetry')
        axes=[(i['x_nm'],rows['x_origin_nm'],rows['site_pitch_nm'],rows['site_count']),(i['y_nm'],rows['y_origin_nm'],rows['row_pitch_nm'],rows['row_count'])]
        require(all((v-a)%p==0 and 0<=(v-a)//p<n for v,a,p,n in axes),'actual instance origin outside row/site intersection')
        checked=0;layers={};bad=[]
        for pin in m['pins']:
            if pin['use'] in ('POWER','GROUND'):continue
            for layer,rect in pin['rects']:
                require(layer in tracks and tracks[layer],'signal layer has no routing tracks '+layer)
                r=frozen.transform_rect(rect,o,m['W'],m['H']);axis='y' if frozen.ASAP7_LAYERS[layer][0]=='H' else 'x'
                c2=r[1]+r[3]+2*i['y_nm'] if axis=='y' else r[0]+r[2]+2*i['x_nm']
                on=any((c2-2*(g[2] if axis=='y' else g[0]))%(2*(g[3] if axis=='y' else g[1]))==0 for g in tracks[layer])
                checked+=1;layers[layer]=layers.get(layer,0)+1
                if not on:bad.append({'pin':pin['name'],'layer':layer,'axis':axis,'centre_twice_nm':c2})
        require(checked>0,'empty signal coverage')
        results.append({'instance':i['name'],'macro':m['name'],'orientation':o,'x_nm':i['x_nm'],'y_nm':i['y_nm'],'lef_sha256':sha(lef),'signal_RECT_centres_checked':checked,'layers':layers,'offtrack':bad})
    ok=all(not r['offtrack'] for r in results)
    return {'status':'PASS_STATIC_INSTANCE_TRACK_CENTRES' if ok else 'REFUSE_OFFTRACK_INSTANCE','instances':results,'tracks_sha256':sha(tracks_path),'row_site':rows,'manifest_canonical_sha256':hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'scope':'caller supplied immutable instance snapshot; every signal/CLOCK RECT centre conjunctively checked','hook_installed':False,'DRC_via_PG_SS_FF_qualified':False,'actual_live_placement_verified':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--json',type=Path,required=True);a=p.parse_args()
    try:r=preflight(json.loads(a.manifest.read_text()),a.root);rc=0 if r['status'].startswith('PASS_') else 1
    except (Refuse,ValueError,KeyError,TypeError,OSError) as e:r={'status':'REFUSE_INPUT_COVERAGE','reason':str(e),'DRC_via_PG_SS_FF_qualified':False};rc=1
    r['manifest_file_sha256']=sha(a.manifest) if a.manifest.is_file() else None
    with a.json.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
    return rc
if __name__=='__main__':raise SystemExit(main())
