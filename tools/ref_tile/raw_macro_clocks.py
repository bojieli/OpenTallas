"""Explicit raw-memory clock sinks; hardened ETMs never enter a glue CTS tree."""
import re
from pathlib import Path

TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|(?P<kind>[A-Za-z_]\w*)\s*\((?P<args>[^()]*)\)\s*\{')
BRACES = re.compile(r'"(?:\\.|[^"\\])*"|[{}]')
SAFE = re.compile(r'[A-Za-z_]\w*')
INSTANCE = re.compile(r'[A-Za-z_][A-Za-z0-9_.$\[\]\\/]*')


def groups(text):
    """Immediate Liberty groups, respecting quoted strings and nested bodies."""
    text = re.sub(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\n]*',
                  lambda m: m[0] if m[0].startswith('"') else '', text, flags=re.S)
    pos = 0
    while (m := TOKEN.search(text, pos)):
        pos = m.end()
        if m['kind'] is None:
            continue
        depth = 1
        for b in BRACES.finditer(text, pos):
            if b[0] == '{': depth += 1
            elif b[0] == '}': depth -= 1
            if depth == 0:
                yield m['kind'], m['args'].strip().strip('"'), text[pos:b.start()]
                pos = b.end()
                break
        else:
            raise ValueError('raw memory Liberty has an unterminated group')


def memory_clock(path, master, multi=False):
    libs = list(groups(path.read_text()))
    if len(libs) != 1 or libs[0][0] != 'library':
        raise ValueError(f'raw memory needs one actual Liberty library: {path}')
    cells = [(name, body) for kind, name, body in groups(libs[0][2]) if kind == 'cell']
    if len(cells) != 1 or cells[0][0] != master:
        raise ValueError(f'raw memory Liberty cell differs from declared master {master}')
    children = list(groups(cells[0][1]))
    memories = [body for kind, _, body in children if kind == 'memory']
    if len(memories) != 1 or any(kind in ('ff', 'latch') for kind, _, _ in children):
        raise ValueError(f'{master}: not a raw Liberty memory cell')
    memory = memories[0]
    if not re.search(r'\btype\s*:\s*(rom|ram)\s*;', memory):
        raise ValueError(f'{master}: raw memory type must be rom or ram')
    for field in ('address_width', 'word_width'):
        if not re.search(rf'\b{field}\s*:\s*[1-9]\d*\s*;', memory):
            raise ValueError(f'{master}: missing positive memory {field}')
    clocks = [name for kind, name, body in children if kind == 'pin'
              and re.search(r'\bclock\s*:\s*true\s*;', body)
              and re.search(r'\bdirection\s*:\s*input\s*;', body)]
    if multi:
        # L2H-PGVM 10-19: a dual-clock raw memory (1r1w2c: wclk + rclk) binds EVERY Liberty clock pin to one root
        if len(clocks) < 2 or len(set(clocks)) != len(clocks) or any(not SAFE.fullmatch(c) for c in clocks):
            raise ValueError(f'{master}: multi-clock raw-memory opt-in requires >= 2 distinct scalar input clocks')
        return tuple(sorted(clocks))
    if len(clocks) != 1 or not SAFE.fullmatch(clocks[0]):
        raise ValueError(f'{master}: raw-memory opt-in requires one scalar input clock')
    return clocks[0]


def contract(spec, root):
    """Validate exact instance/master/pin/root ownership and return frozen inputs."""
    masters = spec.get('soft_root_macro_masters', [])
    bindings = spec.get('soft_root_macro_bindings', {})
    if not masters and not bindings:
        return {}, []
    # TW2-QCTLM 10-19: a LANDED cluster (kind cluster + multiple_cts_roots, tools/landed_parent/lp.py) builds one CTS
    # tree per region root (every clock_ports entry); a raw SRAM owned by a region's glue (qfd_tt_ctlm_dv calendar
    # 2 x 64x512 on ck_core) is an ordinary sink of that root exactly as in a hybrid_entries leaf.  Same exact
    # instance/master/pin/root contract; the root must be one of the region roots.
    multi = spec.get('clock') == 'multiple_cts_roots'
    # L2H-PGVM 10-19: a multiple_cts_roots LEAF tile (independent clock families, e.g. the svg SRAM-FIFO group: each
    # landing bank's payload / dual-clock response SRAM on its own family root) has the same need: raw SRAMs are
    # ordinary sinks of the exact root that clocks them in the RTL.  Same exact instance/master/pin/root contract.
    leaf_multi = spec.get('kind') == 'tile' and multi
    if ((spec.get('kind') != 'cluster' and not leaf_multi) or spec.get('clock') not in ('hybrid_entries', 'multiple_cts_roots')
            or not isinstance(masters, list) or not masters
            or any(not isinstance(m, str) or not SAFE.fullmatch(m) for m in masters) or len(masters) != len(set(masters))
            or not isinstance(bindings, dict) or not bindings):
        raise ValueError('raw memory clocks require explicit named masters and instance bindings in hybrid_entries '
                         'or a landed multiple_cts_roots cluster')
    roots = set(spec.get('clock_ports', []) if multi else spec.get('clock_cts_roots', []))
    if not roots or not roots <= set(spec.get('clock_ports', [])):
        raise ValueError('raw memory roots must preserve the declared clock-port grant')
    declared = {}
    for item in spec.get('children', []):
        if Path(item['view']).name in masters:
            raise ValueError('a hardened child cannot be a raw memory CTS sink')
    for item in spec.get('macros', []):
        view = Path(item['view']); master = view.name
        if master not in masters:
            continue
        inst = item.get('inst', '')
        if (not INSTANCE.fullmatch(inst) or item.get('count', 1) != 1 or item.get('clock_entry')
                or view.is_absolute() or '..' in view.parts):
            raise ValueError('raw memory needs one exact source instance without a hard clock entry')
        inst = inst.replace('\\', '')
        if inst in declared:
            raise ValueError('duplicate raw memory instance')
        declared[inst] = (master, view)
    if set(bindings) != set(declared) or {m for m, _ in declared.values()} != set(masters):
        raise ValueError('raw memory bindings must cover exactly the declared named macro instances')
    result = {}; paths = []; validated = {}
    for inst, b in bindings.items():
        master, view = declared[inst]
        pins_form = isinstance(b, dict) and 'clock_pins' in b
        if pins_form:
            # multi-clock form {master, clock_pins: {pin: root}} (dual-clock raw memory; every pin bound exactly once)
            cp = b.get('clock_pins')
            if (set(b) != {'master', 'clock_pins'} or b['master'] != master or not isinstance(cp, dict) or len(cp) < 2
                    or any(not isinstance(k, str) or not SAFE.fullmatch(k) or not isinstance(v, str)
                           or v not in roots for k, v in cp.items())):
                raise ValueError(f'raw memory binding is not one exact master / clock-pin -> source-root map: {inst}')
        elif (not isinstance(b, dict) or set(b) != {'master', 'clock_pin', 'root'} or b['master'] != master
                or any(not isinstance(b[k], str) for k in b)
                or any(not SAFE.fullmatch(b[k]) for k in ('master', 'clock_pin')) or b['root'] not in roots):
            # the root is an exact granted clock port (may be a bus bit, stream_bank_clk[0]); braced in the Tcl
            raise ValueError(f'raw memory binding is not one exact master/clock/source root: {inst}')
        directory = root / view
        if any((directory / name).exists() for name in ('insertion.json', 'abstract.json', 'export.json')):
            raise ValueError(f'{master}: hardened timing views are not raw memory')
        key = (master, pins_form)
        if key not in validated:
            clocks = []
            for corner in ('tt', 'ff'):
                rel = view / f'{master}_{corner}.lib'
                clocks.append(memory_clock(root / rel, master, pins_form)); paths.append(str(rel))
            if len(set(clocks)) != 1:
                raise ValueError(f'{master}: raw TT/FF memory clock interface differs')
            validated[key] = clocks[0]
        if pins_form:
            if tuple(sorted(b['clock_pins'])) != validated[key]:
                raise ValueError(f'{master}: binding pins are not exactly the TT/FF Liberty clock pins')
        elif b['clock_pin'] != validated[key]:
            raise ValueError(f'{master}: binding is not the actual TT/FF Liberty clock pin')
        result[inst] = {**b, 'clock_pins': dict(b['clock_pins'])} if pins_form else dict(b)
    return result, sorted(set(paths))


def tcl(bindings):
    if not bindings:
        return []
    def one(inst, b):
        if 'clock_pins' in b:
            pins = ' '.join(f'{p} {{{r}}}' for p, r in sorted(b['clock_pins'].items()))
            return '{%s} {master %s pins {%s}}' % (inst, b['master'], pins)
        r = b['root'] if SAFE.fullmatch(b['root']) else '{%s}' % b['root']
        return '{%s} {master %s clock_pin %s root %s}' % (inst, b['master'], b['clock_pin'], r)
    entries = ' '.join(one(inst, b) for inst, b in sorted(bindings.items()))
    return ['set ::ot_ce_raw_memory_bindings [dict create ' + entries + ']']
