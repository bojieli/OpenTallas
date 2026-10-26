"""Hard-core clock contract: measured boundary-register MEANS, TT and FF.

ETM max_clock_tree_path is an extrema bound and never a mean. Release callers
require a SIGNED record tied to the selected view. Historical insertion.json is
available explicitly for diagnostics, and cannot qualify a release kit.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import cores as C

SCHEMA = 'opentallas.core_clock_contract.v1'


class ContractError(ValueError):
    pass


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _mean(stat, where):
    if not isinstance(stat, dict) or not isinstance(stat.get('n'), (int, float)) or stat['n'] <= 0:
        raise ContractError(f'{where}: missing nonempty boundary-register census')
    mean = stat.get('mean_ps', stat.get('mean'))
    if isinstance(mean, bool) or not isinstance(mean, (int, float)) or not math.isfinite(mean) or mean < 0:
        raise ContractError(f'{where}: missing finite nonnegative pin-register mean')
    return dict(mean_ps=float(mean), n=int(stat['n']), basis='pin_register_mean', source=where)


def from_signoff(lib, record, source, pin_names=None):
    """Export a single-clock SIGNED view; per-clock records are required for multiple pins."""
    names = sorted(pin_names if pin_names is not None else C.lib_clocks(lib))
    if record.get('verdict') != 'SIGNED':
        raise ContractError(f'{source}: core is not SIGNED')
    if not names:
        raise ContractError(f'{lib}: no clock pins')
    cell = re.search(r'\bcell\s*\(\s*\"?([^\"\s)]+)', Path(lib).read_text())
    if not cell:
        raise ContractError(f'{lib}: selected liberty cell identity missing')
    module = cell.group(1)
    pins = {}
    per_pin = record.get('clock_measurements', {})
    for pin in names:
        corners = per_pin.get(pin, {}).get('corners')
        if corners is None:
            if len(names) != 1:
                raise ContractError(f'{source}: multiple clock pins need measured per-pin means ({pin})')
            corners = record.get('corners', {})
        vals = {}
        for corner in ('tt', 'ff'):
            item = corners.get(corner, {})
            ports = item.get('clock_ports', [])
            if item.get('design') != module:
                raise ContractError(f'{source}:{corner}: signed design does not match liberty cell {module}')
            if not item.get('done') or item.get('parasitics') not in {'spef', 'rcx'}:
                raise ContractError(f'{source}:{pin}:{corner}: completed extracted-SPEF measurement required')
            if ports and ports != [pin]:
                raise ContractError(f'{source}:{corner}: clock-port identity {ports} != {[pin]}')
            vals[corner] = _mean(item.get('insertion_pinflops'), f'{source}:{pin}:{corner}:insertion_pinflops')
        pins[pin] = vals
    return dict(schema=SCHEMA, view_lib_sha256=digest(lib), signed=True,
                signoff_source=str(source), signoff_verdict=record['verdict'], pins=pins)


def from_budget(lib, pins, source):
    """Explicit first-route parent budget, never a SIGNED/measured assertion.

    pins = {clock_pin: {tt: ps, ff: ps}}. No maxima or ratios are inferred.
    """
    return dict(schema=SCHEMA, view_lib_sha256=digest(lib), signed=False,
                signoff_verdict=None, budget_source=str(source),
                pins={pin: {c: dict(mean_ps=value[c], n=0, basis='parent_budget', source=str(source))
                            for c in ('tt', 'ff')} for pin, value in pins.items()})


def _validate(raw, lib, pins, source, release):
    if raw.get('schema') != SCHEMA or raw.get('view_lib_sha256') != digest(lib):
        raise ContractError(f'{source}: wrong schema or selected liberty does not match clock contract')
    if release and (raw.get('signed') is not True or raw.get('signoff_verdict') != 'SIGNED'):
        raise ContractError(f'{source}: missing SIGNED clock contract')
    out = {}
    for pin in pins:
        entry = raw.get('pins', {}).get(pin, {})
        vals = {}
        for corner in ('tt', 'ff'):
            stat = entry.get(corner, {})
            basis = stat.get('basis')
            if basis not in {'pin_register_mean', 'parent_budget'} or not stat.get('source'):
                raise ContractError(f'{source}:{pin}:{corner}: explicit mean/budget and source basis required')
            if basis == 'parent_budget':
                if release or raw.get('signed'):
                    raise ContractError(f'{source}:{pin}:{corner}: parent budget cannot assert SIGNED')
                mean = stat.get('mean_ps')
                if isinstance(mean, bool) or not isinstance(mean, (int, float)) or not math.isfinite(mean) or mean < 0:
                    raise ContractError(f'{source}:{pin}:{corner}: invalid parent budget')
                vals[corner] = dict(mean_ps=float(mean), n=0, basis=basis, source=stat['source'])
            else:
                vals[corner] = _mean(stat, stat['source'])
        out[pin] = dict(corners=vals, signed=raw.get('signed') is True,
                        contract_source=str(source), signoff_source=raw.get('signoff_source'))
    return out


def load(core, root=None, require_signed=True):
    """Per clock pin {corners:{tt/ff:{mean_ps,n,basis,source}}, signed,...}.

    Search is confined to the exact selected liberty's directory. Never borrow a
    different variant's measurement or infer mean from ETM maximum/minimum.
    """
    if not core.get('lib'):
        raise ContractError(f"{core.get('inst')}: selected core liberty required")
    lib = C.resolve(core['lib'], root)
    if not lib.is_file():
        raise ContractError(f'{lib}: selected core liberty missing')
    pins = sorted(C.clock_pins(core, root))
    if not pins:
        raise ContractError(f'{lib}: no clock pins')
    contract = lib.parent / 'clock_contract.json'
    if contract.is_file():
        return _validate(json.loads(contract.read_text()), lib, pins, contract, require_signed)
    signed = lib.parent / 'signoff.json'
    if signed.is_file():
        record = json.loads(signed.read_text())
        raw = from_signoff(lib, record, signed, pins)
        return _validate(raw, lib, pins, signed, require_signed)
    if require_signed:
        raise ContractError(f'{lib}: no SIGNED mean clock contract; ETM max_clock_tree_path is not a mean')
    path = lib.parent / 'insertion.json'
    if not path.is_file():
        raise ContractError(f'{lib}: pin-register mean measurement missing (no ETM-max fallback)')
    raw = json.loads(path.read_text())
    out = {}
    for pin in pins:
        measurement = raw.get('clock_measurements', {}).get(pin)
        if measurement is None:
            if len(pins) != 1 or raw.get('lib_clock_pin') != pin:
                raise ContractError(f'{path}: explicit clock-pin mapping required for {pin}')
            measurement = raw
        if measurement.get('raw_source') is not True or measurement.get('parasitics') != 'spef':
            raise ContractError(f'{path}:{pin}: raw extracted pin-insertion measurement required')
        vals = {}
        for corner in ('tt', 'ff'):
            item = measurement.get(corner, {})
            if item.get('errors'):
                raise ContractError(f'{path}:{pin}:{corner}: clock measurement has errors')
            vals[corner] = _mean(item.get('boundary'), f'{path}:{pin}:{corner}:boundary')
        out[pin] = dict(corners=vals, signed=False, contract_source=str(path),
                        signoff_source=None, diagnostic='historical measurement; not release qualified')
    return out


def latency_table(P, tn, root=None, require_signed=True):
    rows = []
    t = P.types[tn]
    for core in t.get('hard_cores', []):
        for pin, value in sorted(load(core, root, require_signed).items()):
            vals = value['corners']
            rows.append(dict(inst=core['inst'], module=core.get('module', core['inst']), pin=pin,
                             rise_ps=vals['tt']['mean_ps'], fall_ps=vals['tt']['mean_ps'],
                             corners=vals, basis=vals['tt']['basis'], signed=value['signed'],
                             contract_source=value['contract_source'], signoff_source=value['signoff_source'],
                             lib=core['lib'], tap=C.core_tap_of(t, core['inst'], pin) or 'grid'))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--lib', required=True)
    ap.add_argument('--inst', default='core')
    ap.add_argument('--signoff', help='export this SIGNED record to --out')
    ap.add_argument('--diagnostic', action='store_true')
    ap.add_argument('--out')
    args = ap.parse_args()
    if args.signoff:
        source = Path(args.signoff)
        result = from_signoff(args.lib, json.loads(source.read_text()), source)
    else:
        result = load(dict(inst=args.inst, lib=args.lib), require_signed=not args.diagnostic)
    text = json.dumps(result, indent=1) + '\n'
    if args.out:
        Path(args.out).write_text(text)
    else:
        print(text, end='')


if __name__ == '__main__':
    main()
