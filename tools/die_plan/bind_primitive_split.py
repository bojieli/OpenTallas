"""Explicit exact bit partitions of native FF primitives, before core composition."""
import copy

class PrimitiveSplitError(ValueError):
    pass

def split_cells(cells, specs, Cell):
    """Pure transformation; every original D/Q bit occurs once, controls copied.

    specs=[{member:original_path, fragments:[{path:new_path,bits:[LSB indices]}]}].
    Unlisted cells are identical objects. Unsupported primitives fail closed.
    """
    if not isinstance(specs,list):raise PrimitiveSplitError('primitive_splits must be a list')
    bypath={c.path:c for c in cells};replacements={};records=[];newpaths=set()
    for s in specs:
        path=s['member']
        if path not in bypath or path in replacements:raise PrimitiveSplitError('missing or repeated primitive '+path)
        c=bypath[path];t=c.ytype
        if c.kind!='glue' or t not in ('$dff','$adff'):raise PrimitiveSplitError('unsupported primitive '+path)
        expected={'CLK','D','Q'}|({'ARST'} if t=='$adff' else set())
        if set(c.ports)!=expected:raise PrimitiveSplitError('unexpected primitive port '+path)
        w=len(c.ports['Q']);P=c.yparams
        if len(c.ports['D'])!=w or int(P['WIDTH'],2)!=w:raise PrimitiveSplitError('primitive WIDTH mismatch '+path)
        if any(len(c.ports[p])!=1 for p in expected-{'D','Q'}):raise PrimitiveSplitError('nonscalar control '+path)
        bits=[i for f in s['fragments'] for i in f['bits']]
        if any(type(i) is not int for i in bits) or sorted(bits)!=list(range(w)):raise PrimitiveSplitError('fragments must partition every original D/Q bit exactly once '+path)
        rv=P.get('ARST_VALUE','').zfill(w)
        if t=='$adff' and (len(rv)!=w or set(rv)-set('01xz')):raise PrimitiveSplitError('invalid reset value '+path)
        fs=[];rr=[]
        for f in s['fragments']:
            indices=f['bits'];p=f['path']
            if not indices or p in newpaths or (p in bypath and p!=path):raise PrimitiveSplitError('empty fragment or path collision '+p)
            newpaths.add(p);params=dict(P);params['WIDTH']=format(len(indices),'b')
            if t=='$adff':params['ARST_VALUE']=''.join(rv[w-1-i] for i in reversed(indices))
            ports={pn:([bs[i]for i in indices]if pn in ('D','Q')else list(bs))for pn,bs in c.ports.items()}
            fs.append(Cell(p,c.module,copy.deepcopy(c.params),ports,dict(c.dirs),c.kind,ytype=t,yparams=params,src=c.src))
            rr.append(dict(path=p,original_bits=indices))
        replacements[path]=fs;records.append(dict(member=path,primitive=t,width=w,fragments=rr,terminal_partition_equality=True,controls_and_polarities_unchanged=True))
    out=[f for c in cells for f in replacements.get(c.path,[c])]
    if len({c.path for c in out})!=len(out):raise PrimitiveSplitError('resulting primitive path collision')
    return out,records
