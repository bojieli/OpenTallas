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
import hashlib
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


def view_eligibility(masters, slabs, stations):
    """A routed representative is not an interface-complete die timing view.

    The historical `etm_bound` list means only that a Liberty was substituted.
    Keep that pathfinding ABI, but never use its complement as a signoff gate.
    """
    result = {}
    for master in sorted(masters):
        if master == 'qfd_cdc':
            kind, complete, reason = 'exact_per_bit', True, 'Existing die-to-element bit binding'
        elif master in slabs:
            kind, complete, reason = 'representative_by_role', False, 'One port group does not characterize eight groups and their FIFOs'
        elif master in stations:
            kind, complete, reason = 'representative_by_direction', False, 'Bit-zero copy omits real ready, reset, branch, assembly and clock-forwarding paths'
        elif master == 'ot_hbm3e_phy':
            kind, complete, reason = 'external_characterized_library', None, 'External library is not audited by this mapper'
        else:
            kind, complete, reason = 'assumed_constant', False, 'No routed element binding'
        result[master] = dict(classification=kind, interface_complete=complete,
            final_die_signoff_eligible=complete is True, reason=reason)
    return result


def require_interface_complete(views):
    blockers = [m for m, v in views.items() if not v['final_die_signoff_eligible']]
    if blockers:
        raise ValueError('Final die signoff refused: incomplete or unaudited views: ' + ', '.join(blockers))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--etm', type=Path, required=True)
    ap.add_argument('--lef', type=Path, required=True)
    ap.add_argument('--assumed', type=Path, required=True, help='dir with qfd_elements_{ss,ff}.lib (assumed constants)')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--recipe', default='r20c')
    ap.add_argument('--require-final-signoff', action='store_true',
                    help='fail closed if any master lacks an exact, interface-complete timing view; default output remains pathfinding')
    ap.add_argument('--corners', default='ss,ff', help='comma list; tt needs *_tt.lib ETMs and qfd_elements_tt.lib')
    ap.add_argument('--stubs', type=Path, default=None, help="die_top_lint's stubs (pin directions for --station-etm)")
    ap.add_argument('--station-etm', type=Path, default=None,
                    help='dir with cst/ot_qwen_die_station_cst_{ss,ff}.lib and chead/... (closed routes s2_cst_hm40 / '
                         's2_chead_hm40): bound BY DIRECTION to qfd_cst_*, qfd_chead_* and the r21 relays qfd_rly*')
    a = ap.parse_args(argv)
    import die_top_lint as DTL
    DTL.QWEN_RECIPE = a.recipe
    # die-evidence-2 2026-10-09: r22k (ROM die of the ROM die + KV die pair) has no qfd_cdc (the CDC frames moved to the KV die)
    bind = (DTL.real_blocks('qwen_rom').get('qfd_cdc') or {}).get('binding', {})
    a.out.mkdir(parents=True, exist_ok=True)
    lef_text = a.lef.read_text()
    slabs = sorted(set(re.findall(r'^MACRO (qfd_port_tiles_\w+)$', lef_text, re.M)))
    # the CDC ETM is optional: its routed ODB is gone (EPYC3 cleanup 2026-10-08); without it qfd_cdc stays ASSUMED
    has_cdc = bool(bind) and all((a.etm / f'ot_qwen_stream4_cdc_pc_{c}.lib').exists() for c in a.corners.split(','))
    bound = (['qfd_cdc'] if has_cdc else []) + slabs
    station_bound = {}
    pin_bindings, source_hashes = {}, {}
    for c in a.corners.split(','):
        slab_t = (a.etm / f'ot_qwen_slab_port_group_{c}.lib').read_text()
        cdc_t = (a.etm / f'ot_qwen_stream4_cdc_pc_{c}.lib').read_text() if has_cdc else None
        cdc_b, slab_b = (blocks(cdc_t) if has_cdc else {}), blocks(slab_t)
        pin_bindings[c] = {}

        def record_pin(master, ports, port, bit, source, source_text, source_pin, body):
            source_hashes[source] = hashlib.sha256(source_text.encode()).hexdigest()
            die_pin = f'{port}[{bit}]' if ports[port][1] else port
            pin_bindings[c].setdefault(master, {})[die_pin] = dict(source=source, pin=source_pin,
                source_pin_sha256=hashlib.sha256(body.encode()).hexdigest())
            return body
        widths, cells = set(), []
        # qfd_cdc: exact
        if has_cdc:
            cp = lef_ports(a.lef, 'qfd_cdc')

            def cdc_src(p, i):
                pin = bind[p][i] if isinstance(bind.get(p), list) and len(bind[p]) > 1 else (bind[p][0] if p in bind else p)
                return record_pin('qfd_cdc', cp, p, i, f'ot_qwen_stream4_cdc_pc_{c}.lib', cdc_t, pin, cdc_b[pin])
            widths |= {w for w, idx in cp.values() if idx}
            cells.append(cell_text('qfd_cdc', cp, cdc_src))
        # slabs: by role, the group's clock pin 'clk' -> die 'ck[0]'
        for s in slabs:
            sp = lef_ports(a.lef, s)
            ck = 'ck[0]' if sp.get('ck', (1, False))[1] else 'ck'

            def slab_src(p, i, ck=ck, s=s, sp=sp):
                # by role; a die word wider than the group's port reuses its bits modulo the group width (r21b slabs)
                base = 'bw_d' if re.match(r'(bw|cf)\d*$', p) else 'tw_d'
                nb = sum(1 for k in slab_b if k.startswith(base + '['))
                src = 'clk' if p == 'ck' else f'{base}[{i % nb}]'
                body = record_pin(s, sp, p, i, f'ot_qwen_slab_port_group_{c}.lib', slab_t, src, slab_b[src])
                return retarget(body, {'clk': ck, 'bw_clk': ck})
            widths |= {w for w, idx in sp.values() if idx}
            cells.append(cell_text(s, sp, slab_src))
        # stations / column heads / r21 relays: by direction -- every input bit <- the station's a_d[0] (setup/hold
        # at its input flop), every output bit <- b_d[0] (clock->Q + drive), the clock pin <- clk
        if a.station_etm is not None:
            import qwen_die_element_lib as EL
            sd = EL.stub_dirs(a.stubs)
            for fam, pat in (('cst', r'qfd_cst_\w+|qfd_rly_\w+'), ('chead', r'qfd_chead_\w+')):
                et = (a.station_etm / fam / f'ot_qwen_die_station_{fam}_{c}.lib').read_text()
                eb = blocks(et)
                for mst in sorted(set(re.findall(r'^MACRO (' + pat + r')$', lef_text, re.M))):
                    mp = lef_ports(a.lef, mst)
                    ckn = 'ck[0]' if mp.get('ck', (1, False))[1] else 'ck'

                    def st_src(p, i, eb=eb, ckn=ckn, mst=mst, mp=mp, fam=fam, et=et):
                        if p == 'ck':
                            src = 'clk'
                        else:
                            dirs, _ = EL.bit_dirs(mst, p, i + 1, sd)
                            src = 'b_d[0]' if dirs[i] == 'output' else 'a_d[0]'
                        body = record_pin(mst, mp, p, i, f'{fam}/ot_qwen_die_station_{fam}_{c}.lib', et, src, eb[src])
                        return retarget(body, {'clk': ckn})
                    widths |= {w for w, idx in mp.values() if idx}
                    cells.append(cell_text(mst, mp, st_src))
                    if mst not in bound:
                        bound.append(mst)
                    station_bound[mst] = f'ot_qwen_die_station {fam} (s2_{fam}_hm40 ETM, by pin direction)'
        hdr = (header(cdc_t).replace(f'library (ot_qwen_stream4_cdc_pc_{c})', f'library (qfd_etm_{c})') if has_cdc else
               re.sub(r'library \(\S+\)', f'library (qfd_etm_{c})', header(slab_t), count=1))
        (a.out / f'qfd_etm_{c}.lib').write_text(hdr + types(widths) + '\n' + '\n'.join(cells) + '\n}\n')
        # assumed library without the bound cells
        t = (a.assumed / f'qfd_elements_{c}.lib').read_text()
        for b in bound:
            t = re.sub(r'\n  cell \(' + re.escape(b) + r'\) \{.*?\n  \}(?=\n)', '', t, flags=re.S)
        (a.out / f'qfd_elements_{c}.lib').write_text(t)
    lef_all = sorted(set(re.findall(r'^MACRO (\S+)$', lef_text, re.M)))
    eligibility = view_eligibility(lef_all, slabs, station_bound)
    rec = dict(schema='opentallas.qwen_die_element_views.v2', recipe=a.recipe,
               etm_bound=dict(**({'qfd_cdc': 'ot_qwen_stream4_cdc_pc r11a (exact per bit)'} if has_cdc else {}),
                              **{s: 'ot_qwen_slab_port_group r11c (by role: bw*/cf* <- bw_d, rw/cw* <- tw_d)'
                                 for s in slabs}, **station_bound),
               etm_generated_not_bound=['ot_qwen_rom_core r5b_f3ba (no die master carries its controller-cut ports)'],
               real_lib=['ot_hbm3e_phy (its own characterised .lib)'],
               assumed_constants=sorted({m for m in lef_all if m not in bound and m != 'ot_hbm3e_phy'}),
               view_eligibility=eligibility, source_library_sha256=source_hashes,
               source_pin_bindings=pin_bindings,
               pathfinding_only=any(not v['final_die_signoff_eligible'] for v in eligibility.values()),
               final_die_signoff_eligible=all(v['final_die_signoff_eligible'] for v in eligibility.values()),
               qualification_scope='Interface coverage only; corner margins, DRC, clock budgets and die-context STA remain separate gates')
    (a.out / 'views.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(bound=len(bound), assumed=len(rec['assumed_constants'])), indent=1))
    if a.require_final_signoff:
        require_interface_complete(eligibility)


if __name__ == '__main__':
    main()
