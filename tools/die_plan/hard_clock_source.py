"""Related clocks produced by explicit physical hard-macro output pins."""
import re


_IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z_0-9]*')
_INSTANCE = re.compile(r'[A-Za-z_][A-Za-z_0-9]*(?:[./][A-Za-z_][A-Za-z_0-9]*)*')


def sources(plan, type_name):
    """Canonical ordered declarations, restricted to bound macro pins and synchronous edge ports."""
    part_type = plan.types[type_name]
    clock = part_type.get('clock', {})
    edges = {row['port']: row for row in clock.get('edge_clocks', [])}
    macros = [m for m in part_type.get('contents', []) if m.get('lef') and m.get('lib')]
    out = {}
    targets = set()
    for row in clock.get('hard_clock_sources', []):
        name, src, inst, pin = (row[k] for k in ('name', 'source_port', 'instance', 'pin'))
        if not all(_IDENTIFIER.fullmatch(x) for x in (name, src, pin)) or not _INSTANCE.fullmatch(inst):
            raise ValueError(f'{type_name}: invalid hard clock source name, edge port, or physical pin')
        edge = edges.get(src)
        if edge is None or edge.get('cdc'):
            raise ValueError(f'{type_name}.{name}: {src} is not a synchronous edge clock port')
        if name in out or name in edges or name in ('clk', 'vclk') or (inst, pin) in targets:
            raise ValueError(f'{type_name}.{name}: duplicate hard clock name or target')
        if sum(m.get('physical_inst', m.get('inst')) == inst for m in macros) != 1:
            raise ValueError(f'{type_name}.{name}: {inst} is not one placed macro with declared LEF and Liberty')
        scale = row['multiply_by']
        if type(scale) is not int or scale < 1 or scale > 64:
            raise ValueError(f'{type_name}.{name}: multiply_by must be an integer in 1..64')
        targets.add((inst, pin))
        out[name] = dict(row)
    return out


def sdc_line(row):
    """The only permitted SDC form for a declared related macro source."""
    src = row['source_port']
    return (f"create_generated_clock -name {row['name']} -master_clock {src} -source [get_ports {{{src}}}] "
            f"-multiply_by {row['multiply_by']} [get_pins {{{row['instance']}/{row['pin']}}}]")


def validate_macro_views(plan, type_name, staged_dir):
    """Fail generation if an active provider would disappear during physical link."""
    from pathlib import Path

    part_type = plan.types[type_name]
    staged_dir = Path(staged_dir)
    for row in sources(plan, type_name).values():
        instance, pin = row['instance'], row['pin']
        macro, = [m for m in part_type.get('contents', []) if m.get('lef') and m.get('lib')
                  and m.get('physical_inst', m.get('inst')) == instance]
        lef = staged_dir / Path(macro['lef']).name
        lib = staged_dir / Path(macro['lib']).name
        pin_lef = re.search(rf'(?ms)^\s*PIN\s+{re.escape(pin)}\s*\n(.*?)^\s*END\s+{re.escape(pin)}\s*$',
                            lef.read_text())
        if not pin_lef or not all(re.search(pat, pin_lef[1]) for pat in (r'\bDIRECTION\s+OUTPUT\s*;',
                                                                        r'\bUSE\s+CLOCK\s*;')):
            raise ValueError(f'{type_name}.{row["name"]}: {lef.name} must declare {pin} OUTPUT CLOCK')
        # Only the direct direction declaration, before nested timing or another pin block, counts.
        pin_lib = re.search(rf'\bpin\s*\(\s*"?{re.escape(pin)}"?\s*\)\s*\{{([^{{}}]*)', lib.read_text())
        if not pin_lib or not re.search(r'\bdirection\s*:\s*output\s*;', pin_lib[1]):
            raise ValueError(f'{type_name}.{row["name"]}: {lib.name} must declare {pin} output')
