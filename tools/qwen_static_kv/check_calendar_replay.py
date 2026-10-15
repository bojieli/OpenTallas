#!/usr/bin/env python3
"""Small actual RTL leaf gate. Independent compile roots only; no native claim."""
import argparse,ast,copy,hashlib,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qwen_static_kv.calendar_replay import ROOT,PRODUCER,CONSUMERS,compile_image
# Extract the sizing function without importing unrelated whole-model packages.
_model_tree=ast.parse((ROOT/'tools/uarch_model.py').read_text())
_model_function=next(n for n in _model_tree.body if isinstance(n,ast.FunctionDef) and n.name=='qwen_kv_calendar_replay_model')
exec(compile(ast.Module(body=[_model_function],type_ignores=[]),'uarch_model.py','exec'))

def run(out):
    out.mkdir(parents=True,exist_ok=False)
    manifest={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
              [PRODUCER,*CONSUMERS['HBM'],*CONSUMERS['CORE']]}
    reports=[];negatives=[]
    def reject(name,c):
        try:compile_image(c)
        except ValueError as e:negatives.append(dict(name=name,error=str(e)));return
        raise AssertionError('invalid contract accepted '+name)
    for domain,width in [('HBM',64),('CORE',33)]:
        events=[dict(cycle=n if n<16 else 16+(n-16)*3+n%2,
                     payload=(0x4000800010020001^((n+1)<<19))&((1<<width)-1)) for n in range(64)]
        c=dict(scope='COMPONENT_ONLY',origin='INDEPENDENT_STATIC_CONTRACT',domain=domain,
               cycle_origin='INTERNAL_START_OUTPUT_INTERVAL_0',source_sha256=manifest,
               events=events,stop_cycle=200)
        image=compile_image(c)
        (out/(domain.lower()+'_independent_image.json')).write_text(json.dumps(image,indent=2)+'\n')
        for mutation in ['production','observation','source','cycle','collision','capacity','width','stop','all36']:
            bad=copy.deepcopy(c)
            if mutation=='production':bad['scope']='PRODUCTION'
            elif mutation=='observation':bad['origin']='CONTROLLER_OUTPUT_TRACE'
            elif mutation=='source':bad['source_sha256'][PRODUCER]='0'*64
            elif mutation=='cycle':bad['cycle_origin']='OUTER_STAGE_START'
            elif mutation=='collision':bad['events'][1]['cycle']=0
            elif mutation=='capacity':bad['events']*=2
            elif mutation=='width':bad['events'][0]['payload']=1<<width
            elif mutation=='stop':bad['stop_cycle']=bad['events'][-1]['cycle']
            elif mutation=='all36':bad['stage_count']=36
            reject(domain+'_'+mutation,bad)
        for mut in range(3):
            name=f'{domain.lower()}_m{mut}';top='tb_qkd_kv_calendar_replay'
            binary=out/(name+'.sim')
            build=subprocess.run(['iverilog','-g2012','-s',top,f'-P{top}.MUT={mut}',
              f'-P{top}.WIDTH={width}','-o',str(binary),str(ROOT/PRODUCER),
              str(ROOT/'rtl/test/qwen_static_kv/tb_qkd_kv_calendar_replay.sv')],capture_output=True,text=True)
            (out/(name+'.build.log')).write_text(build.stdout+build.stderr)
            if build.returncode:raise RuntimeError(name+' compile failed')
            result=subprocess.run(['vvp',str(binary)],capture_output=True,text=True)
            log=result.stdout+result.stderr;(out/(name+'.log')).write_text(log)
            if mut==0:
                if result.returncode or 'PASS replay' not in log:raise RuntimeError(name+' failed')
            elif result.returncode==0 or 'EDGE mismatch' not in log:raise RuntimeError(name+' mutant escaped')
            reports.append(dict(name=name,exit=result.returncode,mutant_rejected=bool(mut),log=name+'.log'))
            binary.unlink()
    elaboration={}
    for domain,width in [('HBM',64),('CORE',33)]:
        netlist=out/(domain.lower()+'_elaborated.json')
        result=subprocess.run(['yosys','-Q','-T','-p',
          f'read_verilog -sv {ROOT/PRODUCER}; chparam -set WIDTH {width} qkd_kv_calendar_replay; hierarchy -top qkd_kv_calendar_replay; proc; memory_map; opt_clean; write_json {netlist}'],capture_output=True,text=True)
        (out/(domain.lower()+'_elaboration.log')).write_text(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError('actual boot-flop elaboration failed')
        mod=json.loads(netlist.read_text())['modules']['qkd_kv_calendar_replay']
        cells=mod['cells'];flops=[c for c in cells.values() if c['type'] in ('$dff','$adff')]
        if any(c['type'].startswith('$mem') for c in cells.values()):raise AssertionError('unmapped calendar memory')
        pin_checks={}
        for name in ('payload','cfg_addr','cfg_time','cfg_payload','cfg_we','cfg_seal','start'):
            pin='Q' if name=='payload' else 'D'
            connected={b for c in flops for b in c['connections'][pin]}
            bits=mod['ports'][name]['bits']
            if not all(b in connected for b in bits):raise AssertionError('missing pin flop '+name)
            pin_checks[name]=len(bits)
        elaboration[domain]=dict(width=width,source_ff_bits=sum(len(c['connections']['Q']) for c in flops),
          storage_bits=64*(32+width),inferred_memory_cells=0,direct_pin_flop_bits=pin_checks,
          scope='source elaboration only; no mapped cells/area/CTS/timing claim')
        netlist.unlink()
    replication=dict(pseudo_channels=128,domains=2,events_per_domain_leaf=64,
      source_ff_bits_128PC_two_domains=128*sum(v['source_ff_bits'] for v in elaboration.values()),
      storage_bits_128PC_two_domains=128*sum(v['storage_bits'] for v in elaboration.values()),
      stage_coverage=1,actual_all36_rowcount_evidence=False,physical_slot_grant=False,
      limitation='One leaf/domain/PC has only64 events; actual512 sectors perPC perlayer need at least8 leaves/domain before command/front extras, unless source-proven compression/reuse replaces this mechanism. No all36 coverage.')
    source_paths=[PRODUCER,'rtl/test/qwen_static_kv/tb_qkd_kv_calendar_replay.sv',
                  'tools/qwen_static_kv/calendar_replay.py','tools/qwen_static_kv/check_calendar_replay.py','tools/uarch_model.py']
    report=dict(status='PASS_COMPONENT_ONLY',elaboration=elaboration,replication=replication,model=qwen_kv_calendar_replay_model(),
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_paths},
      runs=reports,negative_controls=negatives,production_installable=False,
      physical_qualified=False,full_token_qualified=False,
      limitation='64-event mechanism per domain only. Test image roots are declared boundary stimuli, not fullshape actual calendars; no controller/front/ring composition, physical storage fit or die binding.')
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(reports),'RTL runs',len(negatives),'compiler rejections')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();run(a.out.resolve())
