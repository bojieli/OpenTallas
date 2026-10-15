#!/usr/bin/env python3
"""Read a pinned Git tree; export structural facts, never physical assumptions."""
import argparse, hashlib, json, re, subprocess
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--repo', default='.')
p.add_argument('--source', default='2eb33e9a8')
p.add_argument('--out', required=True)
a=p.parse_args()
def git(*args):
    return subprocess.check_output(['git','-C',a.repo,*args])
commit=git('rev-parse',a.source).decode().strip()
paths=git('ls-tree','-r','--name-only',commit).decode().splitlines()
def read(path): return git('show',f'{commit}:{path}').decode()
def clean(s): return re.sub(r'//[^\n]*|/\*.*?\*/','',s,flags=re.S)
def balanced(s,i):
    assert s[i]=='('
    depth=1;j=i+1
    while depth:
        if s[j]=='(':depth+=1
        elif s[j]==')':depth-=1
        j+=1
    return s[i+1:j-1],j
sources={}
modules={}
selected=[x for x in paths if x.endswith('.sv') and (x.startswith('rtl/dsrom_sys/s81_static_collective/') or x.startswith('rtl/dsrom_sys/s81_static_hc/') or x in ['rtl/dsrom_sys/s81_ph/coll/dsfd_coll_static_channels.sv','rtl/dsrom_sys/s81_ph/coll/dsfd_coll_ck.sv','rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv','rtl/dsrom_sys/s81_ph/ot_s81ph_fp32_add_rne_preexp.sv','rtl/lib/ot_rst_relay.sv','rtl/link/ot_link_crc32.sv','rtl/hdc/ot_hdc_prefix.sv','rtl/dsrom_sys/s81_ph/ot_s81ph_coll_rstc.sv','rtl/dsrom_sys/s81_ph/ot_s81_pll_bb.sv']) and '/test' not in x and '/tb_' not in x]
for path in selected:
    src=read(path);sources[path]=hashlib.sha256(src.encode()).hexdigest();s=clean(src)
    for match in re.finditer(r'\bmodule\s+(\w+)\s*',s):
        name=match[1];i=match.end()
        if s[i:i+1]=='#':
            i=s.index('(',i);_,i=balanced(s,i)
        i=s.index('(',i);header,end=balanced(s,i)
        ports=[];direction=None;width=1;width_expression=None
        for part in header.split(','):
            part=part.strip()
            m=re.match(r'(input|output|inout)\b\s*(.*)',part,flags=re.S)
            if m:
                direction=m[1];part=m[2];width=1;width_expression=None
                part=re.sub(r'\b(wire|reg|logic|signed)\b','',part).strip()
                w=re.match(r'\[([^]]+)\]\s*(.*)',part,flags=re.S)
                if w:
                    width_expression=w[1];part=w[2]
                    n=re.fullmatch(r'\s*(\d+)\s*:\s*(\d+)\s*',width_expression)
                    width=abs(int(n[1])-int(n[2]))+1 if n else None
            if direction and re.fullmatch(r'\w+',part.strip()):
                ports.append(dict(name=part.strip(),direction=direction,bits=width,width_expression=width_expression))
        modules[name]=dict(source=path,ports=ports,declared_port_bits=sum(x['bits'] for x in ports) if all(x['bits'] is not None for x in ports) else None,body=s[end:s.index('endmodule',end)])
for name,m in modules.items():
    instances=[]
    for typ in modules:
        for match in re.finditer(r'\b'+re.escape(typ)+r'\s*(#\s*)?',m['body']):
            i=match.end()
            if match[1]:
                i=m['body'].index('(',i);params,i=balanced(m['body'],i)
            else:params=''
            tail=re.match(r'\s*(\w+)\s*\(',m['body'][i:])
            if not tail:continue
            inst=tail[1];i+=tail.end()-1;conns,_=balanced(m['body'],i)
            ports={}
            for c in re.finditer(r'\.(\w+)\s*\(',conns):
                expr,_=balanced(conns,c.end()-1);ports[c[1]]=expr.strip()
            instances.append(dict(module=typ,instance=inst,parameters=params,connections=ports,wildcard='.*' in conns))
    m['instances']=instances
    del m['body']
roots=[]
def root(id,clock,ownership,missing):
    roots.append(dict(id=id,clock=clock,logic_ownership=ownership,physical_cut_status=missing,outline_um=None,placed_home=None,physical_pin_coordinates=None))
root('control0','ck_control[0]',['slab.calendar (CURRENT one-clock calendar, three ROMs)','wrapper.reset_q','slab.reset_root[0].rr'],'UNHARDENED; calendar7 candidate is not instantiated')
root('control1','ck_control[1]',['slab.tp4.core','slab.tp4.rank_q/rank_set/rank_fault','slab.tp4.remote_v_map/remote_frame_map combinational mapping','slab.reset_root[1].rr'],'UNHARDENED; core-only module omits wrapper ownership')
root('control2','ck_control[2]',['slab.raw_rows REGISTER_VM_WRITES=0','slab.vm_boundary PINCAP=1 including ot_rst_relay REGIONS=1 SYNC_STAGES=2 TREE_STAGES=1','slab.status_q','slab.reset_root[2].rr'],'VMB-only candidate kit exists; full same-root cut absent')
root('control3','ck_control[3]',['slab.channels.a','slab.host_queue DEPTH=16 MUT=0','slab.reset_root[3].rr'],'UNHARDENED; adapter-only module omits host queue')
root('control4','ck_control[4]',['slab.reduce.identity[0:17]','slab.reduce.fault and lv/le reductions','slab.assemble.seen/assembly_tag/row_valid/row_tag/fault','slab.assemble.write_good/emit_good/destination_index combinational logic','slab.reset_root[4].rr'],'MISSING extracted metadata leaf spanning two modules')
faces=['W0','W1','W2','W3','E0','E1','E2','E3']
for i in range(8):
    owner=f'slab.tp4.L[{i}].lane' if i<3 else f'slab.channels.g_lane[{i-3}].l'
    reset=f'slab.tp4.L[{i}].reset_lane.rr' if i<3 else f'slab.channels.g_lane[{i-3}].reset_lane.rr'
    root(f'lane{i}',f'ck_lane[{i}]',[owner,reset,f'wrapper.c{faces[i]} forwarded-clock buffer'],'UNHARDENED; original module port boundary exists, reset/buffer ownership needs integration')
for i in range(16):
    root(f'hc{i}',f'ck_hc_lane[{i}]',[f'slab.reduce.L[{i}].leaf (three adders, input/output registers)',f'slab.reduce.L[{i}].reset_lane.rr',f'slab.assemble.L[{i}].leaf (512 assembly +512 output bits)'],'MISSING combined arithmetic+assembly cut; source scalar leaves exist separately')
slab=modules['s81_static_collective_slab']
signals={}
for inst in slab['instances']:
    directions={x['name']:x for x in modules[inst['module']]['ports']}
    for port,expr in inst['connections'].items():
        for signal in set(re.findall(r'\b[A-Za-z_]\w*\b',expr)):
            if signal in ['b0','b1']:continue
            signals.setdefault(signal,[]).append(dict(instance=inst['instance'],module=inst['module'],port=port,expression=expr,direction=directions.get(port,{}).get('direction'),declared_port_bits=directions.get(port,{}).get('bits')))
slabports={x['name']:x for x in slab['ports']}
hyperedges=[dict(signal=k,endpoints=v,external_slab_port=slabports.get(k)) for k,v in sorted(signals.items())]
expected=['s81_static_calendar_controller','s81_static_fmt1_core_dynamic','s81_static_fmt1_lane_dynamic','s81_static_raw_fmt1_lane','s81_static_hc_scalar_reduce','s81_static_hc_scalar_assemble','s81_static_host_queue','s81_static_raw_vm_rows','s81_static_vm_boundary','dsfd_coll_static_channels']
view_evidence={}
for name in expected:
    lef=[x for x in paths if x.startswith('physical/') and x.endswith('/'+name+'.lef')]
    view_evidence[name]=dict(committed_lef_paths=lef,source_matched_closed_view=False,status='ABSENT in pinned tree' if not lef else 'PRESENT; requires source/parameter/signoff binding audit')
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
result=dict(schema='s81.actual-collective-structural-graph.v1',source_commit=commit,scope='Structural source audit only. No synthesized root census, area, cut pin count, placement or routing claim.',source_sha256=sources,root_count=len(roots),roots=roots,module_port_boundaries=modules,slab_connection_hyperedges=hyperedges,physical_view_evidence=view_evidence,calendar7_candidate=dict(status='NOT_INTEGRATED_IN_AUDITED_PARENT',module='s81_static_calendar_controller7',existing_clock='clk',additional_delivered_clock_inputs=['clk_rom[0]','clk_rom[1]','clk_rom[2]','clk_outputs[0]','clk_outputs[1]','clk_outputs[2]'],additional_root_count=6,resulting_candidate_root_count=35,parent_port_and_die_delivery_binding='OPEN',note='29 roots describes actual parent only. Replacing its one-clock calendar with the seven-root candidate requires six additional real parent clock inputs, actual delivered phases/resets and new physical ownership/pin binding.'),packing=dict(status='OPEN_MISSING_LEAF_OUTLINES_AND_PHYSICAL_PINS',reservation_only_um=[1727.976,2721.576],needed_area_um2=None,candidate_placements=[],reason='No source-current outlines for 29 root ownership cuts; cannot infer packing or grant geometric routes from historical census or reservation.'))
(out/'graph.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(source_commit=commit,roots=len(roots),modules=len(modules),hyperedges=len(hyperedges),source_files=len(sources),out=str(out/'graph.json'))))
