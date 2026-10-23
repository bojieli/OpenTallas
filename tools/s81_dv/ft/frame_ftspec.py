#!/usr/bin/env python3
"""FT-S81 10-23: quantised shifted-corridor ft spec for the S81 frames (RECIPE.md sections 3/6, COORD rulings).

Frame master frame (R0, W-array orientation; the E array uses the MX master, i.e. the same spec mirrored):
own lanes leave the E face in the kit band (y 91-603). Through-bundles enter the W face at slot j and leave the E face
at slot j+1. Slot 0 = the kit's own band, slot 1 = y 700-1100 (below ck_r1 1588), slot 2 = y 1800-2200 (below ck_r2 2805).
One bundle = the 4 x lanes (276 b, inbound E->W, each with its forwarded clock) + 1 ret lane (70 b, outbound W->E, with
its forwarded clock): the full lane set of the neighbour frame. Variant ftN populates slots 0..N-1 on W and 1..N on E,
so every corridor carries a real lane (no tie-offs). Registers: in + out (pin-register rule); the in-block hop is the
frame width (1436.8 um), within the full-cycle 1.5 mm reach, so full-cycle stations; --clock block (default) puts them on
the frame clock ck_r0 (one station per frame is impossible: frame pitch 1436.8 + 86 = 1523 um > 1499 um M8 reach).
Usage: frame_ftspec.py --base col_h9 --n 2 --out SPEC.json
"""
import argparse, json
SLOTS = [(140.0, 552.0), (700.0, 1100.0), (1800.0, 2200.0), (2300.0, 2700.0)]
OUTLINE = {'col_h9': (1436.832, 3369.6), 'col_h10': (1436.832, 3672.0)}
KIT_TOP = {'col_h9': 'col_h9_l4_lp', 'col_h10': 'col_h10_l4_lp'}


def bundle_ports(j, W, path0):
    """ports/paths for the bundle that enters W at slot j and leaves E at slot j+1; returns (ports, paths)"""
    wlo, whi = SLOTS[j]; elo, ehi = SLOTS[j + 1]
    lanes = [('x%d' % l, 276, 'E') for l in range(4)] + [('r', 70, 'W')]   # (tag, bits, entry face)
    n = len(lanes); ports, paths = [], []
    for i, (tag, bits, ent) in enumerate(lanes):
        k = path0 + i
        # split each slot band evenly over the 5 lanes of the bundle (equal offsets on both faces -> aligned neighbours)
        wa = wlo + (whi - wlo) * i / n; wb = wlo + (whi - wlo) * (i + 1) / n - 2.0
        ea = elo + (ehi - elo) * i / n; eb = elo + (ehi - elo) * (i + 1) / n - 2.0
        fin, fout = (('E', ea, eb), ('W', wa, wb)) if ent == 'E' else (('W', wa, wb), ('E', ea, eb))
        ports += [dict(name=f'ft{k}_i', path=k, dir='input', face=fin[0], lo=round(fin[1], 3), hi=round(fin[2], 3), layer='M8', bits=bits),
                  dict(name=f'ft{k}_o', path=k, dir='output', face=fout[0], lo=round(fout[1], 3), hi=round(fout[2], 3), layer='M8', bits=bits)]
        y = (fin[1] + fin[2]) / 2
        xin, xout = (W - 20.0, 20.0) if ent == 'E' else (20.0, W - 20.0)
        paths.append(dict(path=k, lane=f'bundle{j}_{tag}', **{'in': f'ft{k}_i', 'out': f'ft{k}_o'}, bits=bits, stages=2,
                          len_um=round(W, 1), rep_sites=4, regs_um=[[xin, round(y, 1)], [xout, round((fout[1] + fout[2]) / 2, 1)]]))
    return ports, paths


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--base', choices=sorted(OUTLINE), default='col_h9')
    ap.add_argument('--n', type=int, default=2); ap.add_argument('--out', required=True)
    # --clock block (FT-S81 00:55 decision): stations are plain pin registers on the frame's core root ck_r0, so the ft
    # lanes are LANDED into the frame region (landed-regions standard): frame->frame hops are neighbour-region links,
    # a chain entry from a forwarded die lane needs one die landing, an exit restarts the forwarded clock like ret.
    ap.add_argument('--clock', choices=['block', 'forwarded'], default='block'); a = ap.parse_args()
    W, H = OUTLINE[a.base]; ports, paths = [], []
    for j in range(a.n):
        p, q = bundle_ports(j, W, 5 * j); ports += p; paths += q
    spec = dict(schema='opentallas.die_feedthrough.ftspec.v1', die='s81', block=f'{a.base}_ft{a.n} (quantised, all instances)',
                master=KIT_TOP[a.base], variant=f'{KIT_TOP[a.base]}__ft{a.n}', outline=[W, H], orient='R0',
                layer_contract=dict(signal_max='M7', ft_layers=['M8', 'M9'], pg_max='M7'), clock=a.clock,
                station_hc=0, ports=ports, paths=paths,
                note='FT-S81 quantised shifted-corridor spec (RECIPE.md 6.1); the E array uses the MX master of the same variant')
    json.dump(spec, open(a.out, 'w'), indent=1)
    print(a.out, len(ports), 'ports', len(paths), 'paths', sum(p['bits'] for p in paths), 'bits')


if __name__ == '__main__':
    main()
