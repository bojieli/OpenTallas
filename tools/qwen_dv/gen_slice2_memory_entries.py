#!/usr/bin/env python3
"""Propose exact memory sink/LEF bindings, without asserting CTS or pin escape."""
from pathlib import Path
import hashlib, json, re

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/arch/safe_qw_slice_w_1019'

def clock_pin(view):
    files=list((ROOT/view).glob('*.lef'))
    if len(files)!=1:raise ValueError('unique LEF required: '+view)
    raw=files[0].read_bytes();s=raw.decode()
    m=re.search(r'\bPIN\s+clk\b(.*?)\bEND\s+clk\b',s,re.S)
    if not m or not re.search(r'\bUSE\s+CLOCK\s*;',m[1]):raise ValueError('native clk CLOCK missing: '+view)
    rect=re.findall(r'\bRECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s*;',m[1])
    layers=re.findall(r'\bLAYER\s+(\w+)\s*;',m[1])
    if len(rect)!=1 or len(layers)!=1:raise ValueError('single clock rectangle contract changed: '+view)
    x1,y1,x2,y2=map(float,rect[0])
    return dict(pin='clk',layer=layers[0],rect_um=[x1,y1,x2,y2],centre_um=[(x1+x2)/2,(y1+y2)/2],lef=str(files[0].relative_to(ROOT)),lef_sha256=hashlib.sha256(raw).hexdigest())

def generate():
    raw=(OUT/'geometry_proposal.json').read_bytes();geo=json.loads(raw)
    vm=[x for x in geo['objects'] if x['kind']=='legacy_VM_native_body_escape_pending']
    storage=[x for x in geo['objects'] if x['kind']=='new_native32x64_body']
    vm_names=[f'u_c.u_vm.g_rep[{op}].g_bank[{bank}].u_m' for op in range(3) for bank in range(2)]
    vm_names += [f'u_c.u_vm.g_crom[{bank}].u_{half}' for bank in range(2) for half in ['lo','hi']]
    vm_names += [f'u_c.u_vm.g_btc[{cp}].g_btb[{bank}].u_m' for cp in range(2) for bank in range(4)]
    vm_names += [f'u_c.u_vm.g_prog[{bank}].u_{half}' for bank in range(2) for half in ['lo','hi']]
    if len(vm)!=22 or len(storage)!=42:raise ValueError('actual 22+42 contract changed')
    entries=[]
    for i,obj in enumerate(vm+storage):
        name=vm_names[i] if i<22 else obj['name']
        pin=clock_pin(obj['view']);at=obj['at']
        pos=[round(at[j]+pin['centre_um'][j],6) for j in range(2)]
        if i<10:group=f'vm1024_pair{i//2}'
        elif i<22:group=f'vm_small_triple{(i-10)//3}'
        else:group='storage_'+name.split('.')[2]
        entries.append(dict(instance=name,master=obj['view'].split('/')[-1],clock_pin_path=name+'.clk',
            source_clock='ck_core',active_edge='posedge',native_clock_sink_count=1,macro_origin_um=at,
            pin_global_centre_um=pos,clock_pin=pin,distribution_anchor_group=group,
            reset_pin=None,status='EXPLICIT_CANDIDATE_BINDING_REQUIRES_ELABORATED_AND_NATIVE_GRAPH_MATCH'))
    groups=[]
    for key in dict.fromkeys(e['distribution_anchor_group'] for e in entries):
        es=[e for e in entries if e['distribution_anchor_group']==key]
        anchor=[round(sum(e['pin_global_centre_um'][j] for e in es)/len(es),6) for j in range(2)]
        distances=[round(sum(abs(e['pin_global_centre_um'][j]-anchor[j]) for j in range(2)),6) for e in es]
        groups.append(dict(name=key,sinks=len(es),candidate_clock_distribution_anchor_um=anchor,
            max_unrouted_manhattan_sink_distance_um=max(distances),under405_geometric_lower_bound=max(distances)<=405,
            interpretation='Same ck_core family; anchor is not an extra root, CTS buffer, closure proof, or routed path.'))
    sources=['rtl/qwen_dv/qfd_dv_vm_safe.sv','rtl/qwen_dv/qfd_dv_redstn2_rsafe.sv',
             'rtl/qwen_dv/qfd_dv_slice2_regional_parts.sv','rtl/qwen_dv/lp/qfd_dv_slice2_w_regional_lp.sv']
    return dict(schema='opentallas.qwen.native_memory_entry_proposal.v1',status='SOURCE_BOUND_GEOMETRY_PROPOSAL_NOT_CTS_OR_GATE',
        geometry_sha256=hashlib.sha256(raw).hexdigest(),parent_source_checkpoint='f543b8717',storage_source_checkpoint='b99c1cb10',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
        actual_native_memory_clock_sinks=len(entries),source_clock_roots=['ck_core'],entries=entries,distribution_anchor_groups=groups,
        obligations=['Match every exact instance/master/pin against elaborated current-final RTL and actual post-synth clock-object ownership.',
            'Prove actual CTS arrival/skew/hold/setup at all64 entries, including root-to-anchor routes and real PG/via pin access.',
            'Anchor-to-pin Manhattan geometry is a route lower bound, not a routed <=405um guarantee.',
            'All soft clocks, forwarded halfcycle transports, regional roots, reset forests and hard head/SFU/xs native entries require their own complete audits.',
            'Legacy128x256/256x256 raw face density still fails; allocated channels do not supply the missing PG/GRT/DRC escape proof.'])

if __name__=='__main__':
    d=generate();(OUT/'native_memory_entry_proposal.json').write_text(json.dumps(d,indent=2)+'\n')
    print('native sinks',d['actual_native_memory_clock_sinks'],'anchors',len(d['distribution_anchor_groups']))
