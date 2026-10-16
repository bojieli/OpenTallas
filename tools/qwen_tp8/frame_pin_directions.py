"""Assign only unresolved LEF frame pin directions from the source bus map.

Keep scoped pin state, validate every assignment, and refuse conflicting typed
pins. This transforms diagnostic frame abstracts; it supplies no physical view.
"""
import re


def apply_frame_directions(text, directions):
    for master, ports in directions.items():
        for pin, direction in ports.items():
            if direction not in ('input', 'output', 'inout'):
                raise ValueError(f'Invalid direction {master}.{pin}: {direction!r}')
    macro = pin = None
    fixed = unresolved = checked = 0
    lines = []
    for line in text.splitlines(keepends=True):
        match = re.match(r'^MACRO\s+(\S+)\s*$', line)
        if match:
            macro, pin = match[1], None
        match = re.match(r'^\s+PIN\s+(\S+)\s*$', line)
        if match:
            pin = match[1]
        match = re.match(r'^(\s*DIRECTION\s+)(INPUT|OUTPUT|INOUT)(\s*;.*)$', line.rstrip('\r\n'))
        if match and macro and pin:
            base = pin.split('[')[0]
            desired = directions.get(macro, {}).get(pin, directions.get(macro, {}).get(base))
            if desired is None:
                if match[2] == 'INOUT':
                    unresolved += 1
            else:
                checked += 1
                desired = desired.upper()
                if match[2] != 'INOUT' and match[2] != desired:
                    raise ValueError(f'LEF/source direction conflict {macro}.{pin}: {match[2]} vs {desired}')
                if match[2] == 'INOUT' and desired != 'INOUT':
                    line = match[1] + desired + match[3] + line[len(line.rstrip('\r\n')):]
                    fixed += 1
        end = re.match(r'^\s*END\s+(\S+)\s*$', line)
        if end:
            if end[1] == pin:
                pin = None
            elif end[1] == macro:
                macro, pin = None, None
        lines.append(line)
    return ''.join(lines), dict(fixed=fixed, checked=checked, unresolved_inout=unresolved)
