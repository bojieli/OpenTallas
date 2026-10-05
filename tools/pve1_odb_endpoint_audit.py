"""Fail-closed audit of native endpoint records and canonical source constraints.

No native timing tool is invoked here. Missing or unsupported records are errors.
"""
import math
import tkinter


def replay_sdc(text, inputs, outputs, *, require_propagated=False):
    """Interpret canonical SDC in a safe Tcl interpreter with recording aliases.

    Supports only the source contract's commands, plus clock propagation. Unknown
    commands, filesystem access, extra exceptions and tool-added constraints fail.
    Tcl itself handles escaped names, braces, expressions and command substitution.
    """
    tcl = tkinter.Tcl()
    tcl.call('interp', 'create', '-safe', 'sdc')
    records = []
    universe = set(inputs) | set(outputs)
    def objects(kind, *args):
        if kind == 'get_ports':
            patterns = [p for arg in args if not arg.startswith('-') for p in tcl.splitlist(arg)]
            matched = sorted(p for p in universe if any(p == pat or tcl.call('string', 'match', pat, p) for pat in patterns))
            if not matched:
                raise ValueError('empty port selector')
            return tuple(matched)
        if kind in ('get_clocks', 'all_clocks'):
            if kind == 'get_clocks' and args not in [('core_clk',), ('*',)]:
                raise ValueError('unexpected clock selector')
            return ('core_clk',)
        if kind == 'all_inputs':
            return tuple(sorted(set(inputs) - ({'clk'} if '-no_clocks' in args else set())))
        if kind == 'all_outputs':
            return tuple(sorted(outputs))
        return 'ot_hdc_v41x_vec_red1024'
    for cmd in ('get_ports', 'get_clocks', 'all_clocks', 'all_inputs', 'all_outputs', 'current_design'):
        tcl.createcommand('audit_' + cmd, lambda *a, cmd=cmd: objects(cmd, *a))
        tcl.call('interp', 'alias', 'sdc', cmd, '', 'audit_' + cmd)
    for cmd in ('create_clock', 'set_clock_uncertainty', 'set_input_delay',
                'set_output_delay', 'set_false_path', 'set_load', 'set_max_fanout',
                'set_propagated_clock'):
        def capture(*args, cmd=cmd):
            records.append((cmd, args))
            return ''
        tcl.createcommand('audit_' + cmd, capture)
        tcl.call('interp', 'alias', 'sdc', cmd, '', 'audit_' + cmd)
    try:
        tcl.call('interp', 'eval', 'sdc', text)
    except tkinter.TclError as exc:
        raise ValueError('unsupported or invalid canonical SDC: ' + str(exc)) from exc
    state = dict(clock=[], uncertainties={}, input_delays={}, output_delays={},
                 exceptions=[], loads={}, fanout=[])
    for cmd, args in records:
        if cmd == 'create_clock':
            opts = list(args[:-1]); ports = tcl.splitlist(args[-1])
            allowed = {'-name', '-period', '-waveform'}
            if len(opts) % 2 or any(k not in allowed for k in opts[::2]):
                raise ValueError('unexpected clock option')
            options = dict(zip(opts[::2], opts[1::2]))
            if options.get('-name') != 'core_clk' or float(options['-period']) != 1111 or ports != ('clk',):
                raise ValueError('clock identity differs')
            if '-waveform' in options and tuple(map(float, tcl.splitlist(options['-waveform']))) != (0, 555.5):
                raise ValueError('clock waveform differs')
            state['clock'].append('core_clk')
        elif cmd == 'set_clock_uncertainty':
            if len(args) != 3 or args[0] not in ('-setup', '-hold') or tcl.splitlist(args[-1]) != ('core_clk',):
                raise ValueError('uncertainty scope differs')
            state['uncertainties'][args[0]] = float(args[1])
        elif cmd in ('set_input_delay', 'set_output_delay'):
            words = list(args[:-1]); target = state['input_delays' if cmd == 'set_input_delay' else 'output_delays']
            if words.count('-clock') != 1:
                raise ValueError('IO clock missing')
            index = words.index('-clock')
            if words[index + 1] != 'core_clk':
                raise ValueError('IO clock differs')
            del words[index:index + 2]
            for option in words:
                if option.startswith('-') and option not in ('-min', '-max', '-rise', '-fall', '-add_delay'):
                    raise ValueError('unsupported delay option')
            values = [float(w) for w in words if not w.startswith('-')]
            if values != [0.0]:
                raise ValueError('IO delay differs')
            transitions = ['rise'] if '-rise' in words else ['fall'] if '-fall' in words else ['rise', 'fall']
            modes = ['min'] if '-min' in words else ['max'] if '-max' in words else ['min', 'max']
            for port in tcl.splitlist(args[-1]):
                for edge in transitions:
                    for mode in modes:
                        target[port, edge, mode] = 0
        elif cmd == 'set_false_path':
            if len(args) != 2 or args[0] != '-from' or tcl.splitlist(args[1]) != ('rst_n',):
                raise ValueError('extra or broadened exception')
            state['exceptions'].append('rst_n')
        elif cmd == 'set_load':
            words = list(args[:-1])
            if any(w.startswith('-') and w not in ('-pin_load', '-min', '-max', '-rise', '-fall') for w in words):
                raise ValueError('unsupported load option')
            if [float(w) for w in words if not w.startswith('-')] != [3.898]:
                raise ValueError('output load differs')
            transitions = ['rise'] if '-rise' in words else ['fall'] if '-fall' in words else ['rise', 'fall']
            modes = ['min'] if '-min' in words else ['max'] if '-max' in words else ['min', 'max']
            state['loads'].update({(p, edge, mode): 3.898 for p in tcl.splitlist(args[-1]) for edge in transitions for mode in modes})
        elif cmd == 'set_max_fanout':
            if len(args) != 2 or float(args[0]) != 32 or args[1] != 'ot_hdc_v41x_vec_red1024':
                raise ValueError('fanout differs')
            state['fanout'].append(32)
        elif tcl.splitlist(args[-1]) != ('core_clk',):
            raise ValueError('propagated clock differs')
    expected = lambda ports: {(p, edge, mode): 0 for p in ports for edge in ('rise', 'fall') for mode in ('min', 'max')}
    if (state['clock'] != ['core_clk'] or state['uncertainties'] != {'-setup': 60, '-hold': 25}
            or state['exceptions'] != ['rst_n'] or state['fanout'] != [32]
            or state['input_delays'] != expected(set(inputs) - {'clk'})
            or state['output_delays'] != expected(outputs)
            or state['loads'] != {(p, edge, mode): 3.898 for p in outputs for edge in ('rise', 'fall') for mode in ('min', 'max')}):
        raise ValueError('incomplete actual constraint coverage')
    if require_propagated and not any(cmd == 'set_propagated_clock' for cmd, args in records):
        raise ValueError('terminal propagated clock missing')
    return {'status': 'SOURCE_CONSTRAINTS_EXACT', 'false_path_from': ['rst_n']}


def decode_rows(path):
    with open(path) as handle:
        for line in handle:
            yield tuple(bytes.fromhex(w).decode() for w in line.rstrip('\n').split('\t'))


def audit(rows, canonical_sdc, *, final=False):
    """Reconcile independent native inventories; all omissions block the verdict."""
    groups = {}
    for row in rows:
        groups.setdefault(row[0], []).append(row[1:])
    unique = lambda name: {r[0] for r in groups.get(name, [])}
    for name in ('endpoint', 'non_graph_endpoint', 'required_endpoint', 'odb_pin', 'odb_port', 'input', 'output', 'clock_pin'):
        if len(unique(name)) != len(groups.get(name, [])):
            raise ValueError('duplicate inventory: ' + name)
    if groups.get('complete') != [('1',)] or groups.get('check_setup') != [('1',)]:
        raise ValueError('incomplete native capture or failed check_setup')
    if not unique('endpoint') or not unique('output'):
        raise ValueError('empty functional inventory')
    if not unique('clock_pin'):
        raise ValueError('empty sequential clock inventory')
    if unique('odb_port') != unique('input') | unique('output'):
        raise ValueError('ODB/STA port identities differ')
    endpoints = unique('endpoint') | unique('non_graph_endpoint')
    if unique('endpoint') & unique('non_graph_endpoint'):
        raise ValueError('native graph and non-graph inventories overlap')
    if not endpoints <= unique('odb_pin') | unique('odb_port'):
        raise ValueError('STA endpoint missing in ODB')
    if not unique('required_endpoint') <= endpoints:
        raise ValueError('sequential/output endpoint absent from native graph; structural review required')
    replay_sdc(canonical_sdc, unique('input'), unique('output'), require_propagated=final)
    if any(r[1:] != ('core_clk',) for r in groups.get('clock_pin', [])):
        raise ValueError('unclocked or multiple-clock sequential pin')
    if groups.get('disabled_check'):
        raise ValueError('disabled timing check requires explicit structural review')
    constant_proofs = {(r[0], r[1]) for r in groups.get('disabled_constant_pin', [])}
    for start, end, role, constraint, loop, constant in groups.get('disabled_arc', []):
        if constraint != '0' or loop != '0' or constant != '1' or (start, end) not in constant_proofs:
            raise ValueError('unexplained disabled arc or extra timing disable')
    master_views = {}
    for master, pin, corner, found in groups.get('master_pin', []):
        key = (master, pin, corner)
        if key in master_views or found != '1':
            raise ValueError('duplicate or unmatched full-netlist master pin view')
        master_views[key] = found
    if not master_views or any((master, pin, other) not in master_views
            for master, pin, corner in master_views for other in ('WC', 'BC')):
        raise ValueError('missing SS/FF full-netlist pin qualification')
    macro_names = unique('macro')
    if macro_names:
        # Explicit hold until a source-bound macro arc contract is reviewed.
        # Never treat AUTO_MEMORIES=0 as proof or fabricate a clk-to-q value.
        raise ValueError('memory/BLOCK masters present: SS clk-to-q/read-capture qualification required')
    timing = {}
    fanin = {}
    for start, endpoint in groups.get('startpoint_pair', []):
        fanin.setdefault(endpoint, set()).add(start)
    reset_targets = {ep for start, ep in groups.get('reset_reachable', []) if start == 'rst_n'}
    exception_only = set()
    for ep, corner, mode, slack, functional, reset_reachable in groups.get('timing', []):
        key = (ep, corner, mode)
        if key in timing:
            raise ValueError('duplicate timing row')
        starts = fanin.get(ep, set())
        if functional != str(int(bool(starts - {'rst_n'}))) or reset_reachable != str(int(ep in reset_targets)):
            raise ValueError('startpoint/reset coverage declaration differs')
        if slack == 'EXCEPTED_RESET_ONLY':
            if starts != {'rst_n'} or reset_reachable != '1':
                raise ValueError('reset exception would waive functional paths')
            timing[key] = None
            exception_only.add(ep)
            continue
        value = float(slack)
        if not math.isfinite(value) or abs(value) >= 1e20:
            raise ValueError('missing/unconstrained timing; reset exception is not an endpoint waiver')
        if value < 0 and final:
            raise ValueError('terminal timing violation')
        if functional != '1':
            raise ValueError('no functional startpoint coverage; structural review required')
        if reset_reachable not in ('0', '1'):
            raise ValueError('reset reachability missing')
        timing[key] = value
    expected = {(ep, corner, mode) for ep in endpoints for corner, mode in [('WC', 'max'), ('BC', 'min')]}
    if set(timing) != expected:
        raise ValueError('missing or unexpected endpoint/corner timing rows')
    if not unique('non_graph_endpoint') <= exception_only:
        raise ValueError('non-graph functional endpoint requires structural review')
    for endpoint, role, disabled in groups.get('check_arc', []):
        if endpoint not in endpoints or disabled != '0':
            raise ValueError('timing-check arc omitted or disabled')
        if role not in ('setup', 'hold', 'recovery', 'removal', 'latch_setup', 'latch_hold', 'clock_gating_setup', 'clock_gating_hold'):
            raise ValueError('unreviewed native check role: ' + role)
    return dict(status='ENDPOINT_COVERAGE_VERIFIED' if not final else 'TIMING_COVERAGE_VERIFIED',
                endpoint_count=len(endpoints), timing_rows=len(timing), reset_only_endpoints=len(exception_only),
                macro_count=0, physical_signoff=False)
