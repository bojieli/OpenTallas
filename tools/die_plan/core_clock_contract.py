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


def plan_budget(t, core, pins):
    """{pin: {tt, ff, source}} declared by the plan's explicit parent_budget core taps of this core inst
    (insertion_ps TT, insertion_ff_ps FF).  KIT-TRIAGE-1/G3 11-01: the estimate form of a core whose selected view
    carries no contract file yet (12.3 'current real view' number, 12.4a 'declared budget until a kit exists,
    labelled'); never SIGNED."""
    out, inst = {}, core.get('inst')
    for tp in (t.get('clock', {}) or {}).get('taps', []) or []:
        if tp.get('kind') != 'core' or not str(tp.get('budget_owner', '')).startswith('parent_budget'):
            continue
        if 'insertion_ps' not in tp or 'insertion_ff_ps' not in tp:
            continue
        nm = tp.get('name', '')
        if nm == inst:
            sel = list(pins)
        elif nm.startswith(f'{inst}.') and tp.get('merged_clock_ports'):
            sel = [p for p in tp['merged_clock_ports'] if p in pins]
        elif nm.startswith(f'{inst}.') and nm[len(inst) + 1:] in pins:
            sel = [nm[len(inst) + 1:]]
        else:
            continue
        for pin in sel:
            out[pin] = dict(tt=float(tp['insertion_ps']), ff=float(tp['insertion_ff_ps']),
                            source=f"plan tap {nm}: {tp['budget_owner']}")
    return out


def load(core, root=None, require_signed=True, plan_type=None):
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
    budget = plan_budget(plan_type, core, pins) if plan_type is not None and not path.is_file() else {}
    if budget and set(budget) == set(pins):
        # estimate form (signed False -> release_qualified False): the plan's own parent_budget means for this core
        src = '; '.join(sorted({b['source'] for b in budget.values()}))
        raw = from_budget(lib, {p: dict(tt=b['tt'], ff=b['ff']) for p, b in budget.items()}, src)
        return _validate(raw, lib, pins, f"plan parent_budget ({core.get('inst')})", False)
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


def _lib_groups(text, kind):
    """Brace-matched Liberty groups, including unnamed memory/timing groups."""
    for m in re.finditer(r"\b" + kind + r"\s*\(\s*([^)]*)\)\s*\{", text):
        i, depth = m.end(), 1
        while depth and i < len(text):
            depth += (text[i] == '{') - (text[i] == '}')
            i += 1
        if depth:
            raise ContractError(f'truncated Liberty {kind} group')
        yield m.group(1).strip().strip('"'), text[m.end():i-1]


def native_memory_clock_model(core, root=None):
    """Reference a verified native SRAM CLK timing model, never a CTS mean.

    Recognition requires the aligned-v2 producer's SRAM identity plus complete
    TT/FF native memory interface arcs. Ordinary logic still needs measured means.
    """
    lib = C.resolve(core['lib'], root)
    module = core.get('module', core['inst'])
    meta = lib.parent / (module + '.json')
    if not meta.is_file():
        return None
    aligned = json.loads(meta.read_text()).get('alignment_v2', {})
    if aligned.get('kind') != 'sram':
        return None
    spec = aligned.get('spec', {})
    if spec.get('name') != module or aligned.get('verification', {}).get('pass') is not True:
        raise ContractError(f'{meta}: native SRAM identity/verification missing')
    references = {}
    clock_names = None
    for corner in ('tt', 'ff'):
        selected = lib if corner == 'tt' else lib.with_name(lib.name.replace('_tt.lib', '_ff.lib'))
        if corner == 'tt' and not lib.name.endswith('_tt.lib'):
            raise ContractError(f'{lib}: native SRAM requires explicit TT/FF selected views')
        if not selected.is_file():
            raise ContractError(f'{selected}: native SRAM selected corner absent')
        text = selected.read_text()
        cells = list(_lib_groups(text, 'cell'))
        if len(cells) != 1 or cells[0][0] != module:
            raise ContractError(f'{selected}: native SRAM cell identity mismatch')
        body = cells[0][1]
        memories = list(_lib_groups(body, 'memory'))
        if len(memories) != 1 or not re.search(r'\btype\s*:\s*ram\s*;', memories[0][1]):
            raise ContractError(f'{selected}: native SRAM memory group absent')
        for key, expected in [('address_width', (int(spec['words'])-1).bit_length()), ('word_width', int(spec['bits']))]:
            if not re.search(r'\b' + key + r'\s*:\s*' + str(expected) + r'\s*;', memories[0][1]):
                raise ContractError(f'{selected}: native SRAM {key} mismatch')
        pins = list(C._groups(body))
        clocks = sorted({name for _, name, b in pins if re.search(r'\bclock\s*:\s*true\s*;', b)})
        if len(clocks) != 1 or (clock_names is not None and clocks != clock_names):
            raise ContractError(f'{selected}: native SRAM requires matching single clock pins')
        clock_names = clocks
        counts = dict(setup=0, hold=0, clk_to_q=0)
        for _, name, b in pins:
            direction = re.search(r'\bdirection\s*:\s*(input|output)\s*;', b)
            if name in clocks or not direction:
                continue
            required = ('setup', 'hold') if direction[1] == 'input' else ('clk_to_q',)
            found = set()
            for _, arc in _lib_groups(b, 'timing'):
                related = re.search(r'\brelated_pin\s*:\s*"?([^";\s]+)"?\s*;', arc)
                typ = re.search(r'\btiming_type\s*:\s*(\w+)\s*;', arc)
                if not related or related[1] != clocks[0] or not typ:
                    continue
                category = ('setup' if typ[1].startswith('setup_') else 'hold' if typ[1].startswith('hold_') else
                            'clk_to_q' if typ[1] in ('rising_edge', 'falling_edge') else None)
                if category not in required:
                    continue
                groups = ('cell_rise', 'cell_fall') if category == 'clk_to_q' else ('rise_constraint', 'fall_constraint')
                for group in groups:
                    tables = list(_lib_groups(arc, group))
                    values = re.findall(r'\bvalues\s*\((.*?)\)\s*;', tables[0][1], re.S) if tables else []
                    tokens = re.split(r'[\s,"\\]+', ''.join(values).strip())
                    try:
                        nums = [float(n) for n in tokens if n]
                    except ValueError:
                        nums = []
                    if not nums or any(not math.isfinite(n) for n in nums):
                        raise ContractError(f'{selected}:{name}: native {category} {group} table missing')
                found.add(category)
            if not set(required) <= found:
                raise ContractError(f'{selected}:{name}: native interface arcs incomplete: {required}')
            for category in found:
                counts[category] += 1
        if not all(counts.values()):
            raise ContractError(f'{selected}: native SRAM interface arc census empty')
        references[corner] = dict(lib=str(selected), sha256=digest(selected), arc_census=counts)
    return dict(schema='opentallas.native_memory_clock_model.v1', inst=core['inst'], module=module,
                clock_pins=clock_names, basis='native_liberty_clock_pin', metadata=str(meta),
                metadata_sha256=digest(meta), corners=references)


def native_clock_models(P, tn, root=None):
    models = []
    t = P.types[tn]
    for core in t.get('hard_cores', []):
        model = native_memory_clock_model(core, root)
        if model is None:
            continue
        for tap in t.get('clock', {}).get('taps', []):
            name = tap.get('name', '')
            if tap.get('kind') == 'core' and (name == core['inst'] or name.startswith(core['inst'] + '.')):
                raise ContractError(f"{tn}/{name}: native SRAM early compensation needs an explicit native-clock policy")
        models.append(model)
    return models


def grid_core_estimate(t, core, root=None):
    """KIT-TRIAGE-1/leafmean 11-01 (class, default-on; OWNER 12.28b closure first): a hard core of an unsigned
    estimate-form kit that is NOT a die early tap (tap 'grid': the partition-local tree reaches its pin) and whose
    selected view carries no contract, signoff or insertion record keeps the legacy kit row of every other unsigned
    kit (DIE-KV-60/taps form): the selected view's liberty clock latency, basis legacy_etm_max_bound, labelled
    signed=False / release_qualified=False.  It is never a mean and never feeds a die tap; SIGNED means replace it once
    the core view is signed.  Rows for early-tap pins are never estimated here (the tap-vs-mean check stays)."""
    if not core.get('lib'):
        return None
    lib = C.resolve(core['lib'], root)
    if not lib.is_file() or any((lib.parent / f).is_file()
                                for f in ('clock_contract.json', 'signoff.json', 'insertion.json')):
        return None
    tt = C.lib_clocks(lib)
    if not tt or any(C.core_tap_of(t, core['inst'], pin) for pin in tt):
        return None
    ff_lib = lib.with_name(lib.name.replace('_tt.lib', '_ff.lib'))
    ff = C.lib_clocks(ff_lib) if lib.name.endswith('_tt.lib') and ff_lib.is_file() else {}
    src = f'{core["lib"]}: liberty clock latency (legacy ETM bound, estimate; no measured mean in the selected view)'
    rows = []
    for pin, v in sorted(tt.items()):
        fv = ff.get(pin, v)
        corners = {c: dict(mean_ps=round(float(x['rise']), 2), n=0, basis='legacy_etm_max_bound', source=src)
                   for c, x in (('tt', v), ('ff', fv))}
        rows.append(dict(inst=core['inst'], module=core.get('module', core['inst']), pin=pin,
                         rise_ps=corners['tt']['mean_ps'], fall_ps=round(float(v['fall']), 2),
                         corners=corners, basis='legacy_etm_max_bound', signed=False, release_qualified=False,
                         contract_source=src, signoff_source=None, lib=core['lib'], tap='grid'))
    return rows


def latency_table(P, tn, root=None, require_signed=True):
    rows = []
    t = P.types[tn]
    nolib = sorted(c.get('module', c['inst']) for c in t.get('hard_cores', []) if 'lib' not in c)
    if nolib:
        raise ContractError(f'{tn}: WAIT-DEP hard cores have no selected lib (no routed/provisional view yet): '
                            + ', '.join(dict.fromkeys(nolib)))
    native = {m['inst'] for m in native_clock_models(P, tn, root)}
    for core in t.get('hard_cores', []):
        if core['inst'] in native:
            continue
        try:
            loaded = load(core, root, require_signed, plan_type=t)
        except ContractError:
            est = None if require_signed else grid_core_estimate(t, core, root)
            if est is None:
                raise
            rows.extend(est)
            continue
        for pin, value in sorted(loaded.items()):
            vals = value['corners']
            rows.append(dict(inst=core['inst'], module=core.get('module', core['inst']), pin=pin,
                             rise_ps=vals['tt']['mean_ps'], fall_ps=vals['tt']['mean_ps'],
                             corners=vals, basis=vals['tt']['basis'], signed=value['signed'],
                             release_qualified=value['signed'],
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
