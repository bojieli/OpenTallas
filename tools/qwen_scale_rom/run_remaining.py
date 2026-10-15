#!/usr/bin/env python3
"""Reuse the actual full384macro executable for ranks1..7 and fault controls."""
from pathlib import Path
import argparse,concurrent.futures,hashlib,json,os,subprocess


def main():
    p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);p.add_argument('--images',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(exist_ok=False,parents=True)
    def run_case(name,masks,expected,expect):
        command=[str(a.binary),f'+OT_ROM_DIR={masks}',f'+EXPECTED={expected}']
        result=subprocess.run(command,capture_output=True,text=True)
        log=result.stdout+result.stderr;(a.out/f'{name}.log').write_text(log)
        okay=(result.returncode==0 and 'PASS released_scale_masks' in log) if expect=='pass' else ('FAIL released_scale_masks' in log if expect=='mismatch' else result.returncode!=0 and 'missing actual slab ROM mask' in log)
        print(('PASS' if okay else 'FAIL'),name,'rc',result.returncode,'expected',expect,flush=True)
        return dict(name=name,passed=okay,simulator_returncode=result.returncode,expected_verdict=expect,
                    command=command,log_sha256=hashlib.sha256(log.encode()).hexdigest())
    cases=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(run_case,f'rank{rank}',a.images/f'rank{rank}/masks',a.images/f'rank{rank}/expected_scale_words.hex','pass') for rank in range(1,8)]
        cases.extend(f.result() for f in futures)
    selected='qslab_b2_h1_g3_c0_b0.viamap.hex'
    source=a.images/'rank0/masks'
    for kind in ['bitflip','missing_mask']:
        masks=a.out/kind;masks.mkdir()
        for path in source.glob('qslab_*.viamap.hex'):os.link(path,masks/path.name)
        target=masks/selected;payload=target.read_text();target.unlink()
        if kind=='bitflip':
            rows=payload.splitlines();rows[0]=f'{int(rows[0],16)^1:0532x}';target.write_text('\n'.join(rows)+'\n')
        cases.append(run_case(kind,masks,a.images/'rank0/expected_scale_words.hex','mismatch' if kind=='bitflip' else 'missing'))
    record=dict(schema='opentallas.qwen-scale-native-runtime.v1',binary_sha256=hashlib.sha256(a.binary.read_bytes()).hexdigest(),
                actual_ROM_instances=384,full_shape_words=30576,group_response_cycles=7,cases=cases,
                released_manifest_sha256=hashlib.sha256((a.images/'manifest.json').read_bytes()).hexdigest(),
                all_passed=all(c['passed'] for c in cases),native_token_qualified=False)
    (a.out/'report.json').write_text(json.dumps(record,indent=2)+'\n')
    if not record['all_passed']:raise SystemExit(1)

if __name__=='__main__':main()
