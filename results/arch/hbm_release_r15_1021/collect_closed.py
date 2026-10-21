#!/usr/bin/env python3
"""HBM-DIE15: collect CLOSED next-GEN bind candidates from the closure daemon state into rfc_closed_views.json.
Re-run as more jobs close; then `git checkout <record_commit> -- <view dir>` for any new entry (printed as TODO_CHECKOUT).
Exact-source rule: a relay view is admitted only when its master module text at the job's source commit equals the
module text in this tree (no alias of old-source views onto changed successors)."""
import ast, glob, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
JOBS = Path.home() / '.local/state/closure_loop/jobs'
OUT = Path(__file__).with_name('rfc_closed_views.json')
SRC = 'rtl/hbm_accel/die_glue/hbfd_rly_rfc_masters.sv'
EXTRA = ['hcoll_reduce_lane_u-n32u-d755fcd4c']   # child view: binds through the coll q2/q3 landed parent kit


def mods(txt):
    return {m.group(1): m.group(0) for m in re.finditer(r'(?ms)^\s*module\s+(\w+)\b.*?^\s*endmodule', txt)}


def git_show(rev, path):
    return subprocess.run(['git', '-C', str(ROOT), 'show', f'{rev}:{path}'], capture_output=True, text=True).stdout


here = mods((ROOT / SRC).read_text())
views, children, todo = [], [], []
for f in sorted(JOBS.glob('*.json')):
    n = f.stem
    if not ((n.startswith('hbfd_rly_') and ('_rfc-' in n or '_rrfc-' in n)) or n in EXTRA):
        continue
    j = json.loads(f.read_text())
    if j.get('status') != 'CLOSED':
        continue
    pub = j['publish']; pub = ast.literal_eval(pub) if isinstance(pub, str) else pub
    lint = j.get('child_lint'); lint = ast.literal_eval(lint) if isinstance(lint, str) else (lint or {})
    master = Path(lint.get('lef', '')).stem
    files = subprocess.run(['git', '-C', str(ROOT), 'show', '--name-only', '--format=', pub['branch_commit']],
                           capture_output=True, text=True).stdout.split()
    vdir = next((x.split('/views/')[0] + '/views/' + master for x in files if f'/views/{master}/' in x), None)
    ent = dict(job=n, master=master, view=vdir, record_branch=pub['record_branch'], record_commit=pub['branch_commit'],
               source_commit=j['commit_full'], verdict=j['reason'].split('|')[0].replace('CLOSED ', '').strip())
    if not (ROOT / vdir / f'{master}.lef').is_file():
        todo.append(f'git -C {ROOT} checkout {pub["branch_commit"]} -- {vdir}')
    if n in EXTRA:
        children.append(ent); continue
    theirs = mods(git_show(j['commit_full'], SRC)).get(master)
    if theirs != here.get(master):
        print('SOURCE_CHANGED_SKIP', n, master); continue
    ent['station'] = 'f32' if re.search(r'\bot_hbm_rly(_rr)?_f32\b', theirs) else 'base'
    views.append(ent)
# newest CLOSED job per master wins only if exact; keep one entry per master
by = {}
for v in views:
    by.setdefault(v['master'], v)
views = sorted(by.values(), key=lambda v: v['master'])
OUT.write_text(json.dumps(dict(source=SRC, views=views, child_views=children), indent=1) + '\n')
print('RFC_CLOSED', len(views), 'f32', sum(v['station'] == 'f32' for v in views),
      'base', sum(v['station'] == 'base' for v in views), 'children', [c['master'] for c in children])
for t in todo:
    print('TODO_CHECKOUT', t)
