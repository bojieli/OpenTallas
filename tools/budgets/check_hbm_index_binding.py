#!/usr/bin/env python3
"""Read-only replay and compensation proof for the approved HBM r18 index budget.

No closure-loop imports, state writes, retries or target relaxation. The output
distinguishes a valid budget plan from a stale job binding and physical sign-off.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
RECORD = Path('results/rtl/hbm_index_budget_binding_20261006')
SNAPSHOT = RECORD / 'inputs'
BUDGET = SNAPSHOT / 'results/rtl/budgets_20261006'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stats(values):
    return dict(mean=round(sum(values) / len(values), 1),
                min=round(min(values), 1), max=round(max(values), 1))


def snapshot_modules(snapshot):
    """Load the audited helpers without depending on active-tree Python modules."""
    def load(name, filename):
        spec = importlib.util.spec_from_file_location(name, snapshot / 'tools/budgets' / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    common = load('hbm_audit_common', 'common.py')
    previous = sys.modules.get('common')
    old_path = sys.path[:]
    try:
        sys.modules['common'] = common
        budget = load('hbm_audit_budget_sheet', 'budget_sheet.py')
    finally:
        sys.path[:] = old_path
        if previous is None:
            sys.modules.pop('common', None)
        else:
            sys.modules['common'] = previous
    return common, budget


def check(root, jobs):
    snapshot = root / SNAPSHOT
    manifest_path = snapshot / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    require(manifest['schema'] == 'opentallas.hbm_index_budget_snapshot.v1', 'snapshot schema')
    for name in ('common.py', 'budget_sheet.py'):
        relative = f'tools/budgets/{name}'
        require(sha(snapshot / relative) == manifest['files'][relative]['sha256'],
                f'{relative}: snapshot digest mismatch')
    C, B = snapshot_modules(snapshot)
    base = root / BUDGET
    model_path = base / 'inputs/die_models/hbm.json.gz'
    plan_path = base / 'clock_plan/hbm.json.gz'
    cal_path = base / 'inputs/calibrations.json'
    override_path = base / 'inputs/insertion_override.json'
    model = C.load_die(model_path)
    plan = B.load_plan(plan_path)
    cal = json.loads(cal_path.read_text())
    overrides = json.loads(override_path.read_text())
    require(model['schema'] == 'opentallas.budgets.die_model.v1', 'die schema')
    require(plan['schema'] == 'opentallas.budgets.clock_plan.v1', 'clock plan schema')
    require(model['source_commit'] == plan['source_commit'], 'model/plan source mismatch')
    provenance_path = base / 'inputs/provenance.json'
    provenance = json.loads(provenance_path.read_text())['die_models']['hbm']
    require(provenance['commit'] == model['source_commit'], 'provenance/model source mismatch')
    require(plan['violations']['intra'] == plan['violations']['inter'] == 0, 'clock plan violations')
    expected_masters = {f'hfd_index_q_b{i}' for i in (0, 1, 2, 3, 5)}
    require(set(overrides) == expected_masters, 'approved override scope changed')
    require(json.loads((snapshot / 'physical/hbm_accel_die_views/insertion_override.json').read_text())
            == overrides, 'published override differs from coordinator')
    inputs = [manifest_path, root / 'tools/budgets/check_hbm_index_binding.py']
    inputs += [snapshot / name for name in manifest['files']]
    sheets = {}
    # Replay ALL HBM sheets to include the peers which also pay the extra OCV.
    with tempfile.TemporaryDirectory(prefix='hbm-budget-binding-') as tmp:
        subprocess.run([sys.executable, str(snapshot / 'tools/budgets/budget_sheet.py'),
                        '--die', f'hbm={model_path}:{plan_path}', '--calib', str(cal_path),
                        '--insertion-override', str(override_path), '--out', tmp],
                       check=True, capture_output=True, text=True)
        for p in sorted((Path(tmp) / 'sheets').glob('*.json')):
            expected = json.loads(p.read_text())
            published = base / 'sheets' / p.name
            actual = json.loads(published.read_text())
            if set(actual['dies']) == {'hbm'}:
                require(actual == expected, f'{p.stem}: sheet differs from compensated replay')
            else:
                # Shared PHY/SerDes aggregate other dies; only their insertion
                # participates in this HBM-only proof.
                require(actual['clock']['internal_insertion'] == expected['clock']['internal_insertion'],
                        f'{p.stem}: shared macro insertion mismatch')
            require(actual['schema'] == 'opentallas.budgets.sheet.v1', f'{p.stem}: sheet schema')
            require(expected['totals']['infeasible'] == 0, f'{p.stem}: infeasible HBM interface')
            sheets[p.stem] = expected
            inputs.append(published)

    trees = C.clock_trees(model)
    reg = {k: (v[0], v[1]) for k, v in C.sink_regions(model, trees).items()}
    clock_ports = {}
    for tree, tr in trees.items():
        for inst, port in tr['sinks']:
            clock_ports.setdefault(inst, {})[tree] = port
    for inst, (tree, region) in list(reg.items()):
        pin = f'{inst}/{clock_ports[inst][tree]}'
        reg[inst] = (tree, plan['sink_region'].get(pin, region))
    region_flops = {}
    # Independently reconstruct the SS and FF common flop arrival from every
    # region member; entry + measured internal insertion must equal that value.
    for inst, (_, region) in reg.items():
        tree = reg[inst][0]
        arrival = plan['sink_insertion'].get(f'{inst}/{clock_ports[inst][tree]}')
        if arrival is None:
            continue
        master = model['by'][inst][1]
        ins = sheets[master]['clock']['internal_insertion']
        total = [arrival[0] + ins['ss'], arrival[1] + ins['ff']]
        prev = region_flops.setdefault(region, total)
        region_flops[region] = [max(a, b) for a, b in zip(prev, total)]
    extra = {}
    for master in overrides:
        ins = sheets[master]['clock']['internal_insertion']
        require(ins.get('replanned') is True and ins['grade'] == 'measured', f'{master}: missing replan')
        require(ins['target_ss'] == cal[master]['ss_max'], f'{master}: target lacks approved calibration')
        require(ins['ss'] == cal[master]['ss_mean'], f'{master}: compensated insertion changed')
        extra[master] = round(C.OCV * max(0, ins['target_ss'] - C.LINT_CAP_PS), 1)
    intra = {r: v['intra_budget_ps'] for r, v in plan['regions'].items()}
    fwd = B.fwd_links(model)
    proof = {}
    for master in sorted(expected_masters):
        sh = sheets[master]
        ins = sh['clock']['internal_insertion']
        entries = []
        for inst in model['insts']:
            if inst[1] != master:
                continue
            tree, region = reg[inst[0]]
            arrival = plan['sink_insertion'][f'{inst[0]}/{clock_ports[inst[0]][tree]}']
            ft = [round(v, 1) for v in region_flops[region]]
            entry = [round(ft[0] - ins['ss'], 1), round(ft[1] - ins['ff'], 1)]
            require(all(math.isfinite(v) and v >= 0 for v in entry), f'{master}: invalid entry')
            require(entry[0] >= arrival[0] - 0.1, f'{master}: requires entry before measured CTS arrival')
            entries.append(dict(instance=inst[0], region=region, cts_entry_ss_ff_ps=arrival,
                                region_flop_ss_ff_ps=ft, target_entry_ss_ff_ps=entry,
                                pad_ss_ps=round(entry[0] - arrival[0], 1)))
        require(len(entries) == sh['dies']['hbm'], f'{master}: missing instance')
        for corner, idx in (('ss', 0), ('ff', 1)):
            require(stats([e['target_entry_ss_ff_ps'][idx] for e in entries]) ==
                    sh['clock'][f'entry_target_{corner}_ps'], f'{master}: {corner} entry aggregate')
        require(stats([e['pad_ss_ps'] for e in entries]) == sh['clock']['die_pad_ss_ps'],
                f'{master}: die pad aggregate')
        interfaces = []
        for p in sh['interfaces']:
            require(p['timing'] == 'sync', f'{master}: unexpected interface schema')
            me, peer = p['worst_instance'].removeprefix('hbm:').split('<->')
            drv, ld = (me, peer) if p['dir'] == 'output' else (peer, me)
            fbus = any(bid in model.get('fclk_buses', []) and eps[0][0] == drv
                       and any(e[0] == ld for e in eps[1:])
                       and any(e[0] == me and e[1] == p['port'] for e in eps)
                       for bid, cls, bits, eps in model['buses'])
            kind, base_skew = B.classify(model, model['by'][drv], model['by'][ld], reg, trees, intra, fwd, fbus)
            charge = sum(extra.get(model['by'][i][1], 0) for i in (drv, ld))
            if kind in ('fwd', 'fwd-unlinked'):
                charge = 0
            require(kind == p['skew_class'], f'{master}/{p["port"]}: unexpected clock classification')
            require(round(base_skew + charge, 1) == p['skew_ps'], f'{master}/{p["port"]}: missing OCV charge')
            interfaces.append(dict(port=p['port'], direction=p['dir'], worst_instance=p['worst_instance'],
                                   base_skew_ps=base_skew, extra_ocv_ps=charge, skew_ps=p['skew_ps'],
                                   stages_planned=p['stages_planned'], stages_needed=p['stages_needed']))
        proof[master] = dict(target_ss_ps=ins['target_ss'], compensated_ss_ps=ins['ss'],
                             extra_ocv_ps=extra[master], entries=entries, interfaces=interfaces)

    bindings = []
    for path in sorted(jobs.glob('*.json')):
        j = json.loads(path.read_text())
        master = j['budget']['master']
        require(master in expected_masters, f'{path.name}: job outside scope')
        require(j['status'] == 'NEEDS_BUDGET', f'{path.name}: not historical NEEDS_BUDGET')
        require(j['spec']['source']['commit'] == j['commit_full'], f'{path.name}: source mismatch')
        env = j['calibration']['env']
        measured = env['CK_SS_MEAN']
        ins = sheets[master]['clock']['internal_insertion']
        require(isinstance(measured, (int, float)) and math.isfinite(measured), 'invalid measured insertion')
        bindings.append(dict(job=j['name'], source_commit=j['commit_full'], snapshot_sha256=sha(path),
                             historical_status=j['status'], bound_sheets_ref=j['budget']['sheets_ref'],
                             bound_target_ss_ps=j['budget']['insertion']['target_ss'],
                             approved_target_ss_ps=ins['target_ss'], measured_ss_mean_ps=measured,
                             measured_ss_max_ps=env['CK_SS_MAX'],
                             boundary_max_above_approved_target_ps=max(0, env['CK_SS_MAX'] - ins['target_ss']),
                             compensated_mean_delta_ps=measured - ins['ss'],
                             mean_gate_pass=measured <= ins['target_ss'],
                             stale_binding=j['budget']['insertion'] != ins,
                             corrected_binding=dict(master=master,
                                 sheets_ref='d05ac0e82010636e49ed46a5f6016ddc17cac53a',
                                 sheet_sha256=sha(base / 'sheets' / f'{master}.json'),
                                 insertion=ins, entry_target_ss=sheets[master]['clock']['entry_target_ss_ps']),
                             disposition='rebind complete sheet and regenerate all SDCs through closure owner; '
                                         'preserve historical failure; route and SS/FF sign-off still required'))
        inputs.append(path)
    require(len(bindings) == 5, 'expected five index job snapshots')
    for name, pin in manifest['files'].items():
        require(sha(snapshot / name) == pin['sha256'], f'{name}: snapshot digest mismatch')
    return dict(schema='opentallas.hbm_index_budget_binding.v1', verdict='PASS', signoff_claim=False,
                scope='historical r18 snapshot compensation and job binding audit; no active-main validation or physical adoption',
                replay_source_commit=manifest['audit_commit'], active_main_validated=False,
                model_source_commit=model['source_commit'], replayed_hbm_sheets=len(sheets),
                shared_macros_scope='PHY/SerDes: HBM replay and published insertion only; other dies excluded',
                provenance_note='Generator source is the model/clock-plan embedded commit; publication commit '
                                'is separately named in inputs/provenance.json.',
                inputs={str(p.relative_to(root)): sha(p) for p in sorted(set(inputs))},
                masters=proof, jobs=bindings)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--jobs', type=Path)
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()
    try:
        result = check(args.root.resolve(), args.jobs or args.root / RECORD / 'jobs')
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f'HBM_INDEX_BINDING FAIL: {exc}')
    text = json.dumps(result, indent=2) + '\n'
    if args.out:
        args.out.write_text(text)
    else:
        print(text, end='')
