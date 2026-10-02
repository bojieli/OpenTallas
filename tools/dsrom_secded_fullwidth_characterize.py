#!/usr/bin/env python3
"""Unchanged full SECDED mapping; pin-loaded SS/FF combinational screen only."""
import argparse, collections, gzip, hashlib, json, math, re, resource, shutil, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_secded_fullwidth_characterization_20261002'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def block(s,start):
    p=s.index('{',start); n=1; j=p+1
    while n: n+=(s[j]=='{')-(s[j]=='}'); j+=1
    return s[start:j]
def merged(corner):
    bodies={}; templates={}; prefix=None
    for kind in ('ao','invbuf','oa','simple','seq'):
        s=gzip.decompress((OUT/'inputs'/f'{kind}_{corner}.lib.gz').read_bytes()).decode()
        # FF families reuse template names with different tables. Namespace only
        # identifiers and references, preserving every original table value.
        names=re.findall(r'\b(?:lu_table_template|power_lut_template)\s*\(([^)]+)\)',s)
        for name in names:
            s=re.sub(r'\b'+re.escape(name)+r'\b',kind+'_'+name,s)
        header=s[:re.search(r'\bcell\s*\(',s).start()]
        if prefix is None: prefix=header
        for m in re.finditer(r'\b(?:lu_table_template|power_lut_template)\s*\(([^)]+)\)',header):
            b=block(header,m.start())
            if m[1] in templates and re.sub(r'\s','',templates[m[1]])!=re.sub(r'\s','',b): raise ValueError('template conflict')
            templates[m[1]]=b
        for m in re.finditer(r'\bcell\s*\(([^)]+)\)',s):
            name=m[1].strip(' "'); b=block(s,m.start())
            if name in bodies and bodies[name]!=b: raise ValueError('cell conflict')
            bodies[name]=b
    # Drop original template definitions then reinsert unique templates once.
    for m in reversed(list(re.finditer(r'\b(?:lu_table_template|power_lut_template)\s*\(([^)]+)\)',prefix))):
        b=block(prefix,m.start()); prefix=prefix[:m.start()]+prefix[m.start()+len(b):]
    return prefix+'\n'+'\n'.join(templates.values())+'\n'+'\n'.join(bodies.values())+'\n}\n',bodies
def dcap(cells):
    s=cells['DFFHQNx1_ASAP7_75t_R']; m=re.search(r'\bpin\s*\(D\)',s)
    return float(re.search(r'\bcapacitance\s*:\s*([\d.]+)',block(s,m.start()))[1])
def model():
    return {'candidate':'DS4096-TP4-S58-PAR2-NP2048', 'source_main':'fd7220c1e55397dec90222e1f99a8bd95ae02e03',
      'decoder_source_sha256':sha(OUT/'inputs/decoder.sv'), 'finite_model_sha256':sha(OUT/'inputs/finite_model.json'),
      'MACs_per_cycle':0,'communication_intensity':'corrected systematic data + two fault flags per accepted codeword; no payload arithmetic',
      'raw':{'K':256,'N':266,'replicas_per_die':412,'input_bits_per_instance_cycle':266,'input_bytes_per_instance_cycle':33.25,'output_bits_per_instance_cycle':258,'output_bytes_per_instance_cycle':32.25,'required_boundary_signal_tracks_per_instance':524,'nominal_all_replica_input_bits':109592,'nominal_all_replica_output_bits':106296,'actual_simultaneous_service_not_proven':True},
      'main':{'K':272,'N':282,'representative_replicas':1,'selected_replica_count':256,'consumer_128_pair_demand_if_two_main_words_per_pair':256,'input_bits_per_instance_cycle':282,'input_bytes_per_instance_cycle':35.25,'output_bits_per_instance_cycle':274,'output_bytes_per_instance_cycle':34.25,'required_boundary_signal_tracks_per_instance':556},
      'topology_provenance':{'current_physical_temporal_model_commit':'0e12358804625d6846129ba757058618c82d3831','current_physical_construction':'412 leaf-local raw decoders and256 main decoders; characterization independently measures one full instance each','earlier_13cc_storage_proposal':'4 shared raw decode/gather grants with437304 mux2 selector screen; not substituted for current physical412 topology'},
      'state_bits_existing_decoder':0,'pipeline_cycles_existing_decoder':0,'memory_ports_added':0,
      'load':{'outputs':'one actual DFFHQNx1 D-pin per corrected-data/fault output, corner-specific capacitance','inputs':'20ps port transition characterization condition; source driver slew/arrival remains separate'},
      'period_ps':833.333333,'SS_setup_uncertainty_ps':60,'FF_hold_uncertainty_ps':25,
      'single_user_latency':'finite model exposes raw_decode and weight_decode terminal service parameters; mapping measures existing logic only and does not replace positive capture/gather/wait dependencies',
      'area_slot':{'existing_raw_decoder_allowance_mm2':0.7996465152,'existing_main_decoder_allowance_mm2':0.5279219712,'current_physical_construction_screen_mm2':732.9650770579258,'rule':'measure412*raw plus256*main cell area against existing named allowances, retain allowance floor; no duplicate addition or unproved negative area credit; actual slots/PG/vias/clock/wires remain separate'},
      'four_target_applicability':{'DS_ROM':'PAR2 local raw parity + main SECDED dependency','DS_HBM':'not a ROM-protected weight-path provider','Qwen_ROM':'no qualification transfer; exact independent source/ports required','Qwen_HBM':'not applicable to GPU comparator'},
      'physical_build_admitted':False,'tracks_capacity_after_actual_exclusions':None,'scope':'complete unchanged combinational cones, not a parent/tile/capture timing certificate'}
def proc(args,where,log):
    start=time.monotonic()
    with log.open('x') as f: p=subprocess.run(args,cwd=where,stdout=f,stderr=subprocess.STDOUT)
    return {'returncode':p.returncode,'elapsed_s':time.monotonic()-start}
def input_pins(cell):
    return {m[1].strip(' "') for m in re.finditer(r'\bpin\s*\(([^)]+)\)',cell) if re.search(r'\bdirection\s*:\s*input\s*;',block(cell,m.start()))}
def timing_only(work,reuse):
    """Reuse both completed mappings; load corner families unmodified/separately.
    Liberty templates are scoped to each library, so FF collisions need no
    merged namespace here. No synthesis, retiming or new engine source.
    """
    if work.exists():raise ValueError('preserve first run; no overwrite/retry')
    work.mkdir(parents=True)
    record=json.loads((reuse/'record.json').read_text())
    record['prior_failed_report']=dict(path=str(reuse/'record.json'),sha256=sha(reuse/'record.json'))
    record['timing_runner_sha256']=sha(Path(__file__))
    record['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    record['timing_libraries_unmodified_separate_families']=True
    for corner in ('ss','ff'):
        for kind in ('ao','invbuf','oa','simple','seq'):
            p=work/f'{kind}_{corner}.lib';p.write_bytes(gzip.decompress((OUT/'inputs'/f'{kind}_{corner}.lib.gz').read_bytes()))
    for k in (256,272):
        d=work/f'K{k}';d.mkdir();old=reuse/f'K{k}'
        if sha(old/'mapped.v')!=record['results'][str(k)]['netlist_sha256']:raise ValueError('mapped netlist changed')
        shutil.copyfile(old/'mapped.v',d/'mapped.v');r=record['results'][str(k)]
        r['prior_failed_timing']={c:r[c] for c in ('ss','ff')}
        for corner in ('ss','ff'):
            cap=dcap(merged(corner)[1]);tcl=d/f'{corner}.tcl'
            reads='\n'.join(f'read_liberty {work/f"{kind}_{corner}.lib"}' for kind in ('ao','invbuf','oa','simple','seq'))
            tcl.write_text(reads+f'''
read_verilog {d/'mapped.v'}
link_design ot_rom_secded_dec
create_clock -name virtual -period 833.333333
set_clock_uncertainty -setup 60 [get_clocks virtual]
set_clock_uncertainty -hold 25 [get_clocks virtual]
set_input_delay -max 0 -clock virtual [all_inputs]
set_input_delay -min 0 -clock virtual [all_inputs]
set_output_delay -max 0 -clock virtual [all_outputs]
set_output_delay -min 0 -clock virtual [all_outputs]
set_input_transition 20 [all_inputs]
set_load {cap} [all_outputs]
report_units
report_checks -path_delay max -group_count 3 -format full_clock_expanded -digits 6 -fields {{slew capacitance input_pin net}}
report_checks -path_delay min -group_count 3 -format full_clock_expanded -digits 6 -fields {{slew capacitance input_pin net}}
report_check_types -max_slew -max_capacitance
exit
''')
            pr=proc(['sta','-exit',str(tcl)],d,d/f'{corner}.log');s=(d/f'{corner}.log').read_text()
            r[corner]={'process':pr,'output_load_fF':cap,'data_arrival_ps':[float(x) for x in re.findall(r'([-\d.]+)\s+data arrival time',s)],'virtual_slack_ps':[float(x) for x in re.findall(r'([-\d.]+)\s+slack',s)],'report_sha256':sha(d/f'{corner}.log'),'report_errors':bool(re.search(r'^Error:',s,re.M)),'missing_timing_templates':'table template' in s and 'not found' in s,'raw_warnings':[line for line in s.splitlines() if line.startswith('Warning:')]}
    good=all(r[c]['process']['returncode']==0 and not r[c]['report_errors'] and not r[c]['missing_timing_templates'] and len(r[c]['data_arrival_ps'])>=2 for r in record['results'].values() for c in ('ss','ff'))
    record['status']='CHARACTERIZED_COMBINATIONAL_ONLY' if good else 'FAIL_TIMING_REPORT'
    record['resources_timing_children']=dict(zip(('user_s','system_s','maxrss_KiB'),resource.getrusage(resource.RUSAGE_CHILDREN)[:3]))
    (work/'record.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    return record
def run(work,reuse_k256=None):
    if work.exists(): raise ValueError('preserve first run; no overwrite/retry')
    work.mkdir(parents=True)
    libs={}; cells={}
    for corner in ('ss','ff'):
        s,c=merged(corner); (work/f'{corner}.lib').write_text(s); libs[corner]=work/f'{corner}.lib';cells[corner]=c
        for kind in ('ao','invbuf','oa','simple','seq'):
            (work/f'{kind}_{corner}.lib').write_bytes(gzip.decompress((OUT/'inputs'/f'{kind}_{corner}.lib.gz').read_bytes()))
    record={'model':model(),'tool_versions':{},'results':{},'status':'STARTED','wire_parasitics':False,'clock_skew':False,'FF_registered_hold_closed':False}
    for exe,args in [('yosys',['yosys','-V']),('sta',['sta','-version'])]:
        record['tool_versions'][exe]={'version':subprocess.check_output(args,text=True).strip(),'binary_sha256':sha(Path(shutil.which(exe)))}
    for k in (256,272):
        d=work/f'K{k}'; d.mkdir(); top='ot_rom_secded_dec'
        script=d/'synth.ys';script.write_text(f'''read_verilog -sv {OUT/'inputs/decoder.sv'}
chparam -set K {k} -set R 9 -set N {k+10} {top}
hierarchy -check -top {top}
synth -top {top}
abc -liberty {libs['ss']}
clean
stat -liberty {libs['ss']}
write_verilog -noattr -noexpr {d/'mapped.v'}
write_json {d/'mapped.json'}
''')
        if k==256 and reuse_k256:
            for name in ('mapped.json','mapped.v','synth.log','synth.ys'):shutil.copyfile(reuse_k256/name,d/name)
            r={'mapping':{'returncode':0,'reused_unchanged_completed_netlist':str(reuse_k256),'mapped_json_sha256':sha(reuse_k256/'mapped.json'),'original_source_commit':'347beb640'}}
        else:r={'mapping':proc(['yosys','-s',str(script)],d,d/'synth.log')}
        record['results'][str(k)]=r
        if r['mapping']['returncode']:record['status']='FAIL_MAPPING';break
        net=json.loads((d/'mapped.json').read_text())['modules'][top]
        widths={name:len(port['bits']) for name,port in net['ports'].items()}
        if widths!={'cw':k+10,'data':k,'corrected':1,'uncorrectable':1}: raise ValueError('full port loss')
        if any(not isinstance(b,int) for port in net['ports'].values() for b in port['bits']): raise ValueError('constant port stub')
        directions={name:input_pins(cells['ss'][name]) for name in {c['type'] for c in net['cells'].values()}}
        sinks={b for cell in net['cells'].values() for name,bits in cell['connections'].items() if name in directions[cell['type']] for b in bits}
        if not set(net['ports']['cw']['bits'])<=sinks: raise ValueError('dropped dynamic codeword bit')
        counts=dict(collections.Counter(c['type'] for c in net['cells'].values()))
        r.update(ports=widths,cell_counts=counts,area_um2=sum(count*float(re.search(r'\barea\s*:\s*([\d.]+)',cells['ss'][name])[1]) for name,count in counts.items()),state_bits=0,netlist_sha256=sha(d/'mapped.v'))
        for corner in ('ss','ff'):
            missing=set(counts)-set(cells[corner]); assert not missing, missing
            cap=dcap(cells[corner]);tcl=d/f'{corner}.tcl'
            reads='\n'.join(f'read_liberty {work/f"{kind}_{corner}.lib"}' for kind in ('ao','invbuf','oa','simple','seq'))
            tcl.write_text(reads+f'''
read_verilog {d/'mapped.v'}
link_design {top}
create_clock -name virtual -period 833.333333
set_clock_uncertainty -setup 60 [get_clocks virtual]
set_clock_uncertainty -hold 25 [get_clocks virtual]
set_input_delay -max 0 -clock virtual [all_inputs]
set_input_delay -min 0 -clock virtual [all_inputs]
set_output_delay -max 0 -clock virtual [all_outputs]
set_output_delay -min 0 -clock virtual [all_outputs]
set_input_transition 20 [all_inputs]
set_load {cap} [all_outputs]
report_units
report_checks -path_delay max -group_count 3 -format full_clock_expanded -digits 6 -fields {{slew capacitance input_pin net}}
report_checks -path_delay min -group_count 3 -format full_clock_expanded -digits 6 -fields {{slew capacitance input_pin net}}
report_check_types -max_slew -max_capacitance
exit
''')
            pr=proc(['sta','-exit',str(tcl)],d,d/f'{corner}.log');s=(d/f'{corner}.log').read_text()
            arrivals=[float(x) for x in re.findall(r'([-\d.]+)\s+data arrival time',s)]
            slacks=[float(x) for x in re.findall(r'([-\d.]+)\s+slack',s)]
            r[corner]={'process':pr,'output_load_fF':cap,'data_arrival_ps':arrivals,'virtual_slack_ps':slacks,'report_sha256':sha(d/f'{corner}.log'),'report_errors':bool(re.search(r'^Error:',s,re.M))}
        record['status']='CHARACTERIZED_COMBINATIONAL_ONLY' if all(r[c]['process']['returncode']==0 and not r[c]['report_errors'] and len(r[c]['data_arrival_ps'])>=2 and len(r[c]['virtual_slack_ps'])>=2 for c in ('ss','ff')) else 'FAIL_TIMING_REPORT'
        (work/'record.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    record['resources_children']=dict(zip(('user_s','system_s','maxrss_KiB'),resource.getrusage(resource.RUSAGE_CHILDREN)[:3]))
    (work/'record.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    return record
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');ap.add_argument('--workdir',type=Path);ap.add_argument('--reuse-k256',type=Path);ap.add_argument('--timing-only-reuse',type=Path);a=ap.parse_args()
    if a.prepare:(OUT/'model.json').write_text(json.dumps(model(),indent=2,sort_keys=True)+'\n')
    elif a.workdir:print(json.dumps(timing_only(a.workdir.resolve(),a.timing_only_reuse) if a.timing_only_reuse else run(a.workdir.resolve(),a.reuse_k256),indent=2))
    else:ap.error('--prepare or --workdir required')
