#!/usr/bin/env python3
"""dv_layer_record.py -- per-layer slice-bench measurements -> layer cycles -> token_compose (LB2-S81/RUN, 10-18).

Two steps, no simulation here (benches run on the fleet: run_dv_slice.sh via ot-run, Verilator 5.050):

  collect  one slice-bench run (a run dir: status + sources.sha256 + verilator.version, and its replay dir with
           replay.json + out.txt) -> a measurement JSON for (layer, cut).  A dv_cut_replay.py replay (neighbour
           traffic at the compiled cycles) also needs: verdict_kind SCHEDULE, no unencoded boundary event (partial),
           not STALE, the same die.v as the build, its trace check PASS and every cross-cut compose PASS.  The cut's measured cycles = the last
           scheduled output check minus t0; it counts only when the run PASSES (every check on its scheduled cycle,
           bit-exact, no fault cycle), on Verilator 5.050, the program is the full layer calendar (--full-layer; smoke
           programs never count) and every named mutant run FAILS (the fail witness).
      dv_layer_record.py collect --layer L0 --cut cut_0S --run RUN --replay REPLAY [--mutant RUN ...] [--full-layer] --out m.json

  compose  measurements + layer_slices.json (the cut set each layer needs) + layer_price_p4l.json -> per-layer cycles
           and the token term.  Composition (record.json 'composition'): layer cycles = max over the layer's cuts (the
           slowest slice under the fixed schedule); a layer is MEASURED only when every cut it needs is valid.
           Token: the priced p4l token (dv_layer_price token_cycles_dv) with each layer's critical share rescaled by its
           representative's measured / priced span ratio:
               token = token_dv + sum_L crit_dv(L) * (measured_span(rep L) / dv_span(rep L) - 1)
           Representatives (compress_ratios / engram ids of the model config): ratio 0 -> L0, ratio 2 -> L2 (L14 for
           the Engram layers 1 and 14 if ratio 2, else L0), ratio 1 -> L20, head -> head, MTP draft -> MTP.  Layers
           whose representative is not measured stay at the price (grade PRICED); the record says which.
      dv_layer_record.py compose --slices S.json --price P.json --meas m*.json --out compose.json [--record record.json]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERILATOR = 'Verilator 5.050'
CFG = 'compiler/models/deepseek-v4.1-flash/inference_config.json'
SCHEMA = 'opentallas.s81_dv.layer_measure.v1'


def parse_status(run):
    t = (Path(run) / 'status').read_text() if (Path(run) / 'status').exists() else ''
    m = re.search(r'DV_SLICE cycles=(\d+) in_events=(\d+) out_checks=(\d+) mismatches=(\d+) fault_cycles=(\d+)', t)
    rc = re.search(r'run rc (\d+)', t)
    v = (Path(run) / 'verilator.version').read_text().strip() if (Path(run) / 'verilator.version').exists() else ''
    return dict(run=str(run), rc=int(rc.group(1)) if rc else None, passed='TB_DV_SLICE PASS' in t,
                failed='TB_DV_SLICE FAIL' in t,
                sim=dict(zip(('cycles', 'in_events', 'out_checks', 'mismatches', 'fault_cycles'),
                             map(int, m.groups()))) if m else None,
                verilator=v, sources_sha256_lines=len((Path(run) / 'sources.sha256').read_text().splitlines())
                if (Path(run) / 'sources.sha256').exists() else 0)


def collect(a):
    r = parse_status(a.run)
    rp = json.loads((Path(a.replay) / 'replay.json').read_text())
    outs = [int(ln.split()[0]) for ln in (Path(a.replay) / 'out.txt').read_text().splitlines() if ln.strip()]
    muts = [parse_status(m) for m in a.mutant]
    why = []
    if not r['passed'] or r['rc'] != 0:
        why.append('run did not PASS')
    if r['sim'] and (r['sim']['mismatches'] or r['sim']['fault_cycles']):
        why.append('mismatches / fault cycles')
    if not r['verilator'].startswith(VERILATOR):
        why.append(f'not on {VERILATOR} (daemon version): {r["verilator"] or "unknown"}')
    if rp.get('mutant') or rp.get('check_shift'):
        why.append('replay is a mutant / diagnostic, not the schedule')
    if rp.get('schema') == 'opentallas.s81_dv.cut_replay.v1':      # dv_cut_replay.py (LB2-S81/REPLAY 10-18)
        if rp.get('verdict_kind') != 'SCHEDULE':
            why.append(f"cut replay verdict_kind {rp.get('verdict_kind')} (not SCHEDULE)")
        if rp.get('partial'):
            why.append(f"partial replay: {len(rp.get('unencoded', []))} scheduled boundary events not encoded")
        st = rp.get('stale') or {}
        if st.get('stale'):
            why.append('programme compiled on lane ages the die build does not have (STALE)')
        if not st.get('die_sha_match'):
            why.append('programme compiled on a different die.v than the cut build')
        ck = Path(a.check) if a.check else Path(a.replay) / 'check.json'
        if not ck.exists():
            why.append('no dv_cut_replay check (trace vs schedule) for this run')
        elif json.loads(ck.read_text()).get('verdict') != 'PASS':
            why.append('dv_cut_replay check FAILS (trace vs schedule)')
        for cp in a.compose or []:
            c = json.loads(Path(cp).read_text())
            if c.get('verdict') != 'PASS':
                why.append(f'cross-cut compose {cp} FAILS')
    elif a.check or a.compose:
        why.append('--check / --compose need a dv_cut_replay replay dir')
    if not muts:
        why.append('no mutant witness')
    why += [f'mutant {m["run"]} did not FAIL' for m in muts if not m['failed']]
    if not a.full_layer:
        why.append('smoke program (not declared the full compiled layer calendar: --full-layer)')
    if not r['sources_sha256_lines']:
        why.append('no sources.sha256 (bench file list)')
    doc = dict(schema=SCHEMA, layer=a.layer, cut=a.cut, slice=rp.get('slice'), prog=rp.get('prog'), t0=rp.get('t0'),
               out_checks=len(outs), cycles=(max(outs) - rp['t0']) if outs else None, run=r, mutants=muts,
               by_kind=rp.get('by_kind'),
               not_cut_words=dict(offdie=len(rp.get('offdie', [])), internal=len(rp.get('internal_events', [])),
                                  note='offdie = past the die\'s elastic link layer (end-slice RD beats: bench_vpx); '
                                       'internal = inside one instance (vs commands ride their CTL beat)'),
               valid=not why, why_invalid=why)
    Path(a.out).write_text(json.dumps(doc, indent=1) + '\n')
    print(f"{a.layer} {a.cut}: cycles {doc['cycles']} valid {doc['valid']} {'; '.join(why)}")
    return 0


def representatives(cfg):
    ratios, eng = cfg['compress_ratios'][:cfg['n_layers']], set(cfg['engram_layer_ids'])
    rep = {}
    for L, r in enumerate(ratios):
        rep[f'L{L}'] = 'L0' if r == 0 else ('L14' if L in eng else 'L2') if r == 2 else 'L20'
    rep['head'] = 'head'
    rep['mtp_draft'] = 'MTP'
    return rep


def compose(a):
    slices = json.loads(Path(a.slices).read_text())
    price = json.loads(Path(a.price).read_text())
    cfg = json.loads((ROOT / CFG).read_text() if (ROOT / CFG).exists() else subprocess.run(
        ['git', '-C', str(ROOT), 'show', f'HEAD:{CFG}'], capture_output=True, text=True, check=True).stdout)
    meas = [json.loads(Path(p).read_text()) for p in a.meas]
    need = {L: v['cuts'] for L, v in slices['layers'].items()}
    need['MTP'] = []                     # draft dies not in the p4l netlist (GAP_HEAD): no cut exists yet
    layers = {}
    for L in sorted(set(need) | {m['layer'] for m in meas}):
        got = {m['cut']: m for m in meas if m['layer'] == L}
        cuts = need.get(L, [])
        missing = [c for c in cuts if c not in got]
        invalid = [c for c in cuts if c in got and not got[c]['valid']]
        ok = bool(cuts) and not missing and not invalid
        layers[L] = dict(cuts_needed=cuts, cuts_measured=sorted(got), missing=missing, invalid=invalid,
                         cycles=max(got[c]['cycles'] for c in cuts) if ok else None,
                         bounding_cut=max(cuts, key=lambda c: got[c]['cycles']) if ok else None,
                         grade='MEASURED' if ok else ('NO_CUT_ON_P4L' if not cuts else 'NOT_MEASURED'))
    rep = representatives(cfg)
    wls = {}
    for wl, w in price['workloads'].items():
        tab = w['layers']
        terms, tok = [], w['token_cycles_dv']
        for L, rL in rep.items():
            row = tab.get(L)
            if not row or (L == 'mtp_draft' and wl != 'mtp'):
                continue
            rrow = tab.get('mtp_draft' if rL == 'MTP' else rL)
            m = layers.get(rL)
            if m and m['cycles'] is not None and rrow:
                ratio = m['cycles'] / rrow['dv_span']
                d = row['dv_crit'] * (ratio - 1)
                tok += d
                terms.append(dict(layer=L, rep=rL, crit_dv=row['dv_crit'], ratio=round(ratio, 4), delta=round(d, 1),
                                  grade='MEASURED' if L == rL else 'MEASURED_REP'))
            else:
                terms.append(dict(layer=L, rep=rL, crit_dv=row['dv_crit'], ratio=None, delta=0.0, grade='PRICED'))
        n_meas = sum(t['grade'] != 'PRICED' for t in terms)
        wls[wl] = dict(token_cycles_dv=w['token_cycles_dv'], token_cycles_composed=round(tok, 1),
                       terms_measured=n_meas, terms_priced=len(terms) - n_meas, terms=terms)
    out = dict(schema='opentallas.s81_dv.layer_compose.v1', tool='tools/s81_dv/dv_layer_record.py',
               slices=a.slices, price=a.price, measurements=a.meas,
               rule='layer = max over its cuts (all valid); token = token_dv + sum_L crit_dv(L) * (span_meas(rep) / '
                    'dv_span(rep) - 1); unmeasured representatives stay PRICED',
               layers=layers, workloads=wls)
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    for L, v in layers.items():
        print(f"{L:5s} {v['grade']:13s} cycles {v['cycles']} missing {v['missing']} invalid {v['invalid']}")
    for wl, w in wls.items():
        print(f"{wl}: token dv {w['token_cycles_dv']} composed {w['token_cycles_composed']} "
              f"({w['terms_measured']} measured / {w['terms_priced']} priced terms)")
    if a.record:
        rec = json.loads(Path(a.record).read_text())
        rec['token_compose'] = dict(compose=a.out, workloads={k: {kk: vv for kk, vv in v.items() if kk != 'terms'}
                                                              for k, v in wls.items()},
                                    layers={L: dict(cycles=v['cycles'], grade=v['grade']) for L, v in layers.items()},
                                    note='written by dv_layer_record.py compose; PRICED terms keep the p4l price')
        for row in rec.get('layers', []):
            v = layers.get(row.get('layer'))
            if v and v['cycles'] is not None:
                row['cycles'] = v['cycles']
                row['grade'] = 'MEASURED (slowest cut %s)' % v['bounding_cut']
        Path(a.record).write_text(json.dumps(rec, indent=1) + '\n')
        print('record updated', a.record)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    c = sp.add_parser('collect')
    c.add_argument('--layer', required=True)
    c.add_argument('--cut', required=True)
    c.add_argument('--run', required=True)
    c.add_argument('--replay', required=True)
    c.add_argument('--mutant', action='append', default=[])
    c.add_argument('--full-layer', action='store_true', help='the program is the full compiled layer calendar')
    c.add_argument('--check', help='dv_cut_replay check.json of the run (default REPLAY/check.json)')
    c.add_argument('--compose', action='append', default=[], help='dv_cut_replay compose.json the layer\'s cuts share')
    c.add_argument('--out', required=True)
    k = sp.add_parser('compose')
    k.add_argument('--slices', required=True)
    k.add_argument('--price', required=True)
    k.add_argument('--meas', nargs='*', default=[])
    k.add_argument('--out', required=True)
    k.add_argument('--record')
    a = ap.parse_args(argv)
    return collect(a) if a.cmd == 'collect' else compose(a)


if __name__ == '__main__':
    sys.exit(main())
