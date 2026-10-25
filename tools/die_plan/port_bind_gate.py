#!/usr/bin/env python3
"""Check exact top-level plan port bits before floorplan; missing/extra ports fail closed."""
import argparse
import json
from pathlib import Path
import re


def check(text, top, pins, straps=()):
    """straps: the kit's declared ID straps (OWNER 10-25 option B): each must be an INPUT port named strap_* of the
    top; their bits are plan pins like any other (no pin is waived here)."""
    # Yosys emits non-ANSI top declarations. Limit parsing to that module so cell
    # library declarations and child modules cannot mask missing top ports.
    body = re.search(r"(?ms)^\s*module\s+\\?" + re.escape(top) + r"\s*\(.*?;(?P<body>.*?)^\s*endmodule\b", text)
    if not body:
        return dict(verdict="FAIL", reason=f"top {top} missing")
    bits, inputs = set(), set()
    declarations = re.findall(r"^\s*(input|output|inout)\s+(?:(?:wire|reg|signed)\s+)*(\[\s*\d+\s*:\s*\d+\s*\]\s*)?([^;]+);", body['body'], re.M)
    for kind, width, names in declarations:
        for name in names.split(','):
            name = name.strip().lstrip('\\').strip()
            if kind == 'input':
                inputs.add(name)
            if width:
                hi, lo = map(int, re.findall(r'\d+', width))
                bits.update(f'{name}[{i}]' for i in range(min(hi, lo), max(hi, lo)+1))
            else:
                bits.add(name)
    expected = {p['bus'] if p.get('bit') is None else f"{p['bus']}[{p['bit']}]" for p in pins}
    # Scalar declarations and [0:0] declarations are equivalent in Yosys.
    for name in list(bits):
        if name not in expected and name + '[0]' in expected:
            bits.remove(name); bits.add(name + '[0]')
        elif name.endswith('[0]') and name not in expected and name[:-3] in expected:
            bits.remove(name); bits.add(name[:-3])
    missing, extra = sorted(expected-bits), sorted(bits-expected)
    bad_straps = sorted(x for x in (straps or ()) if not re.match(r'^strap_[A-Za-z0-9_]+$', str(x)) or x not in inputs)
    return dict(verdict='PASS' if not missing and not extra and not bad_straps else 'FAIL', top=top,
                straps=sorted(straps or ()), bad_straps=bad_straps,
                plan_bits=len(expected), netlist_bits=len(bits), missing=len(missing), extra=len(extra),
                missing_examples=missing[:16], extra_examples=extra[:16])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('netlist'); ap.add_argument('kit'); a=ap.parse_args(argv)
    kit=Path(a.kit)
    try:
        budget=json.loads((kit/'budget.json').read_text())
        sj=kit/'straps.json'   # OWNER 10-25 option B: declared ID straps (strap_* inputs)
        sl=(lambda d: d.get('straps',[]) if isinstance(d,dict) else d)(json.loads(sj.read_text())) if sj.is_file() else []
        r=check(Path(a.netlist).read_text(), budget['module'], json.loads((kit/'port_bind_pins.json').read_text()), sl)
    except Exception as e:
        r=dict(verdict='FAIL', reason=f'port-bind checker error: {e}')
    (kit/'port_bind.json').write_text(json.dumps(r,indent=1)+'\n')
    print('PORT_BIND',r['verdict'],json.dumps(r,sort_keys=True))
    return 0 if r['verdict']=='PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
