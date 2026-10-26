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
import argparse, hashlib, json, re, shlex, shutil, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# ot-epyc1tb is retired (HANDOFF 0bu 10-16): never a synthesis host
HOSTS = {'regular-crane': 'ot-epyc4', 'vm-xry57mhfyn': 'ot-agidock128', 'ot-pve1': 'ot-pve1'}
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
    # L2H-GEN2E 10-19: rtl/model_ready_hbm_r14 = the SAFE PC controller core ot_hbm_r14_aq_pc_safe (HBM-MC3 release ctrl)
    roots = ['rtl/gpu', 'rtl/v41rom', 'rtl/hbm_accel', 'rtl/hbm_next', 'rtl/hbm_mtp', 'rtl/hdc', 'rtl/lib', 'rtl/model_ready_hbm_r14', 'rtl/dsrom_sys/s81_window_la/recovered_ctl_m2',
             'physical/hbm_accel_die_views', 'physical/hbm_generic', 'physical/hbm_mtp',
             'physical/hbm_xp_aq_tree13_1014', 'physical/asap7_memory_macros', 'physical/asap7_memory_macros_v2']
    roots = [p for p in roots if (ROOT / p).is_dir()]
    if not roots:
        raise ValueError('pinned HBM source roots are absent from the sparse checkout')
    # LH-GEN2E 10-19: rg is not installed on every coordinator host; same scan with GNU grep (exit codes 0/1 alike)
    cmd = (['timeout', '120', 'rg', '-n', '--glob', '*.sv', '--glob', '*.v', r'^\s*module\s+\w+', *roots] if shutil.which('rg') else
           ['timeout', '120', 'grep', '-rnE', '--include=*.sv', '--include=*.v', r'^\s*module\s+\w+', *roots])
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
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

    def push_prefer():
        if not prefs:
            return ''
        pf = f'v16w/prefer_{cell}.txt'
        (Path(a.views) / 'wrap' / f'prefer_{cell}.txt').write_text('\n'.join(prefs) + '\n')
        for h in sorted(a.ready_hosts):
            subprocess.run(['scp', '-q', '-o', 'ConnectTimeout=8', str(Path(a.views) / 'wrap' / f'prefer_{cell}.txt'), f'{h}:{S}/{pf}'])
        return f' --prefer {pf}'
    for k in range(8):
        prefer = push_prefer()
        out = f'{a.remote_root}/syn/{cell}'
        # Keep exact-source synthesis objects when only their timing export needs
        # retrying. Older objects and failure logs remain available in history.
        legacy_ok = 'true' if a.legacy_source_commit == a.commit else 'false'
        legacy = (f'{legacy_ok} && {{ sources=({a.remote_root}/src_*); '
                  f'[ ${{#sources[@]}} = 1 ] && [ "${{sources[0]}}" = {S} ]; }}')
        compatible = (f'if [ -f {out}/.source_commit ] && [ "$(cat {out}/.source_commit)" != {a.commit} ]; then false; '
                      f'elif [ -f {out}/.wrapper_sha256 ]; then [ "$(cat {out}/.wrapper_sha256)" = {a.wrapper_sha256[cell]} ]; '
                      f'else {legacy}; fi')
        cmd = (f'echo HOST $(hostname); die_retry_stamp=$(date +%s%N); '
               f'if [ -s {out}/{cell}.netlist.v ] && [ -s {out}/{cell}.stat ] && ( {compatible} ); then '
               f'echo REUSE_SYNTH_OBJECT {cell}; else '
               f'if [ -e {out} ]; then mkdir -p {a.remote_root}/syn_history; '
               f'mv {out} {a.remote_root}/syn_history/{cell}.$die_retry_stamp; fi; '
               f'env MEMG={mem} HIER=1 EXTRA={",".join(extra)} WTOP={w} {env} '
               f'bash tools/hbm_die_v15/synth_master.sh . {out} {cell} {m} - {bb}{prefer}; fi && '
               f'echo {a.commit} > {out}/.source_commit && '
               f'sha256sum {S}/v16w/{w}.sv | cut -d" " -f1 > {out}/.wrapper_sha256 && '
               f'mkdir -p {out}/export_history && {{ '
               f'for f in etm.log etm_tt.tcl etm_ff.tcl; do [ ! -e {out}/$f ] || cp {out}/$f {out}/export_history/$f.$die_retry_stamp; done; '
               f'MEMG={mem} bash tools/hbm_die_v15/synth_etm.sh . {out} {cell}; }}')
        log = drive / f'{cell}.r{k}.log'
        with open(log, 'w') as f:
            rc = subprocess.run(['python3', '/home/ubuntu/bin/ot-run', '--mem', str(mem), '--threads', '4', '--priority', 'die', '--dir', S,
                                 '--', 'bash', '-c', cmd],
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


def remote_state(host, remote_root, commit, legacy_commit=None, wrappers=None):
    """Collect existing outputs and admitted commands before dispatching work."""
    script = r'''
import json, pathlib, re, subprocess, sys
root=pathlib.Path(sys.argv[1]); commit=sys.argv[2]; src=root/('src_'+commit); wrappers=json.loads(sys.argv[4])
if not src.is_dir():
 print(json.dumps(dict(ready=False, complete=[], running=[]))); raise SystemExit
complete=[]
legacy_source=sys.argv[3]==commit and list(root.glob('src_*')) == [src]
for d in (root/'syn').glob('*'):
 if d.is_dir() and any(d.glob('*_synth_tt.lib')) and any(d.glob('*_synth_ff.lib')):
  log=d/'etm.log'
  marker=d/'.source_commit'
  same_source=marker.read_text().strip()==commit if marker.is_file() else legacy_source
  wrapper=d/'.wrapper_sha256'
  same_wrapper=wrapper.read_text().strip()==wrappers.get(d.name) if wrapper.is_file() else legacy_source
  if same_source and same_wrapper and log.is_file() and 'OT_ETM_DONE_ff' in log.read_text(errors='replace'):
   complete.append(d.name)
running=set()
for line in subprocess.check_output(['ps','-eo','args='],text=True).splitlines():
 if str(root/'syn')+'/' in line:
  running.update(re.findall(re.escape(str(root/'syn')+'/')+r'([^/\s;]+)',line))
print(json.dumps(dict(ready=True,complete=complete,running=sorted(running))))
'''
    p = subprocess.run(['ssh', '-o', 'ConnectTimeout=8', host,
                        'python3 - ' + remote_root + ' ' + commit + ' ' + (legacy_commit or '-') + ' ' + shlex.quote(json.dumps(wrappers or {}))],
                       input=script, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f'{host} existing-job collection failed: {p.stderr[-300:]}')
    return json.loads(p.stdout.splitlines()[-1])


def main():
    global ROOT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--views', required=True)
    ap.add_argument('--commit', required=True)
    ap.add_argument('--remote-root', default='/srv/opentallas-scratch/claude/hdie-v16case')
    ap.add_argument('--source-root', type=Path, help='immutable source checkout when dispatcher code lives separately')
    ap.add_argument('--workers', type=int, choices=range(1, 9), default=8)
    ap.add_argument('--resume-remote', action='store_true', help='collect and preserve admitted builds and completed objects')
    ap.add_argument('--legacy-source-commit', help='known original source tag for pre-marker objects in a single-source run directory')
    ap.add_argument('cells', nargs='+')
    a = ap.parse_args()
    if a.source_root:
        ROOT = a.source_root.resolve()
    (Path(a.views) / 'drive').mkdir(exist_ok=True)
    rows = {r.split('\t')[0]: r.rstrip('\n').split('\t') for r in open(Path(a.views) / 'jobs.tsv')}
    a.wrapper_sha256 = {c: hashlib.sha256((Path(a.views) / 'wrap' / (rows[c][2] + '.sv')).read_bytes()).hexdigest() for c in a.cells}
    idx = module_index(a.commit)
    lock, summary = threading.Lock(), {}
    pending = set(a.cells)
    hosts = sorted(set(HOSTS.values()) - {'ot-epyc4'})
    while pending:
        states = {}
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            futures = {pool.submit(remote_state, h, a.remote_root, a.commit, a.legacy_source_commit, a.wrapper_sha256): h for h in hosts}
            for future in as_completed(futures):
                states[futures[future]] = future.result()
        a.ready_hosts = {h for h, state in states.items() if state['ready']}
        if not a.ready_hosts:
            raise RuntimeError('no prepared source host; no new dispatch')
        complete, running = {}, {}
        for h, state in states.items():
            complete.update({c: h for c in state['complete']})
            running.update({c: h for c in state['running']})
        if a.resume_remote:
            for c in sorted(pending & complete.keys()):
                summary[c] = True
                print(c, 'REUSE_REMOTE', complete[c], flush=True)
            pending -= complete.keys()
        busy = pending & running.keys()
        free = sorted(pending - busy)
        print('DISPATCH', 'workers', a.workers, 'completed', len(summary), 'admitted_running', len(busy), 'ready', len(free), flush=True)
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            futures = [pool.submit(run, c, rows[c], a, idx, lock, summary) for c in free]
            for future in as_completed(futures):
                future.result()
        pending -= set(free)
        if pending:
            time.sleep(30)
    print('DRIVE_DONE', json.dumps(summary))


if __name__ == '__main__':
    main()
