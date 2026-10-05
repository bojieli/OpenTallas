#!/usr/bin/env python3
"""One retained P1 L20 paired case with PQ+PACK+XMAP; bit repack only."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import dshbm_w2_pair_seq as E
import hbm_accel_activation_layout as X

ROOT=Path(__file__).resolve().parents[1]
TB='tb_hbm_opt_integrated_pq_pack_xmap'
SRC=list(dict.fromkeys([p for p in E.SRC if not p.startswith('rtl/test/')]+[
    'rtl/test/hbm_opt_integrated_20261005/'+TB+'.sv']))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def execute(job,old):
    job.mkdir(parents=True,exist_ok=True)
    case=job/'case';case.mkdir(exist_ok=False)
    receipt=json.loads((old/'fixture.json').read_text())
    assert receipt['original_shape_count']==31 and len(receipt['composite_descriptors'])==28
    assert (old/'seq.hex').read_text().split()==[f'{x:08x}' for d in receipt['composite_descriptors'] for x in d]
    words=[int(x,16) for x in (old/'x.hex').read_text().split()]
    cursor=0;packed=[];layout=[]
    for op,d in enumerate(receipt['composite_descriptors']):
        count=(d[7] if d[6] else 0)+(d[13] if d[10] else 0)
        assert cursor+count<=len(words)
        groups=X.beat_groups(d[3],1,nc=8)
        assert groups==([0,4] if d[3]==2 else [0])
        packed.extend(X.pack_fragment(x,d[3],1,nc=8) for x in words[cursor:cursor+count])
        cursor+=count
        layout.append(dict(op=op,original_ids=receipt['logical_op_labels'][op],groups=groups,addresses=count,expected_beats=count*len(groups)))
    assert cursor==len(words)
    for name in ('seq.hex','lines.hex','reference_out.txt','fixture.json'):shutil.copy2(old/name,case/name)
    width=(8*X.XC+2048+3)//4
    (case/'x.hex').write_text(''.join(f'{v:0{width}x}\n' for v in packed))
    inputs={n:sha(old/n) for n in ('seq.hex','lines.hex','x.hex','reference_out.txt','fixture.json')}
    source_pins={p:sha(ROOT/p) for p in SRC}
    (job/'source_pins.json').write_text(json.dumps(source_pins,indent=2)+'\n')
    (job/'layout.json').write_text(json.dumps(dict(original_inputs=inputs,ops=layout,active_columns=1,flags=dict(ENABLE=1,PQ_ENABLE=1,PACK_W2=1,XMAP=1),packer_sha256=sha(Path(X.__file__)),generated_numeric_inputs=False),indent=2)+'\n')
    build=job/'build';build.mkdir(exist_ok=False);exe=build/('V'+TB)
    argv=['verilator','--binary','--timing','-O2','-Wno-fatal','--top-module',TB,'--Mdir',str(build),'-j','16','-GNC=8','-GXDEPTH=128','-GRMAX=256','-GLEV=4','-GXB=2','-GXMAP=1',*[str(ROOT/p) for p in SRC]]
    (job/'command.json').write_text(json.dumps(argv,indent=2)+'\n')
    with (build/'build.log').open('w') as log:rc=subprocess.run(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
    (build/'build.exit').write_text(str(rc)+'\n')
    if rc:return rc
    (job/'executable_identity.json').write_text(json.dumps(dict(path=str(exe),sha256=sha(exe)),indent=2)+'\n')
    rc=E.run(exe,case)
    r=json.loads((case/'result.json').read_text());_,meta,_=E.parse_output(case/'out.txt')
    beats=[dict(**d,actual_beats=meta.get(d['op'],{}).get('xload_beats')) for d in layout]
    exact_beats=all(d['actual_beats']==d['expected_beats'] for d in beats)
    stable=all(sha(ROOT/p)==h for p,h in source_pins.items())
    baseline_path=ROOT/'results/rtl/hbm_opt_integrated_20261005/joint_p1_r2/summary.json'
    b=json.loads(baseline_path.read_text());base=next(c['total_cycles'] for c in b['cases'] if c['name']=='ar_l20')
    result=dict(r,accepted=rc==0 and exact_beats and stable,beat_counts_exact=exact_beats,activation_loads=beats,source_stable=stable,source_pins=source_pins,flags=dict(ENABLE=1,PQ_ENABLE=1,PACK_W2=1,XMAP=1),baseline_PQ_XMAP_total_cycles=base,baseline_PQ_XMAP_receipt_sha256=sha(baseline_path),joint_total_cycle_saving=base-r['total_cycles'] if r['total_cycles'] is not None else None,full_token_measured=False,physical_ss_ff_qualified=False,clock_scope='1ns component simulation only; SS60/FF25 target not admitted',original_inputs=inputs)
    (job/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('accepted','actual_output_rows','total_cycles','paired_w2_cycles','beat_counts_exact','joint_total_cycle_saving')}))
    return 0 if result['accepted'] else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--job',type=Path,required=True);p.add_argument('--paired-case',type=Path,required=True);a=p.parse_args()
    raise SystemExit(execute(a.job.resolve(),a.paired_case.resolve()))
