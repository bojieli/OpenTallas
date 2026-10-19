#!/usr/bin/env python3
"""HBM-LANDING 10-18: ref_tile specs (tools/ref_tile/specs_hland/<kit>.json) of the HBM d4g forwarded-clock half-cycle lane
masters (rtl/hbm_accel/die_glue/hbfd_lane_masters.sv; gen_hbm_lane_masters.py), modelled on the Qwen qfwd_* kits
(tools/qwen_split/gen_fwd_lane_kits.py) and s81dv_rlyh_276_ew:
  * clocks: physical/qwen_fwd_lane/fwd_lane_clocks.tcl (port names match: ck/ckf/ck_s, ck_o, a/ea/en);
  * recipe 4 flop-first, hold_budget die, M5 cap, pin flops opted out (one flop per bit / ring + registered output);
  * faces from the flow direction <in><out> (EW: in E, out W); en / rs / k straps / fault on the first free face
    (provisional: the die GEN assigns the pins of new tiles top-down and the die adopts the view pins);
  * benches: lint + tools/hbm_die_v16/hbm_lane_bench.sh pass at the master width + the family's mutants, each with its
    committed fail witness results/rtl/hbm_lane_1018/w_<mode><W>.log.
    gen_hbm_lane_kits.py MASTER [MASTER ...] [--branch B --tag T]   then: ref_tile.py gen tools/ref_tile/specs_hland/<kit>.json
"""
import argparse, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ['rtl/hbm_accel/die_glue/hbfd_lane_masters.sv', 'rtl/hbm_accel/die_glue/ot_hbm_lane.sv', 'rtl/qwen_split/qfd_fwd_lane.sv',
       'rtl/hdc/ot_hdc_cg.sv']
CLK_TCL = 'physical/qwen_fwd_lane/fwd_lane_clocks.tcl'
STRAP_TCL = 'physical/hbm_lane/land_straps.tcl'
WIT = 'results/rtl/hbm_lane_1018'
FACES = {'EW': ('E', 'W'), 'WE': ('W', 'E'), 'SN': ('S', 'N'), 'NS': ('N', 'S')}


def parse(m):
    x = re.match(r'hbfd_(lh0|lh|land0|land)_(\d+)_([NSEW]{2})(?:_f(\d))?$', m)
    if not x:
        raise SystemExit(f'not an hbfd lane master: {m}')
    return x.group(1), int(x.group(2)), x.group(3), int(x.group(4) or 1)


def spec(m, a):
    fam, W, d, n = parse(m)
    fi, fo = FACES[d]
    side = 'N' if d in ('EW', 'WE') else 'E'
    vert = d in ('EW', 'WE')               # data pins on vertical faces (E/W): face length = h
    if fam in ('lh0', 'lh'):
        ins = ['ck', 'en', 'a'] if fam == 'lh0' else ['ckf', 'ea', 'a']
        pins = {fi: ins, fo: ['b', 'eb', 'ck_o']}
        face_bits = max(W + 2, n * (W + 2))
        thick = 21.6
    else:
        ins = ['ckf', 'ea', 'a'] if fam == 'land' else ['ck_s', 'en', 'a']
        pins = {fi: ins, fo: ['b'], side: ['ck', 'rs', 'k0', 'k1', 'k2', 'fault']}
        face_bits = W + 2
        thick = 43.2 if W <= 136 else 86.4
    # data face: <= ~5.2 pins/um, on the 2.16 lattice, at least the 136-b fc relay's 32.4 um
    L = max(32.4, 2.16 * -(-face_bits / 5.2 // 2.16))
    w, h = (thick, L) if vert else (L, thick)
    ck = {'lh0': 'ck', 'lh': 'ckf', 'land': 'ck', 'land0': 'ck'}[fam]
    mut = {'lh0': ('full', 'hop0inv'), 'lh': ('full',) + (('forkck',) if n > 1 else ()), 'land': ('sel', 'naive', 'vld'),
           'land0': ('sel', 'naive')}[fam]
    name = m.lower()
    benches = [dict(name='lint', cmd=(f"mkdir -p {{RUN}} && printf '%s\\n' 'module ot_lint_top; {m} u_top (); endmodule' > "
                                      f"{{RUN}}/ot_lint_top.sv && verilator --lint-only -Wno-fatal -Wno-lint -Wno-style "
                                      f"-Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-MODMISSING -DSYNTHESIS --top-module ot_lint_top "
                                      f"{{RUN}}/ot_lint_top.sv {' '.join(SRC)} && echo lint-ok"),
                    expect='pass', threads=1, peak_ram_gb=4, needs=['verilator']),
               dict(name='hbm_lane_exact', cmd=f'bash tools/hbm_die_v16/hbm_lane_bench.sh pass {{RUN}}/bench_p {W}',
                    expect='pass', pass_regex='LANE_BENCH PASS 0 errors in [0-9]+ checks', threads=2, peak_ram_gb=6,
                    needs=['verilator'])]
    for mu in mut:
        benches.append(dict(name=f'{mu}_mutant', cmd=f'bash tools/hbm_die_v16/hbm_lane_bench.sh {mu} {{RUN}}/bench_{mu} {W}',
                            expect='fail', fail_regex='LANE_BENCH FAIL', fail_witness=f'{WIT}/w_{mu}{W}.log',
                            threads=2, peak_ram_gb=6, needs=['verilator']))
    kind = {'lh0': 'hop-0 station (non-inverting ICG on the source root, half-cycle forward)', 'lh': 'half-cycle station',
            'land': 'landing (4-slot ring, read on the sink regional root)', 'land0': 'landing with the hop-0 gate (0-station lane)'}[fam]
    if n > 1:
        kind = f'{n}-branch fork {kind}'
    return dict(
        name=name, top=m, kind='tile', sources=SRC, params={}, clock_port=ck,
        reset_ports=['rs'] if fam.startswith('land') else [],
        outline=dict(w=round(w, 3), h=round(h, 3), exact=True), layer_cap='M5', pins=pins, macros=[], children=[],
        # landing: the die-context IO reference = its block-root registers (the registered output o on ck); the PINFLOP
        # default picked the ring write pointer on the lane clock (gate 10-18: reference arrival 693 ps -> rs recovery -196)
        inter=['*'], refglob='u_land.o*' if fam.startswith('land') else '*', io_budget={'in': 0.2, 'out': 0.2},
        recipe=4, hold_budget='die', inhold=False, outhold=False, io_flop_at_pins={'cols': 4, 'allow_none': True},
        keep_pin_regs=True, forwarded_clock=not fam.startswith('land'),
        pin_regs=dict(enable=False, reason='OWNER RULE 19:50 opt-out (as the coordinator-approved S81 relays and Qwen qfwd frames): '
                      'a lane station is one flip-flop per bit between its pins, a landing is the ring + its registered output; '
                      'a flow pin register would add a stage the die calendar does not price'),
        sdc_extra=[CLK_TCL] + ([STRAP_TCL] if fam.startswith('land') else []),
        boundary_tcl=[CLK_TCL] + ([STRAP_TCL] if fam.startswith('land') else []),
        route=dict(pd=0.45, threads=2, peak_ram_gb=6, pin_h='M4', pin_v='M3 M5', m5_pg_pitch=2.7, hold_margin_ns=0.03,
                   io_hold_margin_ns=0.0, macro_halo_um=5.4),
        structural_change=(f'HBM-LANDING 10-18 (CLOCK-AUDIT HBM row, LANDING-CONTRACT 2-3, 7): {W}-b HBM d4g forwarded-clock lane '
                           f'master {m}: {kind} (Qwen cores rtl/qwen_split/qfd_fwd_lane.sv + rtl/hbm_accel/die_glue/ot_hbm_lane.sv); '
                           f'replaces the full-cycle hbfd_rly_{W}_{d}_fc{"_f%d" % n if n > 1 else ""} BUFx12f forward '
                           f'{"(sink-root re-time stage)" if fam.startswith("land") else ""}. Recipe 4 flop-first, hold_budget die, M5 cap.'),
        job=dict(owner='Claude:HBM-LANDING', branch=a.branch, tag=a.tag,
                 purpose=f'HBM d4g forwarded half-cycle lane master {m} ({kind}, {W} b)',
                 benches=benches, views_to=f'physical/ref_tile/{name}/views', record_to=f'results/rtl/ref_tile/{name}',
                 extra_paths=['physical/qwen_fwd_lane', 'physical/hbm_lane', 'rtl/qwen_split/qfd_fwd_lane.sv', 'rtl/hdc', 'rtl/hbm_accel/die_glue',
                              'tools/hbm_die_v16/hbm_lane_bench.sh', WIT]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('masters', nargs='+')
    ap.add_argument('--branch', default='claude/hland-rtl-1018')
    ap.add_argument('--tag', default='l1')
    ap.add_argument('--out', type=Path, default=ROOT / 'tools/ref_tile/specs_hland')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    for m in a.masters:
        s = spec(m, a)
        (a.out / f"{s['name']}.json").write_text(json.dumps(s, indent=1) + '\n')
        print(s['name'], s['outline'], s['pins'])


if __name__ == '__main__':
    main()
