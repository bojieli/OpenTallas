#!/usr/bin/env python3
"""Export one closed element's REAL routed layout for the Chip Explorer element page (fleet-viz /explorer/element/).

Two steps:

  run   (on the fleet host that holds the job's final routed DB; heavy, goes through ot-heavy)
        explorer_elem_export.py run --orfs <job ECO/route orfs dir with results/.../6_final.odb and w18_sta_{tt,ff}.tcl>
                                    --src <job src checkout> --out <scratch dir> [--mem 96]
        Cuts the closure loop's own sign-off STA preamble out of w18_sta_<corner>.tcl (same odb / spef / 6_final.sdc /
        post-SDCs / macro libs as the verdict) and runs tools/explorer_elem/or_export.py in the ORFS container for the
        TT (setup, geometry, clock tree, power) and FF (hold, clock tree) corners in parallel.

  pack  (local; joins the raw export with the committed closure record)
        explorer_elem_export.py pack --raw <dir with tt.json ff.json cells.bin> --element <id> --job <closure job>
                                     --dest ~/.local/share/fleet-viz/explorer/element/data [--label ...] [--role ...]
        Writes <dest>/<id>.json (+ <id>.cells.bin): facts carry the record path each number is read from.
"""
import argparse, json, os, pathlib, re, shutil, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
IMAGE = 'openroad/orfs:asap7lock'
OPENROAD = '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
STATE = pathlib.Path.home() / '.local/state/closure_loop/jobs'


def preamble(tcl_text):
    """the corner STA setup lines of a closure-loop w18_sta_<corner>.tcl (everything before the first report)"""
    out = []
    for ln in tcl_text.splitlines():
        s = ln.strip()
        if s.startswith('puts ') or s.startswith('report_') or s.startswith('set ') or s.startswith('foreach') or s == 'exit':
            break
        if s: out.append(s)
    if not any(s.startswith('read_db') for s in out) or not any(s.startswith('read_spef') for s in out):
        raise SystemExit('preamble lacks read_db/read_spef: %r' % out[-3:])
    return '\n'.join(out) + '\n'


def cmd_run(a):
    orfs, src, out = pathlib.Path(a.orfs), pathlib.Path(a.src), pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    exp = out / 'exp'; exp.mkdir(exist_ok=True)
    shutil.copy(HERE / 'explorer_elem' / 'or_export.py', exp / 'or_export.py')
    procs = []
    for c in a.corners.split(','):
        (out / ('pre_%s.tcl' % c)).write_text(preamble((orfs / ('w18_sta_%s.tcl' % c)).read_text()))
        cmd = ['ot-heavy', '--mem', str(a.mem), '--', 'docker', 'run', '--rm', '--memory', '%dg' % a.mem,
               '--user', '%d:%d' % (os.getuid(), os.getgid()),
               '-v', '%s:/work:ro' % orfs, '-v', '%s:/src:ro' % src, '-v', '%s:/exp:ro' % exp, '-v', '%s:/out' % out,
               '-e', 'OT_PRE=/out/pre_%s.tcl' % c, '-e', 'OT_CORNER=%s' % c, '-e', 'OT_OUT=/out', '-e', 'OT_NPATH=%d' % a.npath,
               '-e', 'HOME=/tmp', a.image, OPENROAD, '-python', '-exit', '-threads', str(a.threads), '/exp/or_export.py']
        lg = open(out / ('export_%s.log' % c), 'w')
        print(' '.join(cmd), file=lg, flush=True)
        procs.append((c, subprocess.Popen(cmd, stdout=lg, stderr=subprocess.STDOUT)))
    rc = 0
    for c, p in procs:
        r = p.wait(); print('%s rc %d' % (c, r)); rc |= r
    return rc


def _num(x):
    try: return float(x)
    except Exception: return None


def cmd_pack(a):
    raw, dest = pathlib.Path(a.raw), pathlib.Path(a.dest)
    dest.mkdir(parents=True, exist_ok=True)
    tt = json.loads((raw / 'tt.json').read_text())
    ff = json.loads((raw / 'ff.json').read_text()) if (raw / 'ff.json').exists() else None
    st = json.loads((STATE / (a.job + '.json')).read_text()) if (STATE / (a.job + '.json')).exists() else {}
    rec_dir = REPO / 'results/closure_loop' / a.job
    if not (rec_dir / 'verdict.json').exists(): rec_dir = None
    verdict = json.loads((rec_dir / 'verdict.json').read_text()) if rec_dir else None
    vpath = str((rec_dir / 'verdict.json').relative_to(REPO)) if rec_dir else None
    rec_ref = a.record_ref or (vpath and 'main:' + vpath)
    if verdict is None and a.record_ref:  # a record committed on a branch only: <ref>:<path>
        verdict = json.loads(subprocess.run(['git', '-C', str(REPO), 'show', a.record_ref], capture_output=True, text=True, check=True).stdout)
    m = (verdict or {}).get('metrics') or st.get('metrics') or {}
    stx = tt['stats']
    spath = '~/.local/state/closure_loop/jobs/%s.json' % a.job
    raw_ref = '%s:%s' % (a.host, a.raw_remote or a.raw)
    facts = [
        dict(k='closure job', v=a.job, src=rec_ref or spath),
        dict(k='status', v=(verdict or st).get('status'), src=rec_ref or spath),
        dict(k='source commit', v=((verdict or {}).get('source_commit') or st.get('commit_full') or '')[:12], src=rec_ref or spath),
        dict(k='TT setup WNS (sign-off record)', v=_num(m.get('ss_ps') if m.get('setup_corner') == 'tt' else m.get('tt_ps', m.get('ss_ps'))),
             unit='ps', src=rec_ref or spath),
        dict(k='FF hold WNS (sign-off record)', v=_num(m.get('ff_ps')), unit='ps', src=rec_ref or spath),
        dict(k='DRC', v=m.get('drc', 0), src=rec_ref or spath),
        dict(k='SS setup sensitivity', v=_num(m.get('ss_sensitivity_ps')), unit='ps', src=rec_ref or spath),
        dict(k='TT setup WNS (this export re-timed)', v=tt.get('worst_slack_ps'), unit='ps', src=raw_ref + '/tt.json'),
        dict(k='FF hold WNS (this export re-timed)', v=ff and ff.get('worst_slack_ps'), unit='ps', src=raw_ref + '/ff.json'),
        dict(k='die', v='%.2f x %.2f' % (tt['die']['x1'] - tt['die']['x0'], tt['die']['y1'] - tt['die']['y0']), unit='um', src=raw_ref + '/tt.json'),
        dict(k='core area', v=stx['core_area_um2'], unit='um2', src=raw_ref + '/tt.json'),
        dict(k='std-cell area (excl. filler/tap/decap)', v=stx['std_cell_area_um2'], unit='um2', src=raw_ref + '/tt.json'),
        dict(k='macro area', v=stx['macro_area_um2'], unit='um2', src=raw_ref + '/tt.json'),
        dict(k='utilisation (std+macro)/core', v=round(100 * (stx['std_cell_area_um2'] + stx['macro_area_um2']) / stx['core_area_um2'], 1),
             unit='%', src=raw_ref + '/tt.json'),
        dict(k='std cells', v=stx['std_cells'], src=raw_ref + '/tt.json'),
        dict(k='flops', v=stx['flops'], src=raw_ref + '/tt.json'),
        dict(k='LVT cells', v=round(100.0 * stx['lvt_cells'] / max(1, stx['std_cells']), 2), unit='%', src=raw_ref + '/tt.json'),
        dict(k='SLVT cells', v=round(100.0 * stx['slvt_cells'] / max(1, stx['std_cells']), 2), unit='%', src=raw_ref + '/tt.json'),
        dict(k='clock-tree cells', v=stx['clock_tree_cells'], src=raw_ref + '/tt.json'),
        dict(k='macros', v=len(tt['macros']), src=raw_ref + '/tt.json'),
    ]
    if tt.get('power_w'):
        p = tt['power_w']
        facts.append(dict(k='power (vectorless, TT)', v=round(p['total'] * 1e3, 1), unit='mW', note=p['basis'], src=raw_ref + '/power_tt.rpt'))
    for x in a.extra_fact or []:
        facts.append(json.loads(x))
    if m.get('ss_tns_ps') is not None:
        facts.append(dict(k='TT setup TNS', v=_num(m.get('ss_tns_ps')), unit='ps', src=rec_ref or spath))
    el = dict(schema='opentallas.explorer_elem.v1', id=a.element, label=a.label or tt.get('top'), role=a.role,
              summary=a.summary, note=a.note, block=tt.get('top'), job=a.job, host=a.host, db=a.db, record=rec_ref,
              exported_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'), facts=facts,
              geom={k: tt[k] for k in ('die', 'core', 'cells', 'masters', 'modules', 'module_cells', 'macros', 'ports', 'grid',
                                      'quantum_dbu', 'dbu_per_um', 'stats')},
              clocks=tt.get('clocks'), clock_roots=tt.get('clock_roots'),
              clock_tt=tt['clock_tree'], clock_wires=tt.get('clock_wires') and dict(tt['clock_wires'], file='%s.clk.bin' % a.element), clock_ff_leaves=ff and [l[3] for l in ff['clock_tree']['leaves']],
              clock_ff_match=bool(ff and len(ff['clock_tree']['leaves']) == len(tt['clock_tree']['leaves'])),
              setup_paths=tt['paths'], hold_paths=ff and ff['paths'])
    el['geom']['cells']['file'] = '%s.cells.bin' % a.element
    if a.golden:
        gc, gp = a.golden.split(':', 1)
        txt = subprocess.run(['git', '-C', str(REPO), 'show', '%s:%s' % (gc, gp)], capture_output=True, text=True, check=True).stdout
        import hashlib
        el['golden'] = dict(commit=gc, path=gp, sha256=hashlib.sha256(txt.encode()).hexdigest(), text=txt)
    if a.rtl:
        r = json.loads(pathlib.Path(a.rtl).read_text())
        el['rtl_file'] = '%s.rtl.json' % a.element
        el['rtl_meta'] = dict(top=r['top'], source_commit=r.get('source_commit'), files=len(r['files']), top_params=r.get('top_params'))
        (dest / el['rtl_file']).write_text(json.dumps(r, separators=(',', ':')))
    (dest / ('%s.json' % a.element)).write_text(json.dumps(el, separators=(',', ':')))
    shutil.copy(raw / 'cells.bin', dest / ('%s.cells.bin' % a.element))
    if (raw / 'clk.bin').exists(): shutil.copy(raw / 'clk.bin', dest / ('%s.clk.bin' % a.element))
    print('wrote', dest / ('%s.json' % a.element), os.path.getsize(dest / ('%s.json' % a.element)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    r = sp.add_parser('run'); r.add_argument('--orfs', required=True); r.add_argument('--src', required=True)
    r.add_argument('--out', required=True); r.add_argument('--mem', type=int, default=96); r.add_argument('--threads', type=int, default=8)
    r.add_argument('--npath', type=int, default=40); r.add_argument('--corners', default='tt,ff'); r.add_argument('--image', default=IMAGE)
    p = sp.add_parser('pack'); p.add_argument('--raw', required=True); p.add_argument('--element', required=True)
    p.add_argument('--job', required=True); p.add_argument('--dest', required=True); p.add_argument('--label')
    p.add_argument('--role'); p.add_argument('--summary'); p.add_argument('--host', default='')
    p.add_argument('--raw-remote'); p.add_argument('--db', default=''); p.add_argument('--record-ref'); p.add_argument('--note')
    p.add_argument('--rtl', help='rtl.json from tools/explorer_elem/rtl_export.py'); p.add_argument('--golden', help='<commit>:<path> of the golden model')
    p.add_argument('--extra-fact', action='append', help='JSON {"k":..,"v":..,"unit":..,"src":..}; repeatable')
    a = ap.parse_args()
    sys.exit(cmd_run(a) if a.cmd == 'run' else cmd_pack(a))


if __name__ == '__main__':
    main()
