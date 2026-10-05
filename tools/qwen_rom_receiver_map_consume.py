#!/usr/bin/env python3
"""Consume a completed retained-receiver map; never run synthesis or STA.

This records direct mapped connections and raw SS library pin capacitances.
It deliberately provides no routed timing, total issue-cone load, or fit verdict.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def groups(text, kind):
    """Iterate Liberty cell/pin groups, retaining their nested bodies."""
    pattern = re.compile(r'\b' + kind + r'\s*\(\s*([^()]+?)\s*\)\s*\{')
    pos = 0
    while match := pattern.search(text, pos):
        depth, end = 1, match.end()
        quoted = False
        while depth and end < len(text):
            ch = text[end]
            if ch == '"' and text[end - 1] != '\\':
                quoted = not quoted
            if not quoted:
                depth += (ch == '{') - (ch == '}')
            end += 1
        if depth:
            raise ValueError(f'unterminated Liberty {kind} {match[1]}')
        yield match[1].strip('"'), text[match.end():end - 1]
        pos = end


def attr(text, name):
    # The enrolled ASAP7 files omit a semicolon on some area attributes.
    # Every attribute consumed here is scalar and lies on a single line.
    match = re.search(r'\b' + name + r'\s*:\s*([^;\n]+)', text)
    return match[1].strip().strip('"') if match else None


def load_libraries(paths):
    cells, records = {}, []
    for path in paths:
        text = path.read_text()
        unit = re.search(r'capacitive_load_unit\s*\(([^)]+)\)', text)
        records.append(dict(path=str(path), sha256=digest(path),
                            time_unit=attr(text, 'time_unit'),
                            capacitance_unit=unit[1] if unit else None))
        for name, body in groups(text, 'cell'):
            pins = {}
            for pin, pin_body in groups(body, 'pin'):
                cap = attr(pin_body, 'capacitance')
                pins[pin] = dict(direction=attr(pin_body, 'direction'),
                                 capacitance=float(cap) if cap else None,
                                 clock=attr(pin_body, 'clock'),
                                 function=attr(pin_body, 'function'))
            cells[name] = dict(area=float(attr(body, 'area') or 0),
                               sequential=bool(re.search(r'\bff\s*\(', body)),
                               pins=pins, library=str(path))
    return cells, records


ME_REGS = set('active pend pcnt nout_r tiles_r k_r ktot_r wsrc_r round_r '
              'oen_r amax_r rmax_r mbase_r scale_base_r mmode_r split_r '
              'wcs_r ts_r tstep_r ks_r js_r jsh_r xks_r xjs_r xcs_r ots_r '
              'ojs_r t k j cur base_k base_t xk xc xk_base oa ot ot_step '
              'nb nb_t nb_step lb lb_step t_last k_last split_fault'.split())
SU_REGS = set('active cls inflight o v nout_r nin_r nvec_r v_last_r o_last_r '
              'fin_th rowa cura rowb curb rowc curc rowd curd rrow aso asi '
              'bso bsi cso csi dso dsi rso asrc bsrc csrc mc md ma mb ad '
              'dst red redsq imm1 imm2'.split())


def receiver(signal):
    for label, prefix, names in [('ME', 'u_me.u_top.', ME_REGS),
                                 ('SU', 'g_vsu.u_su.', SU_REGS)]:
        for match in re.finditer(re.escape(prefix) + r'([A-Za-z0-9_]+)', signal):
            if match[1] in names:
                return label
    return None


def instances(path):
    # Yosys write_verilog puts one named-port connection per line. Stream the
    # existing file instead of loading the full arithmetic netlist into RAM.
    current = None
    with path.open() as stream:
        for line in stream:
            if current is None:
                match = re.match(r'^\s*(\S+)\s+(\S+)\s+\(\s*$', line)
                if match and match[1] != 'module':
                    current = dict(type=match[1].lstrip('\\'),
                                   name=match[2].lstrip('\\'), ports={})
            else:
                port = re.match(r'^\s*\.([A-Za-z0-9_]+)\((.*)\)\s*,?\s*$', line)
                if port:
                    current['ports'][port[1]] = port[2].strip()
                elif re.match(r'^\s*\);', line):
                    yield current
                    current = None
    if current:
        raise ValueError('truncated mapped instance')


def consume(job, out):
    terminal = (job / 'exit').read_text().strip()
    if terminal != 'map_rc=0':
        raise ValueError(f'mapping not successful: {terminal}')
    netlist = job / 'actual_receivers_SS_mapped.v'
    stats = job / 'mapped.stat.txt'
    if not netlist.is_file() or not stats.is_file():
        raise FileNotFoundError('successful map lacks mapped netlist/statistics')
    launch = json.loads((job / 'launch.json').read_text())
    libpaths = sorted((job / 'lib').glob('*.lib'))
    cells, libraries = load_libraries(libpaths)
    # ASAP7 maps many Q outputs to QN followed by an inverter. Bind that
    # concrete unary cell as well, rather than requiring QN to have the public
    # register name or confusing the output inverter with the register.
    q_aliases = {}
    for inst in instances(netlist):
        lib = cells.get(inst['type'])
        if not lib or lib['sequential']:
            continue
        inputs = [pin for pin, data in lib['pins'].items()
                  if data['direction'] == 'input']
        if len(inputs) != 1:
            continue
        for pin, data in lib['pins'].items():
            if data['direction'] != 'output':
                continue
            net = inst['ports'].get(pin, '')
            label = receiver(net)
            function = (data.get('function') or '').replace(' ', '').strip('()')
            arg = inputs[0]
            if label and function in {arg, '!' + arg, arg + "'"}:
                source = inst['ports'].get(arg)
                if source:
                    q_aliases[source] = dict(receiver=label, register_output=net,
                                             unary_cell=inst['name'],
                                             unary_cell_type=inst['type'],
                                             function=data['function'])
    selected, direct_issue_loads, census = [], [], Counter()
    for inst in instances(netlist):
        census[inst['type']] += 1
        lib = cells.get(inst['type'])
        if not lib:
            continue
        outputs = [net for pin, net in inst['ports'].items()
                   if lib['pins'].get(pin, {}).get('direction') == 'output']
        bindings = [q_aliases[net] for net in outputs if net in q_aliases]
        labels = ({receiver(net) for net in outputs} - {None}) | {
            item['receiver'] for item in bindings}
        is_gate = inst['name'] == 'g_me_cg.u_me_cg.u_icg'
        if (lib['sequential'] and labels) or is_gate:
            selected.append(dict(**inst, receivers=sorted(labels),
                                 public_Q_bindings=bindings,
                                 clock_gate=is_gate, cell_area_raw=lib['area'],
                                 library=lib['library'], pin_data=lib['pins']))
        for pin, net in inst['ports'].items():
            clean = net.lstrip('\\').strip()
            data = lib['pins'].get(pin, {})
            if clean in {'me_go', 'su_go', 'me_en'} and data.get('direction') == 'input':
                direct_issue_loads.append(dict(signal=clean, cell=inst['name'],
                                              cell_type=inst['type'], pin=pin,
                                              capacitance_raw=data.get('capacitance'),
                                              library=lib['library']))
    counts = Counter(label for inst in selected for label in inst['receivers'])
    gates = [inst for inst in selected if inst['clock_gate']]
    unresolved = []
    if len(gates) != 1:
        unresolved.append(f'expected one actual ICG, found {len(gates)}')
    for label in ('ME', 'SU'):
        if not counts[label]:
            unresolved.append(f'no directly named {label} register outputs found; resolve aliases before qualification')
    if len(gates) == 1:
        expected = dict(CLK='clk', ENA='me_en', GCLK='me_clk')
        for pin, signal in expected.items():
            actual = gates[0]['ports'].get(pin, '').lstrip('\\').strip()
            if actual != signal:
                unresolved.append(f'actual ICG {pin}={actual!r}; expected {signal!r}, resolve net aliases')
    unmapped_types = {name: count for name, count in census.items() if name not in cells}
    if unmapped_types:
        unresolved.append('mapped netlist retains types absent from enrolled SS libraries')
    source_warnings = set()
    with (job / 'map.log').open() as stream:
        for line in stream:
            if line.startswith('Warning:') and ('no driver' in line or 'conflicting drivers' in line):
                source_warnings.add(line.strip())
    if source_warnings:
        unresolved.append('original map reports undriven/conflicting source nets; preserve warnings and correct source before qualification')
    record = dict(schema='qwen.rom.actual_receiver_mapping.v1',
                  status='MAPPED_SOURCE_CONSUMED' if not unresolved else 'MAPPED_BINDING_INCOMPLETE',
                  job_root=str(job), source_handoff=launch['source_handoff'],
                  source_core_sha256=launch['source_core_sha256'],
                  netlist_sha256=digest(netlist), stats_sha256=digest(stats),
                  library_units=libraries, mapped_cell_census=dict(census),
                  mapped_cell_area_raw=sum(cells[name]['area'] * count
                                           for name, count in census.items() if name in cells),
                  types_absent_from_SS_libraries=unmapped_types,
                  source_driver_warnings=sorted(source_warnings),
                  selected_register_cell_counts=dict(counts),
                  selected_register_cells=selected, direct_issue_pin_loads=direct_issue_loads,
                  unresolved=unresolved, additional_hardware=False,
                  additional_cycles=0, issue_commit_cycles=4,
                  clock_policy_ps=[833, 60, 25], timing_qualified=False,
                  routed_wire_loads_qualified=False, physical_fit_qualified=False,
                  raw_library_units_only=True, adoption=False,
                  limitations=['Register binding follows directly named Q/QN and one actual library unary buffer/inverter; other aliases require explicit resolution.',
                               'Direct pin loads exclude wire capacitance and transitive enable/mux cones.',
                               'SS mapping is not SS setup/FF hold or generated-clock qualification.',
                               'Register counts are selected surviving mapped cells, not added state.'])
    out.mkdir(parents=True, exist_ok=False)
    (out / 'receiver_mapping.json').write_text(json.dumps(record, indent=2) + '\n')
    return {key: record[key] for key in ('status', 'selected_register_cell_counts', 'unresolved')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(consume(args.job, args.out), indent=2))
