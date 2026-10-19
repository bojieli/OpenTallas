#!/usr/bin/env python3
"""Package collected source-pinned MU regression evidence, preserving pending legs."""
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

BASE = Path('/home/ubuntu/scratch/refill-0730/MUQWREG')
COL = BASE / 'collected'
DEST = Path('/home/ubuntu/wt/refill-muqwreg-1019/results/rtl/mu_qwen_1018/merge_reg_0e6795834')
DEST.mkdir(parents=True, exist_ok=True)

def contents(p):
    return p.read_text(errors='replace') if p.exists() else ''

def targets(n):
    if n.startswith('amix_'):
        g = n[5:]
        root = COL / 'runs/amix/runs'
        if g.startswith('FACES'): names = ['FACES_mut0_nu' + g[5:]]
        elif g.startswith('F'): names = ['F' + g[1:] + '_nu1_ag']
        elif g.startswith('G'): names = ['F' + g[1:] + '_nu4_' + x for x in ['ag', 'm_s21', 'm_s22', 'n']]
        elif g.startswith('H'): names = ['F0_nu' + g[1:] + '_h']
        else: names = ['NEG_n_am7_f' + g[1:]]
        return [root / (x + '.out') for x in names]
    if n == 'sl_DHUSER':
        return sorted((COL / 'runs/adopt_slice/runs').glob('dhuser*.out'))
    if n.startswith('sl_'):
        return [COL / 'runs/adopt_slice/runs' / (n[3:] + '.out')]
    return [COL / 'out' / (n + '.out')]

def expectation(n):
    if n.startswith('amix_N') or n.startswith('sl_NEG') or n.startswith('sl_FACES_mut'):
        return 'FAIL with behavioral witness'
    if n.startswith('coll_'):
        return 'negative-control PASS, cases>0, expected FAIL witnessed' if n != 'coll_mu_bi' else 'PASS, cases>0'
    if n == 'host': return 'MU1 PASS; cm1-4/hm1-4/rm1-2 FAIL; 13 MU0 benches identical'
    if n in ('hroot','kv','ctlm_mu','ctlm_rest','ctlm_nsl12','opseg_mut','tok','head','sl_DHUSER'):
        return 'positives PASS; defined mutants FAIL; suite succeeds'
    return 'PASS'

rows=[]
for cp in sorted((BASE/'legs').glob('*.log')):
    n=cp.stem
    # r3 intentionally supersedes SIGTERM/143, which is never a mutant witness.
    active_cp=BASE/'legs_r3'/cp.name if n.startswith('sl_FACES_mut') else cp
    client=contents(active_cp)
    done=bool(re.search(r'RAN on .*exit \d+', client))
    exit_match=re.findall(r'RAN on .*exit (\d+)', client)
    sources=targets(n)
    texts=[contents(p) for p in sources]
    snippets=[]
    for p,t in zip(sources,texts):
        interesting=[x for x in t.splitlines() if re.search(r'PASS|FAIL|identical|# exit|overall rc|field map', x)]
        snippets.append(p.name+': '+ '; '.join(interesting[-2:]))
    expect=expectation(n)
    if not done:
        status='PENDING'
    elif exit_match[-1]!='0':
        status='UNEXPECTED job exit '+exit_match[-1]
    elif not all(texts):
        status='UNEXPECTED missing evidence'
    elif expect.startswith('FAIL'):
        status='AS EXPECTED' if all(re.search(r'(bench2 .*: FAIL|FACES MUT=.*: FAIL)',t) for t in texts) else 'UNEXPECTED no behavioral FAIL'
    elif n.startswith('coll_'):
        status='AS EXPECTED' if re.search(r'PASS cases=[1-9]\d*',texts[0]) else 'UNEXPECTED hollow/missing PASS'
    elif n.startswith(('amix_','sl_F0')):
        status='AS EXPECTED' if all('PASS' in t and 'FAIL' not in t and '# exit 0' in t for t in texts) else 'UNEXPECTED missing PASS'
    elif n=='sl_DHUSER':
        status='AS EXPECTED' if all(('FAIL' if 'mut' in p.name else 'PASS' if 'fieldmap' not in p.name else 'field map OK') in t for p,t in zip(sources,texts)) else 'UNEXPECTED DHUSER witness'
    elif n=='host':
        status='AS EXPECTED' if texts[0].count(' identical')==13 and 'DIFFERS' not in texts[0] else 'UNEXPECTED identity'
    else:
        status='AS EXPECTED' if ('PASS' in texts[0] and ('# exit 0' in texts[0] or 'overall rc=0' in texts[0])) else 'UNEXPECTED suite result'
    # Pending evidence can be stale r0 output; never export it as the current verdict.
    copied=[]
    if done:
        for p in sources:
            if p.exists():
                rel=p.relative_to(COL); out=DEST/'evidence'/rel
                out.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,out); copied.append(str(Path('evidence')/rel))
    client_out=DEST/'clients'/active_cp.relative_to(BASE)
    client_out.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(active_cp,client_out)
    rows.append(dict(leg=n,expect=expect,status=status,actual='; '.join(snippets) if done else 'Existing fleet job still active; no terminal behavioral verdict',evidence=copied,client=str(client_out.relative_to(DEST))))

now=datetime.now().astimezone().isoformat(timespec='seconds')
counts={s:sum(r['status']==s for r in rows) for s in ['AS EXPECTED','PENDING']}
manifest=dict(source_commit='0e6795834',merged_main_commit='3fd57606f',collected_at=now,verilator='5.050',counts=counts,rows=rows)
(DEST/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
lines=['# Qwen MU combined-commit regression','',f'Source `0e6795834` (merged as `3fd57606f`); Verilator 5.050. Snapshot {now}.', '',f"{counts['AS EXPECTED']} / {len(rows)} legs have terminal results as expected; {counts['PENDING']} remain pending. This snapshot is not a full regression PASS.",'',
'Outer shell exit 0 alone does not validate a mutant. The table checks the behavioral output for nested amix/adopt_slice runs. SIGTERM/143 is infrastructure failure, never expected mutant failure. FACES mutant r3 supersedes r0; collective r2 supersedes the hollow cases=0 r0. Pending output is excluded because the generic collector can otherwise prefer an old completed copy.','',
'Scope excludes OPSEG full2 steady-state rate and the real MU.TOK.QW run gated on B3-B5. DHUSER mutants report FAIL in their text while exiting 0 by design. ctlm_rest records its existing lp_m4 observability waiver.','',
'| Leg | Expect | Actual | Status |','|---|---|---|---|']
for r in rows:
    actual=r['actual'].replace('|',' / ').replace('\n',' ')[:650]
    link=f"[{r['leg']}]({r['evidence'][0]})" if r['evidence'] else f"[{r['leg']}]({r['client']})"
    lines.append(f"| {link} | {r['expect']} | {actual} | {r['status']} |")
(DEST/'README.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(counts)); print('\n'.join(r['leg']+' '+r['status'] for r in rows if r['status']!='AS EXPECTED'))
