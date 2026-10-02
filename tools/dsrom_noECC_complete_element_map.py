#!/usr/bin/env python3
"""Map complete literal q/BF sources once; no timing/physical/adoption claim."""
import argparse
import json
import os
import subprocess
import time
import gzip
import re
from pathlib import Path
from dsrom_noECC_complete_element import BASE,ROOT,sha,build
from dsrom_secded_fullwidth_characterize import merged,block

def save(path,value):
    tmp=path.with_suffix('.new');tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');tmp.replace(path)

def inventory(path,cells,corner):
    net=json.loads(path.read_text())['modules']['ot_v41_rom_elem_w10']
    clocks={};area=0;unmapped={};counts={};captures=0
    for name,c in net['cells'].items():
        typ=c['type'];counts[typ]=counts.get(typ,0)+1
        if typ not in cells:
            if typ!='ot_rom_4096x274_m8':unmapped[typ]=unmapped.get(typ,0)+1
            continue
        cell=cells[typ];area+=float(re.search(r'\barea\s*:\s*([\d.]+)',cell)[1])
        for p,bits in c['connections'].items():
            match=re.search(r'\bpin\s*\('+re.escape(p)+r'\)',cell)
            if not match:continue
            body=block(cell,match.start())
            if not re.search(r'\bclock\s*:\s*true',body):continue
            cap=float(re.search(r'\bcapacitance\s*:\s*([\d.]+)',body)[1])
            for bit in bits:
                item=clocks.setdefault(str(bit),dict(sinks=0,pin_cap_fF=0,masters={},names=[]))
                item['sinks']+=1;item['pin_cap_fF']+=cap;item['masters'][typ]=item['masters'].get(typ,0)+1;item['names'].append(name)
    for bit,item in clocks.items():
        item['net_aliases']=[n for n,v in net['netnames'].items() if int(bit) in v['bits']]
    for c in net['cells'].values():
        if c['type'].startswith('DFF'):
            qb=c['connections'].get('QN',c['connections'].get('Q',[]))
            if any(set(qb)&set(v['bits']) for n,v in net['netnames'].items() if '.cap0' in n or '.cap1' in n):captures+=1
    return dict(corner=corner,cells=sum(counts.values()),master_counts=counts,stdcell_area_um2=area,
        raw_4096_macro_count=counts.get('ot_rom_4096x274_m8',0),unmapped_nonmacro_types=unmapped,
        clock_nets=clocks,capture_flops_identified= captures,
        scope='Mappedcell pin sums; no wires, CTS buffers/skew, clockgating/minpulse, or routed timing qualification.')

def run(work):
    if work.exists():raise ValueError('preserve existing attempt; no overwrite/retry')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip():raise ValueError('clean pinned source required')
    model=build();manifest=json.loads((BASE/'physical_source_manifest.json').read_text())
    work.mkdir(parents=True)
    record=dict(status='RUNNING',pid=os.getpid(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_manifest_sha256=sha(BASE/'physical_source_manifest.json'),model_sha256=sha(BASE/'model.json'),runner_sha256=sha(Path(__file__)),
        versions={'yosys':subprocess.check_output(['yosys','-V'],text=True).strip()},
        host_headroom={'free_m':subprocess.check_output(['free','-m'],text=True),'df_Pm':subprocess.check_output(['df','-Pm',str(work)],text=True),'uptime':subprocess.check_output(['uptime'],text=True)},
        fixed_clocks_GHz=1.2,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
        synthesis_mapping_only=True,physical_PR=False,source_changes=False,
        reuse='Current21-file manifest has no mapped receipt in the retained source/model artifacts; earlierfullcorrector/checker and historicalelement maps are different cones/sources, not reused as this element.',runs=[])
    save(work/'record.json',record)
    _,sscells=merged('ss');_,ffcells=merged('ff')
    text,_=merged('ss');lib=work/'stock_ss.lib';lib.write_text(text)
    record['library_sha256']=sha(lib);save(work/'record.json',record)
    for case,params in manifest['variants'].items():
        d=work/case;d.mkdir();allparams=manifest['params_common']|params
        files=[BASE/'inputs'/f['copy'] for f in manifest['files']]
        script='read_liberty -lib '+str(lib)+'\n'
        script+='read_verilog -sv -DSYNTHESIS '+' '.join(map(str,files))+'\n'
        script+='hierarchy -check -top ot_v41_rom_elem_w10 '+' '.join('-chparam '+k+' '+str(v) for k,v in allparams.items())+'\n'
        script+='synth -top ot_v41_rom_elem_w10 -flatten\n'
        script+='dfflibmap -liberty '+str(lib)+'\nabc -liberty '+str(lib)+'\nclean\n'
        script+='check\nstat -liberty '+str(lib)+'\nwrite_verilog -noattr '+str(d/'mapped.v')+'\nwrite_json '+str(d/'mapped.json')+'\n'
        ys=d/'map.ys';ys.write_text(script)
        entry=dict(case=case,parameters=allparams,started_UTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),script_sha256=sha(ys),log=str(d/'map.log'))
        record['runs'].append(entry)
        with (d/'map.log').open('x') as log:
            p=subprocess.Popen(['yosys','-s',str(ys)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=os.environ|{'OMP_NUM_THREADS':'1'})
            entry['yosys_PID']=p.pid;save(work/'record.json',record);entry['returncode']=p.wait()
        entry['finished_UTC']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());entry['log_sha256']=sha(d/'map.log')
        if entry['returncode']:
            record['status']='FIRST_MAPPING_FAILURE_PRESERVED';save(work/'record.json',record);return 1
        entry['mapped_verilog_sha256']=sha(d/'mapped.v');entry['mapped_json_sha256']=sha(d/'mapped.json')
        entry['inventory']={c:inventory(d/'mapped.json',cells,c) for c,cells in [('ss',sscells),('ff',ffcells)]}
        if entry['inventory']['ss']['raw_4096_macro_count']!=4 or entry['inventory']['ss']['unmapped_nonmacro_types']:
            record['status']='MAPPED_INVENTORY_REJECTED_PRESERVED';save(work/'record.json',record);return 1
        save(work/'record.json',record)
    record['status']='MAPPED_COMPLETE_ELEMENTS_CONTEXT_OPEN';save(work/'record.json',record);return 0

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);a=p.parse_args();raise SystemExit(run(a.work))
