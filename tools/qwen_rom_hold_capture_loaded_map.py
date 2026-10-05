#!/usr/bin/env python3
"""Actual10-ROM/2560capture/80maskFF cone plus existing512bit MEM_PIPE load.
SS/FF mapped pin-load characterization only; ideal wires/clocks, no P&R.
"""
import argparse,hashlib,json,re
from pathlib import Path
from qwen_rom_hold_capture_literal_gate import ROOT,CANDIDATE,candidate_logic,YOSYS
from qwen_rom_hold_capture_gate_prepare import prepare
from qwen_rom_kv_finite_window_gate import guarded_process
from qwen_rom_macro_capture_sta import parse_slack
MODEL='645ae1dd79eed8c20319574e4143b3c0c7b5551d'
MODEL_PATH='results/uarch/qwen_rom_direct_capture_control_20261002/model-r2.json'
BASE=ROOT/'results/uarch/qwen_rom_hold_capture_literal_gate_20261002'
def consumer_endpoints(net):
    bits=set(net['netnames']['consumer_q']['bits'])
    # QN is inverted: follow only the explicit single-input inverter, not
    # arbitrary combinational predecessors, to identify each actual endpoint.
    inv={c['connections']['Y'][0]:c['connections']['A'][0]
         for c in net['cells'].values() if c['type']=='INVx1_ASAP7_75t_R'}
    qbits={inv.get(b,b) for b in bits}
    endpoints=[name+'/D' for name,c in net['cells'].items()
               if c['type']=='DFFHQNx1_ASAP7_75t_R' and c['connections']['QN'][0] in qbits]
    if len(endpoints)!=512 or len(qbits)!=512:
        raise ValueError('Actual512bit endpoint cells missing')
    return endpoints

def block(text,start):
    pos=text.index('{',start);depth=1;i=pos+1
    while depth:
        depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[start:i]


def merge(libraries):
    text=libraries[0].read_text();prefix=text[:re.search(r'\bcell\s*\(',text).start()]
    known={m[2]:block(prefix,m.start()) for m in re.finditer(r'\b(lu_table_template|power_lut_template)\s*\(([^)]+)\)',prefix)}
    cells={};extra=[]
    for path in libraries:
        raw=path.read_text();header=raw[:re.search(r'\bcell\s*\(',raw).start()]
        for m in re.finditer(r'\b(lu_table_template|power_lut_template)\s*\(([^)]+)\)',header):
            definition=block(header,m.start())
            if m[2] not in known:known[m[2]]=definition;extra.append(definition)
            elif re.sub(r'\s+','',known[m[2]])!=re.sub(r'\s+','',definition):raise ValueError('Conflicting timing template '+m[2])
        for m in re.finditer(r'\bcell\s*\(([^)]+)\)',raw):
            name=m[1].strip().strip('"');definition=block(raw,m.start())
            if name in cells and cells[name]!=definition:raise ValueError('Conflicting cell '+name)
            cells[name]=definition
    return prefix+'\n'.join(extra+list(cells.values()))+'\n}\n',cells


def timing_subset(merged,cells,counts):
    """Keep canonical templates/cell bodies; discard only unmapped cells.

    The ABC input remains the full merged library. This STA view avoids
    diagnostics on unused library-only cells without waiving any diagnostics
    on an instantiated cell or changing any timing/pin definition.
    """
    missing=set(counts)-set(cells)-{'ot_rom_4096x266_m8'}
    if missing:raise ValueError('Unbound mapped cells: '+str(sorted(missing)))
    prefix=merged[:re.search(r'\bcell\s*\(',merged).start()]
    return prefix+'\n'.join(cells[name] for name in sorted(counts) if name in cells)+'\n}\n'


def path_loads(output):
    return [dict(fanout=int(m[1]),cap_fF=float(m[2]),slew_ps=float(m[3]),
                 delay_ps=float(m[4]),pin=m[5]) for m in re.finditer(
        r'^\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([-\d.]+)\s+[-\d.]+\s+[\^v]\s+(\S+)',output,re.M)]

def merge_scoped(libraries):
    """Namespace library-local templates; never choose between definitions."""
    prefix=None;templates=[];cells={};renames={}
    for idx,path in enumerate(libraries):
        raw=path.read_text();header=raw[:re.search(r'\bcell\s*\(',raw).start()]
        names=[m[2].strip().strip('"') for m in re.finditer(r'\b(lu_table_template|power_lut_template)\s*\(([^)]+)\)',header)]
        for name in names:
            new='source'+str(idx)+'_'+name
            raw=re.sub(r'\b'+re.escape(name)+r'\b',new,raw);renames[path.name+':'+name]=new
        header=raw[:re.search(r'\bcell\s*\(',raw).start()]
        if prefix is None:prefix=header
        else:
            templates += [block(header,m.start()) for m in re.finditer(r'\b(lu_table_template|power_lut_template)\s*\(([^)]+)\)',header)]
        for m in re.finditer(r'\bcell\s*\(([^)]+)\)',raw):
            name=m[1].strip().strip('"');definition=block(raw,m.start())
            if name in cells:raise ValueError('Duplicate cell in scoped libraries: '+name)
            cells[name]=definition
    return prefix+'\n'.join(templates+list(cells.values()))+'\n}\n',cells,renames


def worst_slack(output):
    if re.search(r'^(?:Warning|Error):',output,re.M) or 'time 1ps' not in output:
        raise ValueError('STA diagnostics/units notqualified')
    values=re.findall(r'([-\d.]+)\s+slack\s+\((MET|VIOLATED)\)',output)
    if not values:raise ValueError('Missing STA path/slack')
    return min(float(v[0]) for v in values)


def loaded_cone():
    raw=(ROOT/CANDIDATE).read_bytes();cone,_=candidate_logic(raw)
    text=cone.decode().replace('qwen_optin_capture_logic','qwen_loaded_capture').replace('ROM_HOLD_DIRECT_CAPTURE=0','ROM_HOLD_DIRECT_CAPTURE=1')
    text=text.replace(' input wire [2*CODE_BANKS*266-1:0] rom_rd,','')
    text=text.replace('output wire [CODE_BANKS-1:0] rom_ce,output wire [11:0] rom_addr);',
        'output wire [CODE_BANKS-1:0] rom_ce,output wire [11:0] rom_addr,output reg [511:0] consumer_q);\n wire [2*CODE_BANKS*266-1:0] rom_rd;')
    source=raw.decode();start=source.index('    generate\n        for (p = 0; p < 2;',source.index('module ot_qwen_rom_tile_hold_capture_candidate'))
    end=source.index('    reg        kvw_ce_q;',start);macros=source[start:end]
    consumer=ROOT/'rtl/hdc/ot_qwen_w12_matvec.sv'
    if 'localparam integer GL = LANES ? G : 1;' not in consumer.read_text() or 'mq_wrom <= wrom_q;' not in consumer.read_text():raise ValueError('Existing consumer stage differs')
    return text.replace('endmodule',macros+'always @(posedge clk) consumer_q <= wrom_q;\nendmodule'),macros


def run(workdir,result,libraries,sta):
    if workdir.exists() or result.exists():raise ValueError('Refusing overwrite')
    terminal=json.loads((BASE/'literal_r1.json').read_text())
    if terminal['status']!='PASS_LITERAL_FORMAL_AND_FOURSTATE':raise ValueError('Literal gate notterminalPASS')
    for path,digest in terminal['source_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise ValueError('Literal source changed: '+path)
    ready=prepare(workdir,MODEL,MODEL_PATH)
    if not ready['RTL_variant_implementation_admitted']:raise ValueError('Model/source price differs')
    cone,macros=loaded_cone();(workdir/'full_loaded_cone.sv').write_text(cone)
    merged,cells,renames=merge_scoped(libraries['ss']);lib=workdir/'mapped_ss.lib';lib.write_text(merged)
    macro={c:ROOT/f'physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8_{c}.lib' for c in ['ss','ff']}
    ys=workdir/'synth.ys';ys.write_text(f'''read_liberty -lib {lib}
read_liberty -lib {macro['ss']}
read_verilog -sv {workdir/'full_loaded_cone.sv'}
hierarchy -check -top qwen_loaded_capture
synth -top qwen_loaded_capture
dfflibmap -liberty {lib}
abc -liberty {lib}
clean
stat -liberty {lib}
rename -enumerate c:*
write_verilog -noattr -noexpr {workdir/'mapped.v'}
write_json {workdir/'mapped.json'}
''')
    # Mark actual80 Q-driving FFcells after proc but BEFORE identical-register
    # merging. Source wirekeep alone didnot preserve these cells in r1.
    proc_ys=workdir/'proc.ys'
    proc_ys.write_text(ys.read_text().split('synth -top')[0]+f"proc\nwrite_json {workdir/'proc.json'}\n")
    prc,pout=guarded_process([YOSYS,'-s',str(proc_ys)],workdir,workdir/'proc.log')
    if prc:raise ValueError('Pre-synthesis process lowering failed')
    pn=json.loads((workdir/'proc.json').read_text())['modules']['qwen_loaded_capture']
    qbits={n['bits'][0] for name,n in pn['netnames'].items() if '.g_direct.g_mask[' in name and name.endswith('.local_sel')}
    selected=[name for name,c in pn['cells'].items() if c['type']=='$adff' and len(c['connections']['Q'])==1 and c['connections']['Q'][0] in qbits]
    if len(qbits)!=80 or len(selected)!=80:raise ValueError('Priced80-register source lowering differs')
    keep=''.join('setattr -set keep 1 c:'+name+'\n' for name in selected)
    ys.write_text(ys.read_text().replace('synth -top qwen_loaded_capture','proc\n'+keep+'synth -top qwen_loaded_capture'))
    rc,output=guarded_process([YOSYS,'-s',str(ys)],workdir,workdir/'synth.log')
    record=dict(schema='opentallas.qwen-rom-hold-capture-loaded-map.v1',status='FAIL_MAPPING',mapping_returncode=rc,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [CANDIDATE,'rtl/hdc/ot_qwen_w12_matvec.sv','tools/qwen_rom_hold_capture_loaded_map.py']},
        synthesis_preservation_Q_cells=selected,scoped_template_renames_SS=renames,
        model_commit=MODEL,model_path=MODEL_PATH,literal_gate_sha256=hashlib.sha256((BASE/'literal_r1.json').read_bytes()).hexdigest(),
        tool_sha256={name:hashlib.sha256(Path(exe).resolve().read_bytes()).hexdigest() for name,exe in [('yosys',YOSYS),('sta',sta)]},
        library_sha256={c:{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in libs} for c,libs in libraries.items()},
        macro_liberty_sha256={c:hashlib.sha256(p.read_bytes()).hexdigest() for c,p in macro.items()},
        macro_instantiation_sha256=hashlib.sha256(macros.encode()).hexdigest(),loaded_cone_sha256=hashlib.sha256(cone.encode()).hexdigest(),
        period_ps=833.333333,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,added_cycles=0,existing_MEM_EXTRA_charged_once=True,
        existing_MEM_PIPE_endpoint_bits=512,endpoint_scope='Existing PART1/G4/W16/INT8 matvec mq_wrom stage loads all retained bank mask/OR paths. Not an added edge.',
        ideal_wire=True,ideal_clock=True,input_transition_ps=20,clock_transition_ps=20,actual_pin_OBS_PG_fit=False,actual_skew_bound=False,physical_build_ready=False,PnR=False,adoption=False)
    if rc==0:
        net=json.loads((workdir/'mapped.json').read_text())['modules']['qwen_loaded_capture'];counts={}
        for cell in net['cells'].values():counts[cell['type']]=counts.get(cell['type'],0)+1
        local=[n for n in net['netnames'] if '.g_direct.g_mask[' in n and n.endswith('.local_sel')]
        local_bits=[net['netnames'][n]['bits'][0] for n in local]
        preserved=len(local)==80 and len(set(local_bits))==80 and counts.get('ot_rom_4096x266_m8')==10 and counts.get('DFFHQNx1_ASAP7_75t_R')==3072 and counts.get('DFFASRHQNx1_ASAP7_75t_R')==86
        area=sum(n*float(re.search(r'\barea\s*:\s*([\d.]+)',cells[t])[1]) for t,n in counts.items() if t in cells)
        record.update(mapped_cell_counts=counts,local_selector_net_names=local,unique_local_selector_bits=len(set(local_bits)),replicas_preserved=preserved,
          mapped_logic_area_um2_including_existing_endpoint=area,mapped_netlist_sha256=hashlib.sha256((workdir/'mapped.v').read_bytes()).hexdigest())
        endpoints=consumer_endpoints(net)
        record['consumer_endpoint_D_pins']=endpoints
        timings=[]
        for corner in ['ss','ff']:
            merged_t,cells_t,namespace=merge_scoped(libraries[corner]);used=workdir/('used_'+corner+'.lib');used.write_text(timing_subset(merged_t,cells_t,counts))
            delay='max' if corner=='ss' else 'min'
            for scope,restrict in [('all',''),('macro','-from [get_cells -hierarchical *u_rom] '),('merge','-to [get_pins {'+' '.join(endpoints)+'}] ')]:
                tcl=workdir/(corner+'_'+scope+'.tcl');tcl.write_text(f'''read_liberty {macro[corner]}
read_liberty {used}
read_verilog {workdir/'mapped.v'}
link_design qwen_loaded_capture
create_clock -name clk -period 833.333333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks clk]
set_clock_uncertainty -hold 25 [get_clocks clk]
set_clock_transition 20 [get_clocks clk]
set_input_transition 20 [get_ports {{rst_n wrom_re wrom_addr*}}]
set_input_delay -clock clk 0 [get_ports {{rst_n wrom_re wrom_addr*}}]
report_units
report_checks {restrict}-path_delay {delay} -format full_clock_expanded -digits 6 -fields {{slew cap input net fanout}}
'''+('report_check_types -max_capacitance -max_slew -max_fanout\n' if scope=='all' else '')+'exit\n')
                trc,out=guarded_process([sta,'-exit',str(tcl)],workdir,workdir/(corner+'_'+scope+'.log'))
                try:slack=worst_slack(out) if trc==0 else None
                except ValueError:slack=None
                timings.append(dict(corner=corner,scope=scope,returncode=trc,slack_ps=slack,path_pin_loads=path_loads(out),report_sha256=hashlib.sha256(out.encode()).hexdigest(),library_limit_violations_present='(VIOLATED)' in out.split('max slew')[-1] if 'max slew' in out else None))
        record['timings']=timings
        complete=all(t['slack_ps'] is not None for t in timings)
        record['status']='FAIL_REPLICA_PRESERVATION' if not preserved else 'FAIL_TIMING_REPLAY' if not complete else 'BLOCKED_MAPPED_TIMING_OR_LIMITS' if any(t['slack_ps']<0 or t['library_limit_violations_present'] for t in timings) else 'PASS_IDEAL_LOADED_CONE_SCREEN_NOT_PHYSICAL_CLOSURE'
    result.parent.mkdir(parents=True,exist_ok=True)
    with result.open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({k:record.get(k) for k in ['status','replicas_preserved','mapped_cell_counts','timings']},indent=2))
    return 0 if record['status'].startswith('PASS') else 1


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--workdir',type=Path,required=True);ap.add_argument('--result',type=Path,required=True);ap.add_argument('--sta',default='/usr/bin/sta')
    for c in ['ss','ff']:ap.add_argument('--library-'+c,type=Path,action='append',required=True)
    a=ap.parse_args();raise SystemExit(run(a.workdir.resolve(),a.result,{'ss':a.library_ss,'ff':a.library_ff},a.sta))
