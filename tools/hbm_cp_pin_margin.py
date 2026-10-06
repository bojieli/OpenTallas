#!/usr/bin/env python3
"""HBM CP pin-margin (SU_PIN_MARGIN) bench, route and sign-off driver (Claude:tk-hbm-cp, 2026-10-06).

bench   : exact lockstep (Icarus) incl. 5 RTL mutants that must FAIL, closed loop with the real
          shared owner (Verilator) incl. a no-replay negative control and a too-tight fault bound.
route   : one ORFS route of ot_hbm_integrated_su_cp_context (canonical owner-veto CP + SU_PIN_MARGIN
          + SU_RELEASE_REPLAY) at an effective 770 ps (setup uncertainty 123 ps on 833.333 ps).
signoff : routed corner STA at 833.333 ps / SS60 / FF25 with IO vs vclk at the measured insertion.
"""
import argparse, json, hashlib, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = 'rtl/hbm_accel/integrated_20261005/'
CP_SRC = ['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv', D+'ot_hbm_integrated_header_decode.sv', D+'ot_hbm_integrated_su_cp_bind.sv',
          D+'ot_hbm_integrated_su_cp_association.sv', D+'ot_hbm_integrated_su_cp_context.sv']
LOOP_SRC = CP_SRC + [D+'ot_hbm_integrated_prior_debt.sv', D+'ot_hbm_integrated_sm0_borrow.sv']
TB = 'rtl/test/hbm_accel/cp_pin_margin_20261006/'
PHYS = 'physical/hbm_cp_pin_margin_20261006/'
CANON = ['ENABLE=1', 'SU_ENABLE=1', 'SU_REGISTERED_OUTPUTS=1', 'SU_REGISTERED_STATUS=1', 'SU_REGISTERED_BOUNDARY=1',
         'SU_BALANCED_OWNER_BOUNDARY=1', 'SU_FAST_OWNER_FRONTIER=1', 'SU_PARALLEL_PHASE_VALIDATION=1',
         'SU_CONTROL_TAIL_CUT=1', 'SU_OWNER_VETO_POLARITY=1', 'SU_FOUR_COMBINATIONAL_CUTS=1']
# RTL mutants of the exact bench (file, old, new): each must produce mismatches.
MUTANTS = {
 'M1_fault_final_validity_dropped': (D+'ot_hbm_integrated_su_cp_bind.sv', 'assign fault=fault_g||!v_final;', 'assign fault=fault_g;'),
 'M2_owner_compare_from_core_stage': (D+'ot_hbm_integrated_su_cp_context.sv', 'assign in_core=in_q2;assign in_next=in_q1;', 'assign in_core=in_q2;assign in_next=in_q2;'),
 'M3_shared_fault_one_stage': (D+'ot_hbm_integrated_su_cp_context.sv', 'assign in_core=in_q2;assign in_next=in_q1;', 'assign in_core={in_q2[IW-1:1],in_q1[0]};assign in_next=in_q1;'),
 'M4_executor_debt_bypass_dropped': (D+'ot_hbm_integrated_su_cp_association.sv', 'assign exec_owned=phase_valid?executor_g:(associated&&raw_grant&&!rails_bad);', 'assign exec_owned=executor_g&&phase_valid;'),
 'M5_owned_final_validity_dropped': (D+'ot_hbm_integrated_su_cp_bind.sv', 'assign owned=owned_g&&v_final;', 'assign owned=owned_g;'),
}
LOOPS = [  # name, PIN, REPLAY, FAULTS, FAULT_BOUND, expect
 ('L1_orig_nofault', 0, 0, 0, 0, 'PASS'), ('L2_pin_replay_nofault', 1, 1, 0, 3, 'PASS'),
 ('L3_pin_noreplay_nofault_NEG', 1, 0, 0, 3, 'FAIL'), ('L4_orig_faults', 0, 0, 1, 0, 'PASS'),
 ('L5_pin_replay_faults', 1, 1, 1, 3, 'PASS'), ('L6_pin_replay_faults_bound2_NEG', 1, 1, 1, 2, 'FAIL')]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sh(cmd, cwd, log, timeout=None):
    with open(log, 'w') as f:
        return subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, timeout=timeout).returncode


def bench(out, work, cycles, ntx, seeds):
    out = ROOT/out; out.mkdir(parents=True, exist_ok=True); work = Path(work); work.mkdir(parents=True, exist_ok=True)
    jobs = []  # (name, kind, expect, cmd list of (cmd,cwd), log)
    def exact_job(name, tree, expect, cyc, seed):
        vvp = work/f'{name}.vvp'
        comp = ['iverilog', '-g2012', f'-Ptb_cp_pin_margin_exact.CYCLES={cyc}', f'-Ptb_cp_pin_margin_exact.SEED={seed}',
                '-o', str(vvp)] + CP_SRC + [TB+'tb_cp_pin_margin_exact.sv']
        return (name, 'exact', expect, [(comp, tree), (['vvp', str(vvp)], tree)])
    for seed in seeds:
        jobs.append(exact_job(f'E_seed{seed}', ROOT, 'PASS', cycles, seed))
    for m, (f, a, b) in MUTANTS.items():
        tree = work/('tree_'+m)
        if tree.exists(): shutil.rmtree(tree)
        for s in CP_SRC + [TB+'tb_cp_pin_margin_exact.sv']:
            (tree/s).parent.mkdir(parents=True, exist_ok=True); shutil.copy(ROOT/s, tree/s)
        t = (tree/f).read_text(); assert t.count(a) == 1, m; (tree/f).write_text(t.replace(a, b))
        jobs.append(exact_job(m, tree, 'FAIL', cycles//4, seeds[0]))
    for name, pin, rep, flt, bound, expect in LOOPS:
        mdir = work/('vl_'+name)
        if mdir.exists(): shutil.rmtree(mdir)
        comp = ['verilator', '--binary', '--timing', '-j', '4', '-Wno-fatal', '-Wno-lint', '-Wno-style', '-Wno-TIMESCALEMOD',
                f'-GPIN={pin}', f'-GREPLAY={rep}', f'-GFAULTS={flt}', f'-GFAULT_BOUND={bound}', f'-GNTX={ntx}', f'-GSEED={seeds[0]}',
                '--top-module', 'tb_cp_pin_margin_loop', '-Mdir', str(mdir)] + LOOP_SRC + [TB+'tb_cp_pin_margin_loop.sv']
        jobs.append((name, 'loop', expect, [(comp, ROOT), ([str(mdir/'Vtb_cp_pin_margin_loop')], ROOT)]))
    import concurrent.futures as cf
    def run(job):
        name, kind, expect, steps = job
        log = out/f'{name}.log'; text = ''
        for i, (cmd, cwd) in enumerate(steps):
            rc = sh(cmd, cwd, work/f'{name}.{i}.log', timeout=7200)
            text += (work/f'{name}.{i}.log').read_text()[-4000:] if i else ''
            if rc and i == 0:
                text = (work/f'{name}.0.log').read_text()[-3000:]; break
        log.write_text(text)
        verdict = 'PASS' if re.search(r'^PASS$', text, re.M) else 'FAIL'
        summary = next((l for l in text.splitlines() if l.startswith(('EXACT', 'LOOP'))), '')
        num = lambda k: int((re.search(rf'\b{k}=(-?\d+)', summary) or [0, -1])[1])
        if expect == 'PASS':
            ok = verdict == 'PASS'
        elif kind == 'exact':   # a mutant must be caught by output mismatches, not by coverage
            ok = num('mismatches') > 0
        elif 'bound2' in name:  # the 3-edge fault latency is tight: bound 2 must report late detections
            ok = num('late') > 0
        else:                   # no replay: the release handshake must break (CP/owner fault or hang)
            ok = verdict == 'FAIL' and (num('cp_fault') > 0 or num('arb_fault_cycles') > 0 or num('timeouts') > 0 or 'HANG' in text)
        return dict(name=name, kind=kind, expect=expect, verdict=verdict, ok=ok, summary=summary)
    with cf.ThreadPoolExecutor(8) as ex:
        res = list(ex.map(run, jobs))
    rec = dict(schema='hbm.cp.pin-margin.bench.v1', source_sha256={s: sha(ROOT/s) for s in LOOP_SRC + [TB+'tb_cp_pin_margin_exact.sv', TB+'tb_cp_pin_margin_loop.sv']},
               cycles=cycles, ntx=ntx, seeds=seeds, results=res, all_expected=all(r['ok'] for r in res),
               mutants={k: dict(file=v[0], old=v[1], new=v[2]) for k, v in MUTANTS.items()})
    (out/'bench.json').write_text(json.dumps(rec, indent=1)+'\n')
    for r in res: print(('OK  ' if r['ok'] else 'BAD ')+r['name'], r['verdict'], 'expect', r['expect'], '|', r['summary'][:220])
    print('ALL_EXPECTED', rec['all_expected'])
    return 0 if rec['all_expected'] else 1


def route_argv(job, threads, tag):
    base = json.loads((ROOT/'results/physical/hbm_cp_owner_veto_parent_context_20261006/r1_terminal/prepared.json').read_text())['argv']
    a = list(base)
    def setv(opt, val):
        a[a.index(opt)+1] = str(val)
    setv('--clock-uncertainty-ns', '0.123')         # effective 770 ps route
    setv('--sdc-append', PHYS+'io_vclk_m.sdc')
    setv('--hold-margin-ns', '0.025')
    setv('--nickname-tag', tag)
    setv('--keep-workdir', f'{job}/work'); setv('--output', f'{job}/physical.json')
    # drop the old body fences / membership hooks; pins come from the canonical 236 coordinates
    out = []; i = 0
    while i < len(a):
        if a[i] == '--step-tcl':
            v = a[i+1]
            if v.startswith('POST_IO_PLACEMENT='): out += ['--step-tcl', 'POST_IO_PLACEMENT='+PHYS+'post_io.tcl']
            elif v.startswith(('PRE_GLOBAL_PLACE=', 'PRE_GLOBAL_ROUTE=', 'PRE_DETAIL_PLACE=')): pass
            else: out += [a[i], v]
            i += 2; continue
        if a[i] == '--orfs-var' and a[i+1].startswith('TMPDIR='):
            i += 2; continue  # /work/tmp does not exist in a fresh work dir
        if a[i] == '--orfs-var' and a[i+1].startswith('NUM_CORES='):
            out += ['--orfs-var', f'NUM_CORES={threads}']; i += 2; continue
        out.append(a[i]); i += 1
    out += ['--param', 'SU_PIN_MARGIN=1', '--param', 'SU_RELEASE_REPLAY=1']
    return out


def route(job, threads, tag):
    job = Path(job); job.mkdir(parents=True, exist_ok=True)
    argv = route_argv(str(job), threads, tag)
    (job/'argv.json').write_text(json.dumps(argv, indent=1)+'\n')
    rc = subprocess.run([sys.executable, 'tools/run_abi3_physical.py'] + argv, cwd=ROOT,
                        stdout=open(job/'route.log', 'w'), stderr=subprocess.STDOUT).returncode
    (job/'route.exit').write_text(f'{rc}\n')
    return rc


def signoff(orfs, output):
    sys.path.insert(0, str(ROOT/'tools/w18')); sys.path.insert(0, str(ROOT/'tools'))
    import corner_sta as base
    original = base.script
    def script(corner, relative, macros, post_sdc=()):
        text = original(corner, relative, macros, post_sdc)
        text = text.replace('set_propagated_clock [all_clocks]', 'set_clock_latency 0 [all_clocks]\nset_propagated_clock [all_clocks]')
        check = 'max' if corner == 'ss' else 'min'
        extra = """
foreach p [all_registers -data_pins] {
 set s [get_property $p slack_CHECK]
 if {$s ne "INF"} {puts "OT_ACTUAL_FF [get_full_name $p] $s"}
}
foreach p [all_outputs] {
 set s [get_property $p slack_CHECK]
 if {$s ne "INF"} {puts "OT_ACTUAL_OUTPUT [get_full_name $p] $s"}
}
foreach p [all_inputs] {
 set s [get_property $p slack_CHECK]
 if {$s ne "INF"} {puts "OT_ACTUAL_INPUT [get_full_name $p] $s"}
}
puts OT_GROUP_R2R
report_checks -path_delay CHECK -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 3 -format full_clock_expanded
puts OT_GROUP_I2R
report_checks -path_delay CHECK -from [all_inputs] -group_path_count 1 -format full_clock_expanded
puts OT_GROUP_OUTPUT
report_checks -path_delay CHECK -to [all_outputs] -group_path_count 1 -format full_clock_expanded
report_clock_latency -clock core_clk
""".replace('CHECK', check)
        return text.replace('exit\n', extra+'\nexit\n')
    base.script = script
    post = [PHYS+'signoff_post.sdc']
    o = Path(orfs).resolve()
    res = dict(schema='hbm.cp.pin-margin.signoff.v1', clock_ps=833.333, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
               io='0.2T+150 ps vs vclk at measured mean insertion; -min 0', post_sdc={p: sha(ROOT/p) for p in post},
               ss=base.run(o, 'ss', [], post), ff=base.run(o, 'ff', [], post))
    for c in ('ss', 'ff'):
        log = (o/f'w18_sta_{c}.log').read_text()
        m = re.search(r'OT_VCLK_INSERTION (\S+) (\S+) (\S+)', log)
        res[c]['vclk_insertion_ps'] = [float(x) for x in m.groups()] if m else None
        vals = [float(x) for x in re.findall(r'^OT_ACTUAL_(?:FF|OUTPUT|INPUT) \S+ (\S+)', log, re.M)]
        res[c]['worst_endpoint_slack_ps'] = min(vals) if vals else None
    ss, ff = res['ss']['worst_slack_ps'], res['ff']['worst_slack_ps']
    res['accept'] = dict(rule='SS >= +40 ps, FF >= +15 ps, DRC 0 (owner UPDATE 2)', ss_ok=ss is not None and ss >= 40,
                         ff_ok=ff is not None and ff >= 15)
    Path(output).write_text(json.dumps(res, indent=1)+'\n')
    print(json.dumps({c: {k: res[c].get(k) for k in ('worst_slack_ps', 'tns_ps', 'worst_reg_to_reg_slack_ps', 'worst_input_to_reg_slack_ps',
          'worst_output_port_slack_ps', 'violating_d_pins', 'vclk_insertion_ps', 'errors')} for c in ('ss', 'ff')} | {'accept': res['accept']}, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('bench'); b.add_argument('--out', default='results/rtl/hbm_cp_pin_margin_20261006/bench_r1')
    b.add_argument('--work', default='/tmp/tkcp-bench'); b.add_argument('--cycles', type=int, default=400000)
    b.add_argument('--ntx', type=int, default=3000); b.add_argument('--seeds', type=int, nargs='+', default=[1, 7])
    r = sub.add_parser('route'); r.add_argument('--job', required=True); r.add_argument('--threads', type=int, default=16)
    r.add_argument('--tag', default='claude_tkcp_pin_margin_r1')
    s = sub.add_parser('signoff'); s.add_argument('--orfs', required=True); s.add_argument('--output', required=True)
    x = ap.parse_args()
    if x.cmd == 'bench': sys.exit(bench(x.out, x.work, x.cycles, x.ntx, x.seeds))
    if x.cmd == 'route': sys.exit(route(x.job, x.threads, x.tag))
    signoff(x.orfs, x.output)
