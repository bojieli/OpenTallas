#!/usr/bin/env python3
"""Explain arc-local dcalc vs graph slew; inventory exact enable distribution."""
import argparse,bisect,gzip,hashlib,json,math,re,shutil
from pathlib import Path
from dsrom_noECC_production_context import cells
from dsrom_noECC_liberty import cell_bodies,block
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_noECC_slew_enable_diagnosis_20261002'
MAP=ROOT/'results/uarch/dsrom_noECC_WAKE_cell_retention_20261002/terminal'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def nums(s):return [float(x) for x in re.findall(r'[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?',s)]
def lookup(cell,related,kind,x,y):
    for m in re.finditer(r'\btiming\s*\(\)',cell):
        b=block(cell,m.start());p=re.search(r'related_pin\s*:\s*"([^"]+)"',b)
        if not p or p[1]!=related:continue
        km=re.search(r'\b'+kind+r'\s*\(',b)
        if not km:continue
        t=block(b,km.start());axes=[nums(re.search(r'index_'+str(i)+r'\s*\((.*?)\);',t,re.S)[1]) for i in (1,2)]
        values=nums(re.search(r'values\s*\((.*?)\);',t,re.S)[1]);a,c=axes
        if len(values)!=len(a)*len(c):raise ValueError('Nonrectangular source table')
        i=max(0,min(len(a)-2,bisect.bisect_right(a,x)-1));j=max(0,min(len(c)-2,bisect.bisect_right(c,y)-1))
        u=(x-a[i])/(a[i+1]-a[i]);v=(y-c[j])/(c[j+1]-c[j])
        z=lambda r,k:values[r*len(c)+k]
        answer=(1-u)*((1-v)*z(i,j)+v*z(i,j+1))+u*((1-v)*z(i+1,j)+v*z(i+1,j+1))
        return dict(value_ps=answer,input_axis_ps=a,load_axis_fF=c,input_bracket_ps=a[i:i+2],load_bracket_fF=c[j:j+2],extrapolation=not(a[0]<=x<=a[-1] and c[0]<=y<=c[-1]))
    raise ValueError('Source arc absent')
def pin_models(lib):
    out={}
    for master,b in lib.items():
        pins={}
        for m in re.finditer(r'\bpin\s*\(([^)]+)\)',b):
            p=block(b,m.start());direction=re.search(r'direction\s*:\s*(\w+)',p)
            caps=[]
            for name in ('capacitance','rise_capacitance','fall_capacitance'):
                z=re.search(r'\b'+name+r'\s*:\s*([\d.]+)',p)
                if z:caps.append(float(z[1]))
            maxcap=re.search(r'max_capacitance\s*:\s*([\d.]+)',p)
            pins[m[1].strip(' "')]=dict(direction=direction[1] if direction else '',mean_cap_fF=caps[0] if caps else 0,max_cap_fF=max(caps,default=0),driver_max_load_fF=float(maxcap[1]) if maxcap else None)
        out[master]=pins
    return out
def inventory(case,libs):
    path=MAP/case/'retained_mapped.v.gz';cs=cells(gzip.decompress(path.read_bytes()).decode());models={c:pin_models(v) for c,v in libs.items()}
    ports={c['name']:{p:n.strip() for p,n in re.findall(r'\.(\w+)\(([^()]*)\)',c['ports'])} for c in cs}
    controls={}
    for c in cs:
        p=ports[c['name']]
        if c['master'].startswith('NAND2') and '.g_pp.rd' in p.get('A',''):
            controls.setdefault(p['B'],[]).append(c)
    if len(controls)!=2 or any(len(v)!=544 for v in controls.values()):raise ValueError('Expected exact two PP bank enables, each544 active data bits')
    output=[]
    for net in sorted(controls):
        drivers=[c for c in cs if any(n==net and models['ss'].get(c['master'],{}).get(p,{}).get('direction')=='output' for p,n in ports[c['name']].items())]
        if len(drivers)!=1 or drivers[0]['master']!='NOR2xp33_ASAP7_75t_R':raise ValueError('Enable driver source differs')
        driver=drivers[0];sinks=[]
        for c in cs:
            for p,n in ports[c['name']].items():
                if n==net and models['ss'].get(c['master'],{}).get(p,{}).get('direction')=='input':
                    sinks.append(dict(cell=c['name'],master=c['master'],pin=p,
                        SS_mean_cap_fF=models['ss'][c['master']][p]['mean_cap_fF'],
                        worst_SS_FF_pin_cap_fF=max(models[k][c['master']][p]['max_cap_fF'] for k in ('ss','ff'))))
        if len(sinks)!=1088:raise ValueError('Missing source capture mux sink')
        worst=sum(x['worst_SS_FF_pin_cap_fF'] for x in sinks)
        # This is only the leaf floor of Maxwell's positive 80ps / 11.52fF
        # BUF4 context: half the cap is reserved for real wire, never zero.
        leaf_floor=math.ceil(worst/5.76)
        limit=models['ss'][driver['master']]['Y']['driver_max_load_fF']
        output.append(dict(net=net,driver=driver,driver_inputs=ports[driver['name']],sink_count=len(sinks),
            SS_mean_pin_cap_fF=sum(x['SS_mean_cap_fF'] for x in sinks),worst_SS_FF_pin_cap_fF=worst,
            driver_source_max_cap_fF=limit,source_cap_overload_ratio=sum(x['SS_mean_cap_fF'] for x in sinks)/limit,
            sinks=sinks,finite_leaf_floor=dict(master='BUFx4_ASAP7_75t_R',pin_budget_fF=5.76,positive_wire_budget_fF=5.76,
                leaf_cells_lowerbound=leaf_floor,leaf_cell_area_um2=leaf_floor*.10206,
                balanced_parents_relays_clock_reset_PG_and_wire_NOT_included=True,no_complete_tree_fit_or_deadline_claim=True)))
    return dict(full_retained_netlist_sha256=sha(path),controls=output)
def control_paths(text):
    paths=[]
    for part in text.split('Startpoint: ')[1:]:
        end=re.search(r'Endpoint: (\S+)',part)
        rows=[]
        for line in part.splitlines():
            m=re.search(r'^\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+[v^] (\S+)/(QN|Y) \((\w+)\)',line)
            if m:rows.append(dict(cell=m[5],pin=m[6],master=m[7],load_fF=float(m[1]),slew_ps=float(m[2]),delay_ps=float(m[3]),arrival_ps=float(m[4])))
        if len(rows)!=3:raise ValueError('Expected full source FF->NOR enable->capture mux path')
        arrival=float(re.search(r'([\d.]+)\s+data arrival time',part)[1])
        setup=-float(re.search(r'([-\d.]+)\s+[-\d.]+\s+library setup time',part)[1])
        slack=float(re.search(r'([-\d.]+)\s+slack',part)[1])
        paths.append(dict(startpoint=part.split()[0],endpoint=end[1],source_FF_enable_mux_rows=rows,arrival_ps=arrival,setup_ps=setup,slack_ps=slack,ideal_clock=True,zero_wire_RC=True,overloaded_extrapolation_NOT_context_closure=True))
    if len(paths)!=4:raise ValueError('Expected all four requested control endpoints')
    return paths
def build(work):
    r=json.loads((work/'record.json').read_text());text=(work/'probe.log').read_text()
    if r['returncode'] or re.search(r'^Error:',text,re.M):raise ValueError('Failed diagnostic retained; cannot price')
    probe=(work/'probe.tcl').read_text()
    if re.search(r'\b(set_driving_cell|set_input_transition|set_annotated_slew|set_delay_calculator)\b',probe):raise ValueError('Annotated/tuned probe not the retained diagnostic')
    current=ROOT/'results/uarch/dsrom_noECC_capture_intrinsic_20261002/terminal_r4'
    unit_sources=[]
    for p in sorted(current.glob('*.lib.gz')):
        s=gzip.decompress(p.read_bytes()).decode()
        if not re.search(r'time_unit\s*:\s*"1ps"',s) or not re.search(r'capacitive_load_unit\s*\(1,\s*ff\)',s):raise ValueError('Different source units')
        if not re.search(r'slew_derate_from_library\s*:\s*1\s*;',s):raise ValueError('Different slew derate')
        for name,value in [('slew_lower_threshold_pct_rise',10),('slew_lower_threshold_pct_fall',10),('slew_upper_threshold_pct_rise',90),('slew_upper_threshold_pct_fall',90),('input_threshold_pct_rise',50),('input_threshold_pct_fall',50),('output_threshold_pct_rise',50),('output_threshold_pct_fall',50)]:
            if not re.search(name+r'\s*:\s*'+str(value)+r'\s*;',s):raise ValueError('Different threshold convention')
        unit_sources.append(dict(source=str(p.relative_to(ROOT)),sha256=sha(p)))
    libs={c:cell_bodies(c) for c in ('ss','ff')}
    data=lookup(libs['ss']['NAND2xp33_ASAP7_75t_R'],'A','rise_transition',35.869339,.385207)
    enable=lookup(libs['ss']['NAND2xp33_ASAP7_75t_R'],'B','rise_transition',11526.486328,.385207)
    if abs(data['value_ps']-32.284248)>.005 or abs(enable['value_ps']-1826.792236)>.005:raise ValueError('Independent source interpolation does not reproduce report')
    schema=ROOT/'results/uarch/dsrom_noECC_capture_intrinsic_20261002/inputs/parent_endpoint_sources'
    pair=(schema/'ot_v41_pair_w17w10_rne_wake_prepare.sv').read_text();field=(schema/'ot_v41_field_w17w10.sv').read_text()
    for name in ('FIX_SECOND_ROW_INDEX','WAKE_REG','GRADUAL_RNE'):
        if not re.search(r'parameter integer '+name+r'\s*=\s*0',pair) or name in field:raise ValueError('Re-audit changed caller')
    return dict(schema='opentallas.dsrom.capture-enable-slew-cause.v1',candidate='DS4096-TP4-S58-PAR2-NP2048',
        measurement=r,probe_errors=[],unit_identity=dict(time='1ps',capacitance='1fF',macro_and_stdcell_thresholds_pct=[10,50,90],slew_derate=1,checked_sources=unit_sources),
        no_set_driving_cell_or_slew_annotation=True,no_delay_calculator_or_Liberty_tuning=True,
        source_interpolation=dict(data_arc_A=data,enable_arc_B=enable),
        cause='Graph STA merges worst output slew from ALL incoming arcs. report_dcalc A is data-only; B is the overloaded bank-enable arc and reproduces the graph slew. No unit/grid inconsistency.',
        OpenSTA_source_semantics='GraphDelayCalc::annotateDelaySlew updates graph driver slew when the incoming gate_slew is worse; reportDelayCalc evaluates the selected edge using that edge input slew.',
        raw_control_to_capture_one_cycle_slack_ps=[float(x) for x in re.findall(r'([-\d.]+)\s+slack',text)],
        complete_enabled_control_paths=control_paths(text),
        control_setup_edges=1,macro_data_setup_edges=2,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,period_ps=2500/3,
        cases={k:inventory(k,libs) for k in ('q','bfcolumn')},
        predecessor_diagnostic_superseded='59bb single-A-arc vs graph observation was incomplete; retain it unchanged. No STA tool bug or physical reticle impossibility inferred.',
        mandatory_implementation='Finite local capture-enable distribution with priced parent/relay buffers and actual strip/corridor routes; preserve source equations, clock edges, valid/bank alignment and retirement. Standard physical fanout repair, not optional arithmetic/performance lever.',
        parent_cfg_schema=dict(source_sha256=sha(schema/'ot_v41_pair_w17w10_rne_wake_prepare.sv'),NSEG=8,CW=25,selected_PHW=10,AW=15,logical_DEPTH=25600,cfg_a_bits=5,cfg_d_bits=48,cfg_v_bits=1,
            c_v='resettable source c_v<=ld_run; no generic nonreset DFF claim',c_a='unconditional source c_a<=ld_k;5 nonreset FF outputs',c_d='48 nonreset held FF outputs; updates only ld_run, preserving source final word OR with cfg_np at ld_k=16',
            cfg_word_final_modification='cmr(ld_a) | {42\'d0, ld_np, 3\'d0} ONLY when ld_k==2*NSEG',
            accepted_go='go && act; act clears on cfg_go and sets on class-valid config writes; no optimistic last-word readiness substitution',
            physical_cfg_provider='Source cmr is generic cm array or DPI. This schema is NOT actual hard cfg ROM read/capture/visible-ACK implementation.',
            nominal_clip_driver_not_source_proof=True),
        parent_selected_passthrough=dict(FIX_SECOND_ROW_INDEX=1,WAKE_REG=1,GRADUAL_RNE=1,source_defaults_remain0=True,
            missing_current_field_passthrough=True,required_join='One source-owned opt-in field/spine->prepared pair->literal element caller with all three passed; map actual cfg register/GO-act endpoints with full live ports. Do not edit original defaults or infer producer drivers from test constants.'),
        PnR_admitted=False,no_engine_RTL_modified=True,no_new_pipeline_cycle_selected=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);a=p.parse_args()
    x=build(a.work);OUT.mkdir(parents=True,exist_ok=True);(OUT/'model.json').write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
    d=OUT/'terminal';d.mkdir(exist_ok=True)
    for name in ('record.json','probe.tcl'):shutil.copyfile(a.work/name,d/name)
    (d/'probe.log.gz').write_bytes(gzip.compress((a.work/'probe.log').read_bytes(),mtime=0))
    print(json.dumps({k:x[k] for k in ('cause','raw_control_to_capture_one_cycle_slack_ps','PnR_admitted')},indent=2))
