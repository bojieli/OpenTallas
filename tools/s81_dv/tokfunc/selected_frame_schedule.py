#!/usr/bin/env python3
"""Extract station/return paths from the selected emitted functional frame.

No flat-parent crossing reconstruction or source-hash substitution. Every
landing encountered by a timed path is followed through its actual bank pair.
These are common-phase source MODEL ages; actual execution remains required.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--kit',type=Path,required=True)
    ap.add_argument('--compiler-root',type=Path,required=True)
    ap.add_argument('--baseline',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    sys.path[:0]=[str(a.compiler_root/'tools/landed_parent'),str(a.compiler_root/'tools/s81_dv')]
    import lp
    import frame_return_plan as RP
    k=json.loads((a.kit/'kit.json').read_text());assert not k['problems']
    sources={f['path']:f['sha256'] for f in k['files']}
    texts={}
    for rel,h in sources.items():
        path=a.kit/'src'/rel;assert sha(path)==h
        texts[rel]=path.read_text()
    def module(name):
        hits=[(p,t) for p,t in texts.items() if re.search(r'\bmodule\s+'+re.escape(name)+r'\b',t)]
        assert len(hits)==1,(name,[p for p,t in hits])
        rel,t=hits[0]
        # Only headers and wires-only frame body are parsed. Actual source is
        # preserved byte for byte in the source closure and simulator list.
        return rel,lp.parse_module(re.sub(r'//[^\n]*|/\*.*?\*/','',t,flags=re.S),name)
    rel,top=module('col_h9_l4_lp')
    assert sources[rel]=='c773586e5cb41288e1a296329a6d82780c6c300af60c3c4a26800bba081250d4'
    _,_,insts=lp.parse_body(top['body'])
    kids={i['inst']:i for i in insts};assert len(kids)==len(insts)
    ports={m:{p['name']:p['dir'] for p in module(m)[1]['ports']} for m in {i['module'] for i in insts}}
    def bits(ex):
        # All timed frame pins are explicit scalar-net concatenations.
        b=re.findall(r'\b(?:sk_n\d+_\d+|n\d+)(?:__l_r\d+)?\b|\blpl_\d+_o\b',ex)
        assert b,('non-explicit timed expression',ex)
        return b
    drv={}
    for i in insts:
        for p,ex in i['conns'].items():
            assert p in ports[i['module']],(i['inst'],p)
            if ports[i['module']][p]=='out':
                for bit,n in enumerate(re.findall(r'\b(?:sk_n\d+_\d+|n\d+)(?:__l_r\d+)?\b|\blpl_\d+_o\b',ex)):
                    assert n not in drv,('multiple driver',n)
                    drv[n]=(i['inst'],p,bit)
    aliases={}
    for m in re.finditer(r'\bassign\s+([^;]+?)\s*=\s*([^;]+);',top['body']):
        lhs,rhs=m.groups()
        if '?' in rhs:
            assert '(MUT == 1)' in rhs,(lhs,rhs)
            rhs=rhs.rsplit(':',1)[1]
        ls=re.findall(r'\b(?:sk_n\d+_\d+|n\d+)(?:__l_r\d+)?\b|\blpl_\d+_o\b',lhs)
        rs=re.findall(r'\b(?:sk_n\d+_\d+|n\d+)(?:__l_r\d+)?\b|\blpl_\d+_o\b',rhs)
        if ls and rs:
            assert len(ls)==len(rs),(lhs,rhs)
            for l,r in zip(ls,rs):assert l not in aliases;aliases[l]=r
    landings={}
    for i in insts:
        if i['module']=='ot_pl_land_vector_reset_r':
            w=kids[i['inst'].removesuffix('_r')+'_w']
            assert w['module']=='ot_pl_land_vector_reset_w'
            assert all(i['conns'][p]==w['conns'][p] for p in ['bank','epo','vld'])
            assert '.D(4)' in i['params'] and '.D(4)' in w['params']
            assert '.K(2)' in i['params'] or '.K((MUT == 2) ? 3 : 2)' in i['params']
            assert '.CHUNK_BITS(24)' in i['params'] and '.CHUNK_BITS(24)' in w['params']
            landings[i['inst']]=dict(writer=w['inst'],source=w['conns']['i'],read_clock=i['conns']['ck'],
                write_clock=w['conns']['ck'],writer_reset=w['conns']['rsi'],reader_reset=i['conns']['rsi'],D=4,K=2,
                steady_common_phase_model_edges=3)
    assert len(landings)==3017,len(landings)
    used=set()
    def back(net,mode):
        flat=add=0;cross=[];seen=set()
        while True:
            assert net not in seen,('loop',net);seen.add(net)
            if net in aliases:net=aliases[net];continue
            assert net in drv,('unresolved timed bit',net,mode)
            name,p,bit=drv[net];i=kids[name];m=i['module']
            if name in landings:
                l=landings[name];used.add(name);net=bits(l['source'])[bit];add+=3
                cross.append(dict(instance=name,bit=bit,**l));continue
            if m=='ot_pl_pad':
                n=re.search(r'\.N\((\d+)\)',i['params']);assert n,(name,i['params'])
                flat+=int(n[1]);net=bits(i['conns']['d'])[bit];continue
            if mode=='control' and m.startswith('ot_s81_cfg7_seq'):
                upstream=back(bits(i['conns']['lc'])[0],'station')
                return dict(source=upstream['source'],flat_link_edges=flat,
                    added_edges=add+upstream['added_edges'],link_edges=flat+add+upstream['added_edges'],
                    crossings=cross+upstream['crossings'])
            pin=None
            if m.startswith('dsfd_rly') or m=='dsfd_rstg':pin='i'
            elif m.startswith('dsfd_qbank') and p.startswith('d_'):pin='e_'+p[2:]
            elif m.startswith('dsfd_qbank') and p.startswith('o_'):pin='i_'+p[2:]
            elif m=='ot_s81_sstn_payload536':pin='i'
            elif m.startswith('ot_s81_sstn'):pin={'xa':'xai','xb':'xbi','cc':'cci'}.get(p)
            if pin:net=bits(i['conns'][pin])[bit];flat+=1;continue
            if mode=='return' and m=='ot_v41_rom_elem_q_qxpq_w10':
                size=len(bits(i['conns'][p]));assert size%2==0
                terminal=name[2:]+'.r'+str(1-bit//(size//2))
            else:terminal=name[2:] if m.startswith('dsfd_node') else name[2:]+'.'+p
            return dict(source=terminal,flat_link_edges=flat,added_edges=add,link_edges=flat+add,crossings=cross)
    nodes={};stations={}
    for i in insts:
        name=i['inst'];m=i['module']
        if m.startswith('dsfd_node'):
            node={}
            for p in 'ab':
                ex=i['conns'][p]
                if re.fullmatch(r"\d+'[bh]0+",ex.strip()):
                    b=dict(source='zero.'+name+'.'+p,flat_link_edges=0,added_edges=0,link_edges=0,crossings=[])
                else:
                    bb=[back(n,'return') for n in bits(ex)]
                    assert len({(b['source'],b['flat_link_edges'],b['added_edges']) for b in bb})==1,(name,p)
                    b=bb[-1]
                node[p]=b['source'];node['link_'+p]=b['link_edges'];node['evidence_'+p]=b
            nodes[name[2:]]=node
        if m=='ot_v41_rom_elem_q_qxpq_w10':
            paths={}
            for p,ex in i['conns'].items():
                if p.startswith('xs_'):
                    bb=[back(n,'station') for n in bits(ex)]
                    sig={(b['source'],b['flat_link_edges'],b['added_edges']) for b in bb}
                    paths[p]=dict(paths=[dict(source=x,flat_link_edges=y,added_edges=z) for x,y,z in sorted(sig)],aligned=len(sig)==1)
            added={b['added_edges'] for v in paths.values() for b in v['paths']}
            stations[name[2:]]=dict(inputs=paths,control={p:back(bits(i['conns'][p])[-1],'control') for p in ['go','cfg_v']},
                added_edges=sorted(added),all_x_inputs_equal_added_edges=len(added)==1)
    cf=next(i for i in insts if i['module']=='dsfd_cfifo_crs4');root=back(bits(cf['conns']['ri'])[-1],'return')
    topology=dict(master='col_h9',r1_skew=True,win=RP.WIN,rst=RP.RST,cf=RP.CF,nodes=nodes,
        root=root['source'],root_link=root['link_edges'],root_evidence=root)
    old=json.loads(a.baseline.read_text())
    def strip(x):
        if isinstance(x,dict):return {k:strip(v) for k,v in x.items() if k not in ['crossings'] and not k.startswith('evidence_') and k!='root_evidence'}
        if isinstance(x,list):return [strip(v) for v in x]
        return x
    comparison=dict(station_semantics_equal=strip(stations)==strip(old['station_inputs']),return_semantics_equal=strip(topology)==strip(old['topology']),
        baseline_sha256=sha(a.baseline),meaning='diagnostic comparison only; model is extracted from selected emitted source')
    out=dict(schema='opentallas.s81.frame_schedule.v1',source_root_kind='functional_kit_src',source_sha256=sources,
        source_root_relative_to_schedule=os.path.relpath(a.kit.resolve()/'src',a.out.resolve().parent),
        selected_frame_path=rel,selected_frame_sha256=sources[rel],functional_kit_sha256=sha(a.kit/'kit.json'),
        added_edges_per_crossing=3,station_inputs=stations,topology=topology,landing_count=len(landings),
        timed_path_landings=len(used),landing_paths=landings,comparison=comparison,
        reset_contract='actual rf3r: rst_n +2 ck_r0 before CRS; forwarded XO reset +2 xk; regional rootpad1 +forest6; chunk private reset relay in local W/R; no physical release/phase proof',
        qualification='SELECTED EMITTED SOURCE MODEL ONLY; actual frame programme/return/clock/reset execution required')
    a.out.write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(dict(stations=len(stations),nodes=len(nodes),landings=len(landings),comparison=comparison)))


if __name__=='__main__':main()
