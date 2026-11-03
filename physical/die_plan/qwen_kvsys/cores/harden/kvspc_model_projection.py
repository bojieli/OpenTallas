#!/usr/bin/env python3
"""Default-off, wrapper-only BASE PC projection for copied split models. PREP only.

Emit raw cores first. The returned reduced models are for emit_split / functional
port declarations only, never emit_core. No leaf/state transform, FT role, macro
registration, timing model or source-event adoption is performed here.
"""
import copy
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
from collections import OrderedDict
import kvspc_face_ports as F

EVENT_SHA256 = 'eb478377b71c74867a4a657c0c5939473bee51271634d96d20d283b2863c8083'
BASE_FILE = 'qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj_nc32.sv'
BANKS = ('pc__front_hbm_data', 'pc__return_hbm_data')
OWNERS = frozenset(('kvpc1', 'kvpc2', 'kvpc3'))
_TOKEN = object()


def require(ok, why):
    if not ok:
        raise ValueError(why)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def section(text, module):
    hits = list(re.finditer(r'\bmodule\s+'+re.escape(module)+r'\b.*?\bendmodule\b', text, re.S))
    require(len(hits) == 1, 'wrong/ambiguous module')
    return hits[0].group()


def declarations(text, module='qkd_kvs_pc'):
    h = section(text, module).split(');', 1)[0]
    out = OrderedDict()
    for d,hi,lo,n in re.findall(r'\b(input|output)\s+wire\s*(?:\[(\d+):(\d+)\])?\s*(\w+)', h):
        require(n not in out, 'duplicate declaration')
        out[n] = dict(dir=d,hi=int(hi) if hi else None,lo=int(lo) if lo else None,gaps=[])
    return out


def port_bits(pd):
    return ((b,i) for b,d in pd.items() for i in ([None] if d['hi'] is None else range(d['lo'],d['hi']+1)))


def bitkeys(pd):
    return set(port_bits(pd))


@dataclass(frozen=True)
class SourceGuard:
    owners: tuple
    event_sha256: str
    source_sha256: tuple
    original_header_sha256: str
    _token: object = field(repr=False, compare=False)


def verified_guard(event_path, overlay, original_wrapper, owners):
    """Verify exact ea246 source conditions; its qualified=false is NOT upgraded."""
    event_path, overlay, original_wrapper = map(Path,(event_path,overlay,original_wrapper))
    require(sha(event_path.read_bytes()) == EVENT_SHA256, 'wrong full-event identity')
    e = json.loads(event_path.read_text())
    require(e['schema']=='opentallas.kv.pc_full_parent_event.v1' and e['status']=='PREP_NOT_ADOPTED' and e['qualified'] is False and e['enabled'] is True and e['enabled_by_default'] is False, 'wrong event scope')
    require(set(owners) and len(set(owners))==len(owners) and set(owners)<=OWNERS, 'unsupported owner selection')
    inputs = []
    for row in e['files']:
        p = overlay/row['file']
        require(p.is_file() and sha(p.read_bytes())==row['after_sha256'], 'full-event source hash mismatch: '+row['file'])
        inputs.append((row['file'],row['after_sha256']))
    require(sha(Path(F.__file__).read_bytes())==e['helpers']['kvspc_face_ports.py'], 'wrapper helper differs from event')
    base = next(r for r in e['files'] if r['file']==BASE_FILE)
    require(sha(original_wrapper.read_bytes())==base['before_sha256'], 'wrong native BASE wrapper source')
    old = section(original_wrapper.read_text(),'qkd_kvs_pc'); new = section((overlay/BASE_FILE).read_text(),'qkd_kvs_pc')
    require(old.split(');',1)[0]==new.split(');',1)[0], 'native public header changed')
    require(len(re.findall(r'qkd_static_kv_pc_path_fan_nc_b\s*#\(\.CORE_CLOCK\(1\),\s*\.MU\(1\)\)\s+u_pc\s*\(',new))==1, 'unsupported BASE owner/CORE_CLOCK/MU')
    for n in ('pll_hbm','pll_hbm_port','pll_hbm_ecc','pll_hbm_cdc','pll_hbm_obs','cal_hck','front_hck','return_hck'):
        require(new.count('.'+n+'(ck)')==1, 'owner14 common-clock condition missing: '+n)
    for n in ('front_hbm_data','return_hbm_data'):
        require(new.count('.'+n+'({4{ck}})')==1, 'active bank-clock source not specialized')
    require(new.count(".land_er({pc__land_er[260:259], 258'd0, pc__land_er[0]})")==1, 'live landing source condition missing')
    return SourceGuard(tuple(owners),EVENT_SHA256,tuple(inputs),sha(old.split(');',1)[0].encode()),_TOKEN)


def project_model(raw, raw_text, guard):
    """Project only pdecl/bit-keyed connections/classes after ONE wrapper call."""
    require(isinstance(guard,SourceGuard) and guard._token is _TOKEN and guard.event_sha256==EVENT_SHA256, 'verified source guard required')
    owner = raw['hc']['inst']
    require(raw['hc']['module']=='qkd_kvs_pc' and owner in guard.owners, 'unsupported module/owner; head projection forbidden')
    require(raw['ms']==[owner] and raw['mine']=={'u_'+owner:owner}, 'model is not genuine selected single BASE leaf')
    require('hck' not in raw['pdecl'] and not any(b.startswith('ft_ck_') for b in raw['pdecl']), 'unsupported clock/FT interface')
    pd = raw['pdecl']; expected = declarations(raw_text)
    require({b:(d['dir'],d['hi'],d['lo']) for b,d in pd.items()}=={b:(d['dir'],d['hi'],d['lo']) for b,d in expected.items()}, 'raw model/header disagreement')
    require(len(pd)==27 and len(bitkeys(pd))==4397, 'wrong raw BASE inventory')
    for b,hi,lo in [('ck',0,0),('pc__land_er',260,0),('pc__land_er_259',260,259)]+[(b,3,0) for b in BANKS]:
        require(b in pd and (pd[b]['dir'],pd[b]['hi'],pd[b]['lo'])==('input',hi,lo), 'wrong width/direction: '+b)
    require(raw_text.count('.hck(ck[0])')==1 and '.hck(hck[0])' not in raw_text, 'raw common-clock binding missing')
    require(len(re.findall(r'\bqkd_kvs_pc__leaf\s+u_leaf\s*\(',raw_text))==1, 'not a genuine BASE leaf wrapper')
    keys = bitkeys(pd)
    require(set(raw['part_conn'])==keys and set(raw['pin_class'])==keys, 'bit-keyed map inventory mismatch')
    for (b,i),cls in raw['pin_class'].items():
        allowed={'out','out_alias','stale_out','gap_out'} if pd[b]['dir']=='output' else {'in','clk','clk_unused','stale_in','strap','gap_in'}
        require(cls in allowed, 'pin class/direction mismatch: '+b)
    for i in (0,259,260):
        key=('pc__land_er',i); v=raw['part_conn'].get(key)
        require(isinstance(v,tuple) and len(v) in (2,3), 'missing live raw landing connection')
        require(raw['pin_class'].get(key) in ('in','strap'), 'wrong live raw landing class')
        live=[x['nb'] for (_,_,bit),x in raw['lb'].items() if bit==i and x['base']=='pc__land_er' and x['boundary']]
        require(v in live, 'live connection was substituted, not ORIGINAL RAW landing')
    for i in (259,260):
        require(raw['part_conn'][('pc__land_er_259',i)] is None and raw['pin_class'][('pc__land_er_259',i)]=='stale_in', 'old high alias is live/substituted')
    wrapped = F.wrapper(raw_text,'qkd_kvs_pc',False)  # ONLY wrapper; never apply_kit/state transforms
    target = declarations(wrapped)
    require(len(target)==25 and len(bitkeys(target))==4129, 'wrapper functional inventory changed')
    # Intentionally reduced copied model: raw emission topology is retained in
    # the caller's untouched raw model, not reused after wrapper transformation.
    out = {k:copy.deepcopy(raw[k]) for k in ('hc','ms','pre','mine','pins','rep')}
    if 'canon' in raw:out['canon']=copy.deepcopy(raw['canon'])
    projected_pd=OrderedDict((b,copy.deepcopy(d)) for b,d in pd.items() if b not in BANKS)
    projected_pd['pc__land_er'].update(hi=0,lo=0,gaps=[])
    projected_pd['pc__land_er_259']=copy.deepcopy(pd['pc__land_er']);projected_pd['pc__land_er_259'].update(hi=260,lo=259,gaps=[])
    require({b:(d['dir'],d['hi'],d['lo']) for b,d in projected_pd.items()}=={b:(d['dir'],d['hi'],d['lo']) for b,d in target.items()}, 'metadata/wrapper projection mismatch')
    out.update(pdecl=projected_pd,part_conn={},pin_class={},wrapper_only_split_model=True)
    for key in port_bits(projected_pd):
        b,i=key; source=('pc__land_er',i) if b=='pc__land_er_259' else key
        out['part_conn'][key]=copy.deepcopy(raw['part_conn'][source]);out['pin_class'][key]=copy.deepcopy(raw['pin_class'][source])
    out['pins']=type(raw['pins'])((k,copy.deepcopy(v)) for k,v in raw['pins'].items() if k in bitkeys(target))
    require(out['part_conn'][('pc__land_er',0)]==raw['part_conn'][('pc__land_er',0)], 'bit0 changed')
    require(not any(b in BANKS or b=='pc__land_er' and i!=0 for b,i in out['part_conn']), 'removed keys survived')
    return out,wrapped


def functional_declaration(model):
    """Functional ABI declaration only; NOT the physical29-port FT macro header."""
    require(model.get('wrapper_only_split_model') is True, 'projected split model required')
    ports=[]
    for b,d in model['pdecl'].items():
        rng=f"[{d['hi']}:{d['lo']}] " if d['hi'] is not None else ''
        ports.append(f"    {d['dir']} wire {rng}{b}")
    return '// PREP functional ports only; physical FT roles remain HOLD. Not a registered macro.\nmodule qkd_kvs_pc (\n'+',\n'.join(ports)+'\n);\nendmodule\n'


def prepare_split(B, models, guard=None, *, enabled=False):
    """Normal raw emit first, wrapper-only projection second, normal split last."""
    if not enabled:return dict(status='DISABLED',qualified=False,models=models)
    import kv_core_rtl as K
    selected=[];cores={};raw_texts={}
    for original in models:
        raw=copy.deepcopy(original)
        text=K.emit_core(B,raw)
        projected,wrapped=project_model(raw,text,guard)
        selected.append(projected);cores[raw['hc']['inst']]=wrapped;raw_texts[raw['hc']['inst']]=text
    split=K.emit_split(B,selected)
    return dict(status='PREP_NOT_ADOPTED',qualified=False,models=selected,raw_cores=raw_texts,wrapped_cores=cores,split=split,
                functional_headers={m['hc']['inst']:functional_declaration(m) for m in selected},
                source_event_sha256=guard.event_sha256,holds=['full programme/ownership/token dates','physical four-FT parent roles','head_p physical/source closure','normal view/GEN/qualification'])
