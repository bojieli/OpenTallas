"""Build the CP1-only early-ingress clock diagnostic; never changes an IO constraint.

The generated plan retains the 250/202.5 ps interface and sender_min only on
partition-driven cuts. Selected local clock trees target 173/140.13 ps.
This is a CTS diagnostic, not a new signed contract or production die plan.
"""
import argparse
import json
from pathlib import Path
import schema as S
import gen_phys as G
import pair


def prepare(raw, target_ps=173.0):
    import copy
    raw = copy.deepcopy(raw)
    raw['clock']['io_hold'] = 'sender_min'
    raw['die']['reach_um'] = 405
    raw['die']['layer_budget']['die_use'] = ['clock_spine', 'reset', 'pg']
    counts = pair.proof_clock(raw, max_sinks=400, radius_um=80.0)
    p = S.Plan(raw)
    out = {}
    for tn, t in p.types.items():
        hold = G.input_hold_min(p, tn)
        inputs = {b['name'] for b in t['buses'] if b['dir'] == 'in'}
        inputs |= {s['name']+'_i' for s in t.get('ft_slots', [])}
        external = inputs - set(hold)
        taps = G.clock_pins(p, tn)
        selected = {}
        for bn, bit, _layer, x, y, face in G.type_pins(p, tn):
            if bn not in external:
                continue
            tap = min(taps, key=lambda a: abs(a[1]-x)+abs(a[2]-y))[0]
            selected[tap] = selected.get(tap, 0)+1
        out[tn] = dict(target_tt_ps=target_ps, target_ff_ps=target_ps*0.81,
                       selected=selected, external_ports=sorted(external),
                       sender_min=hold, density=counts[tn])
    return raw, out


def install(kits, report):
    """Opt-in local target map; all virtual clocks and input/output budgets stay intact."""
    for tn, r in report.items():
        path = kits/tn/'tap_balance.tcl'
        s = path.read_text()
        needle = 'set d [expr {min($tgt - [lindex $v 0], $tb_target + $tb_win - [lindex $v 2])}]'
        assert s.count(needle) == 1
        table = ' '.join(f'{n} {r["target_tt_ps"]:g}' for n in sorted(r['selected']))
        replacement = ('# CP1 early ingress diagnostic: physical local insertion only; no SDC edit.\n'
                       f'    set cp1_early_targets {{{table}}}\n'
                       '    set cp1_target $tgt\n'
                       '    if {[dict exists $cp1_early_targets $n]} {\n'
                       '      set cp1_target [expr {[dict get $cp1_early_targets $n]*$tb_target/250.0}]\n'
                       '    }\n'
                       '    set d [expr {min($cp1_target - [lindex $v 0], $cp1_target + $tb_win - [lindex $v 2])}]')
        path.write_text(s.replace(needle, replacement))
        (kits/tn/'cp1_early_clock.json').write_text(json.dumps(r, indent=2)+'\n')


def main():
    a = argparse.ArgumentParser()
    a.add_argument('plan', type=Path)
    a.add_argument('--out', type=Path, required=True)
    a.add_argument('--install-kits', type=Path)
    args=a.parse_args()
    raw, report = prepare(json.loads(args.plan.read_text()))
    args.out.mkdir(parents=True, exist_ok=True)
    leaves=args.plan.parent/'leaves.sv'
    if leaves.is_file():
        import shutil
        shutil.copyfile(leaves, args.out/'leaves.sv')
        for t in raw['partition_types'].values():
            t['sources']=[str((args.out/'leaves.sv').resolve())]
    (args.out/'pair_plan.json').write_text(json.dumps(raw, indent=1)+'\n')
    (args.out/'early_clock.json').write_text(json.dumps(report, indent=2)+'\n')
    if args.install_kits:
        install(args.install_kits, report)
    print(json.dumps(report, indent=2))

if __name__=='__main__': main()
