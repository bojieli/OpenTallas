#!/usr/bin/env python3
"""Source-matched local control replicas and finite capture-enable distribution.

Only an analytical/source proposal: emits descriptors, never RTL/netlists/STA.
"""
import gzip,json,math,re,hashlib,fnmatch
from pathlib import Path
from collections import Counter
from dsrom_noECC_liberty import cell_bodies,block
from dsrom_noECC_production_context import cells,lef_masters
from dsrom_noECC_slew_enable_diagnosis import pin_models,lookup,nums
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_noECC_enable_distribution_20261002'
PRIOR=ROOT/'results/uarch/dsrom_noECC_WAKE_cell_retention_20261002/terminal'
CTX=ROOT/'results/uarch/dsrom_noECC_production_context_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def overlap(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def bound(body,kinds,x,y,minimum=False,related=None,timing_type=None):
    values=[]
    for m in re.finditer(r'\btiming\s*\(\)',body):
        b=block(body,m.start())
        if related and not re.search(r'related_pin\s*:\s*"'+related+r'"',b):continue
        if timing_type and not re.search(r'timing_type\s*:\s*'+timing_type+r'\s*;',b):continue
        for kind in kinds:
            km=re.search(r'\b'+kind+r'\s*\(',b)
            if not km:continue
            t=block(b,km.start());a=nums(re.search(r'index_1\s*\((.*?)\);',t,re.S)[1]);c=nums(re.search(r'index_2\s*\((.*?)\);',t,re.S)[1]);v=nums(re.search(r'values\s*\((.*?)\);',t,re.S)[1])
            if not(a[0]<=x<=a[-1] and c[0]<=y<=c[-1]):raise ValueError('Table-domain violation '+kind)
            # Restrict source grid to the actual finite envelope; bilinear extrema
            # occur at its grid boundaries. All arcs/edges, never a nominal arc.
            xs=sorted(set([z for z in a if z<=x]+[x]));ys=sorted(set([z for z in c if z<=y]+[y]))
            for u in xs:
                for w in ys:
                    i=max(0,min(len(a)-2,next((j-1 for j,z in enumerate(a) if z>u),len(a)-2)))
                    j=max(0,min(len(c)-2,next((j-1 for j,z in enumerate(c) if z>w),len(c)-2)))
                    f=(u-a[i])/(a[i+1]-a[i]);g=(w-c[j])/(c[j+1]-c[j])
                    z=lambda r,k:v[r*len(c)+k]
                    values.append((1-f)*((1-g)*z(i,j)+g*z(i,j+1))+f*((1-g)*z(i+1,j)+g*z(i+1,j+1)))
    if not values:raise ValueError('No source tables '+str(kinds))
    return (min if minimum else max)(values)
def measure(lib,master,x,cap):
    b=lib[master]
    return dict(master=master,input_slew_envelope_ps=x,load_envelope_fF=cap,delay_ps=bound(b,('cell_rise','cell_fall'),x,cap,related='CLK' if master.startswith('DFF') else None),slew_ps=bound(b,('rise_transition','fall_transition'),x,cap,related='CLK' if master.startswith('DFF') else None))
def domain(s):
    for x in (80,160,320):
        if s<=x:return x
    raise ValueError('No bounded source slew domain: '+str(s))
def ports(cell):return {p:n.strip() for p,n in re.findall(r'\.(\w+)\(([^()]*)\)',cell['ports'])}
def trace(case):
    path=PRIOR/case/'retained_mapped.v.gz';allcells=cells(gzip.decompress(path.read_bytes()).decode());cs={c['name']:c for c in allcells};ps={n:ports(c) for n,c in cs.items()};fan={}
    for n,p in ps.items():
        for k,v in p.items():fan.setdefault(v,[]).append((n,k))
    groups={};enables={}
    for n,c in cs.items():
        p=ps[n];m=re.search(r'g_mac\[(\d)\]\.g_pp\.rd([01])\s*\[(\d+)\]',p.get('A',''))
        if not m or not c['master'].startswith('NAND2'):continue
        mb,bk,bit=map(int,m.groups());nxt=[n1 for n1,k in fan[p['Y']] if k=='B' and cs[n1]['master'].startswith('OAI21')]
        if len(nxt)!=1:raise ValueError('Source hold mux absent')
        mux=nxt[0];ffs=[n1 for n1,k in fan[ps[mux]['Y']] if k=='D' and cs[n1]['master'].startswith('DFF')]
        if len(ffs)!=1:raise ValueError('Source capture FF absent')
        if ps[mux]['A2']!=p['B']:raise ValueError('Different bank-enable mux equation')
        groups.setdefault((mb,bk),[]).append(dict(bit=bit,NAND=n,OAI=mux,FF=ffs[0]))
        enables.setdefault(p['B'],[]).append((mb,bk))
    if len(groups)!=4 or any(len(v)!=272 for v in groups.values()):raise ValueError('Must retain all1088 capture bits')
    return cs,ps,{k:sorted(v,key=lambda x:x['bit']) for k,v in groups.items()},path

def placed(name,master,x,y,lef,role):
    w,h=lef[master]['size_DBU'];orientation='MX' if (y//270)%2==0 else 'R0'
    return dict(instance=name,master=master,bbox_DBU=[x,y,x+w,y+h],orientation=orientation,role=role,pin_OBS_template=master)
def rc(path_length_um,cap_fF,resistance):return path_length_um*resistance*cap_fF

def build():
    inp=OUT/'inputs';receipts=json.loads((inp/'receipts.json').read_text())
    for r in receipts:
        if sha(inp/r['copy'])!=r['sha256']:raise ValueError('Frozen source changed')
    lef=lef_masters(gzip.decompress((inp/'cells.lef.gz').read_bytes()).decode())
    libs={c:cell_bodies(c) for c in ('ss','ff')};pm={c:pin_models(l) for c,l in libs.items()}
    policy=(CTX/'inputs/platform.mk').read_text()
    patterns=[]
    for m in re.finditer(r'^export DONT_USE_CELLS\s*(?:\+=|=)\s*(.*)$',policy,re.M):patterns+=m[1].split()
    semantics={}
    for corner,lib in libs.items():
        semantics[corner]={}
        for master in ('DFFASRHQNx1_ASAP7_75t_R','DFFHQNx1_ASAP7_75t_R'):
            body=lib[master];ff=block(body,re.search(r'\bff\s*\(',body).start())
            qn=block(body,re.search(r'\bpin\s*\(\s*QN\s*\)',body).start())
            if not all(re.search(p,ff) for p in (r'next_state\s*:\s*"!D"',r'clocked_on\s*:\s*"CLK"')) or not re.search(r'function\s*:\s*"IQN"',qn):raise ValueError('Source FF semantics changed')
            if master.startswith('DFFASR') and not all(re.search(p,ff) for p in (r'preset\s*:\s*"!RESETN"',r'clear\s*:\s*"!SETN"')):raise ValueError('Source reset semantics changed')
            semantics[corner][master]=dict(cell_body_sha256=hashlib.sha256(body.encode()).hexdigest(),literal_ff=ff,literal_QN_pin=qn)
    cuts=json.loads((CTX/'local_cuts.json').read_text());ctx=json.loads((CTX/'model.json').read_text())
    geometries=json.loads((PRIOR/'context_terminal.json').read_text());old=json.loads((ROOT/'results/uarch/dsrom_noECC_slew_enable_diagnosis_20261002/model.json').read_text())
    source_rc=(inp/'setRC.tcl').read_text();layer_rc={n:(float(r),float(c)) for n,r,c in re.findall(r'set_layer_rc -layer (M\d) -resistance ([\d.E+-]+) -capacitance ([\d.E+-]+)',source_rc)}
    # One construction, not a design/count sweep. Scalar state clones sample
    # EXACT same D, CLK, RESETN, SETN as original; no added cycle or FF stage.
    cases={};used_masters=set();macro_lef=(inp/'macro.lef').read_text()
    for case in ('q','bfcolumn'):
        cs,ps,groups,path=trace(case);geometry=geometries['cases'][case]['physical_geometry_contract'];regions={}
        for r in geometry['capture_regions']:
            m=re.search(r'g_mac\[(\d)\].g_pp.u_rom([01])',r['instance']);regions[tuple(map(int,m.groups()))]=r['bbox_DBU']
        controls=old['cases'][case]['controls'];driver0=controls[0]['driver_inputs'];driver1=controls[1]['driver_inputs']
        # Derive physical state owners from mapped output driver, not row names.
        ctrl_nets=set(p for c in controls for k,p in c['driver_inputs'].items() if k in ('A','B'))
        ff_candidates=[(n,c) for n,c in cs.items() if c['master'].startswith('DFF') and ps[n].get('QN') in ctrl_nets]
        if len(ff_candidates)!=2:raise ValueError('Expected source valid and bank FF')
        state={('valid' if c['master'].startswith('DFFASR') else 'bank'):(n,c) for n,c in ff_candidates}
        inv=[(n,c) for n,c in cs.items() if c['master'].startswith('INV') and ps[n].get('Y') in ctrl_nets]
        if len(inv)!=1:raise ValueError('Source bank polarity inverter absent')
        placements=[];nets=[];strips=[];source_copies=[];timing=[]
        for (mb,bk),bits in groups.items():
            region=regions[mb,bk];x0,y0,x1,y1=region;rootrow=(round((y0+y1)/2/270))*270
            banned={rootrow,rootrow-270,rootrow-540}|{s['bbox_DBU'][1] for s in cuts['cases'][case]['source_clock_cell_slots'] if overlap(s['bbox_DBU'],region)}
            rows=[y for y in range(y0,y1-269,270) if y not in banned and y>=y0+1350]
            # Local valid/bank FFs, polarity inverter and decode occupy source
            # strip first three spare rows. Captures avoid this reservation.
            local=[]
            for index,role in enumerate(('valid','bank')):
                n,c=state[role];inst=f'enable_s{mb}b{bk}_{role}'
                placements.append(placed(inst,c['master'],x0,rootrow-270-index*270,lef,'control_state_replica'))
                local.append(inst);source_copies.append(dict(instance=inst,original_instance=n,master=c['master'],original_connections=ps[n],new_QN='local_'+inst,unchanged_D_CLK_RESETN_SETN=True))
            original_enable=ps[bits[0]['NAND']]['B']
            original_decode=[c for c in controls if c['driver_inputs']['Y']==original_enable]
            if len(original_decode)!=1:raise ValueError('Missing original bank decode')
            d=original_decode[0]['driver_inputs']
            if d['A']!=ps[state['valid'][0]]['QN']:raise ValueError('Source valid polarity changed')
            invert=d['B']==ps[inv[0][0]]['Y']
            if not invert and d['B']!=ps[state['bank'][0]]['QN']:raise ValueError('Source bank polarity changed')
            if invert:placements.append(placed(f'enable_s{mb}b{bk}_polarity',inv[0][1]['master'],x0+1458,rootrow-540,lef,'source_bank_polarity_replica'))
            placements.append(placed(f'enable_s{mb}b{bk}_SETN1','TIEHIx1_ASAP7_75t_R',x0+1998,rootrow-270,lef,'source_bound_SETN1_tie'))
            nor=(original_decode[0]['driver']['name'] if mb==1 else f'enable_s{mb}b{bk}_decode')
            normaster=('NOR2xp33_ASAP7_75t_R' if mb==1 else 'NOR2x1_ASAP7_75t_R')
            placements.append(placed(nor,normaster,x0+1458,rootrow-270,lef,'source_relocated_existing' if mb==1 else 'same_source_decode_equation'))
            root=f'enable_s{mb}b{bk}_root';placements.append(placed(root,'BUFx24_ASAP7_75t_R',x0+1728,rootrow,lef,'enable_tree_root'))
            leaves=[]
            for j,bit in enumerate(bits):
                row=rows[(j//2)*(len(rows)-1)//135];bx=x0+(j%2)*1566
                for master,key,offset in [('NAND2xp33_ASAP7_75t_R','NAND',0),('OAI21xp33_ASAP7_75t_R','OAI',216),('DFFHQNx1_ASAP7_75t_R','FF',486)]:
                    placements.append(placed(bit[key],master,bx+offset,row,lef,'existing_capture_'+key))
                if j%8==0:
                    leaf=f'enable_s{mb}b{bk}_leaf{j//8}';placements.append(placed(leaf,'BUFx4_ASAP7_75t_R',x0+3132,row,lef,'enable_tree_leaf'));leaves.append(leaf)
                    subset=bits[j:j+8];nets.append(dict(net=leaf+'_Y',driver=leaf+'/Y',source_enable_bank=bk,sinks=[p for b in subset for p in (b['NAND']+'/B',b['OAI']+'/A2')],maximum_L1_to_sink_um=6.5,total_wire_length_upper_um=24,layer='M3',positive_wire_cap_fF=24*layer_rc['M3'][1]))
            if len(leaves)!=34:raise ValueError('One leaf per8 actual bits')
            allowed=[]
            for z in range(x0+3780,x1-108,48):
                z=12+48*math.ceil((z-12)/48)
                guard=[z-36,y0,z+36,y1]
                obstacles=cuts['cases'][case]['expanded_source_PDN_rectangles']+cuts['cases'][case]['source_via_enclosures_near_cut']
                if not any(r['layer']=='M5' and overlap(guard,r['bbox_DBU']) for r in obstacles):allowed.append(z)
            if not allowed:raise ValueError('No legal source PG-excluded M5 trunk track')
            trunk=allowed[0];trunk_wire_um=(y1-y0)/1000+len(leaves)*1.2
            nets.append(dict(net=root+'_Y',driver=root+'/Y',sinks=[n+'/A' for n in leaves],trunk_x_DBU=trunk,track_offset_DBU=12,track_pitch_DBU=48,spacing_guard_DBU=[trunk-36,y0,trunk+36,y1],source_M5_PG_and_nearcut_via_excluded=True,route_bbox_DBU=[trunk-12,y0,trunk+12,y1],layer='M5',wire_length_upper_um=trunk_wire_um,wire_cap_fF=(y1-y0)/1000*layer_rc['M5'][1]+len(leaves)*1.2*layer_rc['M3'][1],maximum_L1_to_sink_um=(y1-y0)/2000+1.2))
            # Bound source SS and FF independently, including the real weak
            # muxes; FF hold is a separate min-path condition, never SS transfer.
            tt={}
            for corner in ('ss','ff'):
                lib=libs[corner];p=pm[corner]
                valcap=p[normaster]['A']['max_cap_fF']+1.0*layer_rc['M3'][1]
                bkcap=max(p[normaster]['B']['max_cap_fF'],p[inv[0][1]['master']]['A']['max_cap_fF'])+1.0*layer_rc['M3'][1]
                f1=measure(lib,state['valid'][1]['master'],320,max(.72,valcap));f2=measure(lib,state['bank'][1]['master'],320,max(.72,bkcap));ffdelay=max(f1['delay_ps'],f2['delay_ps'])
                inverter=measure(lib,inv[0][1]['master'],domain(max(f1['slew_ps'],f2['slew_ps'])),max(.72,valcap))
                norcap=p['BUFx24_ASAP7_75t_R']['A']['max_cap_fF']+1.0*layer_rc['M3'][1]
                dec=measure(lib,normaster,domain(max(f1['slew_ps'],f2['slew_ps'],inverter['slew_ps'])),max(2.88,norcap))
                trunkcap=34*p['BUFx4_ASAP7_75t_R']['A']['max_cap_fF']+nets[-1]['wire_cap_fF']
                rootm=measure(lib,'BUFx24_ASAP7_75t_R',domain(dec['slew_ps']),max(.72,trunkcap))
                wire_delay=rc(nets[-1]['maximum_L1_to_sink_um'],trunkcap,max(layer_rc['M5'][0],layer_rc['M3'][0]))
                leafcap=8*(p['NAND2xp33_ASAP7_75t_R']['B']['max_cap_fF']+p['OAI21xp33_ASAP7_75t_R']['A2']['max_cap_fF'])+24*layer_rc['M3'][1]
                leaf=measure(lib,'BUFx4_ASAP7_75t_R',domain(rootm['slew_ps']+math.log(10)*wire_delay),leafcap)
                leafwire=rc(6.5,leafcap,layer_rc['M3'][0]);muxdomain=domain(leaf['slew_ps']+math.log(10)*leafwire)
                ndcap=p['OAI21xp33_ASAP7_75t_R']['B']['max_cap_fF']+.3*layer_rc['M3'][1];nd=measure(lib,'NAND2xp33_ASAP7_75t_R',muxdomain,max(.72,ndcap))
                outcap=p['DFFHQNx1_ASAP7_75t_R']['D']['max_cap_fF']+.3*layer_rc['M3'][1];oi=measure(lib,'OAI21xp33_ASAP7_75t_R',domain(max(nd['slew_ps'],leaf['slew_ps']+math.log(10)*leafwire)),max(.72,outcap))
                setup=bound(lib['DFFHQNx1_ASAP7_75t_R'],('rise_constraint','fall_constraint'),domain(oi['slew_ps']+2),320,timing_type='setup_rising')
                # Explicit small local wires: four connections, each0.3um.
                local_delay=4*1.0*layer_rc['M3'][0]*max(2.88,norcap)
                subtotal=ffdelay+(inverter['delay_ps'] if invert else 0)+dec['delay_ps']+rootm['delay_ps']+wire_delay+leaf['delay_ps']+leafwire+nd['delay_ps']+oi['delay_ps']+local_delay+setup
                tt[corner]=dict(source_FF=[f1,f2],source_bank_inverter=inverter,source_NOR=dec,tree_root=rootm,tree_leaf=leaf,hold_mux_NAND=nd,hold_mux_OAI=oi,capture_setup_upper_ps=setup,wire_root_delay_upper_ps=wire_delay,wire_leaf_delay_upper_ps=leafwire,local_wire_delay_upper_ps=local_delay,complete_one_edge_subtotal_ps=subtotal,SS_remaining_ps=2500/3-60-25-subtotal if corner=='ss' else None,RC_slew_envelope='source gate slew + ln(10)*R_path*C_total; conservative passive RC construction envelope, not extracted STA',no_table_extrapolation=True)
            timing.append(dict(MB=mb,bank=bk,SS_FF=tt));strips.append(dict(MB=mb,bank=bk,region_DBU=region,source_bits=272,actual_capture_FF=272,source_clock='leaf_clk[0]',tree_leaf_count=34,tree_root_count=1,local_same_edge_state_replicas=2))
        # Literal placements and source templates; no area-only containment.
        collisions=[]
        order=sorted(placements,key=lambda p:p['bbox_DBU'][1])
        for i,a in enumerate(order):
            for b in order[i+1:]:
                if b['bbox_DBU'][1]>=a['bbox_DBU'][3]:break
                if overlap(a['bbox_DBU'],b['bbox_DBU']):collisions.append([a['instance'],b['instance']])
        slot_collisions=[[p['instance'],s['actual_instance']] for p in placements for s in cuts['cases'][case]['source_clock_cell_slots'] if overlap(p['bbox_DBU'],s['bbox_DBU'])]
        macro_bodies=[r['bbox_DBU'] for r in geometry['macro_instances']];macro_collisions=[p['instance'] for p in placements if any(overlap(p['bbox_DBU'],b) for b in macro_bodies)]
        counts=Counter(p['master'] for p in placements if not p['role'].startswith('existing_capture') and p['role']!='source_relocated_existing')
        if any(fnmatch.fnmatch(master,pat) for master in counts for pat in patterns):raise ValueError('NEW control cell violates actual platform policy')
        area=sum(n*lef[m]['area_um2'] for m,n in counts.items());removed=0.0 # Reuse actual2 original decode instances, no removal credit.
        used_masters.update(p['master'] for p in placements)
        # Cloned D input consumers are exact original D ports, no synthetic
        # registered constants. Their finite network must be joined to source
        # predecessor FF/INV in the selected context before any implementation.
        sources=[]
        for role,(n,c) in state.items():
            data=ps[n]['D'];drivers=[dict(instance=k,master=v['master'],connections=ps[k]) for k,v in cs.items() if ps[k].get('Y')==data or ps[k].get('QN')==data]
            if len(drivers)!=1:raise ValueError('Ambiguous clone D producer')
            predecessors=[dict(instance=k,master=v['master'],connections=ps[k]) for k,v in cs.items() if ps[k].get('QN')==drivers[0]['connections'].get('A')]
            if len(predecessors)!=1 or not predecessors[0]['master'].startswith('DFF'):raise ValueError('Actual source D predecessor FF absent')
            if predecessors[0]['connections']['CLK']!=ps[n]['CLK']:raise ValueError('Replica D source clock changed')
            sources.append(dict(actual_predecessor_FF=predecessors[0],role=role,original_FF=n,original_D=data,actual_mapped_driver=drivers[0],added_D_load_SS_fF=4*pm['ss'][c['master']]['D']['max_cap_fF'],added_D_load_FF_fF=4*pm['ff'][c['master']]['D']['max_cap_fF'],proposed_buffer='BUFx24_ASAP7_75t_R',minimum_network_wire_um=281.34,minimum_length_basis='Rectilinear tree spanning four actual replica D homes:138.24um column separation+2*71.55um bank separation; M8 route contract',minimum_wire_cap_fF=281.34*layer_rc['M8'][1],maximum_total_network_wire_um=400,maximum_source_to_replica_L1_um=200,layer='M8',wire_cap_fF=400*layer_rc['M8'][1],source_predecessor_clock_and_all_other_driver_sinks_must_be_bound=True))
        for source in sources:
            source['two_hold_buffers_per_D_network']='Two BUFx4_ASAP7_75t_R; source-axis support requires explicitly reserved18.432um and5.4um M3 wires, not fictitious load or below-grid extrapolation'
            source['hold_wire_construction']=dict(layer='M3',first_length_um=18.432,second_length_um=5.4,first_meander_passes=5,first_horizontal_pass_um=3.6,first_vertical_pitch_um=.108,source_track_pitch_um=.036,minimum_wire_length_is_a_required_physical_constraint=True,cell_and_wire_minimum_load_gated=True)
            dd={}
            for corner in ('ss','ff'):
                lib=libs[corner];pin=pm[corner];driver=source['actual_mapped_driver'];pre=source['actual_predecessor_FF'];
                def fan_cap(net):
                    return sum(pin[c['master']][port]['max_cap_fF'] for name,c in cs.items() for port,n in ps[name].items() if n==net and c['master'] in pin and pin[c['master']].get(port,{}).get('direction')=='input')
                pre_cap=fan_cap(pre['connections']['QN'])+layer_rc['M3'][1]
                f=measure(lib,pre['master'],320,max(.72,pre_cap))
                invcap=fan_cap(source['original_D'])+pin['BUFx4_ASAP7_75t_R']['A']['max_cap_fF']+layer_rc['M3'][1]
                d=measure(lib,driver['master'],domain(f['slew_ps']),max(.72,invcap))
                h1cap=pin['BUFx4_ASAP7_75t_R']['A']['max_cap_fF']+18.432*layer_rc['M3'][1]
                h1=measure(lib,'BUFx4_ASAP7_75t_R',domain(d['slew_ps']),h1cap)
                h1wire=rc(18.432,h1cap,layer_rc['M3'][0])
                h2cap=pin['BUFx24_ASAP7_75t_R']['A']['max_cap_fF']+5.4*layer_rc['M3'][1]
                h2=measure(lib,'BUFx4_ASAP7_75t_R',domain(h1['slew_ps']+math.log(10)*h1wire),h2cap)
                h2wire=rc(5.4,h2cap,layer_rc['M3'][0])
                cap=source['added_D_load_'+corner.upper()+'_fF']+source['wire_cap_fF']
                rb=measure(lib,'BUFx24_ASAP7_75t_R',domain(h2['slew_ps']+math.log(10)*h2wire),cap)
                wire=rc(200,cap,layer_rc['M8'][0]);sinkdomain=domain(rb['slew_ps']+math.log(10)*wire)
                sinkmaster=state[source['role']][1]['master']
                setup=bound(lib[sinkmaster],('rise_constraint','fall_constraint'),sinkdomain,320,timing_type='setup_rising')
                total=sum(t['delay_ps'] for t in (f,d,h1,h2,rb))+h1wire+h2wire+wire+setup
                hold=bound(lib[sinkmaster],('rise_constraint','fall_constraint'),320,320,timing_type='hold_rising')
                mindelay=sum(bound(lib[t['master']],('cell_rise','cell_fall'),t['input_slew_envelope_ps'],t['load_envelope_fF'],minimum=True,related='CLK' if t['master'].startswith('DFF') else None) for t in (f,d,h1,h2,rb))
                dd[corner]=dict(actual_predecessor_FF=f,actual_source_inverter=d,hold_buffers=[h1,h2],hold_wire_delay_upper_ps=h1wire+h2wire,root_buffer=rb,wire_delay_upper_ps=wire,setup_upper_ps=setup,SS_complete_margin_ps=2500/3-60-25-total if corner=='ss' else None,minimum_cell_delay_ps=mindelay,FF_hold_upper_ps=hold,FF_hold_margin_ps=mindelay-hold-25-25 if corner=='ff' else None,all_existing_predecessor_and_inverter_pin_sinks_included=True,predecessor_other_wire_cap_ENVELOPE_fF=layer_rc['M3'][1],predecessor_physical_other_fanout_routes_need_context_check=True)
            source['SS_FF_complete_D_path']=dd
            source['HB1_cell_floor_diagnostic_not_minimum_certificate']=dd['ff']['FF_hold_margin_ps']-bound(libs['ff']['BUFx4_ASAP7_75t_R'],('cell_rise','cell_fall'),dd['ff']['hold_buffers'][0]['input_slew_envelope_ps'],dd['ff']['hold_buffers'][0]['load_envelope_fF'],minimum=True)
        # D networks add2 BUF24 not included in the local strip placement cost.
        extra_D_area=2*lef['BUFx24_ASAP7_75t_R']['area_um2']+4*lef['BUFx4_ASAP7_75t_R']['area_um2']
        boundary=json.loads((ROOT/'results/uarch/dsrom_noECC_capture_intrinsic_20261002/boundary_loads.json').read_text())['cases'][case]['ports']['rst_n']['actual_pin_loads']
        union={}
        for corner in ('ss','ff'):
            profiles=cuts['cases'][case]['leaf_pin_loads_full_source'][corner]
            l0=[(n,p) for n,p in profiles.items() if '[0]' in str(p['source_ICG'])]
            if len(l0)!=1:raise ValueError('Unique real leaf0 source clock required')
            net,profile=l0[0];delta=4*sum(pm[corner][v[1]['master']]['CLK']['max_cap_fF'] for v in state.values())
            rst=4*pm[corner][state['valid'][1]['master']]['RESETN']['max_cap_fF']
            union[corner]=dict(existing_leaf0_net_id=net,existing_source_ICG=profile['source_ICG'],existing_leaf0_sinks=profile['sinks'],new_leaf0_sinks=profile['sinks']+8,existing_leaf0_pin_cap_fF=profile['pin_cap_fF'],extra_clock_pin_cap_fF=delta,composed_leaf0_pin_cap_fF=profile['pin_cap_fF']+delta,existing_reset_pin_cap_fF=boundary[corner][0]['load_fF'],extra_reset_pin_cap_fF=rst,composed_reset_pin_cap_fF=boundary[corner][0]['load_fF']+rst,SETN_constant1_extra_pin_count=4,constant_tie_provider='four actual TIEHIx1_ASAP7_75t_R/H, oneper strip; source platform policy, Liberty H constant1 and LEF slot priced',constant_tie_provider_required=True)
        # Translate every source cell PG terminal, not a percentage reserve.
        power_fail=[];power_count=0
        for item in placements:
            x0,y0,_,_=item['bbox_DBU'];h=lef[item['master']]['size_DBU'][1]
            for pin in lef[item['master']]['pins']:
                if pin['use'] not in ('POWER','GROUND'):continue
                for r in pin['rectangles']:
                    a,b,c,d=r['bbox_DBU'];yy=(b+d)/2
                    if item['orientation']=='MX':yy=h-yy
                    global_y=y0+yy;power_count+=1
                    shadows=cuts['cases'][case]['expanded_source_PDN_rectangles']
                    if not any(s['layer']=='M2' and s.get('net')==pin['name'] and s['bbox_DBU'][1]<=global_y<=s['bbox_DBU'][3] and s['bbox_DBU'][0]<=x0+(a+c)/2<=s['bbox_DBU'][2] for s in shadows):power_fail.append(dict(instance=item['instance'],pin=pin['name'],center_y_DBU=global_y))
        pin_manifest=[dict(instance=p['instance'],master=p['master'],origin_DBU=p['bbox_DBU'][:2],orientation=p['orientation'],CLK=('leaf_clk[0]' if p['role']=='control_state_replica' else None),RESETN=('rst_n' if p['role']=='control_state_replica' and p['master'].startswith('DFFASR') else None),template=p['master']) for p in placements if p['role']=='control_state_replica']
        margin=min(t['SS_FF']['ss']['SS_remaining_ps'] for t in timing)
        cases[case]=dict(full_retained_map_sha256=sha(path),clock_reset_full_source_union=union,clone_translated_CLK_RESET_pin_descriptors=pin_manifest,source_PG_rail_projection_terminal_count=power_count,source_PG_rail_projection_failures=power_fail,strips=strips,source_state_copies=source_copies,placements=placements,enable_nets=nets,complete_enabled_timing=timing,minimum_SS_remaining_ps=margin,retained_unbuffered_screen='b8 q SS top4 -8448.497070ps preserved',added_cell_counts=dict(counts),added_local_cell_area_um2=area,old_source_decode_removal_area_um2=removed,decode_credit_only_after_all_source_sinks_rewired=True,new_D_tree_cell_area_um2=extra_D_area,net_cell_area_delta_um2=area+extra_D_area-removed,conservative_50pct_core_reservation_um2=2*(area+extra_D_area-removed),macro_and_existing_capture_FF_area_credit=0,added_physical_FF=8,added_capture_latency_cycles=0,proposed_D_distribution=sources,clone_clock_pin_debit_SS_FF_fF={c:4*sum(pm[c][v[1]['master']]['CLK']['max_cap_fF'] for v in state.values()) for c in ('ss','ff')},clone_reset_pin_debit_SS_FF_fF={c:4*pm[c][state['valid'][1]['master']]['RESETN']['max_cap_fF'] for c in ('ss','ff')},placement_cell_collisions=collisions,placement_source_WAKExICG_collisions=slot_collisions,placement_macro_body_collisions=macro_collisions,source_PG_clock_pin_escape_pending='Resolve root/leaf pin escapes and every VIA enclosure against translated source PG and OBS. Placement rectangle disjointness is insufficient.',local_SS_model_screen='PASS' if margin>=0 else 'FAIL',implementation_admitted=False)
    caller=json.loads((inp/'Maxwell_selected_caller_r5_WIP.json').read_text())
    return dict(schema='opentallas.dsrom.finite-enable-distribution.v1',candidate='DS4096-TP4-S58-PAR2-NP2048',source_FF_semantics=semantics,actual_DONT_USE_patterns=patterns,production_policy_sha256=sha(CTX/'inputs/platform.mk'),production_policy='Original2 NOR2xp33 retained/relocated; additional2 NOR2x1 function-equivalent and allowed under platform default dontuse. No new xp cells.',method='One local same-edge scalar-control replica per actual capture strip;34 fanout leaves perstrip.8 additional state FF, no additional sampling stage. Source originals/negative evidence untouched.',opt_in_default=False,engine_RTL_or_netlist_emitted=False,new_STA_or_PnR_executed=False,ROM_ECC=False,macro_width=274,macro_depth=4096,physical_macros_per_pair=4,ordered_arithmetic_unchanged=True,selected_parent_flags=caller['source_configuration']['selected_flags'],selected_parent_configuration=caller['source_configuration']['selected_field_parameters'],selected_parent_snapshot_uncommitted_no_qualification_transfer=False,selected_parent_source_commit=receipts[0]["committed_source_pin"],selected_parent_no_physical_qualification_transfer=True,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,skew_reservation_ps=25,period_ps=2500/3,macro_data_edges=2,control_edges=1,cases=cases,physical_master_templates={m:{k:lef[m][k] for k in ('size_DBU','pins','OBS','site','area_um2')} for m in sorted(used_masters|{'BUFx24_ASAP7_75t_R'})},layer_RC_kohm_fF_per_um=layer_rc,source_receipts=receipts,admission_remaining=['Prescribed D-root/HB2 physical slots and wire minima/maxima must join source predecessor and every retained-driver route, including four SETN1 tie pins; max/min screens are conditional on those exact envelopes','Raw full-source CLK/RESET union delivered; Maxwell must bind actual same-level leaf0 clock endpoints/skew<=25ps and source reset recovery/removal, without duplicating existing8 WAKE','Every local root/leaf pin escape and via array against source PG/OBS; source PG rail projection and M5 trunks are checked, other cell pin escapes and native arrays remain open; existing capture feedback/arithmetic FF hold also needs complete context','Committed b328 selected caller manifest and flags must be consumed by the context frontend; caller source pin does not qualify physical constraints'],G0_physical_build_admitted=False)
if __name__=='__main__':
    out=build();OUT.mkdir(parents=True,exist_ok=True);(OUT/'model.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:dict(SS_margin_ps=v['minimum_SS_remaining_ps'],cell_delta_um2=v['net_cell_area_delta_um2'],collisions=len(v['placement_cell_collisions'])) for k,v in out['cases'].items()},indent=2))
