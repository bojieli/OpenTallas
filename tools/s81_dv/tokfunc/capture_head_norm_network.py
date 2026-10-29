#!/usr/bin/env python3
"""Capture actual internal norm and XR/XFIN wiring for a static HEAD component.

Every bus bit must name its actual producer and fixed source transport age.
This is source transport, not local arithmetic latency or physical clock/START
qualification. Existing binder variant and exact-buffer guards remain active.
"""
import argparse
import json
import pickle
import hashlib
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/s81_dv'))
from layer_prog.bound_die import BoundDie,object_items
from layer_prog.bound_entry_transport import BufferSinks
from layer_prog.bound_return_transport import check_variant,desc_of
from layer_prog.bound_xg_transport import XFIN


def one(interfaces,prefix,module):
    names=[n for n,m in interfaces.items()if n.startswith(prefix+'.')and m['module']==module and m['kind']=='leaf']
    if len(names)!=1:raise ValueError(f'{prefix}: need one exact {module}, found {names}')
    return names[0]


def word(die,src,sp,dst,dp,width,sl=0,dl=0):
    meta=die.inventory['leaf_interfaces'].get(dst)
    if meta is not None:
        p=meta['ports'].get(dp,{})
        if p.get('dir')!='input' or p.get('width',0)<dl+width:raise ValueError(f'{dst}.{dp}: exact input width missing')
    source_meta=die.units.get(src)
    if source_meta is not None:
        port=source_meta['ports'].get(sp,{})
        if port.get('dir')!='output' or len(port.get('bits',[]))<sl+width:
            raise ValueError(f'{src}.{sp}: exact output width missing')
    ages=set()
    for b in range(width):
        pin=f'{dst}.{dp}[{dl+b}]';check_variant(die,pin);check_variant(die,f'{src}.{sp}[{sl+b}]')
        d=desc_of(die,pin)
        expected=f'{src}.{sp}[{sl+b}]'
        if source_meta is not None:
            net=source_meta['ports'][sp]['bits'][sl+b]
            producers=die.inventory['drivers'].get(str(net),[])
            if len(producers)!=1:
                raise ValueError(f'{src}.{sp}[{sl+b}]: missing or ambiguous exact parent output driver')
            expected=producers[0]
            check_variant(die,expected)
        if d[1]!=expected:raise ValueError(f'{pin}: actual driver {d[1]} expected {expected}')
        ages.add(d[2])
    if len(ages)!=1:raise ValueError(f'{dst}.{dp}: incoherent bit ages {ages}')
    return next(iter(ages))


def capture(bound,inventory,entry,xg,out):
    if out.exists():raise ValueError('preserve earlier result; fresh output required')
    die=BoundDie(bound,inventory);li=die.inventory['leaf_interfaces']
    ent=json.loads(entry.read_text());net=json.loads(xg.read_text())
    for name,v in [('entry',ent),('xg',net)]:
        if v.get('source_asbuilt_sha256')!=die.inventory['source_asbuilt_sha256']or v.get('die_sha256')!=die.die_sha:
            raise ValueError(name+' differs from exact selected graph')
    wanted={p for ps in die.inventory['input_pins'].values()for p in ps}
    relevant={'ot_s81sl_vn_a','ot_s81sl_vn_b','ot_s81sl_vq',XFIN}
    for n,m in li.items():
        w=BufferSinks.width(m)
        if w is not None:wanted.update(f'{n}.A[{b}]'for b in range(w))
        elif m['module']in relevant:
            for p,z in m['ports'].items():
                if z['dir']=='input':wanted.update(f'{n}.{p}[{b}]'for b in range(z['width']))
    cache=out.parent/'norm_network_sinks.pkl'
    key=(die.die_sha,die.inventory['source_asbuilt_sha256'],hashlib.sha256(inventory.read_bytes()).hexdigest())
    if cache.exists():
        cached_key,raw=pickle.loads(cache.read_bytes())
        if cached_key!=key:raise ValueError('cached source sink graph differs')
    else:
        raw={k:v for k,v in object_items(die.bound/'bind_sinks.json')if k in wanted}
        with cache.open('xb') as f:pickle.dump((key,raw),f,protocol=5)
    die.sinks=BufferSinks(raw,li)
    rows=[]
    for e in ent['leaves']:
        row={k:e[k]for k in('slice','leaf','xr','vp')}
        try:
            if e['status']!='PASS':raise ValueError('entry source not qualified')
            prefix=e['vp'].rsplit('.',1)[0];a=one(li,prefix,'ot_s81sl_vn_a');b=one(li,prefix,'ot_s81sl_vn_b');q=one(li,prefix,'ot_s81sl_vq');vp=e['vp']
            routes={}
            for label,vn,half in [('a',a,0),('b',b,128)]:
                for p,w in [('n_go',1),('n_pre',128),('hw_v',1),('hw_j',3),('hw_hf',1),('hw_d',256),('wl_v',1),('wl_i',3)]:
                    routes[f'vp.{p}->vn_{label}']=word(die,vp,p,vn,p,w)
                routes[f'vp.wl_d->vn_{label}']=word(die,vp,'wl_d',vn,'wl_d',128,sl=half)
                routes[f'xr.rb_v->vn_{label}']=word(die,e['xr'],'rb_v',vn,'rb_v',1)
                routes[f'xr.rb_d->vn_{label}']=word(die,e['xr'],'rb_d',vn,'rb_d',32)
            routes['vn_a.c_v->vn_b']=word(die,a,'c_v',b,'c_v',1)
            routes['vn_a.c_s->vn_b']=word(die,a,'c_s',b,'c_s',31)
            routes['vn_a.y->vq']=word(die,a,'y',q,'y',64)
            routes['vn_b.y->vq']=word(die,b,'y',q,'y',64,dl=64)
            for p,w in [('y_v',1),('y_i',3)]:routes['vn_b.'+p+'->vq']=word(die,b,p,q,p,w)
            for p,w in [('m_v',1),('m_q',1),('m_b',1),('m_i',8)]:routes['vp.'+p+'->vq']=word(die,vp,p,q,p,w)
            row.update(status='PASS_SOURCE_NORM_TRANSPORT',vn_a=a,vn_b=b,vq=q,edges=routes,
                       relative_n_go_b_minus_a=routes['vp.n_go->vn_b']-routes['vp.n_go->vn_a'],
                       chain_transport_edges=routes['vn_a.c_v->vn_b'],local_normr_to_partial_edges=None)
        except(ValueError,KeyError)as exc:row.update(status='BLOCKED',reason=str(exc))
        rows.append(row)
    xrrows=[]
    for e in net['xfin_endpoints']:
        row={k:e[k]for k in('slice','xr','xg','xfin')}
        try:
            fields={dst:word(die,e['xr'],src,e['xfin'],dst,w)for src,dst,w in
                    [('x_go','go',1),('x_mode','mode',1),('x_eps','eps',32),('x_sv','s_v',1),('x_si','s_i',7),('x_s','s',32)]}
            xr=die.units[e['xr']];xgu=die.units[e['xg']]
            row.update(status='PASS_SOURCE_XR_XFIN',edges=fields,xr_master=xr['master'],xr_params=xr.get('params',{}),xg_master=xgu['master'])
        except(ValueError,KeyError)as exc:row.update(status='BLOCKED',reason=str(exc))
        xrrows.append(row)
    record=dict(schema='opentallas.head.norm_network_source.v1',source_asbuilt_sha256=die.inventory['source_asbuilt_sha256'],die_sha256=die.die_sha,
                leaves=rows,xr_xfin=xrrows,transport=net,
                verdict='PASS_SOURCE_NORM_NETWORK'if all(x['status'].startswith('PASS')for x in rows+xrrows)else'BLOCKED',
                local_arithmetic_timing_qualified=False,physical_clock_phase_qualified=False,absolute_START_qualified=False,full_token=False)
    out.write_text(json.dumps(record,indent=1)+'\n')
    print(json.dumps(dict(verdict=record['verdict'],leaves_pass=sum(r['status'].startswith('PASS')for r in rows),
                         xr_xfin_pass=sum(r['status'].startswith('PASS')for r in xrrows),blocked=sum(r['status']=='BLOCKED'for r in rows+xrrows))))
    return 0 if record['verdict'].startswith('PASS')else 2


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in('bound','inventory','entry','xg','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();raise SystemExit(capture(a.bound,a.inventory,a.entry,a.xg,a.out))
