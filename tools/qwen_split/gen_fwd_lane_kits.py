#!/usr/bin/env python3
"""Q-DIE11-RLY 10-18: ref_tile specs of the Qwen compute die's forwarded half-cycle lane frames (OT_SPLIT_FWD_LANES=1):
qfd_rlyh0_* (hop-0 station), qfd_rlyh_* (station), qfd_landh_* / qfd_landh0_* (landings), from a GEN's assigned pin
files (OUT/pins/<master>.json, tools/qwen_tp8/relay_data_run.py --case).

  * RTL: physical/qwen_fwd_lane/qfd_fwd_lane_masters.sv = the die wrappers of the selected masters exactly as
    tools/qwen_split/gen_relay_rtl.py writes them for the die port-bind (kept OUT of rtl/ so the die bind does not see
    two definitions), over rtl/qwen_split/qfd_fwd_lane.sv + rtl/hdc/ot_hdc_cg.sv.
  * frame: the die frame exactly (outline exact); data a / epoch ea on the in face, b / eb on the out face as the die
    LEF has them; the die's centre area pins (clocks, en / rs, k straps, ties, fault) go to the first face the data does
    not use (the die adopts the view's pins).
  * clocks: physical/qwen_fwd_lane/fwd_lane_clocks.tcl (ck_o generated clocks; the landing's lane write clock).
  * recipe 4 flop-first, hold_budget die, M5 cap (LANDING-CONTRACT section 3), pin flops opted out (one flop per bit).
  * benches: tools/qwen_split/bench_fwd_lane.sh at the master's width (all four families of the same generator) --
    pass + mutants (stations: full-cycle forward [+ the first-form inverting hop 0]; landings: read slot one late, no ring), each
    with its committed fail witness results/arch/qwen_split_compute_1014/q_die11_rly_1018/bench/w<W>_<mode>.log.

    gen_fwd_lane_kits.py --pins OUT/pins --masters M [M ...] [--owner O --branch B --tag T]
"""
import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_split'))
import gen_relay_rtl as GR  # noqa: E402

LANE_RTL = ['rtl/qwen_split/qfd_fwd_lane.sv', 'rtl/hdc/ot_hdc_cg.sv']
MASTERS_SV = 'physical/qwen_fwd_lane/qfd_fwd_lane_masters.sv'
CLK_TCL = 'physical/qwen_fwd_lane/fwd_lane_clocks.tcl'
WIT = 'results/arch/qwen_split_compute_1014/q_die11_rly_1018/bench_r2'   # Q-DIE11 10-18: witnesses of the rising-hop-0 RTL
# QK-LANDEN 10-19: witnesses of the registered-en landh0 RTL (+ calendar) for every family's bench at widths 1/128/548/600
WIT_LANDEN = 'results/arch/qwen_split_compute_1014/qk_landen_1019/bench'
# RLYH0-EN 10-19: witnesses of the registered-en rlyh0 RTL (every lane's write epoch G + 1) at widths 1/128/548/600
WIT_RLYH0EN = 'results/arch/qwen_split_compute_1014/rlyh0_en_1019/bench'
MUTANTS = {'qfd_rlyh0_': ('full', 'rlyencomb'),   # RLYH0-EN 10-19: rlyencomb = the hop-0 station's en unregistered
           'qfd_rlyh_': ('full',), 'qfd_landh_': ('sel', 'naive'),
           'qfd_landh0_': ('sel', 'naive', 'encomb'),   # QK-LANDEN 10-19: encomb = en unregistered (closed-view form)
           # Q-H16C 10-18: forwarded RESET lanes (bench_fwd_rst_lane.sh): stations full-cycle forward, landing double register
           'qfd_rlyr0_': ('full',), 'qfd_rlyr_': ('full',), 'qfd_rlyrl_': ('land2',)}
# Q-DIE11 10-18: no hop-0 inversion mutant: the first-form (falling-edge) hop 0 delivers the same word stream through the
# landing window (bench_r2 w*_hop0inv.log PASS: the ring absorbs the T/2), so it is not a bench-observable fault
CLOCK = {'qfd_rlyh0_': 'ck', 'qfd_rlyh_': 'ckf', 'qfd_landh_': 'ck', 'qfd_landh0_': 'ck', 'qfd_rlyr0_': 'ck', 'qfd_rlyr_': 'ckf',
         'qfd_rlyrl_': 'ck'}
RST = ('qfd_rlyr0_', 'qfd_rlyr_', 'qfd_rlyrl_')
RST_DEFAULT = {'qfd_rlyr0_': 'qfd_rlyr0_1_EW_65x30', 'qfd_rlyr_': 'qfd_rlyr_1_EW_65x30', 'qfd_rlyrl_': 'qfd_rlyrl_1_EW_65x30'}


def rst_masters(m):
    """bench_fwd_rst_lane.sh master triple: the kit's own master in its family slot, the default frames elsewhere"""
    fam = GR.fwd_family(m)
    return ' '.join(m if f == fam else RST_DEFAULT[f] for f in RST)


def kit_name(m):
    fam = GR.fwd_family(m)
    rest = m[len(fam):]                                     # <W>_<FiFo>_<w>x<h>
    return f"qfwd_{fam[4:-1]}_{rest.lower()}"


def wrappers(masters, widths, out):
    L = ['module qfd_die ();']
    for j, m in enumerate(masters):
        conns = []
        for p in GR.FWD[GR.fwd_family(m)]:
            w = widths[m] if p in ('a', 'b') else 1
            L.insert(1, f'  wire [{w - 1}:0] n{j}_{p};')
            conns.append(f'.{p}(n{j}_{p})')
        L.append(f'  {m} u{j} ({", ".join(conns)});')
    L.append('endmodule')
    tmp = out.with_suffix('.die.v')
    tmp.write_text('\n'.join(L) + '\n')
    GR.main(str(tmp), str(out))
    tmp.unlink()
    t = out.read_text().replace(f'from {tmp.name}', 'for the qfwd_* kits (tools/qwen_split/gen_fwd_lane_kits.py)')
    out.write_text(t)


def spec(m, pins, a):
    fam = GR.fwd_family(m)
    W = pins['ports']['a']['bits']
    faces = {f: list(v) for f, v in pins['pins'].items()}
    used = set(faces)
    free = next(f for f in ('E', 'W', 'N', 'S') if f not in used)
    inner = [p for p in GR.FWD[fam] if p not in sum(faces.values(), [])]
    faces.setdefault(free, []).extend(inner)
    name = kit_name(m)
    ck = CLOCK[fam]
    benches = [dict(name='lint', cmd=(f"mkdir -p {{RUN}} && printf '%s\\n' 'module ot_lint_top; {m} u_top (); endmodule' > "
                                      f"{{RUN}}/ot_lint_top.sv && verilator --lint-only -Wno-fatal -Wno-lint -Wno-style "
                                      f"-Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-MODMISSING -DSYNTHESIS --top-module ot_lint_top "
                                      f"{{RUN}}/ot_lint_top.sv {' '.join(LANE_RTL)} {MASTERS_SV} && echo lint-ok"),
                    expect='pass', threads=1, peak_ram_gb=4, needs=['verilator']),
               dict(name='fwd_lane_exact', cmd=f'bash tools/qwen_split/bench_fwd_lane.sh pass {{RUN}}/bench_p {W}',
                    expect='pass', pass_regex='FWD_BENCH PASS 0 errors in [0-9]+ checks', threads=2, peak_ram_gb=4,
                    needs=['verilator'])]
    if fam in RST:
        benches[1] = dict(name='fwd_rst_lane_exact', cmd=f'bash tools/qwen_split/bench_fwd_rst_lane.sh pass {{RUN}}/bench_p {rst_masters(m)}',
                          expect='pass', pass_regex='RST_BENCH PASS 0 errors in [0-9]+ checks',
                          pass_witness=f'{a.wit}/{name}_pass.log', threads=2, peak_ram_gb=4, needs=['verilator'])
    for mu in MUTANTS[fam]:
        if fam in RST:
            benches.append(dict(name=f'{mu}_mutant', cmd=f'bash tools/qwen_split/bench_fwd_rst_lane.sh {mu} {{RUN}}/bench_{mu} {rst_masters(m)}',
                                expect='fail', fail_regex='RST_BENCH FAIL', fail_witness=f'{a.wit}/{name}_{mu}.log',
                                threads=2, peak_ram_gb=4, needs=['verilator']))
            continue
        benches.append(dict(name=f'{mu}_mutant', cmd=f'bash tools/qwen_split/bench_fwd_lane.sh {mu} {{RUN}}/bench_{mu} {W}',
                            expect='fail', fail_regex='FWD_BENCH FAIL', fail_witness=f'{a.wit}/w{W}_{mu}.log',
                            threads=2, peak_ram_gb=4, needs=['verilator']))
    kind = {'qfd_rlyh0_': 'hop-0 station (ICG on the source root, rising capture, inverted ck_o)', 'qfd_rlyh_': 'half-cycle station',
            'qfd_landh_': 'landing (ring D 4, read on the block root)', 'qfd_landh0_': 'landing with the hop-0 gate',
            'qfd_rlyr0_': 'reset-lane hop 0 (one register on the source root, inverted ck_o)',
            'qfd_rlyr_': 'reset-lane half-cycle station (inverted ck_o)',
            'qfd_rlyrl_': 'reset-release landing (level re-registered on the receiving root)'}[fam]
    return dict(
        name=name, top=m, kind='tile', sources=LANE_RTL + [MASTERS_SV], params={}, clock_port=ck,
        reset_ports=['rs'] if fam.startswith('qfd_landh') else [],
        outline=dict(w=round(pins['outline']['w'], 3), h=round(pins['outline']['h'], 3), exact=True), layer_cap='M5',
        pins=faces, macros=[], children=[], inter=['*'],
        # Q-DIE11 10-18 kit fix: a landing's boundary reference is its READ-side (block root) counter, not the PINFLOP
        # default (the lane-clock ring flops: L_max 908-1243 ps -> rs input delay > T, TT -639 / -973)
        refglob='*u_land.rc*' if fam.startswith('qfd_landh') else '*', io_budget={'in': 0.2, 'out': 0.2},
        recipe=4, hold_budget='die', inhold=False, outhold=False, io_flop_at_pins={'cols': 4, 'allow_none': True},
        keep_pin_regs=True, forwarded_clock=not fam.startswith(('qfd_landh', 'qfd_rlyrl_')),
        pin_regs=dict(enable=False, reason='OWNER RULE 19:50 opt-out (as the coordinator-approved S81 relays): a lane frame is '
                      'one flip-flop per bit between its pins (station) or the ring + its registered output (landing); a '
                      'flow pin register would add a stage the die calendar does not price'),
        sdc_extra=[CLK_TCL], boundary_tcl=[CLK_TCL],
        route=dict(pd=0.45, threads=2, peak_ram_gb=6, pin_h='M4', pin_v='M3 M5', m5_pg_pitch=2.7, hold_margin_ns=0.03,
                   # QK-FWD 10-18 (KITS rule): boundary hold margin >= 0.025 (~22 ps lost between route repair and sign-off)
                   io_hold_margin_ns=0.03, macro_halo_um=5.4),
        assigned_pin_source=dict(file=f"{a.pins_ref}/{m}.json", note='die-assigned faces of the Qwen compute die GEN '
                                 '(OT_SPLIT_FWD_LANES=1); centre area pins moved to the free face; the die adopts the view pins',
                                 owner='Q-DIE11-RLY'),
        structural_change=(f'Q-DIE11-RLY 10-18 (coordinator HANDOFF 0ea item 1, LANDING-CONTRACT): {W}-b forwarded-clock lane '
                           f'frame {m}: {kind} (rtl/qwen_split/qfd_fwd_lane.sv); replaces the regional-root qfd_rly_{W} relay of '
                           'the same die frame and faces. Recipe 4 flop-first, hold_budget die, M5 cap.' + a.class_note),
        job=dict(owner=a.owner, branch=a.branch, tag=a.tag,
                 purpose=f'Qwen compute die forwarded half-cycle lane frame {m} ({kind}, {W} b)',
                 benches=benches, views_to=f'physical/ref_tile/{name}/views', record_to=f'results/rtl/ref_tile/{name}',
                 extra_paths=['physical/qwen_fwd_lane', 'rtl/qwen_split/qfd_fwd_lane.sv', 'rtl/hdc', 'tools/qwen_split', a.wit]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--pins', required=True, type=Path)
    ap.add_argument('--pins-ref', default='results/arch/qwen_split_compute_1014/q_die11_rly_1018/gen1/pins',
                    help='repo path the spec cites for the pin files (copied there)')
    ap.add_argument('--masters', nargs='+', required=True)
    ap.add_argument('--owner', default='Claude:Q-DIE11-RLY')
    ap.add_argument('--branch', default='claude/q-die11-rly-1018')
    ap.add_argument('--tag', default='f1')
    ap.add_argument('--wit', default=WIT, help='repo dir of the committed bench fail witnesses w<W>_<mutant>.log')
    ap.add_argument('--class-note', default='', help='appended to structural_change (QK-FWD class masters)')
    ap.add_argument('--out', type=Path, default=ROOT / 'tools/ref_tile/specs_qfwd')
    a = ap.parse_args()
    pins = {m: json.loads((a.pins / f'{m}.json').read_text()) for m in a.masters}
    bad = [m for m in a.masters if not GR.fwd_family(m)]
    if bad:
        raise SystemExit(f'not forwarded-lane masters: {bad}')
    widths = {m: pins[m]['ports']['a']['bits'] for m in a.masters}
    # the wrapper file holds every master the repo has a spec for (re-generated as the union)
    have = sorted({json.loads(p.read_text())['top'] for p in a.out.glob('qfwd_*.json')} | set(a.masters)) if a.out.exists() else sorted(a.masters)
    for m in have:
        if m not in widths:
            widths[m] = int(re.match(r'qfd_\w+?_(\d+)_', m).group(1))
    (ROOT / MASTERS_SV).parent.mkdir(parents=True, exist_ok=True)
    wrappers(have, widths, ROOT / MASTERS_SV)
    a.out.mkdir(parents=True, exist_ok=True)
    ref = ROOT / a.pins_ref
    ref.mkdir(parents=True, exist_ok=True)
    for m in a.masters:
        (ref / f'{m}.json').write_text(json.dumps(pins[m], indent=1) + '\n')
        s = spec(m, pins[m], a)
        (a.out / f"{s['name']}.json").write_text(json.dumps(s, indent=1) + '\n')
        print(s['name'], s['top'], s['outline'], {f: v for f, v in s['pins'].items()})


if __name__ == '__main__':
    main()
