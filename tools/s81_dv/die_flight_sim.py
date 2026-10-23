#!/usr/bin/env python3
"""STW-S81c-RTLGAP3 (10-22): lane-flight bench model for a WHOLE-DIE RTL sim (CUT-B head die and similar TBs that
instantiate die.v directly, not a dv_slice_cut cut).

RTL relay stations are zero-delay, so every dsfd_dvland_* landing receives its lane word and forwarded clock ck_f with
NO flight.  The landing reads its ring at strap K (die.v .k(...)) and is legal only for flight F in [K - D + 1, K - 1]
(dv_slice_cut S81-LBGAP/G1/G8).  With F = 0 every landing with K >= D faults at warm-up: the CUT-B 'die landing fault
(cycle 55)' on the 276/276l landings (K 4..19), with or without the kit reset landings.

This rewrites each landing instance line: .ck_f/.i go through dv_flight_sim #(.W, .F) (the same module dv_slice_cut
appends; copied verbatim from tools/s81_dv/dv_slice_cut.py FLIGHT_SIM).  F per landing:
  land-plan row with S1 at --corner: F = clamp(ceil(-S1 / T), K - D + 1, K - 1)
  model row / no row (--land-model):  F = K - 1 (the flight the strap assumes; G7 MODEL K = F + 1)
Bench side only (wire flight), never in the die netlist.  --flight-shift N (MUTANT): F + N -> landings must fault.
Writes <out> (die.v + dv_flight_sim) and <out>.flight.json (per landing K, F, source).
"""
import argparse, json, math, re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def flight_sim_src():
    t = (HERE / 'dv_slice_cut.py').read_text()
    m = re.search(r'^FLIGHT_SIM = """(.*?)"""', t, re.S | re.M)
    return m.group(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--die-v', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--land-plan', required=True); ap.add_argument('--corner', default='tt', choices=['tt', 'ff'])
    ap.add_argument('--land-model', action='store_true'); ap.add_argument('--flight-shift', type=int, default=0)
    a = ap.parse_args()
    LPJ = json.loads(Path(a.land_plan).read_text()); LP = {r['link']: r for r in LPJ['links']}
    T, D0 = float(LPJ['T_ps']), int(LPJ.get('D', 4))
    out, rec, nets = [], {}, {}
    text = Path(a.die_v).read_text()
    for ln in text.split('\n'):
        m = re.match(r'\s*wire\s*(?:\[(\d+):(\d+)\])?\s*([\w\\\s,]+);', ln)
        if m:
            for n in m.group(3).split(','):
                nets[n.strip()] = (int(m.group(1)) - int(m.group(2)) + 1) if m.group(1) else 1
    for ln in text.split('\n'):
        m = re.match(r'(\s*)(dsfd_dvland_\w+)\s+(\w+)\s*\((.*)\);\s*$', ln)
        if not m:
            out.append(ln); continue
        ind, mst, inst, body = m.groups()
        pins = dict(re.findall(r'\.(\w+)\(([^()]*)\)', body))
        km = re.fullmatch(r"(\d+)'([dh])([0-9a-fA-F]+)", pins['k'].strip())
        K = int(km.group(3), 16 if km.group(2) == 'h' else 10)
        link = inst[3:] if inst.startswith('ld_') else inst
        r = LP.get(link); D = int((r or {}).get('D', D0))
        s1 = (r or {}).get('s1', {}).get(a.corner) if r else None
        if s1 is None:
            if not a.land_model:
                raise SystemExit(f'die_flight_sim: landing {inst} has no S1 at {a.corner} (use --land-model)')
            f_raw, src = K - 1, 'model' if r else 'no_row_model'
        else:
            f_raw, src = math.ceil(-float(s1) / T), 'land_plan'
        if r and r.get('K') is not None and int(r['K']) != K:
            raise SystemExit(f'die_flight_sim: {inst} die.v K {K} != land-plan K {r["K"]}')
        F = max(min(max(f_raw, K - D + 1), K - 1) + a.flight_shift, 0)
        di = pins['i'].strip()
        mw = re.fullmatch(r'([\w\\]+)\s*\[(\d+):(\d+)\]', di)
        w = (int(mw.group(2)) - int(mw.group(3)) + 1) if mw else nets.get(di)
        if w is None:
            raise SystemExit(f'die_flight_sim: {inst} .i({di}) width unknown')
        rec[inst] = dict(master=mst, K=K, D=D, F=F, F_raw=f_raw, clipped=F - a.flight_shift != f_raw, source=src)
        if F:
            out.append(f'{ind}wire {inst}__ckf_d; wire [{w - 1}:0] {inst}__i_d;   // lane flight {F} cycles (K {K}, D {D}, {src})')
            out.append(f'{ind}dv_flight_sim #(.W({w}), .F({F})) {inst}__flight (.ck_in({pins["ck_f"]}), .rs({pins["rs"]}), '
                       f'.i_in({di}), .ck_out({inst}__ckf_d), .i_out({inst}__i_d));')
            body = body.replace(f'.ck_f({pins["ck_f"]})', f'.ck_f({inst}__ckf_d)', 1).replace(f'.i({pins["i"]})', f'.i({inst}__i_d)', 1)
        out.append(f'{ind}{mst} {inst} ({body});')
    out.append(flight_sim_src())
    Path(a.out).write_text('\n'.join(out) + '\n')
    Path(a.out + '.flight.json').write_text(json.dumps(dict(die_v=a.die_v, land_plan=a.land_plan, corner=a.corner,
                                                            flight_shift=a.flight_shift, landings=rec), indent=1) + '\n')
    from collections import Counter
    print('die_flight_sim:', len(rec), 'landings', dict(Counter((v['master'], v['F']) for v in rec.values())),
          'clipped', sum(v['clipped'] for v in rec.values()))


if __name__ == '__main__':
    main()
