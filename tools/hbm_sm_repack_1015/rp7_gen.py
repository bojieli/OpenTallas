#!/usr/bin/env python3
"""Split r6 pin faces from the body and preserve its schedule by explicit retiming.

For every original edge a->b, new_delay + pad + offset[a] must equal
old_delay + offset[b].  This is checked before any source is emitted.  A
partition alone would silently change the alignment at the SM fan-ins.
"""
from __future__ import annotations
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/landed_parent'))
import lp

OUT = 'rtl/hbm_accel/sm/repack/h2a7'
REC = 'results/arch/hbm_smh_r7_1021'


def partition(p, h, v, base):
    """MAIN: face roots; FALLBACK: face roots plus split west/east body.

    Existing hard children keep their shape.  X-store gets its own root,
    removing the 485 ps hard insertion from the soft pin tree's balance.
    """
    old = p.region
    new = dict(old)
    face = {'u_pb': 'tpw', 'u_be2': 'tpe', 'u_pr_'+h: 'cpw',
            'u_ro_'+h: 'cpe', 'u_lands': 'upn', 'u_xgi': 'upne',
            'u_xpi': 'upne', 'u_gs': 'mpse'}
    for name, r in face.items():
        if name in new:
            new[name] = r
    for name in new:
        if re.fullmatch(r'u_xs\d+', name):
            new[name] = 'xs'
        elif v == 'f' and new[name] == old[name] and not name.startswith('u_rst_'):
            # W and E row children have separate compact roots.  Other
            # body children retain their band until their landing is explicit.
            if name.startswith('u_rowe'):
                new[name] = 'ce'
            elif name.startswith('u_row'):
                new[name] = 'cw'
    centres = {r['name']: r['centre'] for r in base['regions']}
    height = 1512.0 if h == 'n' else 1252.8
    centres.update(tpw=[43.2, 1317.6], tpe=[648.0, 1317.6],
                   cpw=[43.2, 388.8], cpe=[648.0, 388.8],
                   upn=[207.36, height-43.2], upne=[626.4, height-43.2],
                   mpse=[626.4, 43.2], xs=[432.0, 918.0],
                   cw=[172.8, 432.0], ce=[561.6, 432.0])
    return new, centres


def generate(h, v):
    base = json.loads((ROOT / f'results/arch/hbm_smh_r6_1021/lp_spec_{h}_{v}.json').read_text())
    p = lp.Parent(base)
    oldplan = p.plan()
    new, centres = partition(p, h, v, base)
    ns = copy.deepcopy(base)
    ns['regions'] = [dict(name=r, insts=sorted(i for i in new if new[i] == r), centre=centres[r])
                     for r in dict.fromkeys(new.values())]
    q = lp.Parent(ns)
    newplan = q.plan()
    oldedges = {(a,b,n,pin):add for a,b,n,add,land,pin in oldplan['edges']}
    edges = [(a,b,n,add-oldedges[a,b,n,pin],pin,add,oldedges[a,b,n,pin])
             for a,b,n,add,land,pin in newplan['edges']]
    offsets = {node:0 for edge in edges for node in edge[:2]}
    for it in range(len(offsets)+1):
        changed = False
        for a,b,n,delta,pin,na,oa in edges:
            if offsets[b] < offsets[a]+delta:
                offsets[b] = offsets[a]+delta
                changed = True
        if not changed:
            break
    else:
        raise SystemExit(f'{h}{v}: retiming graph has a positive cycle')
    pads = {}
    proof = []
    for a,b,n,delta,pin,na,oa in edges:
        k = offsets[b]-offsets[a]-delta
        assert k >= 0
        if b.startswith('port:'):
            assert k == 0, 'output needs explicit output register'
            continue
        if k:
            key = (b,n)
            assert key not in pads or pads[key] == k
            pads[key] = k
        assert na+k+offsets[a] == oa+offsets[b]
        proof.append(dict(src=a,dst=b,net=n,old=oa,new=na,pad=k,
                          src_offset=offsets[a],dst_offset=offsets[b]))
    # Emit one compensation register per (net,reader), clocked by the
    # reader's region.  lp inserts the crossing before that register.
    body = p.mod['body']
    replacements, extra, decl = [], [], []
    padnames = {}
    for index, ((inst,n), count) in enumerate(sorted(pads.items())):
        name = f'r7p_{index}'
        padnames[inst,n] = name
        width = lp.eval_width(p.rng(n), p.env)
        decl.append(f'wire [{width-1}:0] {name};')
        assert count % 3 == 0
        extra.append(f'ot_rp7_delay_ring #(.W({width}), .N({count})) u_{name} (.clk(clk), .rst_n(lpr_pin), .d({n}), .q({name}));')
        new['u_'+name] = new[inst]
    oldrst = {i['inst']:i for i in p.insts if i['inst'].startswith('u_rst_')}
    rstnet = {n:i for i in oldrst.values() for pin,ex in i['conns'].items()
              if p.cports[i['module']][pin] == 'out' for n in lp.idents(ex)}
    for ins in p.insts:
        name = ins['inst']
        if name in oldrst:
            replacements.append((*ins['span'], ''))
            new.pop(name)
            continue
        conns = dict(ins['conns'])
        for pin,ex in conns.items():
            if p.cports[ins['module']][pin] != 'in' or pin in base['clock_pins']:
                continue
            if pin in base['reset_pins']:
                # Local reset copies preserve the original age plus the
                # consumer's retiming offset; no direct remote reset wire.
                ns_ = lp.idents(ex)
                if len(ns_) == 1 and next(iter(ns_)) in rstnet:
                    oldi = rstnet[next(iter(ns_))]
                    m = re.search(r'\.N\((\d+)\)', oldi['params'])
                    assert m, oldi
                    depth = int(m.group(1)) + offsets[name]
                elif ex == 'lpr_pin' and offsets[name]:
                    depth = offsets[name]-1
                else:
                    continue
                rn = 'r7rst_'+name
                decl.append(f'wire {rn};')
                extra.append(f'ot_rp5_rst #(.N({depth}), .NC(1)) u_{rn} (.clk(clk), .rst_n(lpr_pin), .r({rn}));')
                new['u_'+rn] = new[name]
                conns[pin] = rn
            else:
                conns[pin] = re.sub(r'\b[A-Za-z_]\w*\b',
                    lambda m:padnames.get((name,m.group()),m.group()), ex)
        text = f"{ins['module']} {ins['params']} {name} (" + ', '.join(f'.{k}({e})' for k,e in conns.items())+');'
        replacements.append((*ins['span'],text))
    for start,end,text in sorted(replacements, reverse=True):
        body = body[:start]+text+body[end:]
    top = f'ot_hbm_smh_rp7{h}_{v}_flat'
    header = ',\n'.join(lp.full_item(x) for x in p.mod['ports'])
    text = f'`timescale 1ns/1ps\nmodule {top} #(parameter integer HMUT=0) (\n{header}\n);\n'
    text += '\n'.join(decl)+'\n'+body+'\n'+'\n'.join(extra)+'\nendmodule\n'
    (ROOT/OUT).mkdir(parents=True,exist_ok=True)
    path = f'{OUT}/{top}.sv'
    (ROOT/path).write_text(text)
    ns.update(top=top, top_lp=top.removesuffix('_flat'), sources=[path],
              out_dir=f'{OUT}/lp_{h}_{v}', record_dir=REC,
              mut_child=f'u_r7rst_u_pub{0 if h == "n" else 1}',
              why='r7 face roots isolated from hard insertion; exact edge-retiming against r6')
    ns['child_sources'] += [f'{OUT}/ot_rp7_delay_ring.sv',
                           'rtl/common/landed_parent/ot_pl_land_field_copies.sv']
    ns['regions'] = [dict(name=r,insts=sorted(i for i in new if new[i]==r),centre=centres[r])
                     for r in dict.fromkeys(new.values())]
    ns['r7'] = dict(output_offsets={n[5:]:o for n,o in offsets.items() if n.startswith('port:') and p.ports[n[5:]]['dir']=='out'},
                    edge_proof=proof,compensation=pads_to_json(pads),child_offsets=offsets,
                    reset_note='consumer reset age retimed locally; new regional forest boot depth recorded by lp')
    (ROOT/REC).mkdir(parents=True,exist_ok=True)
    (ROOT/REC/f'lp_spec_{h}_{v}.json').write_text(json.dumps(ns,indent=1)+'\n')
    print(h,v,'regions',len(ns['regions']),'pads',len(pads),'outputs',ns['r7']['output_offsets'])
    return ns


def pads_to_json(pads):
    return [dict(inst=i,net=n,stages=k) for (i,n),k in sorted(pads.items())]


if __name__ == '__main__':
    for h in 'ns':
        for v in 'mf':
            generate(h,v)
