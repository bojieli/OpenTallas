#!/usr/bin/env python3
"""Drive SYNTH-view builds of v16 die cells on the fleet (H-DIE-V16CASE 2026-10-16).

    v16_synth_drive.py --views VIEWS_DIR --commit SHA --remote-root DIR CELL [CELL ...]

Per cell (jobs.tsv row of v16_views.py): ot-run synth_master.sh (HIER=1, wrapper top WTOP, EXTRA = wrapper + resolved
deps) then synth_etm.sh.  master_filelist.py misses some instantiations (it scans text); when yosys reports
"Module `X' referenced ... is not part of the design" the file that defines X at the snapshot commit (git index, test
benches excluded) is added to EXTRA and the build is retried (<= 6 rounds).  Ambiguous definitions follow
PREFER below (the variant whose parameters the parent instantiates).  Every round's extra files are recorded in
VIEWS_DIR/drive/<cell>.json; logs in VIEWS_DIR/drive/<cell>.r<k>.log.  Nothing is stubbed: a module that cannot be
resolved fails the cell (it is then an excluded region of the die case, with its owner).
"""
import argparse, json, re, subprocess, sys, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# ot-epyc1tb is retired (HANDOFF 0bu 10-16): never a synthesis host
# HBM-CHAIN3 10-18: ot-epyc5 added -- push_prefer scp'd the prefer list only to the hosts named here, so a retry admitted
# on ot-epyc5 died FILELIST_FAIL (GEN2 S2: ot_hbm_idx_query_static, ot_hgi_coll_gq_issue)
HOSTS = {'regular-crane': 'ot-epyc4', 'vm-xry57mhfyn': 'ot-agidock128', 'ot-pve1': 'ot-pve1', 'ot-epyc5': 'ot-epyc5'}
# L2H-GEN2D-RST 10-19 22:00: ot-epyc4/ot-epyc8 drained (HELD); OT_SYNTH_HOSTS=h1,h2,.. names the hosts that carry src_<commit>
# (prefer lists are pushed to exactly these; ot-run only admits where --dir exists).
import os as _os
if _os.environ.get('OT_SYNTH_HOSTS'):
    HOSTS = {h: h for h in _os.environ['OT_SYNTH_HOSTS'].split(',') if h}
PREFER = {'ot_hbm_lk_ep': ['rtl/hbm_accel/tu/lk_ep_20261010/ot_hbm_lk_ep.sv',
                           'rtl/hbm_accel/tu/link_retry_pipeline_20261009/ot_hbm_link_retry_pipeline_cl.sv',
                           'rtl/hbm_accel/tu/link_retry_sram_20261008/ot_hbm_replay_sram_dp.sv'],
          # ot_su12_lane binds SFUT: the c12 vector lane (rtl/hdc/v41x) is the variant with that parameter
          'ot_hgi_sfu_scheduled_engine': ['rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv'],
          # d4f split2 core (H-SU k8): same ot_su12_lane SFUT binding
          'ot_hgi_sfu_core_split2': ['rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv']}
MISSING = re.compile(r"Module `\\?(\w+)' referenced in module .* is not part of the design")
NOPARAM = re.compile(r"Module `\\?(\w+)' referenced in module .* does not have a parameter named '(\w+)'")


def module_index(commit):
    # Scan the actual HBM source checkout, not git grep <rev> over the entire object database (which can decompress
    # hundreds of thousands of blobs on the coordinator). Actual builds still archive the requested immutable ref.
    head = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout.strip()
    wanted = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', commit], check=True, capture_output=True, text=True).stdout.strip()
    if head != wanted:
        raise ValueError('module index requires a checkout of the pinned synthesis commit')
    roots = ['rtl/hbm_accel', 'rtl/hbm_next', 'rtl/hbm_mtp', 'rtl/hdc', 'rtl/lib', 'rtl/dsrom_sys/s81_window_la/recovered_ctl_m2',
             'physical/hbm_accel_die_views', 'physical/hbm_generic', 'physical/hbm_mtp',
             'physical/hbm_xp_aq_tree13_1014', 'physical/asap7_memory_macros', 'physical/asap7_memory_macros_v2']
    roots = [p for p in roots if (ROOT / p).is_dir()]
    if not roots:
        raise ValueError('pinned HBM source roots are absent from the sparse checkout')
    proc = subprocess.run(['timeout', '120', 'rg', '-n', '--glob', '*.sv', '--glob', '*.v', r'^\s*module\s+\w+',
                           *roots], cwd=ROOT, capture_output=True, text=True)
    if proc.returncode not in (0, 1):
        raise RuntimeError(f'HBM module index scan failed rc={proc.returncode}: {proc.stderr[:500]}')
    idx = {}
    for line in proc.stdout.splitlines():
        path, _, txt = line.split(':', 2)
        m = re.match(r'\s*module\s+(\w+)', txt)
        if m and not re.search(r'(^|/)tb_|/test/|/tb/', path):
            idx.setdefault(m.group(1), []).append(path)
    return idx


def run(cell, row, a, idx, lock, summary):
    _, m, w, mem, bb, env = row
    S = f'{a.remote_root}/src_{a.commit}'
    extra = [f'v16w/{w}.sv']
    drive = Path(a.views) / 'drive'
    rec = dict(cell=cell, rounds=[])
    prefs = list(PREFER.get(m, []))
    view = json.loads((Path(a.views) / 'views.json').read_text())[cell]
    scoped = view.get('source', '')
    if scoped.startswith('rtl/hbm_accel/die_glue/scoped_d4g/'):
        # This contract names a private, alpha-renamed child closure; never resolve its top through the global
        # canonical-path heuristic, which would silently synthesize the unscoped implementation instead.
        prefs.insert(0, scoped)
        extra.append(scoped)

    def push_prefer():
        if not prefs:
            return ''
        pf = f'v16w/prefer_{cell}.txt'
        (Path(a.views) / 'wrap' / f'prefer_{cell}.txt').write_text('\n'.join(prefs) + '\n')
        for h in HOSTS.values():
            subprocess.run(['scp', '-q', str(Path(a.views) / 'wrap' / f'prefer_{cell}.txt'), f'{h}:{S}/{pf}'])
        return f' --prefer {pf}'
    for k in range(8):
        prefer = push_prefer()
        out = f'{a.remote_root}/syn/{cell}'
        cmd = (f'echo HOST $(hostname); rm -rf {out}; env MEMG={mem} HIER=1 EXTRA={",".join(extra)} WTOP={w} {env} '
               f'bash tools/hbm_die_v15/synth_master.sh . {out} {cell} {m} - {bb}{prefer} && '
               f'MEMG={mem} bash tools/hbm_die_v15/synth_etm.sh . {out} {cell}')
        log = drive / f'{cell}.r{k}.log'
        with open(log, 'w') as f:
            rc = subprocess.run(['python3', '/home/ubuntu/bin/ot-run', '--mem', str(mem), '--threads', '4', '--dir', S,
                                 '--priority', 'die', '--', 'bash', '-c', cmd],
                                stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL).returncode
        txt = log.read_text()
        hm = re.search(r'^HOST (\S+)', txt, re.M)
        ran = re.search(r'ot-run: RAN on (\S+)', txt)
        host = ran.group(1) if ran else (HOSTS.get(hm.group(1), hm.group(1)) if hm else None)
        rnd = dict(round=k, rc=rc, host=host, extra=list(extra), prefer=list(prefs))
        rec['rounds'].append(rnd)
        if rc == 0 and 'etm rc=0' in txt:
            rec.update(ok=True, host=host, remote=out)
            break
        ylog = subprocess.run(['ssh', host, f'cat {out}/{cell}.log 2>/dev/null | grep -E "ERROR" | head -20'],
                              capture_output=True, text=True).stdout if host else ''
        rnd['errors'] = ylog.strip().splitlines()[:6]
        miss = sorted(set(MISSING.findall(ylog)))
        add, newpref = [], []
        rank = lambda f: (not f.startswith('rtl/'), len(f))   # ambiguous: the rtl/ definition with the shortest path
        for mod in miss:
            cands = sorted(idx.get(mod, []), key=rank)
            if cands and cands[0] not in extra:
                add.append(cands[0])
                if len(cands) > 1:
                    newpref.append(cands[0])
            else:
                rnd.setdefault('unresolvable', []).append((mod, cands))
        for mod, prm in sorted(set(NOPARAM.findall(ylog))):   # pick the variant that declares the parameter
            cands = sorted(idx.get(mod, []), key=rank)
            got = [f for f in cands if f not in prefs and re.search(r'\b' + prm + r'\b', subprocess.run(
                ['git', '-C', str(ROOT), 'show', f'{a.commit}:{f}'], capture_output=True, text=True).stdout)]
            if got:
                newpref.append(got[0])
            else:
                rnd.setdefault('unresolvable', []).append((mod, prm, cands))
        prefs[:0] = [f for f in newpref if f not in prefs]
        if not add and not newpref:
            rec.update(ok=False, host=host)
            break
        extra += add
    with lock:
        (drive / f'{cell}.json').write_text(json.dumps(rec, indent=1))
        summary[cell] = rec.get('ok', False)
        print(cell, 'OK' if rec.get('ok') else 'FAIL', rec['rounds'][-1].get('errors', [])[:2], flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--views', required=True)
    ap.add_argument('--commit', required=True)
    ap.add_argument('--remote-root', default='/srv/opentallas-scratch/claude/hdie-v16case')
    ap.add_argument('cells', nargs='+')
    a = ap.parse_args()
    (Path(a.views) / 'drive').mkdir(exist_ok=True)
    rows = {r.split('\t')[0]: r.rstrip('\n').split('\t') for r in open(Path(a.views) / 'jobs.tsv')}
    idx = module_index(a.commit)
    lock, summary, th = threading.Lock(), {}, []
    for c in a.cells:
        t = threading.Thread(target=run, args=(c, rows[c], a, idx, lock, summary))
        t.start(); th.append(t)
    for t in th:
        t.join()
    print('DRIVE_DONE', json.dumps(summary))


if __name__ == '__main__':
    main()
