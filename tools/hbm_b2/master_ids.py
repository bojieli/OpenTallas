#!/usr/bin/env python3
"""Expose replica IDs and share one pin template per functional interface.
Owner 2026-10-25 07:01 permits ID constants at the parent only. Existing data
specializations are kept separate: TKM's terminal tile has a different interface.
This transforms a copied plan, recipes and canonical cut maps as one batch.
"""
from __future__ import annotations
import argparse, collections, copy, hashlib, json, re, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.die_plan.parent_id_straps import validate_parent_id_straps

FAMILIES = {
    'tkm_tile': (r'ot_hgi_coll_tkm_m_tp192__tile\d+', 'tile_tid', 6),
    'sfu_lane': (r'ot_hgi_sfu_core_split3__lane\d+', 'map_lane_j', 4),
}

def split_bit(name):
    m = re.fullmatch(r'(.+)\[(\d+)\]', name)
    return (m[1], int(m[2])) if m else (name, None)

def canonical_map(pins, cut):
    """Resolve only exact cut buses or unambiguous hierarchy prefixes."""
    result = {}
    for pin in pins:
        bus, bit = split_bit(pin['name'])
        matches = [k for k in cut if bus == k or bus.endswith('_' + k)]
        if len(matches) != 1:
            raise ValueError(f'{bus}: cut resolution has {len(matches)} matches')
        mp = cut[matches[0]]
        if len(mp) != 1:
            raise ValueError(f'{bus}: multi-port cut must be split before unification: {mp}')
        canonical, width = next(iter(mp.items()))
        if bit is not None and bit >= width:
            raise ValueError(f'{bus}[{bit}] outside canonical {canonical}[{width}]')
        result[pin['name']] = canonical + (f'[{bit}]' if bit is not None else '')
    if len(set(result.values())) != len(result):
        raise ValueError('canonical map merges distinct pin bits')
    return result

def append_id(pins, bus, width, outline):
    """Add a compact ID bus on N-face M7 tracks beside the clock inputs."""
    out = copy.deepcopy(pins); w, h = outline
    occupied = [p['x'] for p in pins if p['layer']=='M7' and abs(p['y'] - h) < .1]
    sites = []
    # 0.576um is nine M7 tracks. Use a single compact multi-layer pin band.
    for k in range(int(w / .576)):
        x = round(8.032 + .576*k, 6)
        if x < .576 or x > w-.576 or any(abs(x-y) < .48 for y in occupied):
            continue
        sites.append(x)
        if len(sites) == width:
            break
    if len(sites) != width:
        raise ValueError(f'no N-face space for {bus}[{width}]')
    out.extend(dict(name=f'{bus}[{i}]', layer='M7', x=x, y=round(h-.019, 6))
               for i, x in enumerate(sites))
    return out

def transform(plan_dir, canonical_path, recipe_path, out_dir):
    plan_dir, out_dir = Path(plan_dir).resolve(), Path(out_dir).resolve()
    if out_dir.exists():
        raise ValueError('output must be new; failed or active artifacts are never overwritten')
    out_dir.mkdir(parents=True)
    raw = json.loads((plan_dir/'die_plan.json').read_text())
    conn = json.loads((plan_dir/'core_conns.json').read_text())
    canonical = json.loads(Path(canonical_path).read_text())
    recipes = json.loads(Path(recipe_path).read_text())
    selected = collections.defaultdict(list)
    aliases = []; views = []; report = []; sv_common = []; sv_adapters = []; proof_cases = []
    for tn, typ in raw['partition_types'].items():
        for c in typ.get('hard_cores', []):
            for family, (rx, idport, idwidth) in FAMILIES.items():
                if not re.fullmatch(rx, c['module']):
                    continue
                entry = canonical['types'][family]
                matches = [(k,v) for k,v in entry['type_ids'].items()
                           if re.sub(r'__[\d.]+x[\d.]+$', '', k) == c['module']]
                if len(matches) != 1:
                    raise ValueError(f'{c["module"]}: canonical type has {len(matches)} definitions')
                tid, cut = matches[0]
                straps = cut.get('straps', {})
                if set(straps) != {idport}:
                    raise ValueError(f'{tid}: expected only ID strap {idport}, got {straps}')
                value = straps[idport]
                if not re.fullmatch('[01]{'+str(idwidth)+'}', value):
                    raise ValueError(f'{tid}: malformed ID {value}')
                pins = json.loads((plan_dir/c['pins_file']).read_text())
                rename = canonical_map(pins, cut['cut_pins'])
                normalized = [dict(p, name=rename[p['name']]) for p in pins]
                buses = collections.defaultdict(set)
                for name in rename.values():
                    b,i = split_bit(name); buses[b].add(i)
                signature = tuple(sorted((b, tuple(sorted(i for i in ix if i is not None)), None in ix)
                                         for b,ix in buses.items()))
                # Terminal data ties/open ports are a different interface, never generalized
                # as permission to put non-ID constants on the common parent boundary.
                key = (family, tuple(c['outline_um']), signature)
                selected[key].append((tn,c,cut,tid,normalized,rename,int(value,2)))
    for (family, outline, signature), members in selected.items():
        entry = canonical['types'][family]; _, idport, idwidth = FAMILIES[family]
        def keypins(m):
            return json.dumps(sorted(m[4], key=lambda p:p['name']),sort_keys=True,separators=(',',':'))
        common = collections.Counter(keypins(m) for m in members).most_common(1)[0][0]
        representative = next(m for m in members if keypins(m)==common)
        tn, c, cut, tid, normalized, rename, _ = representative
        label = family + ('_terminal' if cut.get('tied_at_parent') or cut.get('open_at_parent') else '')
        module = entry['top'] + ('__terminal_idpin' if label.endswith('_terminal') else '__idpin')
        pinpath = 'cores/' + module + '__master.json'
        masterpins = append_id(normalized, idport, idwidth, outline)
        pth=out_dir/pinpath; pth.parent.mkdir(parents=True,exist_ok=True)
        pth.write_text(json.dumps(masterpins,indent=1)+'\n')
        # Canonical kit wrapper now receives the ID input through a real plan pin.
        newcut = copy.deepcopy(cut)
        newcut['cut_pins'] = {}
        for b,ix,scalar in signature:
            newcut['cut_pins'][b] = {b:1 if scalar else len(ix)}
        newcut['cut_pins'][idport]={idport:idwidth}
        newcut['straps']={}
        newcut['cut_bits'][0]+=idwidth
        newid=module+'__'+str(outline[0])+'x'+str(outline[1])
        newentry=copy.deepcopy(entry);newentry['type_ids']={newid:newcut}
        newfamily=label+'_idpin'
        canonical['types'][newfamily]=newentry
        recipe=copy.deepcopy(recipes[tid]);recipe['functional_type']=newfamily
        recipe['port_map_note']='Common core; parent straps only replica ID; ID is a real face-shell input'
        recipes[newid]=recipe
        port_specs = {n:(d,w) for n,d,w,_ in entry['ports']}
        common_buses = dict(newcut['cut_pins'])
        def declaration(name, direction, width):
            return f"{direction} wire " + (f"[{width-1}:0] " if width>1 else "") + name
        decls = [declaration(b, port_specs[b][0], port_specs[b][1]) for b in common_buses]
        native_connections = []
        inherited_ties = {k.split('=')[0]:k.split('=')[1] for k in cut.get('tied_at_parent',{})}
        for b,(direction,width) in port_specs.items():
            if b in common_buses: native_connections.append(f".{b}({b})")
            elif direction=='output': native_connections.append(f".{b}()")
            elif b in inherited_ties:
                value=inherited_ties[b]
                if not re.fullmatch(r"[0-9]+",value):raise ValueError('unsupported inherited data specialization')
                native_connections.append(f".{b}({width}'d{value})")
            else:raise ValueError(f'new unbound input {b}; only inherited specialization permitted')
        sv_common.append('module '+module+'(\n  '+',\n  '.join(decls)+');\n  '+entry['top']+' u_core(\n    '+',\n    '.join(native_connections)+');\nendmodule\n')
        for oldtn, oldc, oldcut, oldtid, oldpins, oldrename, idvalue in members:
            portmap={}
            for oldname,newname in oldrename.items():
                ob,oi=split_bit(oldname); nb,ni=split_bit(newname)
                if oi!=ni:raise ValueError('bit position changed')
                if ob in portmap and portmap[ob]!=nb:raise ValueError('non-functional bus rename')
                portmap[ob]=nb
            cm=conn.get(oldtn,{}).get(oldc['inst'],{})
            if any(k not in portmap for k in cm):
                raise ValueError(f'{oldtn}.{oldc["inst"]}: core_conns has unknown port')
            conn.setdefault(oldtn,{})[oldc['inst']]={portmap[k]:v for k,v in cm.items()}
            # Dedicated metadata describes the sole new parent tie allowed by owner.
            # No parent data tie, new relay, or numerical behavior is introduced.
            # Emit the actual parent-side adapter. All IDs enter the shared core as
            # wires. The sole constant on that boundary is the owner's replica ID.
            oldbus = {}
            for oldpin in oldrename:
                ob,oi=split_bit(oldpin);nb,_=split_bit(oldrename[oldpin]);oldbus[ob]=port_specs[nb]
            adapter = oldc['module'] + '__master_id_adapter'
            adecl=[declaration(b,*dw) for b,dw in sorted(oldbus.items())]
            acon=[f".{nb}({ob})" for ob,nb in sorted(portmap.items())]
            acon.append(f".{idport}({idwidth}'d{idvalue})")
            sv_adapters.append('module '+adapter+'(\n  '+',\n  '.join(adecl)+');\n  '+module+' u_shared(\n    '+',\n    '.join(acon)+');\nendmodule\n')
            proof_cases.append(dict(adapter=adapter,common=module,top=entry['top'],id_port=idport,
                                    id_value=idvalue,id_width=idwidth,old_buses=oldbus,port_map=portmap,
                                    top_ports=port_specs,inherited_ties=inherited_ties))
            oldc['parent_id_straps']={idport:dict(width=idwidth,value=idvalue)}
            validate_parent_id_straps(oldc, inputs={b:w for b,(d,w) in port_specs.items() if d=='input'})
            def rename_references(obj):
                if isinstance(obj,str):
                    for old,new in portmap.items():
                        obj=re.sub(re.escape(oldc['inst']+'.'+old)+r'(?![A-Za-z0-9_])',oldc['inst']+'.'+new,obj)
                    return obj
                if isinstance(obj,list):return [rename_references(v) for v in obj]
                if isinstance(obj,dict):return {k:rename_references(v) for k,v in obj.items()}
                return obj
            # Station capture/launch endpoints and leaf bus targets use the new
            # canonical port names too; stale names must not bypass reach checks.
            for key in list(raw['partition_types'][oldtn]):
                if key!='hard_cores':
                    raw['partition_types'][oldtn][key]=rename_references(raw['partition_types'][oldtn][key])
            oldc['module']=module;oldc['pins_file']=pinpath
            aliases.append(dict(type=oldtn,inst=oldc['inst'],old_type_id=oldtid,
                                module=module,id_port=idport,id_value=idvalue,pin_bus_rename=portmap))
        instances = [part['name']+'.'+core['inst'] for mtn,core,*_ in members
                     for part in raw['partitions'] if part['type']==mtn]
        views.append(dict(view=module,module=module,outline_um=list(outline),pins_file=pinpath,
                          pins_sha256=hashlib.sha256(pth.read_bytes()).hexdigest(),
                          recipe_keys=[newid],canonical_type=newfamily,replicas=len(members),
                          instances=instances,placed=len(instances)))
        report.append(dict(family=family,module=module,replicas=len(members),old_pin_templates=len(set(keypins(m) for m in members)),
                           new_pin_templates=1,placed=len(instances),id_input_bits=idwidth,pins=len(masterpins),
                           inherited_data_specialization=bool(cut.get('tied_at_parent')),added_data_cycles=0,
                           id_latency='existing face shell input stage; boot-static ID'))
    for name in ('die_plan.json','core_conns.json'):
        obj=raw if name=='die_plan.json' else conn
        (out_dir/name).write_text(json.dumps(obj,indent=1)+'\n')
    # Copy unchanged plan-relative files; newly shared pin files win.
    for p in plan_dir.rglob('*.json'):
        if p.name in {'g0_report.json','g2_report.json'}:continue
        rel=p.relative_to(plan_dir); q=out_dir/rel
        if not q.exists():q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
    (out_dir/'master_id_common.sv').write_text('`default_nettype none\n'+'\n'.join(sv_common)+'`default_nettype wire\n')
    (out_dir/'master_id_parent_adapters.sv').write_text('`default_nettype none\n'+'\n'.join(sv_adapters)+'`default_nettype wire\n')
    (out_dir/'master_id_binding_cases.json').write_text(json.dumps(proof_cases,indent=1)+'\n')
    (out_dir/'master_id_aliases.json').write_text(json.dumps(aliases,indent=1)+'\n')
    (out_dir/'canonical_ports_master_ids.json').write_text(json.dumps(canonical,indent=1,sort_keys=True)+'\n')
    (out_dir/'recipes_master_ids.json').write_text(json.dumps(recipes,indent=1,sort_keys=True)+'\n')
    (out_dir/'views_master_ids.json').write_text(json.dumps(dict(plan=str(out_dir/'die_plan.json'),view_list=views),indent=1)+'\n')
    (out_dir/'master_id_report.json').write_text(json.dumps(dict(families=report,
       distinct_before=sum(len(v) for v in selected.values()),distinct_after=len(selected),
       limitation='Parent binder must consume parent_id_straps; geometry must pass after plan placement/routing rebuild'),indent=1)+'\n')
    return report

def main():
    a=argparse.ArgumentParser();a.add_argument('--plan-dir',required=True);a.add_argument('--canonical',required=True)
    a.add_argument('--recipes',required=True);a.add_argument('--out',required=True);x=a.parse_args()
    print(json.dumps(transform(x.plan_dir,x.canonical,x.recipes,x.out),indent=1))
if __name__=='__main__':main()
