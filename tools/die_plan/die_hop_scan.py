"""DIE-LEVEL cross-face reach scan (PATH-QC-D3HOOK 2026-10-25): every partition->partition port of a plan, per bit.

For each plan port pid (src part A.bus -> dst part B.bus; the die top wires w_<pid> A.bus[b] -> B.bus[b], gen_rtl.die_top,
so bit b maps to bit b; any mirrored bit order is already in each side's pin table) and each bit b incl. the epoch bit:

    hop = |last register in A on bit b -> A's pin b|   (A frame -> die frame)
        + |A's pin b -> B's pin b|                     (die frame; 0 when the faces abut and the pin tables agree)
        + |B's pin b -> first register in B on bit b|  (B frame -> die frame)

all Manhattan, um.  Pins: gen_phys.type_pins (the TYPE pin table the kit hardens) mapped to the die with Plan.to_die
(orient R0/MX/MY/R180).  Registers: an ft slot bus (<slot>_i / <slot>_o) uses the same station sites as the per-type
scan (results/proto_codex_1025/corrected/scan.py): station 0 = the in-face flop (1 um inset) when bit_sites_um exists,
stations j>=1 = bit_sites_um[j-1][b] cell centre, else regs_um[j], else evenly on check.zroute; A's last register =
station k-1, B's first = station 0.  A non-FT bus end is a registered pin (pin_registers rule) and is taken AT the pin
(distance 0, labelled 'pinreg').  Die-IO ports (@die) are skipped.  Limit = 405 um (Plan.reach).

    python3 tools/die_plan/die_hop_scan.py PLAN.json OUT.json [TYPE ...]   (types = W5-path report filter)
"""
import json, sys, time
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import schema as S, gen_phys, check, ft_bit_sites  # noqa: E402

INSET = {'E': (-1, 0), 'W': (1, 0), 'N': (0, -1), 'S': (0, 1)}


def input_site(pin):
    """Legacy face-placement target of a real input pin; never regs_um[0]."""
    x, y, face = pin
    dx, dy = INSET[face]
    return x + dx, y + dy


def pin_table(P, tn):
    pins = defaultdict(dict)
    for bus, bit, _, x, y, face in gen_phys.type_pins(P, tn):
        pins[bus][bit] = (x, y, face)
    return pins


def normal_slot(P, tn, sn, *, full=None):
    """Only normal FT has the input-face S0 constructor.

    Exact native full-stage packets retain their named-cell coordinates.
    Registered landing inputs retain their separate, legacy post-ring model.
    """
    if full is None:
        from ft_full_stage import load
        full = load(P, tn)
    if sn in full:
        return False
    if P.types[tn].get('clock', {}).get('landing_contract'):
        return False
    raw = getattr(P, 'raw', {})
    edges = raw.get('clock', {}).get('landing_network', {}).get('edges', [])
    landed = {e['id'][len('cland_clk__'):] for e in edges
              if e.get('id', '').startswith('cland_clk__')}
    if not landed:
        return True
    return not any(pid in landed and p['dst']['bus'] == sn+'_i'
                   and p['dst']['part'] in P.parts
                   and P.parts[p['dst']['part']]['type'] == tn
                   for pid, p in getattr(P, 'ports', {}).items())


def station_site(slot, stage, bit, ap, bp, *, normal=True):
    """Normal constructor targets; internal legacy placement stays unchanged."""
    a, b = input_site(ap), input_site(bp)
    if stage == 0 and normal:
        return a
    if slot.get('bit_sites_um') and stage > 0:
        x, y = slot['bit_sites_um'][stage-1][bit]
        w, h = slot['bit_site_cell_um']
        return x+w/2, y+h/2
    if slot.get('bit_sites_um'):
        return a
    if slot.get('regs_um'):
        return tuple(slot['regs_um'][stage])
    route = check.zroute(a, b, ap[2], bp[2])
    return check.point_at(route, check.plen(route)*stage/int(slot.get('stations', 1)))


def first_internal_hops(P, tn, slot, *, pins=None, full=None):
    """Every REAL normal input bit's S0->S1 target distance, before placement.

    An output-only epoch is not an invented input. Exact named/native and
    landed paths keep their existing constructors and are not reinterpreted.
    """
    if int(slot.get('stations', 1)) < 2 or not normal_slot(P, tn, slot['name'], full=full):
        return []
    pins = pin_table(P, tn) if pins is None else pins
    pi, po = pins[slot['name']+'_i'], pins[slot['name']+'_o']
    return [(bit, md(station_site(slot, 0, bit, ap, po.get(bit) or ap),
                     station_site(slot, 1, bit, ap, po.get(bit) or ap)))
            for bit, ap in sorted(pi.items())]


def type_tables(P, tn):
    """({bus: {bit: (x, y, face)}}, {slot: {bit: [station xy]}}), TYPE frame."""
    pins = pin_table(P, tn)
    from ft_full_stage import load, centre
    full = load(P, tn)
    chains = {}
    for slot in P.types[tn].get('ft_slots', []):
        sn, k = slot['name'], int(slot.get('stations', 1))
        ft_bit_sites.validate_slot(slot)
        pi, po, ch = pins[sn + '_i'], pins[sn + '_o'], {}
        normal = normal_slot(P, tn, sn, full=full)
        for bit in set(pi) | set(po):
            ap, bp = pi.get(bit) or po[bit], po.get(bit) or pi[bit]
            st = []
            for j in range(k):
                if sn in full:
                    st.append(centre(full[sn][j, bit]))
                else:
                    st.append(station_site(slot, j, bit, ap, bp, normal=normal))
            ch[bit] = st
        chains[sn] = ch
    return pins, chains


def md(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def main(plan, out, focus):
    t0 = time.time(); P = S.Plan(S.load(plan), Path(plan)); tabs = {}

    def tab(tn):
        if tn not in tabs:
            tabs[tn] = type_tables(P, tn)
        return tabs[tn]
    rows, skipped = [], 0
    for pid, pr in P.ports.items():
        A, B = pr['src']['part'], pr['dst']['part']
        if S.DIE_PART in (A, B):
            skipped += 1; continue
        ba, bb = pr['src']['bus'], pr['dst']['bus']
        (pa, ca), (pb, cb) = tab(P.parts[A]['type']), tab(P.parts[B]['type'])
        sa, sb = P.buses(A)[ba].get('slot'), P.buses(B)[bb].get('slot')
        worst = None
        for bit in range(S.port_pins_count(pr)):
            qa, qb = P.to_die(A, pa[ba][bit][:2]), P.to_die(B, pb[bb][bit][:2])
            ra = P.to_die(A, ca[sa][bit][-1]) if sa else qa        # last register in A on this bit
            rb = P.to_die(B, cb[sb][bit][0]) if sb else qb         # first register in B on this bit
            d = (md(ra, qa), md(qa, qb), md(qb, rb)); h = sum(d)
            rec = dict(port=pid, a=f'{A}.{ba}', a_type=P.parts[A]['type'], b=f'{B}.{bb}', b_type=P.parts[B]['type'],
                       bit=bit, hop_um=round(h, 3), a_reg_to_pin=round(d[0], 3), pin_to_pin=round(d[1], 3),
                       pin_to_b_reg=round(d[2], 3), a_end='ft_last_station' if sa else 'pinreg',
                       b_end='ft_first_station' if sb else 'pinreg', over=h > P.reach + 1e-6)
            rows.append(rec)
    rows.sort(key=lambda r: -r['hop_um'])
    per_port = {}
    for r in rows:
        per_port.setdefault(r['port'], dict(r, over_bits=0))['over_bits'] += r['over']
    fp = [r for r in per_port.values() if r['a_type'] in focus or r['b_type'] in focus]
    res = dict(plan=plan, sha256_prefix=__import__('hashlib').sha256(Path(plan).read_bytes()).hexdigest()[:12],
               reach_um=P.reach, ports=len(per_port), die_io_ports_skipped=skipped, bits=len(rows),
               max_hop_um=rows[0]['hop_um'] if rows else 0, bits_over=sum(r['over'] for r in rows),
               ports_over=sum(r['over_bits'] > 0 for r in per_port.values()),
               pin_mismatch_bits=sum(r['pin_to_pin'] > 1e-3 for r in rows),
               top_bits=rows[:10], worst_bit_per_port=sorted(per_port.values(), key=lambda r: -r['hop_um']),
               focus_types=sorted(focus), focus_worst=fp[:40], elapsed_s=round(time.time() - t0, 1))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(res, indent=1) + '\n')
    print('ports', res['ports'], 'bits', res['bits'], 'max', res['max_hop_um'], 'bits>405', res['bits_over'],
          'ports>405', res['ports_over'], 'pin_mismatch_bits', res['pin_mismatch_bits'], 's', res['elapsed_s'])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], set(sys.argv[3:]))
