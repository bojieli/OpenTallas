#!/usr/bin/env python3
"""Deterministic disabled provider exports from immutable selected definitions."""
import argparse, hashlib, json, math, re
from pathlib import Path

PROVIDERS = {
 'ot_hgi_sfu_core_split3__ctl': ([669.6,626.4],8933,'u_core_u_engine_u_arithmetic_procdff_71639__Q',[0,1021]),
 'ot_hnx_sfu_store_a__da81d76763c9': ([760.32,483.84],1888,'cmd0_Q',[576,895]),
 'ot_hnx_sfu_store_b__1300886e9f18': ([760.32,691.2],2800,'cmd0_Q',[576,895]),
}

def abi(text):
    start = re.search(r'\bmodule\s+\w+', text)
    if not start: raise ValueError('module header absent')
    header = text[start.start():].split(');',1)[0]
    return [dict(name=m[3], direction=m[0], is_vector=bool(m[1]), width=abs(int(m[1])-int(m[2]))+1 if m[1] else 1)
            for m in re.findall(r'\b(input|output|inout)\s+(?:wire|logic|reg)?\s*(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*(\w+)',header)]

def extract(selected, out):
    captures={}; active=None; lines=[]; origin=None; origins={}
    for line in Path(selected).open():
        if line.startswith('`line'): origin=line.strip()
        m=re.match(r'\s*module\s+(\w+)',line)
        if m and m[1] in PROVIDERS:
            if m[1] in captures: raise ValueError('duplicate selected provider')
            active=m[1];lines=[];origins[active]=origin
        if active:
            lines.append(line)
            if re.match(r'\s*endmodule\b',line):
                captures[active]=''.join(lines);active=None
    if set(captures)!=set(PROVIDERS):raise ValueError('missing selected provider')
    out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=[]
    for module,text in sorted(captures.items()):
        outline,declared,port,bits=PROVIDERS[module];ports=abi(text)
        actual=next(p for p in ports if p['name']==port)
        if actual['direction']!='output' or actual['width']<bits[1]+1:raise ValueError('producer ABI changed')
        direct=sum(abs(int(a)-int(b))+1 for a,b in re.findall(r'\breg\s+\[(\d+):(\d+)\]\s+g_compose_m\w+',text))
        if direct!=declared:raise ValueError('selected structural state changed')
        path=out/(module+'.sv');path.write_text(text)
        row=dict(module=module,source=path.name,source_sha256=hashlib.sha256(text.encode()).hexdigest(),original_origin=origins[module],ports=ports,external_bits=sum(p['width']for p in ports),planning_outline_um=outline,old_view_compatibility_credit=False,declared_direct_FF=direct,required_native_export=dict(port=port,bits=bits),START=dict(named_ports=[p for p in ports if'start'in p['name'].lower()],opaque_command_contract='Compiler control vectors remain exact; absence of a named START is not an absence-of-start claim. Native command/epoch/calendar joins required.'),status='DISABLED_PROVIDER_SOURCE_EXPORT_NO_PHYSICAL_BUILD')
        if module.endswith('__ctl'):
            row['source_model']=dict(VM_READ_RETURN=88,VM_WRITE_RETURN=85,VM_bridge_declared_FF=27301,reset_relay_FF=6,total_declared_preopt_FF=36240,native_SRAMs=0,clock_fanout_status='36240 source state bits on one exported clk; actual mapped sinks/tree unknown, clock decomposition/profile is a next gate')
        else:
            row['source_model']=dict(lgroups=2,lgroup_N=16,lgroup_LWB=15,lbank_RB=11,native_SRAMs=32,native_SRAM_master='ot_sram_1r1w_256x256_m2_r2c2',native_memory_bits=2097152,lgroup_declared_soft_FF_including_bank_selectors=643,declared_preopt_soft_FF=direct+1286,constant_LAT0_unused_declared_FF=208,macro_physical_view_status='Must use actual selected native master views; no generic memory substitution')
        row['pin_capacity_model']=dict(clock_and_reset_ports=[p for p in ports if 'clk'in p['name']or'rst'in p['name']],perimeter_um=2*sum(outline),at6pins_per_um_capacity=math.floor((2*sum(outline)-8*4.32)*6),actual_pin_placement='UNBUILT')
        rows.append(row)
    (out/'providers.json').write_text(json.dumps(rows,indent=2)+'\n')
    # One finite GEN-only capsule: exact storeA ABI, all other ports on W/E/N.
    a=next(q for q in rows if 'store_a' in q['module']);W,H=a['planning_outline_um'];pins=[];loads={f:0 for f in 'WEN'}
    capacities={'W':int((H-8.64)/.336)*2,'E':int((H-8.64)/.336)*2,'N':int((W-8.64)/.336)*2}
    for p in a['ports']:
        for bit in range(p['width']):
            name=p['name']+f'[{bit}]'
            if p['name']=='cmd0_Q' and 576<=bit<=895:
                index=bit-576;x=round(W-7.344-(index//2)*.336,6);y=0.;face='S';layer='M4'if index%2 else'M5'
            else:
                face=min(loads,key=lambda f:(loads[f]/capacities[f],f));index=loads[face];loads[face]+=1
                if loads[face]>capacities[face]:raise ValueError('provider pin capacity exceeded')
                v=round(4.32+(index//2)*.336,6);x,y={'W':(0.,v),'E':(W,v),'N':(v,H)}[face];layer='M4'if index%2 else'M5'
            if layer=='M5': x=round(.024+round((x-.024)/.048)*.048,6)
            else: y=round(.024+round((y-.024)/.048)*.048,6)
            pins.append(dict(name=name,direction=p['direction'],face=face,layer=layer,x=x,y=y))
    if len({(p['layer'],p['x'],p['y'])for p in pins})!=len(pins):raise ValueError('duplicate proposed provider pin coordinate')
    macros=[dict(inst=f'm{g}.g_bank[{b}].u_b.g_m11.u_m',master='ot_sram_1r1w_256x256_m2_r2c2',origin_um=[round(17.28+(j%4)*(172.824+8.64),6),round(17.28+(j//4)*(41.064+8.64),6)],outline_um=[172.824,41.064])for j,(g,b)in enumerate((g,b)for g in range(2)for b in range(16))]
    capsule=dict(status='DISABLED_GEN_ONLY_MODEL_AND_RENDER_REVIEW_REQUIRED',provider=a['module'],source=a['source'],outline_um=[W,H],source_abi_sha256=hashlib.sha256(json.dumps(a['ports'],sort_keys=True).encode()).hexdigest(),pin_count=len(pins),pins=pins,macro_candidates=macros,source_model=a['source_model'],clock_ps=833,clock_ports=['store0_clk[0]'],reset_ports=['store0_rst_n[0]'],source_reset_driver='actual ctl u_core_u_rst__rst_n; not a reset alias',explicit_START_ports=[],opaque_command_source='cmd0_Q exact member DFF66973.__native_cut_152; selected ctl command source still UNPLANNED compiler_control',build_dispatched=False,scope='Proposed native ABI floorplan, not a physical provider view; pins/macros must match actual generated source and true native library before GEN/build')
    (out/'storeA_GEN_capsule.json').write_text(json.dumps(capsule,indent=2)+'\n')
    return rows

def export_closures(selected, out):
    tokens={}; current=None
    for line in Path(selected).open():
        match=re.match(r'\s*module\s+(\w+)',line)
        if match:current=match[1];tokens[current]=set()
        elif current:
            first=re.match(r'\s*(\w+)',line)
            if first:tokens[current].add(first[1])
            if re.match(r'\s*endmodule\b',line):current=None
    names=set(tokens);closure={}
    for root in PROVIDERS:
        needed={root};pending=[root]
        while pending:
            for child in tokens[pending.pop()]&names:
                if child not in needed:needed.add(child);pending.append(child)
        closure[root]=needed
    wanted=set().union(*closure.values());texts={};current=None;lines=[]
    for line in Path(selected).open():
        match=re.match(r'\s*module\s+(\w+)',line)
        if match and match[1] in wanted:current=match[1];lines=[]
        if current:
            lines.append(line)
            if re.match(r'\s*endmodule\b',line):texts[current]=''.join(lines);current=None
    rows=[];out=Path(out)
    for root,needed in closure.items():
        path=out/('closure_'+root+'.sv');path.write_text('\n'.join(texts[n]for n in sorted(needed)))
        logic=out/('logic_'+root+'.sv');logic.write_text('\n'.join(texts[n]for n in sorted(needed)if not n.startswith('ot_sram_')))
        macro_abis=[dict(module=n,ports=abi(texts[n]),source_sha256=hashlib.sha256(texts[n].encode()).hexdigest())for n in sorted(needed)if n.startswith('ot_sram_')]
        (out/(root+'_hard_macro_ABIs.json')).write_text(json.dumps(macro_abis,indent=2)+'\n')
        rows.append(dict(top=root,logic_file=logic.name,logic_policy='Exact native memory master definitions excluded only for true same-name native LEF/Liberty binding; no replacement alias',file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),selected_modules=sorted(needed),module_count=len(needed),dependency_policy='Conservative selected-definition lexical closure, including all parameter branches; no substitute or body alias'))
    (out/'closure_manifest.json').write_text(json.dumps(rows,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--selected',required=True);p.add_argument('--out',required=True);a=p.parse_args();extract(a.selected,a.out);export_closures(a.selected,a.out)
if __name__=='__main__':main()
