"""Bijective alpha-renaming of Yosys emitted module/cell IDs for Slang hierarchy paths.

Escaped signal/port names are untouched. Slang's derived-module name builder can
retain the terminating space of an escaped instance ID in an RTLIL identifier.
Use plain identifiers only for module and instance names in this source profile.
"""
import hashlib
import re

TOKEN = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\\[^\s]+|[A-Za-z_$][A-Za-z0-9_$]*|[^\s]')
IDENT = re.compile(r'^(?:\\[^\s]+|[A-Za-z_$][A-Za-z0-9_$]*)$')


def normalize_names(text, top):
    ts = [m for m in TOKEN.finditer(text) if not m[0].startswith(('//', '/*', '"'))]
    vals = [m[0] for m in ts]
    declarations = {i + 1 for i, t in enumerate(vals[:-1]) if t == 'module'}
    modules = {vals[i] for i in declarations}
    if top not in modules:
        raise ValueError(f'native top {top} is not declared')
    occupied = {t.lstrip('\\') for t in vals if IDENT.match(t)}
    names = {}
    roles = {}
    selected = {}

    def mark(i, role):
        old = vals[i]
        if not old.startswith('\\'):
            return
        new = names.setdefault(old, 'hc_a_' + hashlib.sha256(old.encode()).hexdigest()[:16])
        if new in occupied:
            raise ValueError(f'alpha name collision for {old}')
        roles.setdefault(old, set()).add(role)
        selected[i] = new

    # Every use of a known emitted module identifier is a type name, except the
    # declaration itself. Instance names are recognized structurally after type
    # and optional parameter list; unknown SRAM types are the external masters.
    for i, typ in enumerate(vals):
        if typ not in modules and not typ.startswith('ot_sram_'):
            continue
        if i in declarations:
            mark(i, 'module')
            continue
        j = i + 1
        if j < len(vals) and vals[j] == '#':
            j += 1
            if j >= len(vals) or vals[j] != '(':
                raise ValueError(f'unsupported parameter syntax after {typ}')
            depth = 1
            j += 1
            while j < len(vals) and depth:
                depth += (vals[j] == '(') - (vals[j] == ')')
                j += 1
        if j + 1 < len(vals) and IDENT.match(vals[j]) and vals[j + 1] == '(':
            mark(i, 'module')
            mark(j, 'instance')
    # Require all references of an escaped module name to have been recognized.
    # Never guess the role of an identifier or alter a port with a similar name.
    for i, typ in enumerate(vals):
        if typ.startswith('\\') and typ in modules and i not in selected:
            raise ValueError(f'unclassified escaped module reference {typ}')
    pieces = []
    pos = 0
    for i in sorted(selected):
        m = ts[i]
        pieces.extend((text[pos:m.start()], selected[i]))
        pos = m.end()
    pieces.append(text[pos:])
    result = ''.join(pieces)
    report = dict(kind='HC_EMITTED_IDENTIFIER_ALPHA_V1',
                  module_names={k[1:]: names[k] for k in names if 'module' in roles[k]},
                  instance_names={k[1:]: names[k] for k in names if 'instance' in roles[k]},
                  replacements=len(selected), added_cycles=0)
    # Exact lexical inverse proves that this operation changes only the selected
    # identifier tokens; no expression, port, literal or statement can change.
    inverse = {v: k for k, v in names.items()}
    restored = TOKEN.sub(lambda m: inverse.get(m[0], m[0]), result)
    if restored != text:
        raise ValueError('alpha transform is not byte-invertible')
    return result, report


def placement_name(name, report):
    """Translate an emitted flat cell name from the existing Tcl placement entry."""
    logical = name.replace('\\[', '[').replace('\\]', ']')
    return report['instance_names'].get(logical, name)
