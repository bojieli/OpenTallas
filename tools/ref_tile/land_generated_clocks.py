"""Typed, source-bound LAND bank-clock proposal. Not installed in gate hooks.

This API never alters a primary clock, removes a path, or grants CTS admission.
An emitted script proves only one exact source-bound compiled scenario.
"""
import hashlib
import itertools
import json
import math
import re
from pathlib import Path

SCHEMA = 'ot.land-bank-clock.v1'
CASE = ('K', 'phase_index', 'extra_age_cycles', 'reset_order')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def artifact(root, item):
    if not isinstance(item, dict) or set(item) != {'path', 'sha256'}:
        raise ValueError('artifact requires path and sha256')
    path = (root / item['path']).resolve()
    if not path.is_relative_to(root) or not path.is_file() or digest(path) != item['sha256']:
        raise ValueError('missing, foreign or stale artifact: ' + str(item.get('path')))
    return path


def word(value):
    # Literal instance identities only. No glob, regexp, Tcl, or duplicate wrapper.
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_./]*', value):
        raise ValueError('unsafe or nonliteral identity')
    if value.count('u_ot_pr_core') > 1:
        raise ValueError('double wrapper prefix')
    return '{' + value + '}'


def exact_keys(data, expected, what):
    if not isinstance(data, dict) or set(data) != set(expected):
        raise ValueError(what + ': missing or unknown fields')


def liberty_groups(text, kind):
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    for match in re.finditer(r'\b'+kind+r'\s*\(\s*([^)]*?)\s*\)\s*\{', text):
        start = match.end(); depth = 1; quoted = False; escaped = False
        for i in range(start, len(text)):
            char = text[i]
            if escaped:
                escaped = False; continue
            if char == '\\':
                escaped = True; continue
            if char == '"':
                quoted = not quoted
            if not quoted:
                depth += (char == '{') - (char == '}')
            if depth == 0:
                yield match.group(1).strip('"'), text[start:i]
                break
        else:
            raise ValueError('unterminated native Liberty group')


def validate_certificate(cert):
    if cert.get('status') != 'BEHAVIORAL_EDGE_WINDOW_PASS_NOT_PHYSICAL_TIMING' or not cert.get('two_boot_epochs'):
        raise ValueError('actual two-boot behavioral certificate required')
    if cert.get('period_T') != 4 or cert.get('high_pulse_T') != .5:
        raise ValueError('only actual period4T, pulseT/2 LAND banks reviewed')
    rows = cert['rows']
    cases = {tuple(r[k] for k in CASE) for r in rows}
    extras = {r['extra_age_cycles'] for r in rows}
    expected = set(itertools.product(range(8), range(8), sorted(extras), range(2)))
    if extras not in ({0, 2}, {0, 1, 2}) or cases != expected or len(rows) != len(cases)*4:
        raise ValueError('missing/duplicate legal K, phase, age or reset scenario')
    if {(tuple(r[k] for k in CASE), r['bank']) for r in rows} != {(v,b) for v in cases for b in range(4)}:
        raise ValueError('incomplete bank coverage')
    for row in rows:
        if not (row.get('checks',0)>0 and .25 <= row['min_age_T'] <= row.get('max_age_T',0) <= 3.25 and row.get('min_overwrite_gap_T',0) >= .75):
            raise ValueError('unproven actual behavioral bank window')
        for side in ('write', 'read'):
            p = row[side+'_phase_cycles']
            if type(p) is not int or p not in range(4) or row[side+'_generated_edges'] != [1+2*p,2+2*p,9+2*p]:
                raise ValueError('wrong actual generated bank waveform')
        age = (row['read_phase_cycles']-row['write_phase_cycles']) % 4 + row['phase_index']/8
        if abs(age-row['min_age_T']) > 1e-8:
            raise ValueError('phase collapsed or disagrees with actual bank age')
    return rows, cases


def validate(spec, root):
    """Validate a deliberately narrow source/certificate/compiled-scenario join.

    compiled manifest must be produced by the compiler/die phase owner. It is
    never manufactured from an E_case age or a behavioral test's root phase.
    Review of that producer is a separate prerequisite to installing gate hooks.
    """
    root = Path(root).resolve()
    c = spec.get('land_generated_clocks')
    exact_keys(c, ('schema', 'sources', 'top', 'params', 'defines', 'certificate',
                   'compiled', 'banks', 'reserves_ps', 'icg', 'behavioral_binding'), 'LAND contract')
    if c['schema'] != SCHEMA or spec.get('clock') != 'multiple_cts_roots':
        raise ValueError('LAND contract requires typed multi-root policy')
    if any(spec.get(k) for k in ('sdc_extra', 'boundary_tcl', 'pre_cts_extra')):
        raise ValueError('LAND custom timing hooks forbidden')
    if (c['top'], c['params'], c['defines']) != (spec['top'], spec.get('params', {}), spec.get('defines', [])):
        raise ValueError('top/parameter/define binding mismatch')
    if sorted(x['path'] for x in c['sources']) != sorted(spec['sources']):
        raise ValueError('exact RTL source coverage required')
    for x in c['sources']:
        artifact(root, x)
    if c['reserves_ps'] != {'same_setup': 60, 'cross_setup': 150,
                            'cross_setup_slow': 210, 'hold': 25, 'cross_hold': 100}:
        raise ValueError('timing reserves may not change')
    icg = c['icg']
    exact_keys(icg, ('master', 'clock_pin', 'enable_pin', 'output_pin', 'liberty'), 'native ICG')
    for key in ('master','clock_pin','enable_pin','output_pin'):
        word(icg[key])
    libtext = artifact(root, icg['liberty']).read_text()
    cells = [body for name, body in liberty_groups(libtext, 'cell') if name == icg['master']]
    if len(cells) != 1 or not re.search(r'\bclock_gating_integrated_cell\s*:\s*latch_posedge\s*;', cells[0]):
        raise ValueError('actual native latch-posedge ICG Liberty required')
    for pin, attribute in (('clock_pin','clock_gate_clock_pin'),('enable_pin','clock_gate_enable_pin'),('output_pin','clock_gate_out_pin')):
        bodies = [body for name, body in liberty_groups(cells[0], 'pin') if name == icg[pin]]
        if len(bodies) != 1 or not re.search(r'\b'+attribute+r'\s*:\s*true\s*;', bodies[0]):
            raise ValueError('native ICG pin semantics missing: ' + pin)
    cert = json.loads(artifact(root, c['certificate']).read_text())
    compiled = json.loads(artifact(root, c['compiled']).read_text())
    behavioral = json.loads(artifact(root, c['behavioral_binding']).read_text())
    exact_keys(behavioral, ('sources','top','params','defines','certificate_sha256','witness_sha256'), 'behavioral source binding')
    for key in ('sources','top','params','defines'):
        if behavioral[key] != c[key]:
            raise ValueError('behavioral source binding mismatch: ' + key)
    if behavioral['certificate_sha256'] != c['certificate']['sha256'] or behavioral['witness_sha256'] != cert.get('witness_sha256'):
        raise ValueError('behavioral certificate/witness binding mismatch')
    exact_keys(compiled, ('schema', 'sources', 'top', 'params', 'defines', 'case',
                          'root_waveforms_ns', 'reset_origin', 'enable_witness',
                          'mapped_netlist', 'mapped_topology', 'compiler_inputs'), 'compiled manifest')
    if compiled['schema'] != 'ot.land-compiled-scenario.v1':
        raise ValueError('compiled scenario schema mismatch')
    for key in ('sources', 'top', 'params', 'defines'):
        if compiled[key] != c[key]:
            raise ValueError('compiled source binding mismatch: ' + key)
    # Inputs, enable waveform witness and mapped netlist are immutable dependencies,
    # not approval booleans. Runtime Tcl also checks the exact mapped netlist hash.
    for x in compiled['compiler_inputs']:
        artifact(root, x)
    if not compiled['compiler_inputs']:
        raise ValueError('compiled scenario requires actual compiler inputs')
    artifact(root, compiled['enable_witness'])
    if compiled['enable_witness']['sha256'] != cert.get('witness_sha256'):
        raise ValueError('enable waveform witness differs from actual certificate')
    artifact(root, compiled['mapped_netlist'])
    topology = json.loads(artifact(root, compiled['mapped_topology']).read_text())
    if topology.get('mapped_sha256') != compiled['mapped_netlist']['sha256']:
        raise ValueError('mapped topology/netlist binding mismatch')
    if not isinstance(compiled['reset_origin'], dict) or set(compiled['reset_origin']) != {'write', 'read', 'first_usable'}:
        raise ValueError('explicit reset-origin and boot first-usable binding required')
    if any(type(x) is not int or x < 0 for x in compiled['reset_origin'].values()):
        raise ValueError('reset origin must be compiled absolute edges')
    rows, cases = validate_certificate(cert)
    selected = compiled['case']
    exact_keys(selected, CASE, 'compiled case')
    selected_key = tuple(selected[k] for k in CASE)
    if selected_key not in cases:
        raise ValueError('compiled case outside proven coverage')
    selected_rows = {r['bank']: r for r in rows if tuple(r[k] for k in CASE) == selected_key}
    if len(c['banks']) != 8:
        raise ValueError('exactly eight physical bank ICGs required')
    identities = set(); roles = set(); names = set()
    for b in c['banks']:
        exact_keys(b, ('name','side','bank','source_port','source_clock','cell','master',
                       'clock_pin','enable_pin','output_pin'), 'bank')
        for field in ('name','source_port','source_clock','cell','master','clock_pin','enable_pin','output_pin'):
            word(b[field])
        if b['side'] not in ('write', 'read') or type(b['bank']) is not int or b['bank'] not in range(4):
            raise ValueError('invalid bank role')
        if b['source_port'] not in spec['clock_ports']:
            raise ValueError('foreign clock source')
        if b['cell'] in identities or b['name'] in names or (b['side'],b['bank']) in roles:
            raise ValueError('duplicate bank identity')
        identities.add(b['cell']); names.add(b['name']); roles.add((b['side'],b['bank']))
        if any(b[k] != icg[k] for k in ('master','clock_pin','enable_pin','output_pin')):
            raise ValueError('bank differs from native ICG identity')
        actual = topology.get('banks', {}).get(b['cell'])
        if actual != {k:b[k] for k in ('master','source_port','clock_pin','enable_pin','output_pin')}:
            raise ValueError('mapped ICG source/target/master topology mismatch')
        row = selected_rows[b['bank']]
        # Preserve native phase. PH .875 must stay .875 rather than E_case1/PH0.
        for side in ('write','read'):
            p = row[side+'_phase_cycles']
            if type(p) is not int or p not in range(4) or row[side+'_generated_edges'] != [1+2*p,2+2*p,9+2*p]:
                raise ValueError('wrong actual generated bank waveform')
        nominal = (row['read_phase_cycles']-row['write_phase_cycles']) % 4
        if abs(nominal + row['phase_index']/8 - row['min_age_T']) > 1e-8:
            raise ValueError('phase collapsed or disagrees with actual bank age')
        waveform = compiled['root_waveforms_ns'].get(b['source_port'])
        if not isinstance(waveform, list) or len(waveform) != 3:
            raise ValueError('actual root period/rise/fall required')
        period,rise,fall = waveform
        if not all(type(x) in (int,float) and math.isfinite(x) for x in waveform) or period <= 0 or not 0 <= rise < fall < rise+period:
            raise ValueError('invalid root waveform')
    if any(len({b['source_port'] for b in c['banks'] if b['side']==side}) != 1 for side in ('write','read')):
        raise ValueError('one exact physical source port per bank family required')
    ports = {b['side']:b['source_port'] for b in c['banks']}
    if len(set(ports.values())) != 2 or set(compiled['root_waveforms_ns']) != set(ports.values()):
        raise ValueError('exact two physical source roots required')
    wp,wr,_ = compiled['root_waveforms_ns'][ports['write']]
    rp,rr,_ = compiled['root_waveforms_ns'][ports['read']]
    if wp != rp or abs(((rr-wr)/wp)%1-selected['phase_index']/8)>1e-8:
        raise ValueError('compiled native root phase disagrees with scenario')
    return c, compiled, selected_rows


def emit(spec, root):
    """Return preCTS proposal Tcl, requiring existing actual primary roots."""
    c, compiled, rows = validate(spec, root)
    o = ['# LAND GENERATED CLOCK PROPOSAL: no automatic gate admission',
         '# Requires separately reviewed producer, native census and TT/FF checks.',
         'if {![llength [info commands ot_cf_root]]} {error "LAND: native family API missing"}',
         'ot_cf_refresh',
         'if {![info exists ::ot_land_loaded_liberty]} {error \"LAND: exact loaded native ICG Liberty required\"}',
         'if {[lindex [exec sha256sum -- $::ot_land_loaded_liberty] 0] ne {'+c['icg']['liberty']['sha256']+'}} {error \"LAND: wrong native ICG Liberty\"}',
         'proc ot_land_one {objects label} {',
         '  if {[llength $objects] != 1} {error "LAND: missing/ambiguous $label"}',
         '  return [lindex $objects 0]', '}',
         'proc ot_land_close {a b label} {',
         '  if {abs($a-$b)>1e-5} {error "LAND: wrong $label ($a != $b)"}', '}',
         'if {![info exists ::ot_land_mapped_netlist]} {error "LAND: exact running mapped netlist path required"}',
         'set ot_land_sha [lindex [exec sha256sum -- $::ot_land_mapped_netlist] 0]',
         'if {$ot_land_sha ne {'+compiled['mapped_netlist']['sha256']+'}} {error "LAND: stale mapped netlist"}']
    for b in c['banks']:
        q = {k:word(b[k]) for k in ('name','source_port','source_clock','cell','master')}
        period,rise,fall = compiled['root_waveforms_ns'][b['source_port']]
        edges = rows[b['bank']][b['side']+'_generated_edges']
        o += [f'set ot_lp [ot_land_one [get_ports {q["source_port"]}] source_port]',
              f'set ot_lc [ot_land_one [get_clocks {q["source_clock"]}] source_clock]',
              f'if {{[ot_cf_root {q["source_clock"]}] ne {q["source_clock"]}}} {{error "LAND: source clock is not primary"}}',
              'if {[lmap ot_lsp [$ot_lc sources] {get_full_name $ot_lsp}] ne [get_full_name $ot_lp]} {error "LAND: foreign primary source"}',
              f'ot_land_close [sta::time_sta_ui [$ot_lc period]] {period} root_period',
              f'ot_land_close [sta::time_sta_ui [lindex [$ot_lc waveform] 0]] {rise} root_rise',
              f'ot_land_close [sta::time_sta_ui [lindex [$ot_lc waveform] 1]] {fall} root_fall',
              f'set ot_li [ot_land_one [get_cells -hierarchical {q["cell"]}] ICG_cell]',
              f'if {{[get_property $ot_li ref_name] ne {q["master"]}}} {{error "LAND: wrong native ICG master"}}']
        # Exact native gate pins, never a name-derived clock target or wildcard.
        for pinvar,field in (('ot_lpin','clock_pin'),('ot_lepin','enable_pin'),('ot_lout','output_pin')):
            o.append(f'set {pinvar} [ot_land_one [get_pins {word(b["cell"]+"/"+b[field])}] ICG_{field}]')
        o += ['set ot_lroots {}',
              'foreach ot_lowner [get_property $ot_lpin clocks] {lappend ot_lroots [ot_cf_root [get_full_name $ot_lowner]]}',
              f'if {{[lsort -unique $ot_lroots] ne {q["source_clock"]}}} {{error "LAND: foreign ICG clock lineage"}}',
              f'if {{[llength [get_clocks -quiet {q["name"]}]]}} {{error "LAND: generated clock already exists"}}',
              f'create_generated_clock -name {q["name"]} -master_clock {q["source_clock"]} -source $ot_lp -edges {{{" ".join(map(str,edges))}}} $ot_lout']
    o += ['# No uncertainty/path exceptions emitted; CE retains60/25 base,150/210+100 cross-family.',
          '# ICG gating setup/hold, all-family data/select/reset timing and native TT/FF receipts still required.']
    return '\n'.join(o)+'\n'


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(emit(json.loads(args.spec.read_text()), args.root))
