#!/usr/bin/env python3
"""Verify all physical leaf wrapper connections against actual core ports.

This proves the five thin boundaries have matching named ports and bit widths;
it does not establish arithmetic, placement, or timing qualification.
"""
import argparse
import ast
import json
import tempfile
from pathlib import Path
import su_tile_tops as T
from native_physical_join import ROOT,HD,blob,sha


def integer(text,env):
    node=ast.parse(text,mode='eval')
    allowed=(ast.Expression,ast.Constant,ast.Name,ast.Load,ast.BinOp,ast.UnaryOp,
             ast.Add,ast.Sub,ast.Mult,ast.FloorDiv,ast.Div,ast.LShift,ast.RShift,ast.USub,ast.UAdd)
    if any(not isinstance(x,allowed) for x in ast.walk(node)):raise ValueError(text)
    return int(eval(compile(node,'<width>','eval'),{'__builtins__':{}},env))


def check(rev):
    paths=[HD+'dsfd_su_t_cn_ik.sv',HD+'ot_s81_su_cn_ik.sv',HD+'ot_s81_su_qn.sv']
    with tempfile.TemporaryDirectory() as d:
        tmp=Path(d)
        for p in paths:
            q=tmp/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(blob(rev,p))
        saved=T.ROOT;T.ROOT=tmp
        try:mods={name:data for p in paths for name,data in T.modules(p).items()}
        finally:T.ROOT=saved
    report=[]
    for top in ['dsfd_su_t_cn8','dsfd_su_t_cn4','dsfd_su_t_cnnw','dsfd_su_t_ikh','dsfd_su_t_ikr']:
        _,ptxt,body=mods[top];pins=T.port_widths(ptxt)
        instances=list(T.instances(body))
        assert len(instances)==1,top
        _,_,core,override,inst,connected=instances[0]
        defaults,cptxt,cbody=mods[core];cpins=T.port_widths(cptxt)
        assert set(connected)==set(cpins),(top,'missing/unknown core ports',set(cpins)^set(connected))
        assert set(connected.values())==set(pins),(top,'disconnected or transformed wrapper ports')
        # Integer defaults are ordered in the actual module declaration.
        env={}
        for k,v in defaults.items():env[k]=integer(override.get(k,v),env)
        for k,v in override.items():
            assert k in defaults,(top,k)
        counts={}
        for name,wp in connected.items():
            cd,cw=cpins[name];wd,ww=pins[wp]
            cb=integer(cw,env)+1 if cw is not None else 1
            wb=integer(ww,{})+1 if ww is not None else 1
            assert cd==wd and cb==wb,(top,name,cd,cb,wd,wb)
            counts[wp]=cb
        assert pins['ck']==('input',None) and pins['rst']==('input',None),top
        assert not any(token in T.strip_comments(body) for token in ['always','reg ','logic ']),top
        report.append(dict(top=top,core=core,parameters=env,port_bits=counts,core_to_wrapper_pin=connected,verdict='PASS'))
    return dict(schema='opentallas.s81.native-leaf-wrappers.v1',source_revision=rev,
                source_sha256={p:sha(blob(rev,p)) for p in paths},wrappers=report,
                qualification_scope='named port, width, scalar clock/reset, and no added state only')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',default='5f2fa2ea2');p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();d=check(a.source);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+'\n')
    print('PASS five native wrappers: exact core port names and widths, scalar roots, no added state')
