#!/usr/bin/env python3
"""A face proof leg returned by a different engine, recorded under its own name (COORD 11-04 05:23 LOOP-GAP item 5).

    hr_named_leg.py record --fp FP --module M --leg post|emitted_v --ys Y --abc-log L --mut-ys Y --mut-abc-log L
                           [--ruling TEXT] [--note TEXT]

Writes FP/named_legs.json (schema below) next to eq_rc.txt, which stays unchanged: this is never post rc=0.  The form:
yosys miter of pre against the leg's netlist with macros exposed as ports and flops at zero (write_aiger -zinit), then
ABC strash; scorr; dprove, plus a mutant of the same form that ABC must refute.  Refuses unless the script shows that
form and the logs show that outcome.  The limit travels with the record: state outside zero init is not proved.
hr_dead_inputs.named_legs reads the record and re-checks each netlist against its sha.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = 'opentallas.hr_named_proof_legs.v1'
LIMIT = 'state outside zero init is not proved'
ENGINE = 'yosys miter -equiv + write_aiger -zinit, then ABC strash; scorr; dprove'
FORM = ('miter -equiv -flatten gold gate m', 'setundef -init -zero', 'write_aiger -zinit',
        'expose -evert gold/t:ot_sram*', 'expose -evert gate/t:ot_sram*', 'delete t:ot_sram*')
STATS = re.compile(r'i/o\s*=\s*(\d+)/\s*(\d+)\s+lat\s*=\s*(\d+)\s+and\s*=\s*(\d+)')
ANSI = re.compile(r'\x1b\[[0-9;]*m')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_ys(path, fp):
    """-> (gold, gate) netlist basenames, both checked to be files of the proof dir; refuses another form."""
    text = Path(path).read_text()
    missing = [f for f in FORM if f not in text]
    if missing:
        raise ValueError(f'{path}: not the named-leg form, missing {missing}')
    reads = re.findall(r'^read_(?:json|verilog -sv)\s+(\S+)\s*$', text, re.M)
    if len(reads) < 2:
        raise ValueError(f'{path}: needs gold and gate netlist reads, found {reads}')
    for r in reads[:2]:
        if Path(r).resolve() != (Path(fp) / Path(r).name).resolve():
            raise ValueError(f'{path}: netlist {r} is not in the proof dir {fp}')
    return Path(reads[0]).name, Path(reads[1]).name


def read_log(path):
    text = ANSI.sub('', Path(path).read_text())
    stats = [tuple(int(x) for x in m) for m in STATS.findall(text)]
    if len(stats) < 2:
        raise ValueError(f'{path}: no ABC stats before and after scorr, proof did not run')
    frame = re.search(r'asserted in frame (\d+)', text)
    return dict(before=dict(latches=stats[0][2], ands=stats[0][3]), after=dict(latches=stats[1][2], ands=stats[1][3]),
                unsat='UNSATISFIABLE' in text or 'Networks are equivalent' in text,
                refuted='Networks are not equivalent' in text, frame=int(frame[1]) if frame else None)


def build(fp, module, ys, abc_log, mut_ys, mut_abc_log, ruling='', note=''):
    gold, gate = read_ys(ys, fp)
    mgold, mgate = read_ys(mut_ys, fp)
    if mgold != gold or mgate == gate or not mgate.startswith('mut'):
        raise ValueError(f'mutant must share gold {gold} and read a mut* netlist, got {mgold} / {mgate}')
    leg, mut = read_log(abc_log), read_log(mut_abc_log)
    if not leg['unsat'] or leg['refuted']:
        raise ValueError(f'{abc_log}: leg did not return UNSATISFIABLE')
    if not mut['refuted'] or mut['frame'] is None:
        raise ValueError(f'{mut_abc_log}: mutant was not caught, the control proves nothing')
    fp = Path(fp)
    return dict(
        module=module, engine=ENGINE, initial_state='zero', srams='ports', limit=LIMIT, result='UNSATISFIABLE',
        gold=gold, gold_sha256=sha(fp / gold), gate=gate, gate_sha256=sha(fp / gate),
        before=leg['before'], after=leg['after'], script_sha256=sha(ys), log_sha256=sha(abc_log),
        source=dict(script=str(ys), log=str(abc_log)),
        mutant=dict(result='NOT_EQUIVALENT', frame=mut['frame'], gate=mgate, gate_sha256=sha(fp / mgate),
                    script_sha256=sha(mut_ys), log_sha256=sha(mut_abc_log),
                    source=dict(script=str(mut_ys), log=str(mut_abc_log))),
        ruling=ruling, note=note)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['record'])
    ap.add_argument('--fp', required=True)
    ap.add_argument('--module', required=True)
    ap.add_argument('--leg', required=True, choices=['post', 'emitted_v'])
    ap.add_argument('--ys', required=True)
    ap.add_argument('--abc-log', required=True)
    ap.add_argument('--mut-ys', required=True)
    ap.add_argument('--mut-abc-log', required=True)
    ap.add_argument('--ruling', default='COORD 2026-11-04 05:23 PST LOOP-GAP 05:20 item 5')
    ap.add_argument('--note', default='')
    a = ap.parse_args(argv)
    path = Path(a.fp) / 'named_legs.json'
    doc = json.loads(path.read_text()) if path.is_file() else dict(schema=SCHEMA, module=a.module, legs={})
    if doc['module'] != a.module:
        raise SystemExit(f'{path}: module {doc["module"]} is not {a.module}')
    doc['legs'][a.leg] = build(a.fp, a.module, a.ys, a.abc_log, a.mut_ys, a.mut_abc_log, a.ruling, a.note)
    path.write_text(json.dumps(doc, indent=1) + '\n')
    print(json.dumps({a.leg: dict(after=doc['legs'][a.leg]['after'], mutant_frame=doc['legs'][a.leg]['mutant']['frame'])}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
