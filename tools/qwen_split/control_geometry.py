#!/usr/bin/env python3
"""Source-bound control alternatives. Opt-in analysis; never changes production homes.

Full-face cuts are conservative pin-demand screens, not routed channel admission.
Relay counts are per-branch 500um lower bounds, never allocator results.
"""
import argparse, collections, copy, hashlib, json, math, re
from pathlib import Path
from incident_pin_audit import audit

GROUP = ('seq_su','tt_ctlm','xs_tap','res_train_issue','up4_sel_station')
VM = {'su_vm_va_q','vrd','vrq','svq_v','vwr','coll_cmd_free'}
SU = {'su','sd','acc','su_va_re','su_va_addr','su_va_q','su_vm_va_re','su_vm_va_addr'}

def face_counts(model):
    i=next(i for i in model['insts'] if i['n']=='seq_su'); c=collections.Counter()
    for p in model['masters'][i['m']]['pins']:
        r=p['rect'];x=(r[0]+r[2])/2;y=(r[1]+r[3])/2
        if i['o'] in ('MY','R180'):x=i['w']-x
        if i['o'] in ('MX','R180'):y=i['h']-y
        f='W' if x<.3 else 'E' if x>i['w']-.3 else 'S' if y<.3 else 'N' if y>i['h']-.3 else 'INTERIOR'
        c[f]+=1
    # Only M7 is credited vertically: source contract omits M9 pitch.
    adj=model['routing_capacity_model']['regional_layer_adjustment']['hub']
    tr=model['routing_capacity_model']['track_geometry_um']
    caph=sum(math.floor(i['h']/tr[l][1]) for l in ('M6','M8'))*(1-adj)
    capv=math.floor(i['w']/tr['M7'][1])*(1-adj)
    return {f:dict(pins=n,capacity_tracks=caph if f in ('W','E') else capv,
                   utilization=n/(caph if f in ('W','E') else capv),limit=.6,
                   layers=['M6','M8'] if f in ('W','E') else ['M7'],
                   scope='Full-face pin-demand screen; detailed access, channel cuts and competing traffic OPEN') for f,n in c.items()}

def repin(model,homes):
    """Requested fresh seq master: SU east, VM south, store controls west.

    Keeps source identities and all clock entries. This requires a real successor
    body/pin build; external geometry cannot qualify its internal timing.
    """
    ii={i['n']:i for i in model['insts']};seq=ii['seq_su'];su=ii['sp_su64_sfu'];pins=model['masters'][seq['m']]['pins']
    maps={n:{p['name']:p for p in model['masters'][ii[n]['m']]['pins']}for n in ('seq_su','sp_su64_sfu')}
    def lookup(n,p,k):
        q=maps[n].get(f'{p}[{k}]')
        if q is None:
            j=model['port_join'][ii[n]['m']][p];q=maps[n][f'{j[0]}[{j[1][k]}]']
        return q
    targets={}
    for b in model['buses']:
        se=[p for n,p in b['e'] if n=='seq_su'];su_e=[p for n,p in b['e'] if n=='sp_su64_sfu']
        if len(se)!=1 or len(su_e)!=1 or se[0] not in SU:continue
        for k in range(b['n']):
            dst=lookup('seq_su',se[0],k);src=lookup('sp_su64_sfu',su_e[0],k);r=src['rect']
            targets[dst['name']]=su['y']+(r[1]+r[3])/2-homes['seq_su']['y']
    # Stable nearest-track monotone projection at .048um pin pitch.
    ordered=sorted(targets,key=lambda n:(targets[n],n));step=.048;off=.012
    yy=[]
    for n in ordered:
        y=off+round((targets[n]-off)/step)*step
        yy.append(max(y,yy[-1]+step if yy else off))
    for j in range(len(yy)-1,-1,-1):yy[j]=min(yy[j],seq['h']-.012 if j==len(yy)-1 else yy[j+1]-step)
    if yy[0]<.012-1e-7:raise ValueError('SU face does not fit')
    ym=dict(zip(ordered,yy));old={p['name']:copy.deepcopy(p) for p in pins}
    south=[p for p in pins if p['name'].split('[')[0] in VM or p['rect'][3]<.3]
    south.sort(key=lambda p:p['name']);sw=.096*(len(south)-1);start=(seq['w']-sw)/2
    for j,p in enumerate(south):
        # Local x inverted by MY; all centers on M5 preferred x track.
        x=.012+round((start+j*.096-.012)/.048)*.048
        p.update(layer='M5',rect=[round(x-.012,6),0.,round(x+.012,6),.192])
    west=[p for p in pins if p['name'].split('[')[0].startswith(('cbc','cbr'))]
    for j,p in enumerate(west):
        y=.012+round(((seq['h']-len(west)*.096)/2+j*.096-.012)/.048)*.048
        p.update(layer='M4',rect=[seq['w']-.192,round(y-.012,6),seq['w'],round(y+.012,6)])
    for p in pins:
        if p['name'] in ym:
            y=ym[p['name']];p.update(layer='M4',rect=[0.,round(y-.012,6),.192,round(y+.012,6)])
    return [dict(name=p['name'],before=old[p['name']],requested=p) for p in pins if p!=old[p['name']]]

def validate_fresh_seq(before,after):
    """Reject lost identities, moved clock/reset entries and illegal requested pins."""
    old={p['name']:p for p in before['pins']};new={p['name']:p for p in after['pins']}
    if len(new)!=len(after['pins']) or set(old)!=set(new):raise ValueError('pin identities changed')
    seen=set()
    for n,p in new.items():
        if p==old[n]:continue
        if n.split('[')[0] in ('ck','ck_sched','rsi'):raise ValueError('clock/reset moved')
        x0,y0,x1,y1=p['rect']
        if x0< -1e-7 or y0< -1e-7 or x1>after['w']+1e-7 or y1>after['h']+1e-7:raise ValueError('pin outside outline')
        axis=1 if p['layer']=='M4' else 0 if p['layer']=='M5' else None
        if axis is None:raise ValueError('unsupported requested layer')
        center=((x0+x1)/2,(y0+y1)/2)[axis]
        if abs((center-.012)/.048-round((center-.012)/.048))>1e-5:raise ValueError('off track')
        key=(p['layer'],tuple(p['rect']))
        if key in seen:raise ValueError('duplicate requested pin shape')
        seen.add(key)
    return dict(identities=len(new),changed=len(seen),source_clock_reset_entries_unchanged=True,requested_track_bounds_unique=True)

def evaluate(model,homes):
    r=audit(model,homes)
    r['face_pin_demand']=face_counts(model)
    for z in r['links']:
        z['branch_relay_depth_lower_bound_at_500um']=max(0,math.ceil(z['max_pin_L1_um']/500)-1) if z['max_pin_L1_um'] is not None else None
    r['qualification']=False
    r['relay_static_cost']='OPEN: lower bounds do not include obstacles, pair reach, equal ages, physical relay sites or static-program operation counts. Real allocator required.'
    return r

def figure(path,model,rows):
    # Same scale/crop for every panel; local complete actual rectangles shown.
    x0,y0,x1,y1=13900,4100,19450,11450;scale=.075;w=(x1-x0)*scale;h=(y1-y0)*scale
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{3*(w+20)}" height="{h+90}">','<rect width="100%" height="100%" fill="white"/>']
    for col,(name,homes) in enumerate(rows):
        ox=10+col*(w+20);oy=48
        out += [f'<text x="{ox}" y="20" font-size="12">{name}</text>',f'<rect x="{ox}" y="{oy}" width="{w}" height="{h}" fill="#fafafa" stroke="#999"/>']
        for q in model['insts']:
            i=dict(q);i.update(homes.get(i['n'],{}))
            if i['x']<x0 or i['y']<y0 or i['x']+i['w']>x1 or i['y']+i['h']>y1:continue
            color='#91c9d4' if i['n'] in ('sp_su64_sfu','sp_vector_memory') else '#b49acc' if i['n'] in ('seq_su','tt_ctlm') else '#e4c385'
            x=ox+(i['x']-x0)*scale;y=oy+(y1-i['y']-i['h'])*scale
            out.append(f'<rect x="{x}" y="{y}" width="{i["w"]*scale}" height="{i["h"]*scale}" fill="{color}" stroke="#333" stroke-width=".35"><title>{i["n"]} {i["x"]},{i["y"]} {i["o"]}</title></rect>')
            if i['w']>400:out.append(f'<text x="{x+2}" y="{y+12}" font-size="10">{i["n"]}</text>')
        out.append(f'<text x="{ox}" y="{h+72}" font-size="10">Common scale. Source rectangles; route/clock gates OPEN.</text>')
    path.write_text('\n'.join(out)+'\n</svg>\n')

def typed_grant(base,requested,homes,out):
    from source_pin_plan import rtl_ports
    root=Path(__file__).resolve().parents[2];rtl='rtl/qwen_split/qfd_seq_su_static.sv'
    ports=rtl_ports(root/rtl,'qfd_seq_su_static');master=copy.deepcopy(requested)
    aliases={};present=set()
    for p in master['pins']:
        old=p['name'];m=re.fullmatch(r'(.+)__(\d+)_(\d+)\[(\d+)\]',old)
        if m:stem=m[1];bit=int(m[2])+int(m[4])
        else:
            m=re.fullmatch(r'(.+)\[(\d+)\]',old)
            if not m:raise ValueError('unnumbered generated pin '+old)
            stem,bit=m[1],int(m[2])
        if stem not in ports or bit>=ports[stem][0]:raise ValueError('physical alias not an actual source pin '+old)
        new=stem if ports[stem][0]==1 else f'{stem}[{bit}]'
        if new in present:raise ValueError('duplicate logical source pin '+new)
        present.add(new);aliases[old]=new;p['name']=new
    expected={p if w==1 else f'{p}[{k}]'for p,(w,d)in ports.items()for k in range(w)}
    missing=sorted(expected-present)
    if set(missing)!={f'kvd[{k}]'for k in range(44)}:raise ValueError('unexpected native graph interface omission')
    for k in range(44):
        y=round(.012+round((8+k*.096-.012)/.048)*.048,6)
        master['pins'].append(dict(name=f'kvd[{k}]',layer='M4',rect=[master['w']-.192,y-.012,master['w'],y+.012]))
    if {p['name']for p in master['pins']}!=expected:raise ValueError('typed interface mismatch')
    manifest=(root/'tools/qwen_split/static_seq_vm.f').read_text().splitlines()[:17]
    hashes={p:hashlib.sha256((root/p).read_bytes()).hexdigest()for p in manifest if (root/p).exists()}
    missing_sources=[p for p in manifest if not (root/p).exists()]
    record=dict(schema='opentallas.qwen.seq.source_pin_candidate.v1',status='PROPOSED_NEW_MASTER_NOT_PHYSICALLY_QUALIFIED',
      source_top='qfd_seq_su_static',source=rtl,source_sha256=hashlib.sha256((root/rtl).read_bytes()).hexdigest(),
      source_ports={p:dict(width=w,direction=d)for p,(w,d)in ports.items()},source_bits=len(expected),physical_pin_count=len(master['pins']),
      defines=['OT_QFD_SEQ_SU_NOWROM'],source_manifest_sha256=hashes,unmaterialized_source_paths=missing_sources,
      slot='seq_su',outline=[master['w'],master['h']],home=homes['seq_su'],related_home=homes['tt_ctlm'],
      native_geometry_source_commit=base['source_commit'],native_geometry_source_pins=11551,
      geometry_alias_to_actual_source_pin=aliases,missing_native_graph_output_bits=missing,
      requested_added_external_pin_bits=44,added_data_cycles=0,added_data_flops=0,
      clock_entry_pins_unchanged=['ck','ck_sched'],clock_timing='OPEN: source-derived ownership and measured per-entry phi-R required',
      candidate_master=master,old_closed_view_reuse_allowed=False,
      admission='REFUSED until exact source-complete component bench + mutant, synthesis clock/memory census, fresh body/pin layout and native clock proof; then TT/FF/DRC0 and whole graph relay/static cost',
      qualification=False)
    (out/'typed_seq_grant.json').write_text(json.dumps(record,indent=1)+'\n')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('model',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    base=json.loads(a.model.read_text());old={i['n']:i for i in base['insts']};rows=[];results=[]
    common={n:{k:old[n][k] for k in ('x','y','o')}for n in GROUP}
    baseline=evaluate(base,common)
    (a.out/'baseline_all_incident_audit.json').write_text(json.dumps(baseline,indent=1)+'\n')
    for name,y,change in [('existing_pins_contact_7800',7800,False),('existing_pins_margin_7850',7850,False),('split_faces_fresh_master_7900',7900,True)]:
        homes=copy.deepcopy(common);homes['seq_su'].update(x=14671.176,y=y,o='MY');homes['tt_ctlm']['y']=round(y+518.376+43.2,6)
        m=copy.deepcopy(base)
        for i in m['insts']:i.update(homes.get(i['n'],{}))
        requested=repin(m,homes) if change else []
        validation=validate_fresh_seq(base['masters'][old['seq_su']['m']],m['masters'][old['seq_su']['m']])
        r=evaluate(m,homes);r['name']=name;r['requested_pin_changes']=len(requested);r['pin_integrity']=validation
        (a.out/f'{name}_homes.json').write_text(json.dumps(homes,indent=2)+'\n')
        if requested:typed_grant(base,m['masters'][old['seq_su']['m']],homes,a.out)
        if requested:(a.out/'requested_seq_pin_delta.json').write_text(json.dumps(requested,indent=1)+'\n');(a.out/'requested_seq_master.json').write_text(json.dumps(m['masters'][old['seq_su']['m']],indent=1)+'\n')
        (a.out/f'{name}_audit.json').write_text(json.dumps(r,indent=1)+'\n');results.append(r);rows.append((name,homes))
    (a.out/'summary.json').write_text(json.dumps(dict(input_sha256=hashlib.sha256(a.model.read_bytes()).hexdigest(),source_commit=base['source_commit'],source_sha256=base['source_sha256'],baseline_data_bit_branch_L1_um=baseline['all_data_bit_branch_L1_um'],candidates=[{k:v for k,v in r.items()if k not in ('links','missing_pins')}for r in results],qualification=False,required=['Fresh typed seq pin/body grant before any physical gate','Full current b2 native graph and all bus cut screens','Real relay allocator and static compiler cost for all incident buses','Actual phi-R clock delivery, TT setup/FF hold/DRC0']),indent=2)+'\n')
    figure(a.out/'control_candidates.svg',base,rows)
    for r in results:print(r['name'],r['overlaps'],r['complete_numeric_pins'],r['all_data_bit_branch_L1_um'],{f:round(z['utilization'],4)for f,z in r['face_pin_demand'].items()})
if __name__=='__main__':main()
