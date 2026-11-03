#!/usr/bin/env python3
"""Bind an already generated ring_hold kit to the plan its parent obligation came from (DH56-IOHP 11-03).

    python3 tools/die_plan/io_hold_kit_bind.py PLAN.json KIT [--write]

Before gen_phys.ring_hold_obligation, a plan clock.ring_hold kit got hold_in_min_ports_ps on its forwarded ring inputs
(sdc_lint._io_hold_ctx), so signoff.py applied the IO-HOLD parent obligation, but budget.json carried no io_hold plan
digest and io_hold_qualification.apply_obligation could never accept any receipt ('parent plan differs').  This tool
adds exactly the block the fixed generator writes, budget.json io_hold = {mode: ring_hold, plan_sha256, requires_parent},
and only when the kit's obligation is provably this plan's:
  * budget.json die / type are the plan's die / a plan type, and budget.json has no io_hold yet;
  * gen_phys.ring_hold_obligation(P, type) and no sender_min io_hold.tcl (an A kit already has the block);
  * sdc_lint.json hold_in_min_ports_ps == sdc_lint._io_hold_ctx(P, type) (the obligation itself);
  * constraint.sdc contains landing_contract.ring_input_sdc(P, type) verbatim (the ring contract the kit timed).
Nothing else in the kit changes (no timing input: budget.json io_hold is read only by io_hold_qualification);
the previous file is kept as budget.json.pre-io-hold-bind.  Exit 0 bound (or would bind), 1 refused.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def check(plan_path, kit):
    import gen_phys
    import landing_contract as LC
    import schema as S
    import sdc_lint
    from io_hold_qualification import plan_digest
    kd = Path(kit)
    raw = json.loads(Path(plan_path).read_text())
    P = S.Plan(raw, Path(plan_path))
    bud = json.loads((kd / 'budget.json').read_text())
    tn, why = bud.get('type'), []
    if bud.get('die') != P.name:
        why.append(f"budget die {bud.get('die')} != plan {P.name}")
    if tn not in P.types:
        why.append(f'type {tn} not in plan')
    if bud.get('io_hold'):
        why.append('budget.json already has io_hold')
    if (kd / 'io_hold.tcl').is_file():
        why.append('sender_min kit (io_hold.tcl): regenerate, not a ring_hold bind')
    if not why:
        if not gen_phys.ring_hold_obligation(P, tn):
            why.append('plan has no ring_hold obligation for this type')
        want = sdc_lint._io_hold_ctx(P, tn).get('hold_in_min_ports_ps')
        have = json.loads((kd / 'sdc_lint.json').read_text()).get('hold_in_min_ports_ps')
        if not want or want != have:
            why.append(f'sdc_lint hold_in_min_ports_ps {have} != plan {want}')
        ring = LC.ring_input_sdc(P, tn).strip()
        if not ring or ring not in (kd / 'constraint.sdc').read_text():
            why.append('constraint.sdc ring inputs differ from the plan ring_input_sdc')
    block = dict(mode='ring_hold', plan_sha256=plan_digest(raw), requires_parent=True)
    return dict(kit=str(kd), type=tn, plan=str(plan_path), io_hold=block, ok=not why, problems=why)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('plan')
    ap.add_argument('kit')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args(argv)
    r = check(a.plan, a.kit)
    if r['ok'] and a.write:
        b = Path(a.kit) / 'budget.json'
        bak = b.with_name('budget.json.pre-io-hold-bind')
        if not bak.exists():
            shutil.copy2(b, bak)
        bud = json.loads(b.read_text())
        bud['io_hold'] = r['io_hold']
        b.write_text(json.dumps(bud, indent=1) + '\n')
        r['written'] = str(b)
    print(json.dumps(r, indent=1))
    return 0 if r['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
