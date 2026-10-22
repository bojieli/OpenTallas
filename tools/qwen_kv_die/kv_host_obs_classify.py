#!/usr/bin/env python3
"""KV-BIND5-OBS 10-19: classify the KV-die OUTPUT_OPEN observation ports of the HOST root (and dcal / d2d) by their
structural readers inside the flattened, cleaned RTL of their own master.

The die port bind (die_port_bind.py v2) reports an output OPEN when no die net reads it.  For a hardened / frame master
the port is either (i) a TAP of a net that has a live reader inside the master (the functional path is complete; only the
observation copy leaves the master unread) or (ii) a net whose ONLY reader is the port (the logic is observation-only
and needs a real reader on the die, or is dead).  This tool decides (i) / (ii) per BIT, structurally:

  1. filelist  : the RTL closure of the master (die_port_bind.rtl_index + child_closure; same resolution as the bind)
  2. yosys     : read; hierarchy -top M; proc; flatten; opt_clean  (opt_clean deletes every cell whose outputs are
                 unused, iteratively, so every remaining reader is live) ; write_json
  3. analyze   : for every output port bit -> readers = cell INPUT connections on that bit's net (constant bits, and
                 bits whose net is an input port = feed-through, are reported as such).

  kv_host_obs_classify.py run --master M [--top-file F] --out DIR     (fleet: ot-run; writes DIR/obs_readers.json)

A bit with >= 1 live internal reader is a TAP (DUP role: the same net is consumed inside the master).  A port with a bit
that has no internal reader is OBSERVATION-ONLY and must get a real die reader (CSR / health plane) -- never a waiver.
"""
import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_port_bind as P   # noqa: E402

ROOTS = ['rtl/qwen_sys', 'rtl/lib', 'rtl/qwen_split', 'rtl/hdc', 'rtl/link', 'rtl/physical']
# hard-macro behavioural models (die_port_bind MACRO_DIRS resolution; only the host's three SRAM types)
# blackbox (_bb.v: ports + directions only) -- a macro's inputs are real readers; its behavioural model is not needed
MACRO_FILES = []


def filelist(master, top_file=None):
    files = ([top_file] if top_file else []) + [f for f in MACRO_FILES if (ROOT / f).exists()]
    for _ in range(4):
        idx, amb = P.rtl_index([r for r in ROOTS if (ROOT / r).exists()], files, {}, files)
        seen = set()
        unres, models, _ = P.child_closure(idx, [master], set(), seen_out=seen)
        # unresolved hard macros / foreign leaves: their behavioural model (macro library, then the S81 PH memory)
        add = []
        for u in unres:
            for f in (f'physical/asap7_memory_macros_v2/{u}/{u}_bb.v', f'physical/asap7_memory_macros/{u}/{u}_bb.v',
                      f'rtl/dsrom_sys/s81_ph/{u}.sv'):
                if (ROOT / f).exists() and f not in files:
                    add.append(f)
                    break
        if not add:
            break
        files += add
    paths = sorted({idx[m].path for m in seen})
    return paths, unres, {k: v for k, v in amb.items() if k in seen}


def yosys(master, paths, out):
    # analysis copy: elaboration-time parameter guards `initial if (..) $fatal(..)` are not accepted by this Yosys outside
    # an initial-only context; they never create hardware, so the copy turns them into $display (readers unchanged)
    import re
    sd = out / 'src'
    sd.mkdir(exist_ok=True)
    cp = []
    for i, p in enumerate(paths):
        q = sd / f'{i:04d}_{Path(p).name}'
        q.write_text(re.sub(r'\$fatal\s*\(\s*\d+\s*,', '$display(', Path(p).read_text(errors='replace')))
        cp.append(str(q))
    ys = out / 'obs.ys'
    inc = sorted({str(Path(p).parent) for p in paths})
    bb = [c for c, p in zip(cp, paths) if p.endswith('_bb.v')]
    cp = [c for c, p in zip(cp, paths) if not p.endswith('_bb.v')]
    lines = (['read_verilog -lib ' + ' '.join(bb)] if bb else []) + [
             'read_verilog -sv ' + ' '.join('-I' + d for d in inc) + ' ' + ' '.join(cp),
             f'hierarchy -top {master}', 'proc', 'flatten', 'opt_clean', f'write_json {out / "flat.json"}']
    ys.write_text('\n'.join(lines) + '\n')
    r = subprocess.run(['yosys', '-q', '-l', str(out / 'yosys.log'), '-s', str(ys)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f'yosys failed rc={r.returncode}: {r.stderr[-2000:]}')


def analyze(master, out, ports=None):
    d = json.loads((out / 'flat.json').read_text())
    m = d['modules'][master]
    readers = defaultdict(list)
    for cn, c in m['cells'].items():
        dirs = c.get('port_directions', {})
        for pn, bits in c['connections'].items():
            if dirs.get(pn, 'input') != 'output':
                for b in bits:
                    if isinstance(b, int):
                        readers[b].append(f'{c["type"]}:{cn}.{pn}')
    inbits = {b for p in m['ports'].values() if p['direction'] == 'input' for b in p['bits'] if isinstance(b, int)}
    res = {}
    for pn, p in m['ports'].items():
        if p['direction'] != 'output' or (ports and pn not in ports):
            continue
        tap, only, const, thru = [], [], [], []
        ex = []
        for i, b in enumerate(p['bits']):
            if not isinstance(b, int):
                const.append(i)
            elif b in inbits:
                thru.append(i)
            elif readers.get(b):
                tap.append(i)
                if len(ex) < 2:
                    ex.append(readers[b][0])
            else:
                only.append(i)
        res[pn] = dict(width=len(p['bits']), tap_bits=len(tap), observation_only_bits=only, const_bits=const,
                       feedthrough_bits=thru, reader_examples=ex,
                       verdict=('TAP' if tap and not only else 'OBS_ONLY' if only and not tap else
                                'MIXED' if only else 'CONST' if const and not thru else 'FEEDTHRU'))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['run', 'filelist'])
    ap.add_argument('--master', required=True)
    ap.add_argument('--top-file')
    ap.add_argument('--ports', help='comma list (default: every output)')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    paths, unres, amb = filelist(a.master, a.top_file)
    (out / 'files.json').write_text(json.dumps(dict(files=paths, unresolved=unres, ambiguous=amb), indent=1))
    if a.cmd == 'filelist':
        print(len(paths), 'files; unresolved', len(unres))
        return
    if unres:
        raise SystemExit(f'unresolved children (no RTL): {sorted(unres)[:20]}')
    yosys(a.master, paths, out)
    res = analyze(a.master, out, set(a.ports.split(',')) if a.ports else None)
    # live flops of the observation window (KV-BIND5-OBS: the window's pin registers must survive opt_clean = they are read)
    cells = json.loads((out / 'flat.json').read_text())['modules'][a.master]['cells']
    win = {}
    for cn, c in cells.items():
        if 'u_obs' in cn and 'dff' in c['type']:
            key = cn.split('u_obs.')[-1].split('[')[0].split('$')[0] or c['type']
            win[key] = win.get(key, 0) + int(str(c['parameters'].get('WIDTH', '1')), 2 if set(str(c['parameters'].get('WIDTH', '1'))) <= {'0', '1'} and len(str(c['parameters'].get('WIDTH', '1'))) > 8 else 10)
    (out / 'obs_readers.json').write_text(json.dumps(dict(schema='opentallas.kv_host_obs_readers.v1', master=a.master,
                                                          ports=res, window_flops=win), indent=1))
    print('window flops', sum(win.values()), dict(sorted(win.items())[:12]))
    for pn, r in sorted(res.items()):
        print(f'{r["verdict"]:8s} {pn:32s} w={r["width"]:4d} tap={r["tap_bits"]:4d} only={len(r["observation_only_bits"]):4d} '
              f'{r["reader_examples"][:1]}')


if __name__ == '__main__':
    main()
