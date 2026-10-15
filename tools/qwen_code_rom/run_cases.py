#!/usr/bin/env python3
"""Check every released tile/bank cohort on the identical actual hardened pair.

The minimum physical circuit is reused, not replaced: case masks are exact
hash-checked aliases of the real native instance payloads. Native full-die
ROM_TILE identity/strap binding remains a separate required composition gate.
"""
from pathlib import Path
import argparse,concurrent.futures,gzip,hashlib,json,os,subprocess,tempfile,time


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);p.add_argument('--images',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--workers',type=int,default=16);p.add_argument('--ranks',default='0,1,2,3,4,5,6,7')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);scratch=a.out/'case_cohorts';scratch.mkdir()
    root=json.loads((a.images/'manifest.json').read_text());cases=[]
    wanted={int(x) for x in a.ranks.split(',')}
    for rr in root['rank_manifests']:
        if rr['rank'] not in wanted:continue
        path=Path(rr['manifest'])
        if sha(path)!=rr['manifest_sha256']:raise ValueError('immutable rank manifest changed')
        manifest=json.loads(path.read_text())
        for pair in manifest['pairs']:cases.append((rr['rank'],pair))
    lookup=a.images/'int8_bf16_observer.hex';started=time.time()
    def run_case(item,mutant=None):
        rank,pair=item
        expected=a.images/f'rank{rank}/expected'/pair['expected_file']
        if sha(expected)!=pair['expected_sha256']:raise ValueError('observer case payload drift')
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            d=Path(directory)
            ids=[]
            for col in pair['columns']:
                original=a.images/f'rank{rank}/masks'/col['file']
                if sha(original)!=col['sha256']:raise ValueError('actual native ROM mask changed')
                alias=d/f"qtile_t0_b0_c{col['native_column']}.viamap.hex"
                os.link(original,alias);ids.append(col['instance'])
            if mutant:
                path=d/'qtile_t0_b0_c0.viamap.hex';payload=path.read_text();path.unlink()
                if mutant=='bitflip':
                    rows=payload.splitlines();rows[0]=f'{int(rows[0],16)^1:0532x}';path.write_text('\n'.join(rows)+'\n')
            result=subprocess.run([str(a.binary),f'+OT_ROM_DIR={d}',f'+EXPECTED={expected}',f'+LOOKUP={lookup}'],capture_output=True,text=True)
            log=result.stdout+result.stderr
            if mutant=='bitflip':okay='FAIL released_code_pair' in log
            elif mutant=='missing_mask':okay=result.returncode!=0 and 'missing native tile ROM mask' in log
            else:okay=result.returncode==0 and 'PASS released_code_pair checked4100' in log
            return dict(rank=rank,tile=pair['tile'],bank=pair['bank'],actual_native_instance_ids=ids,
                        expected_sha256=pair['expected_sha256'],macro_sha256=[c['sha256'] for c in pair['columns']],
                        compiled_minimum_circuit_instance_ids=['qtile_t0_b0_c0','qtile_t0_b0_c1'],
                        mutant=mutant,passed=okay,returncode=result.returncode,simulator_log=log)
    failed=[];completed=0
    with gzip.open(a.out/'cases.jsonl.gz','wt',compresslevel=6) as receipts:
        with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
            futures=[pool.submit(run_case,case) for case in cases]
            for future in concurrent.futures.as_completed(futures):
                record=future.result();receipts.write(json.dumps(record,separators=(',',':'))+'\n');completed+=1
                if not record['passed']:failed.append(record)
                if completed%256==0 or completed==len(cases):
                    progress=dict(completed=completed,total=len(cases),failures=len(failed),elapsed_seconds=time.time()-started)
                    (a.out/'progress.json').write_text(json.dumps(progress)+'\n');print('CODE_PAIR_PROGRESS',json.dumps(progress),flush=True)
    mutants=[]
    for kind in ['bitflip','missing_mask']:
        record=run_case(cases[0],kind);mutants.append(record)
        (a.out/f'{kind}.log').write_text(record['simulator_log'])
    report=dict(schema='opentallas.qwen-tp8-code-pair-cohort-proof.v1',binary_sha256=sha(a.binary),
                native_image_manifest_sha256=sha(a.images/'manifest.json'),minimum_circuit='ot_qwen_tile_rpair actual two-ROM physical leaf',
                ranks=sorted(wanted),cohorts=completed,actual_native_macro_payloads=2*completed,words_per_pair=4096,
                masked_tail_slots_per_pair=4,fixed_response_cycles=7,failures=failed,mutants=mutants,
                all_passed=not failed and all(m['passed'] for m in mutants),elapsed_seconds=time.time()-started,
                native_full_layer_or_die_qualified=False,
                remaining=['generated die must bind every ROM_TILE constant to matching hardware tile_id strap',
                           'native command/operand/result composition and physical qualification'])
    (a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS_CODE_COHORTS' if report['all_passed'] else 'FAIL_CODE_COHORTS',completed,flush=True)
    if not report['all_passed']:raise SystemExit(1)

if __name__=='__main__':main()
