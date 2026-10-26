#!/usr/bin/env python3
"""Full-shape QNT control-copy exactness gate against immutable 69c124e5d RTL.

Run on an admitted fleet host with ot-heavy; no full-SU duplication. The reference
and candidate are extracted from commits, never from working-tree RTL. Metadata
retains commands, hashes, full output logs and measured resource consumption.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

RTL = 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_qn.sv'
REF = '69c124e5d'
MARK = '// ---------------------------------------------------------------------------------------------------------------------\n// NORM ENGINE:'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def extract(repo, commit):
    data = subprocess.check_output(['git', 'show', f'{commit}:{RTL}'], cwd=repo)
    return data, data.split(MARK.encode(), 1)[0]

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate-commit', required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--pinned-sources-dir', type=Path, help='minimal git-show export with immutable source binding')
    args = ap.parse_args()
    repo = Path(__file__).resolve().parents[2]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    if args.pinned_sources_dir:
        src = args.pinned_sources_dir
        export = json.loads((src/'export_binding.json').read_text())
        cand_commit, ref_commit = export['candidate_commit'], export['reference_commit']
        if not cand_commit.startswith(args.candidate_commit) or not ref_commit.startswith(REF):
            raise RuntimeError('export commit mismatch')
        cand_full = (src/'candidate_full.sv').read_bytes()
        ref_full = (src/'reference_full.sv').read_bytes()
        if sha(cand_full) != export['candidate_full_sha256'] or sha(ref_full) != export['reference_full_sha256']:
            raise RuntimeError('export source hash mismatch')
        cand = cand_full.split(MARK.encode(), 1)[0]
        ref = ref_full.split(MARK.encode(), 1)[0]
    else:
        cand_commit = subprocess.check_output(['git', 'rev-parse', args.candidate_commit], cwd=repo, text=True).strip()
        ref_commit = subprocess.check_output(['git', 'rev-parse', REF], cwd=repo, text=True).strip()
        cand_full, cand = extract(repo, cand_commit)
        ref_full, ref = extract(repo, ref_commit)
    renamed = ref.replace(b'ot_s81_su_qnt', b'ot_s81_su_qnt_reference').replace(b'ot_s81_su_qn_keep_ff', b'ot_s81_su_qn_keep_ff_reference')
    checked_ref = (repo/'tests/rtl/s81su_qnt_cb/reference_69c124e5d.sv').read_bytes()
    if checked_ref != renamed:
        raise RuntimeError('checked-in reference differs from immutable extraction plus module rename')
    cand_path = out/'candidate_qnt.sv'
    ref_path = out/'reference_qnt.sv'
    tb_path = out/'tb_qnt_cb.sv'
    cand_path.write_bytes(cand)
    ref_path.write_bytes(renamed)
    tb_path.write_bytes((repo/'tests/rtl/s81su_qnt_cb/tb_qnt_cb.sv').read_bytes())
    binding = dict(candidate_commit=cand_commit, reference_commit=ref_commit, source_path=RTL,
                   candidate_full_sha256=sha(cand_full), reference_full_sha256=sha(ref_full),
                   candidate_component_sha256=sha(cand), reference_original_component_sha256=sha(ref),
                   reference_renamed_component_sha256=sha(renamed), bench_sha256=sha(tb_path.read_bytes()),
                   runner_sha256=sha(Path(__file__).read_bytes()), shape=dict(N=256,S_RD=16,NFI=33),
                   variants=[256,32,16], comparison='all 4305 output bits each cycle; no payload masking',
                   host=subprocess.check_output(['hostname'],text=True).strip(), started_epoch=time.time())
    (out/'source_binding.json').write_text(json.dumps(binding,indent=2)+'\n')
    verdicts=[]
    for mutant in [0,6]:
        run = out/f'm{mutant}'
        run.mkdir()
        obj = run/'obj'
        command=['verilator','--binary','--timing','-j','4','-Wno-fatal','--top-module','tb_qnt_cb',
                 f'-GMUT={mutant}','--Mdir',str(obj),'--output-split','20000','--output-split-cfuncs','200',
                 str(ref_path),str(cand_path),str(tb_path)]
        (run/'command.json').write_text(json.dumps(dict(build=command,run=[str(obj/'Vtb_qnt_cb')]),indent=2)+'\n')
        with (run/'build.log').open('w') as log:
            build=subprocess.run(['/usr/bin/time','-v',*command],stdout=log,stderr=subprocess.STDOUT)
        if build.returncode:
            verdict=dict(mutant=mutant,build_exit=build.returncode,verdict='BUILD_FAIL')
            (run/'terminal.json').write_text(json.dumps(verdict,indent=2)+'\n')
            raise RuntimeError(f'build failed: {run}')
        with (run/'run.log').open('w') as log:
            sim=subprocess.run(['/usr/bin/time','-v',str(obj/'Vtb_qnt_cb')],stdout=log,stderr=subprocess.STDOUT)
        text=(run/'run.log').read_text()
        expected=(mutant==0 and sim.returncode==0 and 'PASS QNT_CB' in text) or (mutant==6 and sim.returncode!=0 and 'FAIL QNT_CB active_data=1' in text)
        verdict=dict(mutant=mutant,build_exit=0,run_exit=sim.returncode,verdict='PASS' if expected else 'UNEXPECTED_RESULT',
                     negative_control=(mutant==6),summary=next((line for line in text.splitlines() if 'active_data=1' in line), next((line for line in text.splitlines() if 'QNT_CB' in line),'')))
        if mutant==0:
            verdict['counts']={key:int(value) for key,value in re.findall(r'(cycles|checks|jobs|starts|resets|valid_rows|valid_cycles|parameter_pulses|fault_cycles|empty|full|uneven|added_cycles)=(\d+)',text)}
        (run/'terminal.json').write_text(json.dumps(verdict,indent=2)+'\n')
        verdicts.append(verdict)
        print(json.dumps(verdict),flush=True)
        if not expected:
            raise RuntimeError('unexpected gate result')
    (out/'terminal.json').write_text(json.dumps(dict(verdict='PASS',added_cycles=0,results=verdicts,completed_epoch=time.time()),indent=2)+'\n')

if __name__=='__main__':
    main()
