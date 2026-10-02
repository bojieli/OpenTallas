#!/usr/bin/env python3
"""Map complete literal q/BF sources once; no timing/physical/adoption claim."""
import argparse
import json
import os
import subprocess
import time
import gzip
import re
import shutil
import math
from pathlib import Path
from dsrom_noECC_complete_element import BASE,ROOT,sha,build
from dsrom_secded_fullwidth_characterize import merged,block

def save(path,value):
    tmp=path.with_suffix('.new');tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');tmp.replace(path)

def inventory(path,cells,corner):
    net=json.loads(path.read_text())['modules']['ot_v41_rom_elem_w10']
    cache={}
    for typ in {c['type'] for c in net['cells'].values()} & cells.keys():
        body=cells[typ];area=float(re.search(r'\barea\s*:\s*([\d.]+)',body)[1]);pins={}
        for m in re.finditer(r'\bpin\s*\(([^)]+)\)',body):
            pb=block(body,m.start())
            cap=re.search(r'\bcapacitance\s*:\s*([\d.]+)',pb)
            pins[m[1].strip(' "')]=dict(clock=bool(re.search(r'\bclock\s*:\s*true',pb)),cap=float(cap[1]) if cap else 0)
        cache[typ]=(area,pins)
    aliases={};gates={};counts={};unmapped={};clock={};state={};area=0;metadata=0;captures=0
    for n,v in net['netnames'].items():
        for bit in v['bits']:
            if isinstance(bit,int):aliases.setdefault(bit,[]).append(n)
    for name,c in net['cells'].items():
        typ=c['type']
        if typ=='$scopeinfo':metadata+=1;continue
        counts[typ]=counts.get(typ,0)+1
        if 'ICG' in typ:gates[c['connections']['GCLK'][0]]=name
        if typ=='ot_rom_4096x274_m8':
            cap=8.6838 if corner=='ss' else 10.3732
            bit=c['connections']['clk'][0]
            z=clock.setdefault(bit,dict(sinks=0,pin_cap_fF=0,masters={}))
            z['sinks']+=1;z['pin_cap_fF']+=cap;z['masters'][typ]=z['masters'].get(typ,0)+1
            continue
        if typ not in cache:unmapped[typ]=unmapped.get(typ,0)+1;continue
        ca,pins=cache[typ];area+=ca
        for pin,bits in c['connections'].items():
            if pins.get(pin,{}).get('clock'):
                for bit in bits:
                    z=clock.setdefault(bit,dict(sinks=0,pin_cap_fF=0,masters={}))
                    z['sinks']+=1;z['pin_cap_fF']+=pins[pin]['cap'];z['masters'][typ]=z['masters'].get(typ,0)+1
        if typ.startswith('DFF'):
            src=c['attributes'].get('src','')
            state[src]=state.get(src,0)+1
            if re.search(r'ot_v41_rom_elem_w10\.sv:746\.',src):captures+=1
    for bit,z in clock.items():
        z['net_aliases']=aliases.get(bit,[]);z['source_ICG']=gates.get(bit,'root')
        z['load_groups_lowerbound_before_wires']=math.ceil(z['pin_cap_fF']/46.08) if bit in gates else None
    wake={n:v['bits'] for n,v in net['netnames'].items() if n.startswith('g_wake.g_leaf') and n.endswith('.wake')}
    distinct=len({tuple(v) for v in wake.values()})
    return dict(corner=corner,cells=sum(counts.values()),master_counts=counts,stdcell_area_um2=area,
        raw_4096_macro_count=counts.get('ot_rom_4096x274_m8',0),unmapped_nonmacro_types=unmapped,
        Yosys_scopeinfo_metadata_not_hardware=metadata,clock_nets={str(k):v for k,v in clock.items()},
        source_FF_count_by_location=state,capture_flops_identified=captures,
        capture_scope='Source746..749 captures two272bit activepayloads perMB in twoPPbanks;unusedtwohighbits optimized,274physicalmacroports unchanged',
        wake_nets=wake,distinct_WAKE_FF_output_nets=distinct,
        source_8leaf_WAKE_replica_retention_pass=distinct==8,
        scope='Mappedcell pin sums; no wires, CTS/skew, clockgating/minpulse, or routed timing qualification.')

def wake_cells(path):
    net=json.loads(path.read_text())['modules']['ot_v41_rom_elem_w10']
    ff={k:c for k,c in net['cells'].items() if c['type'].startswith('DFF') and
        re.search(r'ot_v41_rom_elem_w10\.sv:191\.',c.get('attributes',{}).get('src',''))}
    q={tuple(c['connections'][p]) for c in ff.values() for p in c['connections']
       if c['port_directions'][p]=='output'}
    w={tuple(v['bits']) for k,v in net['netnames'].items()
       if k.startswith('g_wake.g_leaf') and k.endswith('.wake')}
    def attr(c,n):return bool(int(c.get('attributes',{}).get(n,'0'),2))
    return dict(mapped_local_FF_count=len(ff),distinct_FF_outputs=len(q),distinct_WAKE_outputs=len(w),
        real_cell_keep_and_dont_touch=all(attr(c,'keep') and attr(c,'dont_touch') for c in ff.values()),
        cells=ff,passed=len(ff)==8 and len(q)==8 and len(w)==8 and
        all(attr(c,'keep') and attr(c,'dont_touch') for c in ff.values()))

def run(work,backend,reuse_q=None,only_case=None):
    if work.exists():raise ValueError('preserve existing attempt; no overwrite/retry')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip():raise ValueError('clean pinned source required')
    model=build();manifest=json.loads((BASE/'physical_source_manifest.json').read_text())
    work.mkdir(parents=True)
    container='dsrom-wake-retention-a910'
    expected_image='sha256:af971398d91e5d154ec40d3df26554efd8790107268a4c7f1e6bb8f222979d34'
    if backend=='pinned-orfs':
        observed=subprocess.check_output(['docker','inspect',container,'--format','{{.Image}}'],text=True).strip()
        if observed!=expected_image:raise ValueError('pinned mapping image mismatch')
    command=['yosys'] if backend=='local' else ['docker','exec',container,'yosys']
    record=dict(status='RUNNING',pid=os.getpid(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_manifest_sha256=sha(BASE/'physical_source_manifest.json'),model_sha256=sha(BASE/'model.json'),runner_sha256=sha(Path(__file__)),
        versions={'yosys':subprocess.check_output(command+['-V'],text=True).strip()},backend=backend,
        container_image=expected_image if backend=='pinned-orfs' else None,
        host_headroom={'free_m':subprocess.check_output(['free','-m'],text=True),'df_Pm':subprocess.check_output(['df','-Pm',str(work)],text=True),'uptime':subprocess.check_output(['uptime'],text=True)},
        fixed_clocks_GHz=1.2,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
        synthesis_mapping_only=True,physical_PR=False,source_changes=False,
        reuse='Current21-file manifest has no mapped receipt in the retained source/model artifacts; earlierfullcorrector/checker and historicalelement maps are different cones/sources, not reused as this element.',runs=[])
    save(work/'record.json',record)
    _,sscells=merged('ss');_,ffcells=merged('ff')
    text,_=merged('ss');lib=work/'stock_ss.lib';lib.write_text(text)
    files=[];copies=work/'source_files';copies.mkdir()
    for f in manifest['files']:
        origin=BASE/'inputs'/f['copy'];copy=copies/origin.name
        shutil.copyfile(origin,copy)
        if sha(copy)!=f['sha256']:raise ValueError('literal source copy changed')
        files.append(copy)
    jobroot=work if backend=='local' else Path('/tmp')/work.name
    if backend=='pinned-orfs':
        subprocess.run(['docker','exec',container,'mkdir',str(jobroot)],check=True)
        subprocess.run(['docker','cp',str(work)+'/.',container+':'+str(jobroot)],check=True)
    record['library_sha256']=sha(lib);save(work/'record.json',record)
    for case,params in manifest['variants'].items():
        if only_case and case!=only_case:continue
        d=work/case;d.mkdir();allparams=manifest['params_common']|params
        if case=='q' and reuse_q:
            prior=json.loads((reuse_q/'record.json').read_text())
            if prior['status']=='RUNNING':raise ValueError('preserve live attempt; await terminal before reuse')
            old=prior['runs'][0]
            if prior['source_manifest_sha256']!=record['source_manifest_sha256'] or old['parameters']!=allparams or old['returncode']!=0:
                raise ValueError('reuse source/params/mapping mismatch')
            for n in ('mapped.v','mapped.json','map.ys','map.log'):
                if n.startswith('mapped'):
                    key='mapped_json_sha256' if n.endswith('.json') else 'mapped_verilog_sha256'
                    if sha(reuse_q/'q'/n)!=old[key]:raise ValueError('reuse mapped artifact pin changed')
                shutil.copyfile(reuse_q/'q'/n,d/n)
            entry=dict(case='q',parameters=allparams,reused_from=str(reuse_q),source_commit=prior['source_commit'],
                returncode=0,mapped_verilog_sha256=sha(d/'mapped.v'),mapped_json_sha256=sha(d/'mapped.json'),
                synthesis_reexecuted=False,inventory={c:inventory(d/'mapped.json',cells,c) for c,cells in [('ss',sscells),('ff',ffcells)]})
            record['runs'].append(entry);save(work/'record.json',record)
            continue
        joblib=jobroot/'stock_ss.lib';jobdir=jobroot/case
        script='read_liberty -lib '+str(joblib)+'\n'
        script+='read_verilog -sv -DSYNTHESIS '+' '.join(str(jobroot/'source_files'/f.name) for f in files)+'\n'
        script+='hierarchy -check -top ot_v41_rom_elem_w10 '+' '.join('-chparam '+k+' '+str(v) for k,v in allparams.items())+'\n'
        script+='proc\nflatten\n'
        script+='select -set local_wake ot_v41_rom_elem_w10/w:g_wake.g_leaf*.wake %ci1 ot_v41_rom_elem_w10/t:$adff %i\n'
        script+='select -assert-count 8 @local_wake\n'
        script+='setattr -set keep 1 -set dont_touch 1 @local_wake\nselect -clear\n'
        script+='write_json '+str(jobdir/'wake_before_opt.json')+'\n'
        script+='synth -top ot_v41_rom_elem_w10 -flatten\n'
        script+='dfflibmap -liberty '+str(joblib)+'\nabc -liberty '+str(joblib)+'\nclean\n'
        script+='check\nstat -liberty '+str(joblib)+'\nwrite_verilog -noattr '+str(jobdir/'mapped.v')+'\nwrite_json '+str(jobdir/'mapped.json')+'\n'
        ys=d/'map.ys';ys.write_text(script)
        entry=dict(case=case,parameters=allparams,started_UTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),script_sha256=sha(ys),log=str(d/'map.log'))
        record['runs'].append(entry)
        if backend=='pinned-orfs':subprocess.run(['docker','cp',str(d),container+':'+str(jobroot)],check=True)
        with (d/'map.log').open('x') as log:
            p=subprocess.Popen(command+['-s',str(jobdir/'map.ys')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=os.environ|{'OMP_NUM_THREADS':'1'})
            entry['yosys_PID']=p.pid;save(work/'record.json',record);entry['returncode']=p.wait()
        if backend=='pinned-orfs':subprocess.run(['docker','cp',container+':'+str(jobdir)+'/.',str(d)],check=True)
        entry['finished_UTC']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());entry['log_sha256']=sha(d/'map.log')
        if entry['returncode']:
            record['status']='FIRST_MAPPING_FAILURE_PRESERVED';save(work/'record.json',record);return 1
        entry['mapped_verilog_sha256']=sha(d/'mapped.v');entry['mapped_json_sha256']=sha(d/'mapped.json')
        entry['inventory']={c:inventory(d/'mapped.json',cells,c) for c,cells in [('ss',sscells),('ff',ffcells)]}
        entry['WAKE_cell_retention']=wake_cells(d/'mapped.json')
        if entry['inventory']['ss']['raw_4096_macro_count']!=4 or entry['inventory']['ss']['unmapped_nonmacro_types']:
            record['status']='MAPPED_INVENTORY_REJECTED_PRESERVED';save(work/'record.json',record);return 1
        save(work/'record.json',record)
    record['status']='MAPPED_COMPLETE_ELEMENTS_CONTEXT_OPEN'
    record['flow']='proc; flatten; select exactly 8 WAKE $adff Q drivers; keep=1/dont_touch=1 cells; unchanged synth/dfflibmap/abc'
    record['prior_failed_mapping_commit']='a91078135ddaeedbb76be3535ab91b849fbf9ad4'
    record['engine_sources_changed']=False
    record['WAKE_replica_retention_pass']=all(r['inventory']['ss']['source_8leaf_WAKE_replica_retention_pass'] for r in record['runs'])
    record['physical_G0_admitted']=False
    if not record['WAKE_replica_retention_pass'] or not all(r['WAKE_cell_retention']['passed'] for r in record['runs']):
        record['status']='WAKE_CELL_RETENTION_FAILURE_PRESERVED';save(work/'record.json',record);return 1
    record['selected_case']=only_case
    save(work/'record.json',record);return 0

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);p.add_argument('--backend',choices=['local','pinned-orfs'],default='local');p.add_argument('--reuse-q',type=Path);p.add_argument('--only-case',choices=['q','bfcolumn']);a=p.parse_args();raise SystemExit(run(a.work,a.backend,a.reuse_q,a.only_case))
