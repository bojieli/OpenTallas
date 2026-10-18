#!/usr/bin/env python3
"""dv_slice_replay.py -- turn the compiler's static schedule into the slice bench's replay / check files
(LAYERBENCH-S81, TOK.DS.BENCH.3, 10-18).

Input: the compiler's DIR (dv_layer_compile.py: schedule.json events + links, prog/ctl_templates.json), the cut slice's
tb_ports.json (dv_slice_tb.py) and the die.v sid straps.  Supported event kinds (the L0 slice-norm smoke):

  CTL at <slice>.ri_e / ri_w   the neighbour slice's ring stop injects the template beat on its line toward the slice
                               (ot_s81sl_rstop: a control-plane line beat with hops 0 takes the side's line default,
                               W side hops = col, E side 7 - col, src = the injector's sid strap).  The compiler's event
                               cycle e is the beat's line-out edge at the slice (path: neighbour line inject + link age +
                               rstop 2), so the replay drives the neighbour's <line>_src lanes (beat[276 l +: 276] on
                               lane l) for ONE cycle at e - 2 - max lane age, as the neighbour's output register would.
  check: forwarded CTL         the slice forwards the beat on its other side with hops - 1 at line-out edge e; the beat
                               lands at the next neighbour's landing outputs (inside the cut) at e + the bundle's max lane
                               age: every lane is checked at that ONE cycle (a lane with a smaller E lands earlier and
                               tears the beat: a schedule fault, the receiving ring stop has no lane re-alignment).
Cycles are offset by --t0 (bench cycles after reset release).  Plan-only events (NX / XQ fixture payloads) are listed
in replay.json as unchecked until the fixtures fork supplies the golden words.
Usage: dv_slice_replay.py --prog DIR --ports tb_ports.json --die-v die.v --slice u_s_3S --out DIR [--t0 100]
       [--mutant shift1 | hops]   (negative controls: replay one cycle late / a wrong hops field -> the bench must FAIL)
"""
import argparse
import json
import re
from pathlib import Path

RSTOP_HOP = 2
LANE = 276


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--prog', required=True)
    ap.add_argument('--ports', required=True)
    ap.add_argument('--die-v', required=True)
    ap.add_argument('--slice', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--t0', type=int, default=100)
    ap.add_argument('--mutant', default='')
    ap.add_argument('--check-shift', type=int, default=0,
                    help='DIAGNOSTIC ONLY: move every forward check by N cycles (to check payload / hops at a measured, '
                         'non-scheduled arrival when the schedule itself fails); recorded, never a schedule verdict')
    a = ap.parse_args(argv)
    prog = Path(a.prog)
    S = json.loads((prog / 'schedule.json').read_text())
    T = {t['i']: t for t in json.loads((prog / 'prog/ctl_templates.json').read_text())['templates']}
    ports = {p['port']: p for p in json.loads(Path(a.ports).read_text())}
    dv = Path(a.die_v).read_text()
    sid = {m.group(1): int(m.group(2)) for m in re.finditer(r'\b(u_s_\w+)\s*\(.*?\.sid\(4\'d(\d+)\)', dv)}
    sl = a.slice
    col, tier = int(sl[4]), sl[5]
    links = S['links']

    def lanes(src_inst, src_port, dst_inst):
        ls = sorted(k for k, L in links.items() if [src_inst, src_port] in L['src'] and any(x[0] == dst_inst for x in L['dst']))
        return ls

    ins, outs, rec = [], [], []
    for e in S['events']:
        if e['inst'] != sl or e['kind'] != 'CTL' or e['dir'] != 'in':
            continue
        side = e['port']                                   # ri_e: from the E neighbour (col + 1), ri_w: from col - 1
        nb_col = col + 1 if side == 'ri_e' else col - 1
        nb = f'u_s_{nb_col}{tier}'
        nb_port = 'ro_w' if side == 'ri_e' else 'ro_e'
        L_in = lanes(nb, nb_port, sl)
        age_in = max(links[k]['age_edges'] for k in L_in)
        t_inj = int(round(e['cycle'] - RSTOP_HOP - age_in)) + a.t0
        ti = int(e['payload'].split()[1].rstrip(';'))
        beat = int(T[ti]['beat'], 16)
        hops = (nb_col if nb_port == 'ro_w' else 7 - nb_col)
        hw = hops + 1 if a.mutant == 'hops' else hops      # mutant: the replayed neighbour sends a wrong hops field
        wire = (beat & ~(0x1F << 4) & ~(0xF << 9)) | (hw & 0x1F) << 4 | (sid[nb] & 0xF) << 9
        if a.mutant == 'shift1':
            t_inj += 1
        for k in L_in:
            l = int(k.split('_l')[-1])
            pn = f'i__w_{k}_src'
            word = (wire >> (LANE * l)) & ((1 << LANE) - 1)
            ins.append((t_inj, ports[pn]['index'], word, k))
            ins.append((t_inj + 1, ports[pn]['index'], 0, k))
        # forwarded beat: the other side, hops - 1, landed at the next neighbour
        fw_col = col - 1 if side == 'ri_e' else col + 1
        fw = f'u_s_{fw_col}{tier}'
        fw_port = 'ro_w' if side == 'ri_e' else 'ro_e'
        fwd = (wire & ~(0x1F << 4)) | ((hops - 1) & 0x1F) << 4    # expectation from the unmutated hops
        chk = []
        if hops - 1 > 0 and 0 <= fw_col <= 7:
            L_out = lanes(sl, fw_port, fw)
            age_out = max(links[k]['age_edges'] for k in L_out) if L_out else 0
            for k in L_out:
                l = int(k.split('_l')[-1])
                pn = f'o__w_{k}_lnd'
                if pn not in ports:
                    continue
                # the beat is whole when its slowest lane lands (the compiler's line model): every lane is checked
                # at that ONE cycle -- a lane landing earlier (smaller E) tears the beat and fails here
                tc = int(round(e['cycle'] + age_out)) + a.t0 + a.check_shift
                word = (fwd >> (LANE * l)) & ((1 << LANE) - 1)
                outs.append((tc, ports[pn]['index'], (1 << LANE) - 1, word, k))
                chk.append(dict(lane=k, port=pn, cycle=tc, lane_age=links[k]['age_edges'], lane_E=links[k]['E']))
        rec.append(dict(tag=e['tag'], plan_cycle=e['cycle'], template=ti, from_=nb, lanes_in=L_in, age_in=age_in,
                        inject_cycle=t_inj, hops=hops, src_sid=sid[nb], forward_checks=chk))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ins.sort(key=lambda r: (r[0], r[1]))
    outs.sort(key=lambda r: (r[0], r[1]))
    (out / 'in.txt').write_text(''.join(f'{c} {i} {w:x}\n' for c, i, w, _ in ins))
    (out / 'out.txt').write_text(''.join(f'{c} {i} {m:x} {w:x}\n' for c, i, m, w, _ in outs))
    plan = [e for e in S['events'] if e.get('plan_only')]
    (out / 'replay.json').write_text(json.dumps(dict(schema='opentallas.s81_dv.slice_replay.v1', prog=str(prog),
        slice=sl, sid=sid.get(sl), t0=a.t0, mutant=a.mutant or None,
        check_shift=a.check_shift, verdict_kind='DIAGNOSTIC (checks moved off the schedule)' if a.check_shift else 'SCHEDULE', ctl=rec, in_events=len(ins), out_checks=len(outs),
        unchecked_plan_events=plan, ncyc=max([c for c, *_ in outs] + [c for c, *_ in ins]) + 50), indent=1) + '\n')
    print(f'dv_slice_replay: {len(rec)} CTL beats -> {len(ins)} lane events, {len(outs)} forward checks; '
          f'ncyc {max([c for c, *_ in outs] + [0]) + 50}')


if __name__ == '__main__':
    main()
