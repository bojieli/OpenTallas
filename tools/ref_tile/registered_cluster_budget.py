"""ROOT-review candidate admission for physical level 1 registered clusters.

This is not native qualification or permission to adopt a hardened view. A padded
source may establish eligibility to *test* a pad-free successor. That successor
still owes its own native TT/FF and die-link/routed closure evidence.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path


def evidence_paths(spec, root):
    """Files needed when the exact candidate is materialised or shipped remotely."""
    entry = spec.get('registered_cluster_candidate')
    if not entry:
        return []
    receipt = json.loads((Path(root) / entry['path']).read_text())
    return sorted({entry['path'], 'tools/hier_contract/pinreg_audit.py',
                   *(x['path'] for x in receipt['sources']),
                   *(receipt[k]['path'] for k in ('gate', 'insertion', 'tt_lib', 'ff_lib', 'tt_probe', 'ff_probe'))})


def check(spec, root):
    """Fail closed on absent, stale or incomplete experimental admission evidence."""
    root = Path(root).resolve()
    def need(ok, message):
        if not ok:
            raise ValueError('registered cluster candidate: ' + message)
    def number(v):
        return isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v)
    def artifact(entry):
        need(isinstance(entry, dict), 'missing artifact')
        p = (root / str(entry.get('path', ''))).resolve()
        need(p.is_relative_to(root) and p.is_file(), 'artifact outside tree or absent')
        need(hashlib.sha256(p.read_bytes()).hexdigest() == entry.get('sha256'), 'stale artifact: ' + str(p))
        return p
    need(spec.get('kind') == 'cluster' and spec.get('cluster_level', 1) == 1, 'physical level must remain 1')
    need(spec.get('registered_boundary_contract') == 'all-data-pins', 'explicit registered boundary required')
    need(spec.get('child_clock_ref') == 'boundary' and spec.get('children'), 'actual boundary child references required')
    need(number(spec.get('route', {}).get('io_hold_margin_ns')) and spec['route']['io_hold_margin_ns'] >= .03,
         'io_hold_margin_ns must be >= .03')
    entry = spec.get('registered_cluster_candidate')
    receipt = json.loads(artifact(entry).read_text())
    need(receipt.get('schema') == 1 and receipt.get('scope') == 'candidate-only', 'candidate-only receipt required')
    need(receipt.get('source_commit') and len(receipt['source_commit']) == 40, 'full source commit required')
    # Timing, source selection and the child hard views must describe this exact boundary.
    identity = {k: spec.get(k) for k in ('top', 'sources', 'params', 'defines', 'hard_define', 'children', 'clock_port', 'reset_ports')}
    need(receipt.get('identity') == identity, 'receipt does not describe selected RTL/parameters/children')
    sources = receipt.get('sources', [])
    need(sources and {x['path'] for x in sources} == set(spec.get('sources', [])), 'complete RTL source census required')
    for item in sources:
        artifact(item)
    gate = json.loads(artifact(receipt.get('gate')).read_text())
    binding = gate.get('source_binding', {})
    need(binding.get('start_commit') == receipt['source_commit'] and binding.get('remote_archive_verified') is True,
         'verified source-pinned gate required')
    shipped = {f['path']: f for f in binding.get('files', [])}
    need(all(shipped.get(x['path'], {}).get('sha256') == x['sha256'] for x in sources), 'RTL differs from actual gate archive')
    reset = gate.get('reset_landing', {})
    need(reset.get('ok') is True and reset.get('waived') is False and reset.get('max_sinks') == 2
         and reset.get('ports') and all(p.get('sinks') == 2 and p.get('flops') == 2 and p.get('macros') == 0 for p in reset['ports']),
         'actual two-flop reset landing required')
    need(receipt.get('reset_stages') == 2 and len(receipt.get('reset_stage_cells', [])) == 2,
         'source-reviewed two-stage reset chain required')
    clocks = spec.get('clock_ports') or [spec.get('clock_port')]
    need(len(clocks) == 1 and clocks[0] and not spec.get('clock_entry_domains'), 'single real clock root required')
    measurements = gate.get('clock', {}).get('clock_measurements', [])
    need(len(measurements) == 1 and measurements[0].get('source') == clocks[0], 'per-root TT/FF measurements required')
    cells = {Path(c['view']).name for c in spec['children']}
    for corner in ('tt', 'ff'):
        m = measurements[0].get(corner, {})
        b = m.get('boundary', {})
        need(b.get('n', 0) > 0 and all(number(b.get(k)) for k in ('mean', 'min', 'max')), 'real ' + corner + ' root reference required')
        refs = m.get('child_flop', {}).get('refs', {})
        need(set(refs) == cells and all(x.get('basis') == 'insertion.json boundary mean' and number(x.get('ref_ps'))
                                     and x.get('pins', 0) > 0 for x in refs.values()), 'real ' + corner + ' child references required')
    budget = receipt.get('parent_boundary_budget', {})
    need(budget.get('owner') and budget.get('candidate_only') is True and budget.get('C_ps') == 25
         and budget.get('hold_uncertainty_ps') == 25 and budget.get('setup_uncertainty_ps') == 60
         and budget.get('neighbor_skew_max_ps') == 80 and budget.get('native_tt_launch_max_ps') == 220
         and budget.get('native_tt_capture_max_ps') == 190 and budget.get('required_die_checks') == ['D1', 'D2', 'D3', 'D4'],
         'explicit unchanged parent boundary budget required')
    need(budget.get('entry_compensation_ps') == {clocks[0]: {c: -measurements[0][c]['boundary']['mean'] for c in ('tt', 'ff')}},
         'parent must explicitly price measured TT/FF boundary compensation')
    # Recompute the complete census from actual source-pinned STA output; never trust a boolean PASS field.
    loader = importlib.util.spec_from_file_location('_registered_pinreg_audit', root / 'tools/hier_contract/pinreg_audit.py')
    audit = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(audit)
    ins = json.loads(artifact(receipt.get('insertion')).read_text())
    context = receipt.get('native_context', {})
    need(context.get('source_commit') == receipt['source_commit'] and context.get('db') == ins.get('db')
         and context.get('adoption_proof') is False, 'source-pinned native STA context required')
    artifact(receipt.get('tt_probe'))
    artifact(receipt.get('ff_probe'))
    actual = ins.get('clock_measurements', {}).get(clocks[0], {})
    for corner in ('tt', 'ff'):
        need(actual.get(corner, {}).get('boundary') == measurements[0][corner]['boundary'] and
             actual.get(corner, {}).get('child_flop', {}).get('refs') == measurements[0][corner]['child_flop']['refs'],
             'STA insertion differs from gate')
    census = {}
    for corner in ('tt', 'ff'):
        lib = audit.parse_lib(artifact(receipt.get(corner + '_lib')))
        need(lib.get('cell') == spec['top'], 'native model top differs from selected source')
        refs = audit.clock_refs(lib, ins, corner)
        need(set(refs) == set(clocks) and all(str(r.get('src', '')).startswith('insertion.json') for r in refs.values()),
             'native model lacks measured clock reference')
        pins = audit.pin_metrics(lib, refs)
        # OpenSTA ETM writes physical supply pins as arc-free inputs. No user exclusion is permitted.
        for rail in ('VDD', 'VSS'):
            if rail in pins and not lib['pins'][rail]['arcs']:
                del pins[rail]
        need(pins and not any(p['comb'] or p['dir'] not in ('input', 'output') for p in pins.values()), 'combinational or unknown boundary')
        need(all(p['out'] is not None and p['lmin'] is not None if p['dir'] == 'output' else
                 p['inp'] is not None and p['hold'] is not None for p in pins.values()), 'unregistered or unconstrained boundary')
        census[corner] = pins
    need(set(census['tt']) == set(census['ff']), 'TT/FF pin census mismatch')
    need(min(p['lmin'] for p in census['ff'].values() if p['dir'] == 'output') >= 25, 'actual FF output launch below C25')
    return census
