#!/usr/bin/env python3
"""Read-only actual mapped capture/ICG capacity audit; never admits physical work."""
import argparse,collections,hashlib,json,math,re
from pathlib import Path

def block(text, pattern):
    m=re.search(pattern,text);assert m,pattern
    start=text.index('{',m.start());depth=1;i=start+1
    while depth:
        depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[m.start():i]

def row_pack(items, width_sites):
    capacity=width_sites//2 # Same 50% local density, no free-space borrowing.
    rows=[]
    for item in sorted(items,reverse=True):
        if item>capacity:return None
        for i,used in enumerate(rows):
            if used+item<=capacity:rows[i]+=item;break
        else:rows.append(item)
    return len(rows)

def audit(netlist,lef,seq_lib,macro_lef):
    macro_lib=macro_lef.with_name(macro_lef.stem+'_ss.lib')
    raw=netlist.read_bytes();assert hashlib.sha256(raw).hexdigest()=='d6b8f7848db0fdfb1f1142deaa298154c4a6366447ee5d1906df8055ed4ba2ea'
    text=raw.decode();cells={};drivers={};clocks=collections.defaultdict(list)
    for typ,name,body in re.findall(r'^\s+(\w+)\s+(\\?\S+)\s+\((.*?)\n\s*\);',text,re.M|re.S):
        p={k:x.strip() for k,x in re.findall(r'\.(\w+)\(([^)]+)\)',body)};cells[name]=(typ,p)
        for k in ('Y','Z','Q','QN'):
            if k in p:drivers[p[k]]=name
        if typ.startswith('DFF'):clocks[p['CLK']].append(name)
    geometry={};blocks={};ls=lef.read_text()
    for name,body in re.findall(r'MACRO (\S+)\n(.*?)END \1',ls,re.S):
        m=re.search(r'SIZE ([\d.]+) BY ([\d.]+)',body)
        if m:geometry[name]=tuple(float(v) for v in m.groups());blocks[name]='MACRO '+name+'\n'+body+'END '+name
    port_edges={};port_y={}
    for name,body in re.findall(r'  PIN (\S+)\n(.*?)  END \1',macro_lef.read_text(),re.S):
        m=re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',body)
        if m and name.startswith('rd_out'):
            bit=int(re.search(r'\[(\d+)\]',name).group(1))
            port_edges[bit]='west' if float(m[1])==0 else 'east'
            port_y[bit]=round((float(m[2])+float(m[4]))*500)
    groups=collections.defaultdict(lambda:dict(bundles=[],bundle_names=[],aux=set(),names=set(),bits=[]))
    for name,(typ,p) in cells.items():
        m=re.fullmatch(r'(\\g_mac\[\d+\]\.g_pp)\.cap([01])\[(\d+)\]\$_DFFE_PP_',name)
        if not m:continue
        gate=drivers[p['D']];gt,gp=cells[gate]
        assert gt=='AO21x1_ASAP7_75t_R'
        rd=[v for v in gp.values() if re.fullmatch(r'\\g_mac\[\d+\]\.g_pp\.rd[01]\[\d+\]',v)]
        assert len(rd)==1
        bit=int(re.search(r'\[(\d+)\]$',rd[0]).group(1));edge=port_edges[bit]
        macro=m[1]+'.u_rom'+m[2];g=groups[(macro,edge)]
        feedback=[drivers[v] for k,v in gp.items() if k not in ('Y','Z') and v in drivers and cells[drivers[v]][0]=='NOR2x1_ASAP7_75t_R']
        assert len(feedback)==1 and cells[name][1]['QN'] in cells[feedback[0]][1].values()
        bundle=[name,gate,feedback[0]]
        sites=sum(round(geometry[cells[n][0]][0]/.054) for n in bundle)
        g['bundles'].append(sites);g['bundle_names'].append(bundle);g['bits'].append(bit);g['names'].update(bundle)
        for k,v in gp.items():
            if k in ('Y','Z') or v not in drivers:continue
            d=drivers[v]
            if d not in bundle:g['aux'].add(d)
    results=[];selected=set();total_unique=set();certificates=[]
    for (macro,edge),g in sorted(groups.items()):
        aux=[round(geometry[cells[n][0]][0]/.054) for n in g['aux']]
        items=g['bundles']+aux;names=g['names']|g['aux'];total_unique.update(names)
        selected.update(cells[n][0] for n in names)
        mirrored=macro.endswith('rom1')
        origin=74250 if mirrored else 6480
        centers=[origin+(62910-port_y[b] if mirrored else port_y[b]) for b in g['bits']]
        band_rows=(max(centers)-2160)//270-(min(centers)-2160)//270+1
        width=120
        while row_pack(items,width)>band_rows:width+=2
        physical_edge=('east' if edge=='west' else 'west') if 'g_mac[1]' in macro else edge
        # Read-only constructive bins with actual mapped names and real LEF widths.
        bundles=[(sum(round(geometry[cells[n][0]][0]/.054) for n in b),b) for b in g['bundle_names']]
        bundles += [(round(geometry[cells[n][0]][0]/.054),[n]) for n in sorted(g['aux'])]
        bins=[]
        for w,names_in_bundle in sorted(bundles,key=lambda b:(-b[0],b[1])):
            for idx,entry in enumerate(bins):
                if entry['used']+w<=width//2:break
            else:idx=len(bins);bins.append(dict(used=0,cells=[]))
            entry=bins[idx]
            for n in names_in_bundle:
                cw=round(geometry[cells[n][0]][0]/.054)
                assert abs(geometry[cells[n][0]][0]-cw*.054)<1e-9 and geometry[cells[n][0]][1]==.27
                entry['cells'].append(dict(name=n,type=cells[n][0],site_start=entry['used'],site_width=cw))
                entry['used']+=cw
        assert len(bins)<=band_rows and all(b['used']<=width//2 for b in bins)
        certificates.append(dict(macro=macro,lef_edge=edge,physical_edge=physical_edge,width_sites=width,
            first_global_site_row=(min(centers)-2160)//270,available_rows=band_rows,rows=bins,
            scope='Relative constructive site bins only. Aux control names can recur across edge reservations; not an executable placement. Obstacles, cell-pin access and clocks remain unqualified.'))
        results.append(dict(macro=macro,edge=edge,physical_edge=physical_edge,capture_bits=len(g['bundles']),bundle_sites=sorted(set(g['bundles'])),
            auxiliary_cell_types=dict(collections.Counter(cells[n][0] for n in g['aux'])),
            actual_capture_pin_band_rows=band_rows,actual_capture_pin_y_nm=[min(centers),max(centers)],
            unique_local_cell_count=len(names),cell_area_um2=math.fsum(math.prod(geometry[cells[n][0]]) for n in names),
            corridor_120sites_rows=row_pack(items,120),corridor_120sites_pin_band_fits=row_pack(items,120)<=band_rows,
            conservative_bundle_packing_min_width_sites_in_actual_pin_band=width,
            conservative_bundle_packing_min_width_um_in_actual_pin_band=width*.054,
            scope='Constructive 50% row-bin budget only; no legal placement, pins, PG, CTS or routing proof. Bundle cells may require more spacing.'))
    lib=seq_lib.read_text();clock_caps={};libblocks={}
    assert re.search(r'capacitive_load_unit\s*\(1,\s*ff\)',lib)
    macro_clk=block(macro_lib.read_text(),r'pin\s*\(clk\)\s*\{')
    macro_cap=float(re.search(r'\bcapacitance\s*:\s*([\d.]+)',macro_clk)[1])
    def clockcap(typ):
        if typ not in clock_caps:
            b=block(lib,r'cell\s*\('+re.escape(typ)+r'\)\s*\{');libblocks[typ]=b
            pin=block(b,r'pin\s*\(CLK\)\s*\{');clock_caps[typ]=float(re.search(r'\bcapacitance\s*:\s*([\d.]+)',pin)[1])
        return clock_caps[typ]
    gates=[]
    for n,(typ,p) in cells.items():
        if typ!='ICGx1_ASAP7_75t_R':continue
        sinks=clocks[p['GCLK']];hist=collections.Counter(cells[s][0] for s in sinks)
        gates.append(dict(name=n,gclk=p['GCLK'],flop_clock_sinks=len(sinks),flop_types=dict(hist),
            summed_flop_CLK_capacitance_ff=sum(count*clockcap(t) for t,count in hist.items()),
            macro_clock_sinks=[cn for cn,(ct,cp) in cells.items() if ct=='ot_rom_4096x274_m8' and cp['clk']==p['GCLK']],
            scope='Pre-CTS flop endpoint capacitance only; excludes wire/buffers. Macro endpoint capacitance separately priced. No slew/timing/power qualification.'))
    selected.update(['ICGx1_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R'])
    ig=block(lib,r'cell\s*\(ICGx1_ASAP7_75t_R\)\s*\{');libblocks['ICGx1_ASAP7_75t_R']=ig
    out=block(ig,r'pin\s*\(GCLK\)\s*\{')
    mx=re.search(r'max_capacitance\s*:\s*([\d.]+)',out)
    for g in gates:
        g['macro_CLK_capacitance_ff']=len(g['macro_clock_sinks'])*macro_cap
        g['total_endpoint_CLK_capacitance_ff']=g['summed_flop_CLK_capacitance_ff']+g['macro_CLK_capacitance_ff']
        g['unbuffered_endpoint_load_exceeds_ICG_max_capacitance']=g['total_endpoint_CLK_capacitance_ff']>float(mx[1])
    return dict(schema='opentallas.w10.capture-localfit.v1',verdict='CAPTURE_PIN_BAND_OVERFLOW_PHYSICAL_HOLD',physical_admission=False,
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [netlist,lef,seq_lib,macro_lef,macro_lib]},
        density=.5,macro_side_rows=233,all_signal_pin_band_rows_upper_bound=52,existing_capture_corridor_width_sites=120,
        capture_flops=sum(r['capture_bits'] for r in results),edge_budgets=results,row_bin_certificates=certificates,
        unique_capture_cone_cell_area_um2=math.fsum(math.prod(geometry[cells[n][0]]) for n in total_unique),
        note='Local cells already included in fullmap62705.9um2; never add this area again. Shared controls assigned per-edge conservatively; global union deduplicated.',
        icg_gates=gates,macro_CLK_capacitance_ff=macro_cap,
        physical_admission_excluded_hosts=['155.103.253.39'],
        conditional_capture_corridor=dict(width_um=10.368,left_macro_x_um=26.352,right_macro_x_um=851.256,
            scope='Site-bin construction only, no LEF/placement change or extra cell area; root allport and actual routing/CTS pending.'),icg_GCLK_max_capacitance_ff=float(mx[1]) if mx else None,
        flop_clock_capacitance_ff=clock_caps,
        unresolved=['Actual local routing/track and macro all-port escape/PG master review','Shared-control global fanout and clock tree buffer site reserve','Constructive geometric legalization and timing with selected real cells','SS/FF full context and actual power/IR'],
        jobs_launched=0),{n:blocks[n] for n in sorted(selected)},libblocks

if __name__=='__main__':
    a=argparse.ArgumentParser()
    for n in ['netlist','lef','seq-lib','macro-lef','output']:a.add_argument('--'+n,type=Path,required=True)
    p=a.parse_args();r,lefs,libs=audit(p.netlist,p.lef,p.seq_lib,p.macro_lef)
    p.output.parent.mkdir(parents=True,exist_ok=True);p.output.write_text(json.dumps(r,indent=2)+'\n')
    (p.output.parent/'selected_cell_lef.txt').write_text('\n\n'.join(lefs.values())+'\n')
    (p.output.parent/'selected_cell_SS_liberty.txt').write_text('\n\n'.join(libs.values())+'\n')
