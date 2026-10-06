#!/usr/bin/env python3
"""Qwen ROM die: bind ETMs of the CLOSED, ROUTED Qwen elements to the die's abstract masters for die-level STA.

ETMs: OpenSTA write_timing_model on each element's final ODB + SPEF + SDC (propagated clock, plus the boundary
reference SDC its sign-off used) at SS and FF; each reproduces its sign-off record exactly (see the README of the
record directory).  This tool writes, per corner, one Liberty library whose cells carry the DIE master names and pin
names, every die pin bit's body (direction, capacitance, timing arcs) copied from its element pin:

  qfd_cdc            <- ot_qwen_stream4_cdc_pc (route r11a)      EXACT per bit: die_top_lint's binding (ho/hi/co/ci
                                                                  -> h_* / l_* / w_* pins), clk/hclk/c_arst_n/h_arst_n
  qfd_port_tiles_*   <- ot_qwen_slab_port_group (route r11c)     BY ROLE: every block-word / fragment input bit
                                                                  (bw*, cf*) <- bw_d[i], every output word bit
                                                                  (rw, cw*) <- tw_d[i] (a band slab is 8 such groups +
                                                                  their word FIFOs: the group's pin timing is the
                                                                  slab's boundary timing; the slab itself is not routed)
  clock pins         <- the element's clock pin (clock tree insertion arcs), related pins renamed to the die clock

Every other die master keeps the ASSUMED-constant view (tools/qwen_die_element_lib.py); the list is returned and
recorded.  The core (ot_qwen_rom_core, r5b_f3ba) ETM is generated but NOT bound: no die master carries its
controller-cut ports (the spine sequencer slab is a reservation with die-word ports).

    python3 tools/qwen_die_etm_map.py --etm DIR --lef CASE/elements.lef --assumed DIR --out DIR --recipe r20c
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))


def blocks(text):
    """name -> body text of every pin("...") group (scalar pins and bus bits)."""
    out = {}
    for m in re.finditer(r'pin\("([^"]+)"\)\s*\{', text):
        i, depth = m.end(), 1
        while depth:
            c = text[i]
            depth += (c == '{') - (c == '}')
            i += 1
        out[m.group(1)] = text[m.end():i - 1]
    return out


def header(text):
    """library header up to (not including) the first cell group, without the library's closing brace."""
    return text[:text.index('  cell (')]


def retarget(body, clkmap):
    for a, b in clkmap.items():
        body = body.replace(f'related_pin : "{a}"', f'related_pin : "{b}"')
    return body


def lef_ports(path, master):
    ports, cur = {}, None
    for ln in Path(path).read_text().splitlines():
        t = ln.split()
        if t[:1] == ['MACRO']:
            cur = t[1]
        elif cur == master and t[:1] == ['PIN']:
            m = re.match(r'([^\[]+)(?:\[(\d+)\])?$', t[1])
            p, i = m.group(1), m.group(2)
            if p in ('VDD', 'VSS'):
                continue
            w = (int(i) + 1) if i is not None else 1
            ports[p] = max(ports.get(p, (0, False))[0], w), (i is not None) or ports.get(p, (0, False))[1]
    return ports


def cell_text(name, ports, src):
    """ports: {die port: (width, indexed)}, src(port, bit) -> body text."""
    L = [f'  cell ("{name}") {{', '    is_macro_cell : true;', '    dont_touch : true;', '    dont_use : true;']
    for p, (w, idx) in sorted(ports.items()):
        if not idx:
            L.append(f'    pin("{p}") {{{src(p, 0)}}}')
            continue
        d = re.search(r'direction : (\w+);', src(p, 0)).group(1)
        L.append(f'    bus("{p}") {{\n      bus_type : qd_b{w};\n      direction : {d};')
        for i in range(w):
            L.append(f'    pin("{p}[{i}]") {{{src(p, i)}}}')
        L.append('    }')
    L.append('  }')
    return '\n'.join(L)


def types(widths):
    return '\n'.join(f'  type ("qd_b{w}") {{\n    base_type : array;\n    data_type : bit;\n    bit_width : {w};\n'
                     f'    bit_from : {w - 1};\n    bit_to : 0;\n  }}' for w in sorted(widths))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--etm', type=Path, required=True)
    ap.add_argument('--lef', type=Path, required=True)
    ap.add_argument('--assumed', type=Path, required=True, help='dir with qfd_elements_{ss,ff}.lib (assumed constants)')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--recipe', default='r20c')
    a = ap.parse_args(argv)
    import die_top_lint as DTL
    DTL.QWEN_RECIPE = a.recipe
    bind = DTL.real_blocks('qwen_rom')['qfd_cdc']['binding']
    a.out.mkdir(parents=True, exist_ok=True)
    lef_text = a.lef.read_text()
    slabs = sorted(set(re.findall(r'^MACRO (qfd_port_tiles_\w+)$', lef_text, re.M)))
    bound = ['qfd_cdc'] + slabs
    for c in ('ss', 'ff'):
        cdc_t = (a.etm / f'ot_qwen_stream4_cdc_pc_{c}.lib').read_text()
        slab_t = (a.etm / f'ot_qwen_slab_port_group_{c}.lib').read_text()
        cdc_b, slab_b = blocks(cdc_t), blocks(slab_t)
        widths, cells = set(), []
        # qfd_cdc: exact
        cp = lef_ports(a.lef, 'qfd_cdc')

        def cdc_src(p, i):
            pin = bind[p][i] if isinstance(bind.get(p), list) and len(bind[p]) > 1 else (bind[p][0] if p in bind else p)
            return cdc_b[pin]
        widths |= {w for w, idx in cp.values() if idx}
        cells.append(cell_text('qfd_cdc', cp, cdc_src))
        # slabs: by role, the group's clock pin 'clk' -> die 'ck[0]'
        for s in slabs:
            sp = lef_ports(a.lef, s)
            ck = 'ck[0]' if sp.get('ck', (1, False))[1] else 'ck'

            def slab_src(p, i, ck=ck):
                if p == 'ck':
                    return slab_b['clk']
                src = f'bw_d[{i}]' if re.match(r'(bw|cf)\d*$', p) else f'tw_d[{i}]'
                return retarget(slab_b[src], {'clk': ck, 'bw_clk': ck})
            widths |= {w for w, idx in sp.values() if idx}
            cells.append(cell_text(s, sp, slab_src))
        hdr = header(cdc_t).replace(f'library (ot_qwen_stream4_cdc_pc_{c})', f'library (qfd_etm_{c})')
        (a.out / f'qfd_etm_{c}.lib').write_text(hdr + types(widths) + '\n' + '\n'.join(cells) + '\n}\n')
        # assumed library without the bound cells
        t = (a.assumed / f'qfd_elements_{c}.lib').read_text()
        for b in bound:
            t = re.sub(r'\n  cell \(' + re.escape(b) + r'\) \{.*?\n  \}(?=\n)', '', t, flags=re.S)
        (a.out / f'qfd_elements_{c}.lib').write_text(t)
    lef_all = sorted(set(re.findall(r'^MACRO (\S+)$', lef_text, re.M)))
    rec = dict(schema='opentallas.qwen_die_element_views.v1', recipe=a.recipe,
               etm_bound=dict(qfd_cdc='ot_qwen_stream4_cdc_pc r11a (exact per bit)',
                              **{s: 'ot_qwen_slab_port_group r11c (by role: bw*/cf* <- bw_d, rw/cw* <- tw_d)'
                                 for s in slabs}),
               etm_generated_not_bound=['ot_qwen_rom_core r5b_f3ba (no die master carries its controller-cut ports)'],
               real_lib=['ot_hbm3e_phy (its own characterised .lib)'],
               assumed_constants=[m for m in lef_all if m not in bound and m != 'ot_hbm3e_phy'])
    (a.out / 'views.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(bound=len(bound), assumed=len(rec['assumed_constants'])), indent=1))


if __name__ == '__main__':
    main()
