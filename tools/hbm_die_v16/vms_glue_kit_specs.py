#!/usr/bin/env python3
"""OWNERS-HBM/VM-GLUE 2026-10-18: tile specs of the three VM hub-glue masters (hfd_hgi_vms_glue_{sw,e,nw}_t,
gen_vms_glue_tiles.py) -> tools/ref_tile/specs_hbm_vm_glue/<kit>.json.
Pin plan (ports from the tile headers; <= 6 pins/um on every face; flop-first/last RTL, so no synthesis pin registers):
  ring face   cw_out+ccw_in (to/from the NEXT hub) | clk rst_n | cw_in+ccw_out (from/to the PREVIOUS hub), 8,896 b.
              SW / NW at R0: E face (toward the central channel); E master at R0 = SE: W face; NE = MX of SE (the
              ring stays on the W face, so ONE pin plan serves both E hubs; only the order along the face mirrors).
  far face    banks 0..3 (b<k>_* = 1,399 b each, grouped per bank) = 5,596 b.
  N face      banks 4, 5 + cq (local clients) ;  S face  banks 6, 7 + cr + control / strap / status.
Outline 777.6 x 1555.2 um (lattice 43.2: 18 x 36): the ring face needs >= 8,896 / 6 = 1,483 um; the width carries
2 banks + clients per N / S face at <= 4.5 /um.  The tile is pin-bound (synth area ~2-3 % of the core).
    vms_glue_kit_specs.py [--check]
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
RTL = 'rtl/hbm_accel/generic/vm/static/'
SRC = [RTL + x for x in ('hfd_hgi_vms_glue_tiles.sv', 'hfd_hgi_vms_static_glue.sv', 'ot_vms_hub_static.sv',
                          'ot_vms_rstop_static.sv', 'ot_vms_rcl_static.sv', 'ot_vms_status_static.sv')]
OUTDIR = ROOT / 'tools/ref_tile/specs_hbm_vm_glue'
W, H = 777.6, 1555.2
MARGIN = 4.32
BANKP = ('xq', 'xq2', 'eg', 'pq', 'pr', 'status', 'xq_done', 'xq2_done', 'flt')
M = dict(
    sw=dict(top='hfd_hgi_vms_glue_sw_t', ring='E', far='W', q='SW', inst='hb_vms_SW', bench=[('SW', 'pos'), ('SW', 'bank')]),
    e=dict(top='hfd_hgi_vms_glue_e_t', ring='W', far='E', q='SE (R0, sid 1) / NE (MX, sid 3)', inst='hb_vms_SE, hb_vms_NE',
           bench=[('SE', 'pos'), ('NE', 'pos'), ('SE', 'bank'), ('SE', 'sid'), ('NE', 'sid')]),
    nw=dict(top='hfd_hgi_vms_glue_nw_t', ring='E', far='W', q='NW', inst='hb_vms_NW', bench=[('NW', 'pos'), ('NW', 'bank')]))
TAG = lambda q: 'VMS_HOIST_EQUIV' if q in ('SW', 'NW') else 'VMS_QB_EQUIV'
WIT = 'results/rtl/vm_glue_1018/bench/'


def ports(top):
    t = (ROOT / SRC[0]).read_text()
    body = re.search(rf'module {top} \((.*?)\);', t, re.S).group(1)
    out = []
    for l in body.split('\n'):
        m = re.match(r'\s*(input|output) wire (\[(\d+):0\] )?(\w+)', l)
        if m:
            out.append((m.group(4), int(m.group(3)) + 1 if m.group(3) else 1))
    return out


def lay(face_len, groups):
    """groups: [[(port, bits), ...], gap_um?] laid out in order over the face; span proportional to bits."""
    tot = sum(b for g in groups for _, b in g)
    usable = face_len - 2 * MARGIN
    rng, x = {}, MARGIN
    for g in groups:
        for p, b in g:
            span = usable * b / tot
            rng[p] = [round(x, 3), round(x + span, 3)]; x += span
    return rng, tot / usable


def spec(k, c):
    P = dict(ports(c['top']))
    bank = lambda b: [(f'b{b}_{n}', P[f'b{b}_{n}']) for n in BANKP if f'b{b}_{n}' in P]
    used = set()
    faces, ranges, dens = {}, {}, {}
    def put(face, flen, groups):
        r, d = lay(flen, groups); ranges.update(r); dens[face] = round(d, 2)
        faces[face] = [p for g in groups for p, _ in g]; used.update(faces[face])
    ring = [[('cw_out', 2224), ('ccw_in', 2224)], [('clk', 1), ('rst_n', 1)], [('cw_in', 2224), ('ccw_out', 2224)]]
    put(c['ring'], H, ring)
    put(c['far'], H, [bank(b) for b in range(4)])
    put('N', W, [bank(4), bank(5)] + ([[('cq', P['cq'])]] if 'cq' in P else []))
    rest = [(p, b) for p, b in P.items() if p not in used and not re.match(r'b\d_', p)]
    put('S', W, [bank(6), bank(7), rest])
    assert set(P) == used, set(P) - used
    assert max(dens.values()) <= 6.0, dens
    benches = []
    for q, m in c['bench']:
        cmd = f'bash tools/hbm_die_v16/run_vms_glue_tile_equiv.sh {q} {m} {{RUN}}/bench'
        b = dict(name=f'{q.lower()}_{m}' if m == 'pos' else f'mut_{m}_{q.lower()}', cmd=cmd, expect='pass' if m == 'pos' else 'fail',
                 threads=8, peak_ram_gb=16, needs=['verilator'])
        if m == 'pos':
            b.update(pass_regex=f'^{TAG(q)} {q} PASS checks=[1-9][0-9]* errors=0$', min_count_regex=f'{TAG(q)} {q} PASS checks=(\\d+)',
                     pass_witness=WIT + f'{q}pos.sim.log')
        else:
            b.update(fail_regex=f'^{TAG(q)} {q} FAIL checks=[0-9]+ errors=[1-9][0-9]*$', fail_witness=WIT + f'{q}{m}.sim.log')
        benches.append(b)
    purpose = (f"OWNERS-HBM/VM-GLUE 2026-10-18 (HBM d4g plan (b), top-down contract: glue goes into a hardened tile): VM hub glue "
               f"tile for {c['q']} ({c['inst']}) = ot_vms_hub_static + 2 ot_vms_rstop_static + ot_vms_rcl_static + "
               f"ot_vms_status_static, the 8 banks hoisted to die-level instances (gen_vms_hoist.py / HBM-B-RTL1 qb glue, logic "
               f"unchanged). Tile top {c['top']} (gen_vms_glue_tiles.py): one clock (clk_hub/clk_ring/clk_replay are one stream "
               f"clock), per-bank bank ports{', sid strap pin (one master for SE and NE)' if k == 'e' else ''}. Every port lands on / "
               f"leaves from a flop except bank_status (status OR / CE adder rungs, as the slice) and the xq_done fault compare.")
    return {
        'name': f'hfd_hgi_vms_glue_{k}', 'top': c['top'], 'kind': 'tile', 'sources': SRC,
        'clock_port': 'clk', 'reset_ports': ['rst_n'], 'pins': faces, 'layer_cap': 'M5', 'recipe': 2,
        'route': {'pd': 0.5, 'period_ps': 833.333, 'threads': 16, 'peak_ram_gb': 64, 'hold_margin_ns': 0.03,
                  'pin_balance': {'group_max': 1}},
        'outline': {'w': W, 'h': H}, 'pin_ranges': ranges, 'params': {}, 'children': [], 'inter': [],
        'pin_regs': {'enable': False, 'reason': 'RTL registers the pins: the hub captures cq/client_seq/bank_client/'
                     'response_seq/pr/enables on plain flops and drives cr/pq from flops; both ring stops capture l_in/pi/eg/ri/'
                     'tx controls and drive l_out/xq/rce/cco/ack/wko/mirror_busy/fault from flops; the replay client likewise; '
                     'sid lands on flops. Exceptions (the slice RTL, priced as is): bank_status feeds the status OR / CE adder '
                     'rung before its first flop, xq_done feeds the commit fault compare. Synthesis pin registers would add an '
                     'unpriced cycle and break the lockstep with the full slice.'},
        'io_flop_at_pins': {'cols': 4, 'allow_none': True}, 'inhold': True, 'outhold': True, 'keep_pin_regs': True,
        'pin_reg_split': True, 'hold_pad': {'cell': 'HB2xp67_ASAP7_75t_R'},
        'purpose': purpose,
        'pin_density_per_um': dens,
        'job': {'owner': 'Claude OWNERS-HBM/VM-GLUE 1018', 'branch': 'claude/vm-glue-1018', 'tag': 'g1', 'purpose': purpose,
                'extra_paths': ['rtl/hbm_accel/generic/vm', 'rtl/lib', 'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2',
                                'tools/hbm_die_v16', 'tools/hbm_die_v15/v16_layers'],
                'record_to': f'results/rtl/ref_tile/hfd_hgi_vms_glue_{k}', 'benches': benches,
                'views_to': f'physical/ref_tile/hfd_hgi_vms_glue_{k}/views'},
    }


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True); ok = True
    for k, c in M.items():
        s = json.dumps(spec(k, c), indent=1) + '\n'; f = OUTDIR / f'hfd_hgi_vms_glue_{k}.json'
        if '--check' in sys.argv:
            ok &= f.exists() and f.read_text() == s
        else:
            f.write_text(s); print('WROTE', f.relative_to(ROOT), json.loads(s)['pin_density_per_um'])
    if '--check' in sys.argv:
        print('VMS_GLUE_KIT_SPECS', 'CHECK_PASS' if ok else 'CHECK_FAIL'); sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
