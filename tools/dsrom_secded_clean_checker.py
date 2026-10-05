#!/usr/bin/env python3
"""Source-extracted checker measurement only; no engine/retirement implementation."""
import argparse,collections,gzip,hashlib,json,re,resource,shutil,subprocess,time
from pathlib import Path
from dsrom_secded_fullwidth_characterize import ROOT,OUT as FULL,merged,dcap,input_pins,proc,sha
OUT=ROOT/'results/uarch/dsrom_secded_clean_checker_20261002'
def extract(src):
    fun=src[src.index('    function automatic integer pos_of'):src.index('    endfunction')+len('    endfunction')]
    checks=src[src.index('        for (gi = 0; gi < R; gi = gi + 1) begin : g_chk'):src.index('        for (gi = 0; gi < K; gi = gi + 1) begin : g_fix')]
    return '''// Offline source characterization harness only, engine opt-in remains off.
module ot_rom_secded_clean_checker #(parameter integer K=256,R=9,N=K+R+1)
(input wire[N-1:0] cw, output wire[R-1:0] syn,
 output wire overall, output wire clean);
'''+fun+'\n    genvar gi;\n    generate\n'+checks+'''    endgenerate
    assign overall = ^cw;
    wire syn_zero = (syn == {R{1'b0}});
    assign clean = syn_zero & ~overall;
endmodule
'''
def prepare():
    OUT.mkdir(parents=True,exist_ok=True);src=(ROOT/'rtl/dft/ot_rom_secded_dec.sv').read_text()
    cone=extract(src);(OUT/'checker_cone.sv').write_text(cone)
    replicas=[dict(K=256,N=266,count=412,held_word_bits=274),dict(K=272,N=282,count=256,held_word_bits=282)]
    admitted=json.loads((OUT/'inputs/maxwell_model.json').read_text())
    assert admitted['admission']['existing_detector_cone_characterization']
    assert admitted['decoder_source_sha256']==sha(ROOT/'rtl/dft/ot_rom_secded_dec.sv')
    assert admitted['buffer_and_fence']['new_header_bits']==74
    bits=sum(v['count']*(v['held_word_bits']+74+12) for v in replicas)
    m=dict(schema='opentallas.dsrom.clean-checker-model.v1',candidate='DS4096-TP4-S58-PAR2-NP2048',source_sha256=sha(ROOT/'rtl/dft/ot_rom_secded_dec.sv'),cone_sha256=sha(OUT/'checker_cone.sv'),engine_opt_in_default=False,
      replicas=replicas,MACs_per_cycle=0,source_state_bits=0,source_pipeline_cycles=0,
      input_ports=[dict(K=v['K'],bits=v['N'],bytes=v['N']/8,outputs_bits=11,outputs_bytes=11/8,direct_payload_bits=v['K'],logical_boundary_tracks=v['N']+11+v['K']) for v in replicas],
      pin_load='one actual corner-specific DFFHQNx1 D pin on each syndrome9, overall and clean output;20ps input transition, actual input pin loads extracted',
      retained_word_state_bits=bits,retained_word_DFF_cell_area_only_mm2=bits*.2916/1e6,retained_word_FF50_proxy_mm2=bits*7.5816e-7,
      state_contract='per instance: complete held raw physical274 or main assembled282 + source identity74 includingnonce16; checker syndrome9/overall/clean +valid1. Raw reserved8 retained but not ECC data. No embedding credit.',
      Maxwell_model_sha256=sha(OUT/'inputs/maxwell_model.json'),Maxwell_admission_commit='6e7c88e7ae1f7d8f4b5308a3d1e5d993bc7eec20',
      Maxwell_current_area_screen_mm2=admitted['area']['screen_mm2'],
      own_extra_state_beyond_Maxwell_exception_hold_bits=bits-admitted['area']['separate_exception_hold_reference_bits'],
      original_fullcorrector_area_allowance_mm2=1.3275684864,new_checker_logic_charged_additionally=True,
      clean_contract='syn==0 && overall==0 AND valid accepted word/identity; payload direct release only after checker decision; source full decoder returns same data and no flags in this condition. No error-frequency or data-change assumption.',
      finite_contract='one accepted word/debt seat per replica; forbid overwrite/epoch/bank reuse until matched consumerACK or corrected-good ACK or fault/cancel physical drain. Full word and address/transaction remain held on error. No unchecked or early retirement. New reads refused while busy.',
      isolation_contract='fast syndrome/overall outputs drive declared capture pins only. Slow correction is fed from held word or registered check state; unisolated sharing/dedup can recreate full-corrector fanout221/176 and is rejected.',
      provisional_checker_latency_cycles=2,checker_latency_is_after_accepted_fullword_capture=True,guaranteed_II_cycles=None,
      composed_model='Retain Maxwell clean detector2cycles and heldII2 provisional service. Measurement may support an isolated1cycle logic screen; no automatic cycle reduction or token gain without actual capture/clock/route/accepted service.',
      SS_period_ps=833.333333,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
      area_slot='Keep existing733.7227518355257 conservative service screen and fullcorrector floors; add held state and mapped checkers without reuse credit. Actual slots/translated PG/OBS/via/clock/wire still required.',
      routing_capacity_after_exclusions=None,engine_RTL_admitted=False,PR_admitted=False,
      four_target_applicability={'DS_ROM':'current PAR2 ECC word validation','DS_HBM':'no ROM parity provider transfer','Qwen_ROM':'separate source/interface model required','Qwen_HBM':'not applicable to GPU comparator'},
      fullcorrector_failure_commit='9c3aeed6c292151bf32d54de342b44e1e348be24')
    (OUT/'model.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n');return m
def run(work):
    if work.exists():raise ValueError('retain first run, no overwrite/retry')
    work.mkdir(parents=True);model=json.loads((OUT/'model.json').read_text())
    assert sha(OUT/'checker_cone.sv')==model['cone_sha256']
    record=dict(model=model,results={},status='STARTED',input_transition_ps=20,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),tool_sha256={t:sha(Path(shutil.which(t))) for t in ('yosys','sta')},tool_versions={'yosys':subprocess.check_output(['yosys','-V'],text=True).strip(),'sta':subprocess.check_output(['sta','-version'],text=True).strip()},wire_and_clock_context_bound=False,physical_adoption=False)
    ss,sc=merged('ss');(work/'mapping_ss.lib').write_text(ss)
    corner_cells={c:merged(c)[1] for c in ('ss','ff')}
    for c in ('ss','ff'):
        for family in ('ao','invbuf','oa','simple','seq'):(work/f'{family}_{c}.lib').write_bytes(gzip.decompress((FULL/'inputs'/f'{family}_{c}.lib.gz').read_bytes()))
    for k in (256,272):
        d=work/f'K{k}';d.mkdir();s=d/'synth.ys';s.write_text(f'''read_verilog -sv {OUT/'checker_cone.sv'}
chparam -set K {k} -set R 9 -set N {k+10} ot_rom_secded_clean_checker
hierarchy -check -top ot_rom_secded_clean_checker
synth -top ot_rom_secded_clean_checker
abc -liberty {work/'mapping_ss.lib'}
clean
stat -liberty {work/'mapping_ss.lib'}
write_verilog -noattr -noexpr {d/'mapped.v'}
write_json {d/'mapped.json'}
''')
        v={'mapping':proc(['yosys','-s',str(s)],d,d/'synth.log')};record['results'][str(k)]=v
        if v['mapping']['returncode']:record['status']='FAIL_MAPPING';break
        n=json.loads((d/'mapped.json').read_text())['modules']['ot_rom_secded_clean_checker'];counts=dict(collections.Counter(x['type'] for x in n['cells'].values()))
        assert {name:len(p['bits']) for name,p in n['ports'].items()}==dict(cw=k+10,syn=9,overall=1,clean=1)
        assert all(isinstance(b,int) for p in n['ports'].values() for b in p['bits'])
        dirs={name:input_pins(sc[name]) for name in counts};sinks={b for cell in n['cells'].values() for p,bits in cell['connections'].items() if p in dirs[cell['type']] for b in bits};assert set(n['ports']['cw']['bits'])<=sinks
        v.update(ports={name:len(p['bits']) for name,p in n['ports'].items()},cell_counts=counts,mapped_area_um2=sum(count*float(re.search(r'\barea\s*:\s*([\d.]+)',sc[name])[1]) for name,count in counts.items()),state_bits=0,netlist_sha256=sha(d/'mapped.v'))
        for c in ('ss','ff'):
            cap=dcap(corner_cells[c]);t=d/f'{c}.tcl';reads='\n'.join(f'read_liberty {work/f"{family}_{c}.lib"}' for family in ('ao','invbuf','oa','simple','seq'))
            t.write_text(reads+f'''
read_verilog {d/'mapped.v'}
link_design ot_rom_secded_clean_checker
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
report_checks -to [get_ports clean] -path_delay max -group_count 1 -format full_clock_expanded -digits 6 -fields {{slew capacitance input_pin net}}
report_checks -path_delay max -group_count 1 -format full_clock_expanded -digits 6 -fields {{slew capacitance input_pin net}}
report_checks -path_delay min -group_count 1 -format full_clock_expanded -digits 6 -fields {{slew capacitance input_pin net}}
report_check_types -max_slew -max_capacitance
exit
''')
            pr=proc(['sta','-exit',str(t)],d,d/f'{c}.log');raw=(d/f'{c}.log').read_text();arr=[float(x) for x in re.findall(r'([-\d.]+)\s+data arrival time',raw) if float(x)>=0];sl=[float(x) for x in re.findall(r'([-\d.]+)\s+slack',raw)]
            v[c]=dict(process=pr,output_D_pin_fF=cap,clean_max_delay_ps=arr[0] if arr else None,all_outputs_max_delay_ps=arr[1] if len(arr)>1 else None,min_delay_ps=arr[2] if len(arr)>2 else None,virtual_slack_ps=sl,errors=bool(re.search(r'^Error:',raw,re.M)),missing_templates='table template' in raw and 'not found' in raw,library_limits_exceeded='(VIOLATED)' in raw.split('max slew')[-1],report_sha256=sha(d/f'{c}.log'))
        (work/'record.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    record['status']='MEASURED_CHECKER_ONLY_CONTEXT_OPEN' if len(record['results'])==2 and all(v[c]['process']['returncode']==0 and not v[c]['errors'] and not v[c]['missing_templates'] and v[c]['clean_max_delay_ps'] is not None for v in record['results'].values() for c in ('ss','ff')) else 'FAIL_CHARACTERIZATION'
    record['actual_resources_children']=dict(zip(('user_s','system_s','maxrss_KiB'),resource.getrusage(resource.RUSAGE_CHILDREN)[:3]));(work/'record.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n');return record
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');ap.add_argument('--workdir',type=Path);a=ap.parse_args()
    if a.prepare:print(json.dumps(prepare(),indent=2))
    elif a.workdir:print(json.dumps(run(a.workdir.resolve()),indent=2))
    else:ap.error('--prepare or --workdir required')
