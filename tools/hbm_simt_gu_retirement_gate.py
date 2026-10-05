#!/usr/bin/env python3
"""Selected-SIMT exporter gate, retained actual FP32 input, comparator-only golden.

Run --prepare locally (no build), then --run on admitted compute. This proves
only the real conversion/retirement/LSU boundary, not a live GU producer chain.
"""
import argparse,ast,hashlib,json,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOP='tb_hbm_accel_gu_retirement'

def sources():
    tree=ast.parse((ROOT/'tools/gpu_sys/run_system.py').read_text())
    deps=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
              and any(isinstance(t,ast.Name) and t.id=='DEP_SRC' for t in n.targets))
    return list(dict.fromkeys(['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
       'rtl/hbm_accel/collective/ot_hbm_accel_gu_metadata.sv','rtl/gpu_sys/ot_gpu_simt_lane.sv','rtl/gpu_sys/ot_gpu_simt_divlane.sv',
       'rtl/gpu_sys/ot_gpu_bd_line.sv','rtl/hbm_accel/collective/ot_hbm_accel_simt_sm.sv']+deps+
       ['rtl/test/hbm_accel/'+TOP+'.sv']))

def prepare(out):
    import numpy as np
    import hdc_golden as G
    base=ROOT/'results/rtl/dshbm_expert_workgroup_20261005/runtime_r2_PASS'
    rec=json.loads((base/'L20_record.json').read_text())
    if rec['status']!='PASS_ACTUAL_SOURCE_ROUTED_GU_ALL_ROWS' or rec['router_ids'][:2]!=[41,65]:
        raise ValueError('Actual source-selected expert identity missing')
    vals=[];descs=[];seen=set()
    with tarfile.open(base/'actual_results.tar.gz') as archive:
        for c in rec['cases']:
            if c['expert'] not in (41,65):continue
            if not c['exact'] or c['exit'] or c['mismatches']:raise ValueError('Failed actual GU span')
            a,b=c['rows']; assert b-a==12
            path=f"L20/die{c['die']:02}_sm{c['sm']:02}/out.txt"
            rows={}
            for line in archive.extractfile(path).read().decode().splitlines():
                if line.startswith('#'):continue
                op,row,value=line.split()
                if int(op)==0:rows[int(row)]=int(value,16)&0xffffffff
            if set(rows)!=set(range(12)):raise ValueError('Incomplete cold native GU rows')
            for row in range(a,b):
                key=c['expert'],c['matrix'],row
                if key in seen:raise ValueError('Duplicate source row')
                seen.add(key);vals.append(rows[row-a])
            descs.extend([c['expert'],int(c['matrix']=='w3'),a,c['sm'],c['die']])
    assert len(seen)==9216 and len(descs)==3840
    out.mkdir(parents=True,exist_ok=False)
    # expected[] never enters driver stimulus, descriptors, payload or store.
    expected=G.bits(G.to_bf16(G.from_bits(np.asarray(vals,dtype=np.uint32))))
    for name,data in [('actual.hex',vals),('expected.hex',expected),('descriptors.hex',descs)]:
        (out/name).write_text(''.join(f'{int(x):08x}\n' for x in data))
    (out/'input_source.json').write_text(json.dumps(dict(scope='retained real native GU FP32, cold op0; golden BF16 comparator only',
        live_full_chain=False,source_record_sha256=hashlib.sha256((base/'L20_record.json').read_bytes()).hexdigest(),
        archive_sha256=hashlib.sha256((base/'actual_results.tar.gz').read_bytes()).hexdigest(),
        rows=9216,spans=768,experts=[41,65],files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.hex')}),indent=2)+'\n')

def run(work):
    # Icarus is sufficient for this real minimum SIMT component; no wholeloader,
    # matrix arithmetic variant or downstream SwiGLU numerical build occurs.
    pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources()}
    (work/'source_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
    for enabled in (1,0):
        log=work/f'build_{enabled}.log'
        cmd=['iverilog','-g2012','-s',TOP,'-P'+TOP+'.EXPORT='+str(enabled),'-o',str(work/f'gate_{enabled}.vvp')]+(['-DGU_METADATA_FAULTS'] if enabled else [])+[str(ROOT/p) for p in sources()]
        with log.open('w') as f:rc=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
        if rc:return rc
        with (work/f'run_{enabled}.log').open('w') as f:
            rc=subprocess.run(['vvp',str(work/f'gate_{enabled}.vvp')],cwd=work,stdout=f,stderr=subprocess.STDOUT).returncode
        if rc:return rc
    return 0

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',type=Path);p.add_argument('--run',type=Path);a=p.parse_args()
    if a.prepare:prepare(a.prepare.resolve())
    if a.run:raise SystemExit(run(a.run.resolve()))
