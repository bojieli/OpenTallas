#!/usr/bin/env python3
"""Map exactly the source-selected capture object; no new engine RTL or VM model."""
import argparse,hashlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
SOURCE='rtl/dsrom_sys/rd64_capture/ot_dsrom_rd64_vm_capture.sv'
PARAMS={'ENABLE':1,'ROOTS':128,'CAPACITY':1,'VM_AW':19,'VM_ALWAYS_ACCEPT':1}
LIBS=['SEQ_RVT_TT_nldm_220123','INVBUF_RVT_TT_nldm_220122','SIMPLE_RVT_TT_nldm_211120']

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check_source():
    selection=json.loads((ROOT/'rtl/dsrom_sys/s81_capture_parent/selection.json').read_text())
    if selection['parameters']['ROM_R']!=128 or selection['parameters']['ROM_PHW']!=10 or selection['parameters']['S81_CAPTURE']!=1:raise ValueError('not selected S81 parent')
    if selection['source_sha256'][SOURCE]!=sha(ROOT/SOURCE):raise ValueError('capture changed from actual parent')
    model=json.loads((ROOT/'results/uarch/dsrom_s81_rd64_capture_20261004/rtl_preparation_model.json').read_text())
    if model['ROOTS']!=128 or model['CAPACITY']!=1 or model['raw_bits_all_roots']!=16527:raise ValueError('capture model dimensions changed')
    return selection,model

def script(libs):
    args=' '.join('-G '+k+'='+str(v) for k,v in PARAMS.items())
    return '\n'.join(['read_liberty -lib '+str(p) for p in libs]+[
        'read_slang --top ot_dsrom_rd64_vm_capture '+args+' '+str(ROOT/SOURCE),
        'synth -top ot_dsrom_rd64_vm_capture -flatten -noabc',
        'dfflibmap -liberty '+str(libs[0]),'abc -g NAND',
        'techmap -map '+str(HERE/'native_map.v'),'clean','check -assert',
        'write_json mapped.json','write_verilog -noattr mapped.v','stat'])+'\n'

def run(out,pdk):
    selection,model=check_source();out.mkdir(parents=True,exist_ok=False)
    libs=[pdk/('asap7sc7p5t_'+n+'.lib') for n in LIBS]
    for p in libs:
        if not p.is_file():raise ValueError('missing actual library '+str(p))
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    pins={str(ROOT/SOURCE):sha(ROOT/SOURCE),str(HERE/'native_map.v'):sha(HERE/'native_map.v')}
    pins.update({str(p):sha(p) for p in libs})
    identity=subprocess.check_output(['yosys','-V'],text=True).strip()
    prep={'source_commit':commit,'source_parent_commit':'57e3f45e3473e9e36b052f558a3b65ab71b1d6d1','parameters':PARAMS,
          'source_sha256':pins,'tool':identity,'raw_model_bits':model['raw_bits_all_roots'],
          'scope':'Full selected capture object including address arithmetic/formatting/quotas; native VM grant cone excluded, not free',
          'new_RTL':False,'PnR':False,'corner':'TT AREA ONLY; no SSFF/timing or physical admission',
          'retained_parent_VM_physical_ports_proven':False,'new_latency_edges':0,
          'body_addition_requires_disjoint_containment':True}
    (out/'preparation.json').write_text(json.dumps(prep,sort_keys=True,indent=2)+'\n')
    (out/'map.ys').write_text(script(libs));start=time.time()
    with (out/'mapped.log').open('w') as log:
        proc=subprocess.Popen(['yosys','-m','slang','-s','map.ys'],cwd=out,stdout=log,stderr=subprocess.STDOUT)
        (out/'process.json').write_text(json.dumps({'yosys_PID':proc.pid,'started_unix':start})+'\n');rc=proc.wait()
    terminal={'exit_code':rc,'elapsed_s':time.time()-start,'source_commit':commit,'source_unchanged':all(sha(p)==h for p,h in pins.items()),'physical_admission':False}
    if rc==0:
        net=json.loads((out/'mapped.json').read_text())['modules']['ot_dsrom_rd64_vm_capture']
        from collections import Counter
        counts=Counter(c['type'] for c in net['cells'].values())
        terminal['actual_cell_census']=dict(sorted(counts.items()));terminal['actual_cells']=sum(counts.values())
        terminal['actual_FF_cells']=sum(v for k,v in counts.items() if k.startswith('DFF'))
        terminal['ports']={k:dict(direction=v['direction'],bits=len(v['bits'])) for k,v in net['ports'].items()}
        terminal['unmapped_cells']=[k for k in counts if k.startswith('$')]
        if terminal['unmapped_cells']:terminal['exit_code']=1
    terminal['artifacts_sha256']={p.name:sha(p) for p in out.iterdir() if p.is_file()}
    (out/'terminal.json').write_text(json.dumps(terminal,sort_keys=True,indent=2)+'\n')
    print(json.dumps(terminal,sort_keys=True));return terminal['exit_code']

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);ap.add_argument('--lib-dir',type=Path,default=Path.home()/'.local/opentallas-pdk-asap7/lib/NLDM');a=ap.parse_args()
    raise SystemExit(run(a.out,a.lib_dir))
