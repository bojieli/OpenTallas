#!/usr/bin/env python3
"""OWNERS-HBM/VM-GLUE 2026-10-18, physical rework HBM-KITS-C/VMGLUE 10-18 (g2): tile specs of the three VM hub-glue
masters (hfd_hgi_vms_glue_{sw,e,nw}_t, gen_vms_glue_tiles.py) -> tools/ref_tile/specs_hbm_vm_glue/<kit>.json.
g1 (6ec5eae69, 777.6 x 1555.2) failed its --cts gates structurally: rst_n 19k flop loads, xq_done / flt / status
registers between pins > 1,100 um apart, one TritonCTS root at 421 ps spread, ring lane k of the ring face up to ~1.8 mm
from bank k's face.  g2:
  outline     648 x 1555.2 um (lattice 43.2: 15 x 36).  The ring face is pin-bound (8,898 b <= 6 / um needs 1,483 um);
              the width is the minimum that keeps the N / S faces (2 banks + cq / cr + control) <= 5.5 / um.
  ring face   LANE BANDS: per lane k the four ring buses' lane bits <cw_in|cw_out|ccw_out|ccw_in>_l<k> side by side
              (transit in -> out and egress / eject stay inside one ~192 um band), bands ordered along the face as the
              banks sit around the tile; the 16-b headers + clk + rst_n in the middle (the header controls every band).
                plan A (SW, E = SE R0 / NE MX): bottom -> top lanes 6 7 0 1 | hdr clk rst | 2 3 4 5
                plan B (NW = the y-mirror of SW, so NW faces NE (= MX of SE) lane for lane):  5 4 3 2 | hdr | 1 0 7 6
              SW / NW: ring on the E face; E master: ring on the W face (SE R0 and NE MX both face the central channel).
  far face    banks 0..3 (A bottom -> top 0 1 2 3, B 3 2 1 0), 1,399 b each.
  N / S       A: N banks 4, 5 (+ cq), S banks 6, 7 (+ cr + control / strap / status);  B: S banks 4, 5, N banks 6, 7 +
              control.  The bank whose lane band is farther from that face sits at the ring-face end.
  clock       measured balanced clock spine (physical/common_flow/clock_spine.tcl, leaf <= 16 sinks), clock entry in
              the middle of the ring face beside the ring-stop register mass.  Rule: pin-flop spread <= 80 ps TT and FF.
  reset       rst_n drives only ot_rst_relay; 7 regional copies (g3: + hub bank face groups E / N / S).
  g3          (HH-3 10-19) ring_tx_enable / ring_tx_source move to the middle of the ring face beside the headers: they
              feed the per-lane-band control copies of both ring stops.
  boundary    every port lands on / leaves from a flop (bank-side ports through the tile's own landing / relay stage).
  g4          (HBM-SAFE-VMGLUE 10-19, SAFE-DESIGN checklist) same outline / pin plan; RTL reach stages (gen_vms_glue_tiles.py
              DB / DD / DC) so no single-cycle wire > ~405 um, registered one-hot schedule selects, 11 reset regions
              (+ lower / upper lane-band halves of each ring stop); reset_landing on (tools from main).
    vms_glue_kit_specs.py [--check]
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
RTL = 'rtl/hbm_accel/generic/vm/static/'
# synthesis needs the first four; the rest are read by the lockstep bench (contract reference) -- listed so the bench
# sources are part of the kit's source binding
SRC = [RTL + 'hfd_hgi_vms_glue_tiles.sv', RTL + 'hfd_hgi_vms_glue_lt.sv', RTL + 'ot_vms_status_static.sv', 'rtl/lib/ot_rst_relay.sv',
       RTL + 'hfd_hgi_vms_glue_tiles_ref.sv', RTL + 'hfd_hgi_vms_static_glue.sv', RTL + 'ot_vms_hub_static.sv',
       RTL + 'ot_vms_rstop_static.sv', RTL + 'ot_vms_rcl_static.sv']
OUTDIR = ROOT / 'tools/ref_tile/specs_hbm_vm_glue'
W, H = 648.0, 1555.2
MARGIN = 4.32
BANKP = ('xq', 'xq2', 'eg', 'pq', 'pr', 'status', 'xq_done', 'xq2_done', 'flt')
RING = ('cw_in', 'cw_out', 'ccw_out', 'ccw_in')
M = dict(
    sw=dict(top='hfd_hgi_vms_glue_sw_t', ring='E', far='W', plan='A', q='SW', inst='hb_vms_SW',
            bench=[('SW', 'pos'), ('SW', 'rmut'), ('SW', 'land'), ('SW', 'g3'), ('SW', 'g4')]),
    e=dict(top='hfd_hgi_vms_glue_e_t', ring='W', far='E', plan='A', q='SE (R0, sid 1) / NE (MX, sid 3)', inst='hb_vms_SE, hb_vms_NE',
           bench=[('SE', 'pos'), ('NE', 'pos'), ('SE', 'rmut'), ('SE', 'land'), ('SE', 'sid'), ('NE', 'sid'), ('SE', 'g3'), ('SE', 'g4')]),
    nw=dict(top='hfd_hgi_vms_glue_nw_t', ring='E', far='W', plan='B', q='NW', inst='hb_vms_NW',
            bench=[('NW', 'pos'), ('NW', 'rmut'), ('NW', 'land'), ('NW', 'g3'), ('NW', 'g4')]))
FACE = dict(E='right', W='left', N='top', S='bottom')
TAG = 'VMS_GLUE_LT_EQUIV'
WIT = 'results/rtl/vm_glue_1018/bench_g4/'


def ports(top):
    t = (ROOT / SRC[0]).read_text()
    body = re.search(rf'module {top} #\(parameter integer MUT=0\) \((.*?)\);', t, re.S).group(1)
    out = []
    for l in body.split('\n'):
        m = re.match(r'\s*(input|output) wire (\[(\d+):0\] )?(\w+)', l)
        if m:
            out.append((m.group(4), int(m.group(3)) + 1 if m.group(3) else 1))
    return out


def lay(face_len, items):
    """items: [(port, bits)] laid out in order from the face's left / bottom end; span proportional to bits"""
    tot = sum(b for _, b in items)
    usable = face_len - 2 * MARGIN
    rng, x = {}, MARGIN
    for p, b in items:
        span = usable * b / tot
        rng[p] = [round(x, 3), round(x + span, 3)]; x += span
    return rng, tot / usable


def spec(k, c):
    P = dict(ports(c['top']))
    bank = lambda b: [(f'b{b}_{n}', P[f'b{b}_{n}']) for n in BANKP if f'b{b}_{n}' in P]
    lane = lambda b: [(f'{n}_l{b}', P[f'{n}_l{b}']) for n in RING]
    # g3: the ring tx controls sit with the headers in the middle of the ring face (they feed the per-band copies)
    hdr = [('cw_in_h', 16), ('cw_out_h', 16), ('ring_tx_enable', 2), ('ring_tx_source', 6), ('clk', 1), ('rst_n', 1),
           ('ccw_out_h', 16), ('ccw_in_h', 16)]
    A = c['plan'] == 'A'
    ring = [x for b in (6, 7, 0, 1) for x in lane(b)] + hdr + [x for b in (2, 3, 4, 5) for x in lane(b)]
    if not A:
        ring = ring[::-1]
    far = [x for b in ((0, 1, 2, 3) if A else (3, 2, 1, 0)) for x in bank(b)]
    used = {p for p, _ in ring + far}
    for b in range(8):
        used |= {p for p, _ in bank(b)}
    ctl = [(p, b) for p, b in P.items() if p not in used and p not in ('cq', 'cr')]
    cq = [('cq', P['cq'])] if 'cq' in P else []
    cr = [('cr', P['cr'])] if 'cr' in P else []
    ring_right = c['ring'] == 'E'          # N / S faces run left -> right; the ring-face end is the right end for SW / NW
    def toward_ring(far_end, ring_end):    # [far-end items..., ring-end items...] in left -> right order
        return far_end + ring_end if ring_right else ring_end[::-1] + far_end[::-1]
    if A:   # N: banks 4 (band farther from N -> ring end), 5 + cq ; S: banks 7 (ring end), 6 + cr + control
        north = toward_ring(cq + bank(5), bank(4))
        south = toward_ring(cr + ctl + bank(6), bank(7))
    else:   # B (y-mirror of A): S: banks 4 (ring end), 5 ; N: banks 7 (ring end), 6 + control
        south = toward_ring(bank(5), bank(4))
        north = toward_ring(ctl + bank(6), bank(7))
    faces, ranges, dens = {}, {}, {}
    for f, items, flen in ((c['ring'], ring, H), (c['far'], far, H), ('N', north, W), ('S', south, W)):
        r, d = lay(flen, items); ranges.update(r); dens[f] = round(d, 2); faces[f] = [p for p, _ in items]
    allp = [p for f in faces.values() for p in f]
    assert sorted(allp) == sorted(P), set(P) ^ set(allp)
    assert max(dens.values()) <= 6.0, dens
    benches = []
    for q, m in c['bench']:
        cmd = f'bash tools/hbm_die_v16/run_vms_glue_tile_equiv.sh {q} {m} {{RUN}}/bench'
        b = dict(name=f'{q.lower()}_{m}' if m == 'pos' else f'mut_{m}_{q.lower()}', cmd=cmd, expect='pass' if m == 'pos' else 'fail',
                 threads=8, peak_ram_gb=8, needs=['verilator'])
        if m == 'pos':
            b.update(pass_regex=f'^{TAG} {q} PASS checks=[1-9][0-9]* errors=0$', min_count_regex=f'{TAG} {q} PASS checks=(\\d+)',
                     pass_witness=WIT + f'{q}pos.sim.log')
        else:
            b.update(fail_regex=f'^{TAG} {q} FAIL checks=[0-9]+ errors=[1-9][0-9]*$', fail_witness=WIT + f'{q}{m}.sim.log')
        benches.append(b)
    purpose = (f"OWNERS-HBM/VM-GLUE + HBM-KITS-C/VMGLUE 2026-10-18 g2 + HOURLY-HBM/HH-3 g3 + HBM-SAFE-VMGLUE g4 10-19 (HBM d4g plan (b), glue "
               f"goes into a hardened tile): VM hub glue tile for {c['q']} ({c['inst']}) = hfd_vms_glue_core_lt "
               f"(ot_vms_hub_lt + 2 ot_vms_rstop_lt + ot_vms_rcl_lt + ot_vms_status_static), the 8 banks are die-level "
               f"instances. g3 = the g2 setup fix: ring stop bit-sliced per lane band (per-band tx control / header "
               f"decode copies, rce lane-OR tree), hub request scatter and response gather registered per bank face "
               f"group, replay select replicated, 7 reset regions. Tile top {c['top']} (gen_vms_glue_tiles.py): one "
               f"clock, per-bank and per-lane ring ports, one landing / relay stage on every bank-side port "
               f"(COMMIT_DELAY 8){', sid strap pin (one master for SE and NE)' if k == 'e' else ''}. Contract vs the "
               f"historical glue: bank-side ports +1 each way; g3 stop inputs +1, rce +2, hub pq +1, pr / response "
               f"enables +1; reset release +3 (lockstep bench vs <tile>_ref). g4 (SAFE-DESIGN checklist): reach stages "
               f"(no single-cycle wire > ~405 um): bank-side ports pin flop + 2 relays (xq_done + 3, COMMIT_DELAY 13), hub "
               f"client ports pin flop + 2 relays, hub <-> ring-stop relays (pi / ri / cco / rce / faults +1), stop inputs +2 "
               f"with per-half relay copies, 3-level rce tree; registered one-hot schedule selects (bank / tx / replay); 11 "
               f"reset regions; reset_landing on.")
    return {
        'name': f'hfd_hgi_vms_glue_{k}', 'top': c['top'], 'kind': 'tile', 'sources': SRC,
        'clock_port': 'clk', 'reset_ports': ['rst_n'], 'reset_landing': {'enable': True, 'stages': 2}, 'pins': faces, 'layer_cap': 'M5', 'recipe': 2,
        'clock': 'spine', 'orfs_vars': {'OT_SPINE_LEAF_N': '16'},
        'route': {'pd': 0.5, 'period_ps': 833.333, 'threads': 16, 'peak_ram_gb': 64, 'hold_margin_ns': 0.03,
                  'io_hold_margin_ns': 0.03, 'pin_balance': {'group_max': 1}},
        'outline': {'w': W, 'h': H}, 'pin_ranges': ranges, 'params': {}, 'children': [], 'inter': [],
        'pin_regs': {'enable': False, 'reason': 'RTL registers every pin (g4: each port is a pin flop + reach relays, '
                     'gen_vms_glue_tiles.py DB / DD / DC): bank-side inputs land on the tile landing flops '
                     '(eg / pr / xq_done / xq2_done / status / flt) and bank-side outputs leave from the tile relay flops (xq / '
                     'xq2 / pq); the hub captures cq / client_seq / bank_client / response_seq / enables on plain flops and '
                     'drives cr from flops; both ring stops capture l_in / tx controls and drive l_out / mirror_busy / fault '
                     'from flops; status drives vmstat from a flop; sid lands on flops. A synthesis pin stage would add an '
                     'edge the contract (gen_vms_glue_tiles.py) does not have.'},
        'io_flop_at_pins': {'cols': 4, 'allow_none': True}, 'inhold': True, 'outhold': True, 'keep_pin_regs': True,
        'pin_reg_split': True, 'hold_pad': {'cell': 'HB2xp67_ASAP7_75t_R'},
        'purpose': purpose,
        'pin_density_per_um': dens,
        'job': {'owner': 'Claude HBM-SAFE-VMGLUE 1019', 'branch': 'claude/vm-glue-g4-1019', 'tag': 'g4', 'purpose': purpose,
                'extra_paths': ['rtl/hbm_accel/generic/vm', 'rtl/lib', 'tools/hbm_die_v16'],
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
