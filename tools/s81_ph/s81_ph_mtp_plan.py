#!/usr/bin/env python3
"""Contract pin plans of the DS-ROM S81 MTP elements (stream mtp-rom, 2026-10-08; RTL rtl/dsrom_sys/mtp/dsfd_mtp_tops.sv).

Pins follow the S81-PH generator conventions (tools/s81_ph/s81_ph_tiles_plan.plan: M4 on W / E faces, M5 on N / S,
offset 0.012, pitch 0.048 x pitch_tracks, 0.024 x 0.192 at the face).  Wide buses at pitch_tracks 4 (5.2 bits / um /
layer, inside the 6 b/um design target of tools/fp_margin_lint.py).  Outlines: x on the 10.8-um lcm, y on 2.16;
sized by the pin perimeter (the logic is small: yosys census below) at <= ~25 % estimated utilisation.

  element        die (home: owned by stream mtp-die)          outline (um)      cells est (yosys generic, um2)
  dsfd_mtp_seq   head die (one, beside the head controller)   151.2 x 151.2      ~4,900 (11.9k flops)
  dsfd_wfc_tok   S0 layer die (abutting the SOURCE WFC)        108.0 x 108.0      ~2,400 (4.7k flops)
  dsfd_wfc_lnk   every WFC (layer dies)                        216.0 x 151.2      ~2,100 (5.7k flops)
  dsfd_wfc_vmx   every WFC (between WFC and sp_vm)             248.4 x 241.92     ~20,900 (51k flops; routed std 32.7k um2 -> ~54 % util, reviewer DR6)
  dsfd_drf_fan   draft dies (primary rank + replica 0)         302.4 x 410.4      ~4,700 (12.4k flops)

    python3 tools/s81_ph/s81_ph_mtp_plan.py   -> physical/s81_ph_views/ports/contract/<master>/{ports.json,io_place.tcl,
                                                 ports.svh}, physical/s81_ph_views/specs/<master>.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_ph'))
import s81_ph_tiles_plan as TP  # noqa: E402

FLIT, NW, UW, VWA = 512, 21, 10, 15
SW, DW = UW + 3 * NW + 4, UW + 3 + NW

SPECS = [
    dict(master='dsfd_mtp_seq', w_um=151.2, h_um=151.2, domain='stream_1p2',
         note='head-die MTP sequencer: W = RESULT in from the head controller, E = token return to S0, '
              'N = draft chain (seed out, rows in, draft-head step out / result in), S = cfg / acc / clock',
         ports=[['f_rv', 1, 'input', 'W', 'M4', 1, 0.08], ['f_rd', FLIT, 'input', 'W', 'M4', 4, 0.5],
                ['t_rg', 1, 'output', 'W', 'M4', 1, 0.92],
                ['t_tv', 1, 'output', 'E', 'M4', 1, 0.08], ['t_td', FLIT, 'output', 'E', 'M4', 4, 0.5],
                ['f_tg', 1, 'input', 'E', 'M4', 1, 0.92],
                ['t_sv', 1, 'output', 'N', 'M5', 1, 0.03], ['t_sd', SW, 'output', 'N', 'M5', 4, 0.17],
                ['f_sg', 1, 'input', 'N', 'M5', 1, 0.31],
                ['f_wv', 1, 'input', 'N', 'M5', 1, 0.34], ['f_wd', UW, 'input', 'N', 'M5', 4, 0.38],
                ['t_wg', 1, 'output', 'N', 'M5', 1, 0.42],
                ['t_hv', 1, 'output', 'N', 'M5', 1, 0.46], ['t_hd', DW, 'output', 'N', 'M5', 4, 0.56],
                ['f_hg', 1, 'input', 'N', 'M5', 1, 0.66],
                ['f_qv', 1, 'input', 'N', 'M5', 1, 0.70], ['f_qd', DW, 'input', 'N', 'M5', 4, 0.80],
                ['t_qg', 1, 'output', 'N', 'M5', 1, 0.90],
                ['ck', 1, 'input', 'S', 'M5', 1, 0.05], ['rst', 1, 'input', 'S', 'M5', 1, 0.08],
                ['f_cfg', 2 * NW, 'input', 'S', 'M5', 4, 0.3], ['t_acc', 2 * NW + UW + 5, 'output', 'S', 'M5', 4, 0.72]]),
    dict(master='dsfd_wfc_tok', w_um=108.0, h_um=108.0, domain='stream_1p2',
         note='S0 cfg / prompt / draft store: W = DRAFT flits from dsfd_wfc_lnk, E = the WFC (prompt port in, '
              'response + cfg out; abutting, default one-edge read / opt-in READPIPE2 three-edge read + returned valid/index), S = config port / clock',
         ports=[['f_dw', FLIT + 1, 'input', 'W', 'M4', 3, 0.5],
                ['f_pr', UW + NW + 5, 'input', 'E', 'M4', 4, 0.2], ['t_pr', NW + 1, 'output', 'E', 'M4', 4, 0.48],
                ['t_cfg', 10 + 2 * NW, 'output', 'E', 'M4', 4, 0.78], ['t_ft', 1, 'output', 'E', 'M4', 1, 0.97],
                ['ck', 1, 'input', 'S', 'M5', 1, 0.05], ['rst', 1, 'input', 'S', 'M5', 1, 0.09],
                ['f_c', 3 + UW + 2 * NW, 'input', 'S', 'M5', 4, 0.55]]),
    dict(master='dsfd_wfc_lnk', w_um=216.0, h_um=151.2, domain='stream_1p2',
         note='WFC link bridge: W = die link in, E = die link out, N = the WFC in_* / out_* (abutting), '
              'S = DRAFT out to dsfd_wfc_tok, VM credit in, clock',
         ports=[['f_liv', 1, 'input', 'W', 'M4', 1, 0.05], ['f_lid', FLIT + 1, 'input', 'W', 'M4', 4, 0.5],
                ['t_lir', 1, 'output', 'W', 'M4', 1, 0.95],
                ['t_lov', 1, 'output', 'E', 'M4', 1, 0.05], ['t_lod', FLIT + 1, 'output', 'E', 'M4', 4, 0.5],
                ['f_lor', 1, 'input', 'E', 'M4', 1, 0.95],
                ['t_wiv', 1, 'output', 'N', 'M5', 1, 0.02], ['t_wid', FLIT + 1, 'output', 'N', 'M5', 4, 0.26],
                ['f_wig', 1, 'input', 'N', 'M5', 1, 0.49],
                ['f_wov', 1, 'input', 'N', 'M5', 1, 0.51], ['f_wod', FLIT + 1, 'input', 'N', 'M5', 4, 0.74],
                ['t_wog', 1, 'output', 'N', 'M5', 1, 0.98],
                ['t_dw', FLIT + 1, 'output', 'S', 'M5', 4, 0.5], ['f_vc', 1, 'input', 'S', 'M5', 1, 0.96],
                ['t_ft', 1, 'output', 'S', 'M5', 1, 0.985],
                ['ck', 1, 'input', 'S', 'M5', 1, 0.015], ['rst', 1, 'input', 'S', 'M5', 1, 0.03]]),
    dict(master='dsfd_wfc_vmx', w_um=291.6, h_um=280.8, domain='stream_1p2+serial_0p9',
         note='WFC VM / core transport: W = the WFC (VM write, VM read, read data; abutting, default one-edge read / opt-in READPIPE2 three-edge read + returned valid/index), '
              'E = sp_vm (0.9 GHz write / read), N = the WFC core start / done + VM credit, S = stage core (0.9 GHz) '
              '+ clocks',
         ports=[['f_vw', 1 + VWA + FLIT, 'input', 'W', 'M4', 3, 0.27], ['f_vr', VWA + 1, 'input', 'W', 'M4', 3, 0.53],
                ['t_vq', FLIT, 'output', 'W', 'M4', 3, 0.78],
                ['t_vqi', 7, 'output', 'W', 'M4', 1, 0.985],
                ['t_swv', 1, 'output', 'E', 'M4', 1, 0.02], ['t_swd', VWA + FLIT, 'output', 'E', 'M4', 3, 0.26],
                ['f_swr', 1, 'input', 'E', 'M4', 1, 0.495], ['f_swa', 1, 'input', 'E', 'M4', 1, 0.505],
                ['f_srq', FLIT + 1, 'input', 'E', 'M4', 3, 0.74],
                ['f_cs', UW + 2 * NW + 1, 'input', 'N', 'M5', 4, 0.25], ['t_cd', NW + 33, 'output', 'N', 'M5', 4, 0.65],
                ['t_vc', 1, 'output', 'N', 'M5', 1, 0.95],
                ['t_ks', UW + 2 * NW + 1, 'output', 'S', 'M5', 4, 0.3], ['f_kd', NW + 33, 'input', 'S', 'M5', 4, 0.62],
                ['t_srv', 1, 'output', 'S', 'M5', 1, 0.78], ['t_srd', VWA, 'output', 'S', 'M5', 4, 0.83],
                ['f_srr', 1, 'input', 'S', 'M5', 1, 0.88], ['t_ft', 1, 'output', 'S', 'M5', 1, 0.97],
                ['ck', 1, 'input', 'S', 'M5', 1, 0.02], ['ckv', 1, 'input', 'S', 'M5', 1, 0.05],
                ['rst', 1, 'input', 'S', 'M5', 1, 0.08], ['rsv', 1, 'input', 'S', 'M5', 1, 0.11]]),
    dict(master='dsfd_drf_fan', w_um=302.4, h_um=410.4, domain='stream_1p2',
         note='draft-die fan-out node (N 4): N = parent link, S = this die (local engine), W = children 0 / 1, '
              'E = children 2 / 3 (bit-sliced child buses: child k = bits k*513 ..)',
         ports=[['f_uiv', 1, 'input', 'N', 'M5', 1, 0.02], ['f_uid', FLIT + 1, 'input', 'N', 'M5', 4, 0.26],
                ['t_uir', 1, 'output', 'N', 'M5', 1, 0.49],
                ['t_uov', 1, 'output', 'N', 'M5', 1, 0.51], ['t_uod', FLIT + 1, 'output', 'N', 'M5', 4, 0.74],
                ['f_uor', 1, 'input', 'N', 'M5', 1, 0.98],
                ['t_cov', 4, 'output', 'N', 'M5', 2, 0.445], ['f_cor', 4, 'input', 'N', 'M5', 2, 0.465],
                ['f_civ', 4, 'input', 'N', 'M5', 2, 0.535], ['t_cir', 4, 'output', 'N', 'M5', 2, 0.555],
                ['t_lov', 1, 'output', 'S', 'M5', 1, 0.07], ['t_lod', FLIT + 1, 'output', 'S', 'M5', 4, 0.27],
                ['f_lor', 1, 'input', 'S', 'M5', 1, 0.48],
                ['f_liv', 1, 'input', 'S', 'M5', 1, 0.52], ['f_lid', FLIT + 1, 'input', 'S', 'M5', 4, 0.73],
                ['t_lir', 1, 'output', 'S', 'M5', 1, 0.94],
                ['ck', 1, 'input', 'S', 'M5', 1, 0.015], ['rst', 1, 'input', 'S', 'M5', 1, 0.03],
                ['t_ft', 1, 'output', 'S', 'M5', 1, 0.985]]),
]


def child_ports(spec):
    """the 4 child links as 2 faces x 2 links: t_cod / f_cid are N*(FLIT+1) buses, bit-sliced per child"""
    W, H = spec['w_um'], spec['h_um']
    out = {}
    n_tr = int((H - 2 * TP.OFF) / TP.P)
    for name, d, half in (('t_cod', 'output', 0), ('f_cid', 'input', 1)):
        pins = []
        for c in range(4):
            face = 'W' if c < 2 else 'E'
            # per face: [child a out, child a in, child b out, child b in], each FLIT+1 bits at pitch 4
            slot = (c % 2) * 2 + half
            t0 = 8 + slot * ((FLIT + 1) * 4 + 6)
            assert t0 + (FLIT + 1) * 4 < n_tr - 40, (name, c)
            for i in range(FLIT + 1):
                t = t0 + i * 4
                pins.append([f'{name}[{c * (FLIT + 1) + i}]', 'M4'] +
                            [TP.r4(v) for v in TP.pin_rect(face, TP.OFF + t * TP.P, W, H)])
        out[name] = dict(bits=4 * (FLIT + 1), layer='M4', pins=pins, direction=d, face='W+E')
    return out


def main():
    summ = {}
    for spec in SPECS:
        ports = TP.plan(spec)
        if spec['master'] == 'dsfd_drf_fan':
            ports.update(child_ports(spec))
            spec = dict(spec, ports=spec['ports'] + [['t_cod/f_cid', 'see child_ports()']])
        rec = TP.write(spec['master'], spec['w_um'], spec['h_um'], spec['domain'], ports, spec)
        rec['generator'] = dict(file='tools/s81_ph/s81_ph_mtp_plan.py')
        d = ROOT / 'physical/s81_ph_views/ports/contract' / spec['master']
        (d / 'ports.json').write_text(json.dumps(rec, indent=0) + '\n')
        (d / 'io_place.tcl').write_text((d / 'io_place.tcl').read_text().replace('tools/s81_ph/s81_ph_tiles_plan.py',
                                                                                 'tools/s81_ph/s81_ph_mtp_plan.py'))
        npins = sum(len(p['pins']) for p in ports.values())
        summ[spec['master']] = dict(w=spec['w_um'], h=spec['h_um'], pins=npins,
                                    mm2=round(spec['w_um'] * spec['h_um'] / 1e6, 5))
    print(json.dumps(summ, indent=1))


if __name__ == '__main__':
    main()
