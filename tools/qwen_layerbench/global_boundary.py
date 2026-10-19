"""Opt-in native Qwen DV boundary ABI; no new data memory or timing credit.

Local VM uses 4096 FP32/user. Global X addresses are full-width identities
consumed by ot_qfd_xs_tap, not indices into that VM. The 4e718c010 vector
lowerer emits zero-based X epochs; this adapter joins them to the exact
global ME programme into aligned X identities (4096 / 16384 / 32768).

This is an address join only. Its caller must reserve the shared scalar,
stream and X epochs through their last consumers, including arm pipeline and
reset. It cannot establish a production token schedule by itself.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hdc_isa as ISA

X_USER_STRIDE=65536
X_WINDOW=1<<22
# Exact 4e718c010 SU layout (qfd_dv_slice2 si[456:0]).
SU_FIELDS=[('go',1),('nout',18),('nin',18),('asrc',1),('a',24),('aso',24),('asi',24),
 ('bsrc',1),('b',24),('bso',24),('bsi',24),('csrc',1),('c',24),('cso',24),('csi',24),
 ('ma',2),('mb',2),('ad',3),('sfu',3),('mc',1),('md',1),('dst',2),('d',24),('dso',24),
 ('dsi',24),('red',2),('redsq',1),('rb',24),('rso',24),('imm1',32),('imm2',32)]
SU_LAYOUT={};_off=0
for _key,_width in SU_FIELDS: SU_LAYOUT[_key]=(_off,_width);_off+=_width


def get(word,layout,key):
    off,width=layout[key];return (word>>off)&((1<<width)-1)


def put(word,layout,key,value):
    off,width=layout[key]
    if not 0<=value<1<<width:raise ValueError('field overflow '+key)
    return (word&~(((1<<width)-1)<<off))|(value<<off)


def user_base(user):
    if user not in range(4):raise ValueError('user outside actual four-user ABI')
    return user*X_USER_STRIDE


def layer_contract(program):
    """Bind all four actual ME words, never infer a namespace from low bits."""
    expected={1:('qkv',4096,4096),12:('o',50672,512),16:('gu',4096,4096),20:('down',55280,1536)}
    words=[int(x,16) for x in Path(program).read_text().split()]
    if len(words)!=25:raise ValueError('requires exact fused25word layer geometry')
    rows={}
    for pc,(name,base,count) in expected.items():
        w=words[pc];f=ISA.decode(w)
        if f['unit']!=1 or f['me_wsrc'] or f['me_xbase']!=base or f['me_xks']!=1 or f['me_xjs']:
            raise ValueError('unqualified ME geometry '+name)
        if (1<<f['me_split'])*f['me_k']!=count or f['me_xcs']!=f['me_k']:
            raise ValueError('non-native affine X geometry '+name)
        rows[name]=dict(pc=pc,original_base=base,base={'qkv':4096,'o':16384,'gu':4096,'down':32768}[name],elements=count,word=f'{w:0256x}')
    return dict(program_sha256=hashlib.sha256(Path(program).read_bytes()).hexdigest(),epochs=rows)


def rewrite_me(word,user,epoch):
    if word!=int(epoch['word'],16):raise ValueError('ME source word differs from pinned epoch')
    return put(word,ISA.LAYOUT,'me_xbase',epoch['base']+user_base(user))


def rewrite_xpf72(word,user,epoch):
    """ctlm_image.xpf_pack native72-bit descriptor; timing metadata unchanged."""
    if not 0<=word<1<<72:raise ValueError('XPF descriptor width')
    f=ISA.decode(int(epoch['word'],16))
    expected=(f['me_round']<<71)|(f['me_k']<<53)|(f['me_split']<<49)|(f['me_xks']<<37)|(f['me_xcs']<<25)|(epoch['original_base']<<1)|1
    if word!=expected:raise ValueError('XPF/ME source identity mismatch')
    return (word&~(((1<<24)-1)<<1))|((epoch['base']+user_base(user))<<1)


def rewrite_x(word,user,contract):
    """Post-local-relocation SU hook: modifies only window01 d address.

    xs is reused for qkv/gu. Both allocated epochs have base4096. xa feeds
    o_proj base16384; silu feeds down base32768. Original global ME bases
    50672/55280 are 48mod64 and cannot feed the native64element packer. No other X-producing shape
    is accepted. PSUM golden indices and D2D Q/K/V kinds remain unchanged.
    """
    if word==0:return word
    g=lambda k:get(word,SU_LAYOUT,k)
    if g('dst')!=1 or g('d')>>22!=1:return word
    local=g('d')&(X_WINDOW-1)
    if g('nout')>1 and g('nin')==128 and g('dso')==1536: name='qkv'
    elif g('nout')==1 and g('nin')==128 and g('sfu')==4: name='down'
    elif g('nout')==1 and g('nin')==128 and g('sfu')==0: name='o'
    else:raise ValueError('unqualified X producer shape')
    e=contract['epochs'][name]
    high=local+(g('nout')-1)*g('dso')+(g('nin')-1)*g('dsi')
    if high>=e['elements'] or local%64:raise ValueError('X producer outside exact epoch')
    address=e['base']+user_base(user)+local
    if address+high-local>=X_WINDOW:raise ValueError('X namespace overlaps window selector')
    return put(word,SU_LAYOUT,'d',X_WINDOW|address)


def check_lifetimes(events):
    """Fail closed on actual shared ownership; intervals are charged edges.

    Every event supplies immutable producer/consumer identities and reserves
    [arm,retire) for scalar, stream and X resources. Stage changes and user
    changes do not reset a live physical owner. No arbitrary ready wait.
    """
    occupied={}
    for e in events:
        if not e.get('producer_sha256') or not e.get('consumer_sha256'):
            raise ValueError('unbound producer/consumer')
        if e['user'] not in range(4) or e['stage'] not in range(38) or not 0<=e['arm']<e['retire']:
            raise ValueError('invalid ownership interval')
        for resource in e['resources']:
            if resource not in ('scalar','stream','xepoch0','xepoch1'):
                raise ValueError('unknown physical ownership resource')
            for prior in occupied.setdefault(resource,[]):
                if max(e['arm'],prior['arm'])<min(e['retire'],prior['retire']):
                    raise ValueError('overlapping physical '+resource+' ownership')
            occupied[resource].append(e)
    return occupied


def head_contract(plan,die):
    """Exact global head namespaces; slice normalize/PROG/table join is separate."""
    p=json.loads(Path(plan).read_text())
    h=next(v for v in p['head_profiles'] if v['die']==die)
    if len(h['program_hex'])!=8:raise ValueError('unexpected head programme')
    out=[]
    for pc in range(3,7):
        w=int(h['program_hex'][pc],16);f=ISA.decode(w)
        if f['unit']!=1 or f['me_xbase']!=8192 or f['me_k']!=8 or f['me_split']!=9 or f['me_xcs']!=8 or f['me_xks']!=1:
            raise ValueError('unexpected actual head epoch')
        out.append(dict(pc=pc,original_base=8192,base=8192,elements=4096,word=f'{w:0256x}'))
    return dict(plan_sha256=hashlib.sha256(Path(plan).read_bytes()).hexdigest(),die=die,epochs=out,
                scope='Actual head ME identities only; local finalnorm lowering and live ownership remain required')
