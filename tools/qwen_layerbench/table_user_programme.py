"""Exact field relocation of lowered DV SU instructions; excludes transport joins.

This maps the already compact local DV operands, not the global ME programme.
PSUM tags, X/D2D stream addresses, dimensions, reduction order and arithmetic
fields are preserved. Scalar ROOT configuration and stream user identity must
be compiled separately before a token can be claimed.
"""
FIELDS = [('go',1),('nout',18),('nin',18),('asrc',1),('a',24),('aso',24),('asi',24),
 ('bsrc',1),('b',24),('bso',24),('bsi',24),('csrc',1),('c',24),('cso',24),('csi',24),
 ('ma',2),('mb',2),('ad',3),('sfu',3),('mc',1),('md',1),('dst',2),('d',24),('dso',24),
 ('dsi',24),('red',2),('redsq',1),('rb',24),('rso',24),('imm1',32),('imm2',32)]


def unpack(word):
    if not 0 <= word < 1<<457: raise ValueError('instruction exceeds457 bits')
    out={}
    for key,bits in FIELDS:
        out[key]=word&((1<<bits)-1);word>>=bits
    return out


def pack(fields):
    word=0;shift=0
    for key,bits in FIELDS:
        value=fields[key]
        if not 0 <= value < 1<<bits: raise ValueError('relocation carry in '+key)
        word|=value<<shift;shift+=bits
    return word


def relocate(word,user,vm_high_water=1472):
    if user not in range(4): raise ValueError('user out of range')
    if word==0:return 0,[]  # unused PROG slots remain unused
    f=unpack(word);changes={};proof=[]
    if f['go'] or f['nin']==0 or f['nout']==0:raise ValueError('invalid stored instruction')
    if f['asrc']:raise ValueError('unqualified WROM A source')
    for field,src in (('a',0),('b',f['bsrc']),('c',f['csrc'])):
        cap=2048 if src else vm_high_water
        high=f[field]+(f['nout']-1)*f[field+'so']+(f['nin']-1)*f[field+'si']
        if high>=cap:raise ValueError('operand outside compact '+('CROM' if src else 'VM')+' region: '+field)
        stride=2048 if src else 4096
        changes[field]=f[field]+user*stride
        proof.append(dict(field=field,space='CROM' if src else 'VM',local_first=f[field],local_last=high,
                          user_first=f[field]+user*stride,user_last=high+user*stride))
    if f['dst']==1 and f['d']>>22==0:
        high=f['d']+(f['nout']-1)*f['dso']+(f['nin']-1)*f['dsi']
        if high>=vm_high_water:raise ValueError('destination outside compact VM region')
        changes['d']=f['d']+user*4096
        proof.append(dict(field='d',space='VM',local_first=f['d'],local_last=high,
                          user_first=f['d']+user*4096,user_last=high+user*4096))
    if f['red'] and f['rb']>>22==0:
        high=f['rb']+(f['nout']-1)*f['rso']
        if high>=vm_high_water:raise ValueError('reducer destination outside compact VM region')
        changes['rb']=f['rb']+user*4096
        proof.append(dict(field='rb',space='VM',local_first=f['rb'],local_last=high,
                          user_first=f['rb']+user*4096,user_last=high+user*4096))
    out=dict(f);out.update(changes)
    for key in f:
        if key not in changes and out[key]!=f[key]:raise AssertionError('non-address field changed')
    return pack(out),proof
