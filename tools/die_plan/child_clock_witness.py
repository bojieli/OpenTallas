"""Retain native child clock witnesses in an existing routed export session.

Retention does not qualify source equivalence, nested ETMs or credited skew.
"""
import hashlib
import json
import math
import re
from pathlib import Path


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def tcl(tools, corner, libraries, inputs, reuse_graph=False, library_variable=None):
    if corner not in ('tt', 'ff'):
        raise ValueError('Child clock witnesses require actual TT/FF sessions')
    if (not libraries and not library_variable) or not inputs:
        raise ValueError('Exact library and constraint inputs are required')
    if library_variable is not None and not re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', library_variable):
        raise ValueError('Invalid native library variable')
    if reuse_graph:
        body = ('if {![info exists ::ot_ps_retained_pairs] || ![info exists ::ot_ps_retained_counts]} '
                '{error "CHILD_CLOCK_WITNESS native measured graph was not retained"}\n'
                'set P $::ot_ps_retained_pairs\nlassign $::ot_ps_retained_counts np nx nd\n')
    else:
        tools = Path(tools)
        family = tools.parents[1] / 'physical/common_flow/clock_family.tcl'
        if not family.is_file():
            family = tools / 'clock_family.tcl'
        body = family.read_text() + '\nset ::ot_ps_lib_only 1\n' + (tools / 'pair_skew.tcl').read_text() + '\nunset ::ot_ps_lib_only\n'
        body += 'set ::ot_ps_method tag\nsta::worst_slack_cmd max\nsta::worst_slack_cmd min\nset ::ot_ps_R [ot_ps_regs]\nlassign [ot_ps_related $::ot_ps_R] P np nx nd\n'
    prefix = f'/out/child_clock_{corner}'
    for suffix, header, source in [
        ('endpoints', 'reference clock_pin clock late_ps early_ps edge', '::ot_ps_R'),
        ('pairs', 'launch capture_setup data_pin raw_setup_ps raw_hold_ps capture_hold', 'P'),
        ('roots', 'clock_edge late_ps early_ps', '::ot_ps_insertion'),
    ]:
        body += f'set f [open {prefix}_{suffix}.tsv w]\nputs $f [join {{{header}}} \\t]\n'
        row = '[join $row \\t]' if suffix == 'pairs' else '$key\\t[join $row \\t]'
        body += f'dict for {{key row}} ${source} {{puts $f "{row}"}}\nclose $f\n'
    body += f'''set f [open {prefix}_masters.tsv w]
puts $f "reference\\tclock_pin\\tmaster"
dict for {{ref row}} $::ot_ps_R {{
  set pin [lindex $row 0]
  set cell [get_cells -of_objects [get_pins $pin]]
  if {{[llength $cell] != 1}} {{error "CHILD_CLOCK_WITNESS ambiguous endpoint master $pin"}}
  puts $f "$ref\\t$pin\\t[get_property $cell ref_name]"
}}
close $f
set f [open {prefix}_clocks.tsv w]
puts $f "clock\\tsource_kind\\tsource"
foreach clock [all_clocks] {{
  set name [get_full_name $clock]
  set sources [get_property $clock sources]
  if {{![llength $sources]}} {{puts $f "$name\\tvirtual\\t"}}
  foreach source $sources {{
    set pin [get_full_name $source]
    set kind [expr {{[llength [get_ports -quiet $pin]] ? "port" : "pin"}}]
    puts $f "$name\\t$kind\\t$pin"
  }}
}}
close $f
set f [open {prefix}_counts.tsv w]
puts $f "refs\\t[dict size $::ot_ps_R]"
puts $f "pairs\\t$np"
puts $f "captures\\t$nd"
puts $f "inter_clock_pairs_skipped\\t$nx"
puts $f "missing\\t$::ot_ps_noarr"
close $f
set f [open {prefix}_inputs.tsv w]
'''
    for kind, paths in [('liberty', libraries), ('constraint', inputs)]:
        for path in paths:
            if any(c in path for c in '{}\n\r\t') or not path.startswith('/'):
                raise ValueError('Unrepresentable absolute witness input path')
            body += f'puts $f [join [list {kind} {{{path}}} [lindex [exec sha256sum {{{path}}}] 0]] \\t]\n'
    if library_variable:
        body += f'foreach path ${library_variable} {{puts $f [join [list liberty $path [lindex [exec sha256sum -- $path] 0]] \\t]}}\n'
    body += 'close $f\nif {$::ot_ps_noarr != 0} {error "CHILD_CLOCK_WITNESS missing actual clock arrivals"}\n'
    body += f'puts "OT_CHILD_CLOCK_WITNESS {corner} COMPLETE"\n'
    return body


def rows(path, header=None):
    result = [line.split('\t') for line in Path(path).read_text().splitlines()]
    if header is not None:
        if not result or result.pop(0) != header.split():
            raise ValueError(f'{Path(path).name}: invalid header')
    width = len(header.split()) if header else 3
    if any(len(row) != width for row in result):
        raise ValueError(f'{Path(path).name}: truncated row')
    return result


def finite(values):
    if any(not math.isfinite(float(value)) for value in values):
        raise ValueError('Nonfinite native clock arrival')


def record(out, base, name, export_record, layout="export"):
    out, base = Path(out), Path(base)
    target = out / 'child_clock_witness.json'
    target.unlink(missing_ok=True)
    if layout not in ('export', 'signoff'): raise ValueError('Unknown witness layout')
    native = {p: sha(base / p) for p in ['6_final.odb', '6_final.spef', '6_final.v']}
    result = {'schema': 'opentallas.child_clock_witness.v1', 'qualification': 'NOT_ASSERTED',
              'hierarchical_expansion': 'NOT_ASSERTED', 'source_equivalence': 'NOT_ASSERTED',
              'source_identity_kind': 'routed_native_netlist_sha256',
              'scope': 'Actual native endpoints and same-clock related pairs; no CRPR credit or source/EQ waiver',
              'native': native, 'corners': {}}
    for c in ['tt', 'ff']:
        prefix = f'child_clock_{c}'
        folder = out / c if layout == 'signoff' else out
        log = (folder / ('sta.log' if layout == 'signoff' else f'export_{c}.log')).read_text()
        if f'OT_CHILD_CLOCK_WITNESS {c} COMPLETE' not in log.splitlines():
            raise ValueError(f'{c}: incomplete native witness')
        counts = dict(line.split('\t') for line in (folder / f'{prefix}_counts.tsv').read_text().splitlines())
        counts = {k: int(v) for k, v in counts.items()}
        if not {'refs', 'pairs', 'captures', 'inter_clock_pairs_skipped', 'missing'}.issubset(counts):
            raise ValueError(f'{c}: incomplete native census fields')
        if counts['missing'] or counts['refs'] < 1 or any(v < 0 for v in counts.values()):
            raise ValueError(f'{c}: missing endpoint coverage')
        endpoints = rows(folder / f'{prefix}_endpoints.tsv', 'reference clock_pin clock late_ps early_ps edge')
        masters = rows(folder / f'{prefix}_masters.tsv', 'reference clock_pin master')
        pairs = rows(folder / f'{prefix}_pairs.tsv', 'launch capture_setup data_pin raw_setup_ps raw_hold_ps capture_hold')
        roots = rows(folder / f'{prefix}_roots.tsv', 'clock_edge late_ps early_ps')
        clocks = rows(folder / f'{prefix}_clocks.tsv', 'clock source_kind source')
        if any(not clock or kind not in ('port', 'pin', 'virtual') or (kind != 'virtual' and not source) for clock, kind, source in clocks):
            raise ValueError(f'{c}: malformed actual clock source')
        refs = {row[0]: row for row in endpoints}
        root_names = {row[0] for row in roots}
        source_names = {row[0] for row in clocks if row[1] in ('port', 'pin') and row[2]}
        if len(refs) != counts['refs'] or len(endpoints) != counts['refs'] or len(masters) != counts['refs']:
            raise ValueError(f'{c}: endpoint/master count mismatch')
        if len(pairs) != counts['pairs'] or not roots:
            raise ValueError(f'{c}: pair/root count mismatch')
        if {row[0] for row in masters} != refs.keys() or any(not row[2] or row[1] != refs[row[0]][1] for row in masters):
            raise ValueError(f'{c}: endpoint master identities do not match')
        for ref, pin, clock, late, early, edge in endpoints:
            root = clock if edge == 'rise' else clock + ' fall'
            if not pin or edge not in ('rise', 'fall') or clock not in source_names or root not in root_names:
                raise ValueError(f'{c}: missing actual clock source/root identity')
            finite([late, early])
        for root, late, early in roots:
            finite([late, early])
        for launch, capture, data, setup, hold, hold_capture in pairs:
            if not data or any(ref not in refs for ref in (launch, capture, hold_capture)):
                raise ValueError(f'{c}: related-pair endpoint identity missing')
            finite([setup, hold])
        inputs = rows(folder / f'{prefix}_inputs.tsv')
        if not {'liberty', 'constraint'}.issubset({row[0] for row in inputs}) or any(
                kind not in ('liberty', 'constraint') or not path.startswith('/') or not re.fullmatch('[0-9a-f]{64}', digest)
                for kind, path, digest in inputs):
            raise ValueError(f'{c}: missing exact library/constraint identities')
        files = {str((folder / f'{prefix}_{k}.tsv').relative_to(out)): sha(folder / f'{prefix}_{k}.tsv') for k in
                 ['endpoints', 'pairs', 'roots', 'clocks', 'masters', 'counts', 'inputs']}
        extraction = folder / ('session.tcl' if layout == 'signoff' else f'export_{c}.tcl')
        files[str(extraction.relative_to(out))] = sha(extraction)
        if layout == 'signoff':
            libraries_path = folder / 'libraries.json'
            libraries = json.loads(libraries_path.read_text())
            observed = {path: digest for kind, path, digest in inputs if kind == 'liberty'}
            expected = {row['path']: row['sha256'] for row in libraries['libraries']}
            if libraries.get('status') != 'LOADED' or libraries.get('corner') != c.upper() or observed != expected:
                raise ValueError(f'{c}: native loaded-library receipt mismatch')
            for artifact in [folder / 'session.tcl', libraries_path]:
                files[str(artifact.relative_to(out))] = sha(artifact)
            for kind, path, digest in inputs:
                if kind == 'constraint':
                    relative = Path(path).relative_to('/sdc')
                    if relative.is_absolute() or '..' in relative.parts:
                        raise ValueError(f'{c}: unrepresentable constraint snapshot')
                    snapshot = folder / 'sdcdir' / relative
                    if sha(snapshot) != digest:
                        raise ValueError(f'{c}: constraint snapshot identity mismatch')
                    files[str(snapshot.relative_to(out))] = digest
        result['corners'][c] = {'counts': counts, 'files': files,
                                'exported_liberty_sha256': sha(out / f'{name}_{c}.lib') if layout == 'export' else None,
                                'extraction_tcl_sha256': sha(folder / ('session.tcl' if layout == 'signoff' else f'export_{c}.tcl')),
                                'constraint_sequence': export_record['sdc_sequence'][c] if layout == 'export' else {'session': c + '/session.tcl', 'policy': export_record['policy']}}
    target.write_text(json.dumps(result, indent=2) + '\n')
    return {'path': target.name, 'sha256': sha(target), 'qualification': 'NOT_ASSERTED'}
