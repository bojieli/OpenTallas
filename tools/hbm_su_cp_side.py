#!/usr/bin/env python3
"""SU-side CP block (ot_hbm_su_cp_side) bench, route and sign-off driver (Claude:hbm-su-cpin, 2026-10-06).

bench   : exact lockstep (Icarus) vs the canonical context with per-class input/output delays, incl. RTL
          mutants that must FAIL; closed loop with the real shared owner ot_hbm_integrated_sm0_borrow
          (Verilator) incl. a no-replay negative and a too-tight fault bound; DET=1 latency runs
          (canonical, standalone pin-margin, SU-side block) for the per-transaction cycle cost.
route   : one ORFS route of ot_hbm_su_cp_side at an effective 770 ps (setup uncertainty 123 ps on 833.333 ps).
signoff : routed corner STA at 833.333 ps / SS60 / FF25, IO per port class vs vclk at the measured insertion.
"""
import argparse, json, hashlib, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = 'rtl/hbm_accel/integrated_20261005/'
SIDE = 'rtl/hbm_accel/integrated_20261006/ot_hbm_su_cp_side.sv'
CP_SRC = ['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv', D+'ot_hbm_integrated_header_decode.sv', D+'ot_hbm_integrated_su_cp_bind.sv',
          D+'ot_hbm_integrated_su_cp_association.sv', D+'ot_hbm_integrated_su_cp_context.sv', SIDE]
LOOP_SRC = CP_SRC + [D+'ot_hbm_integrated_prior_debt.sv', D+'ot_hbm_integrated_sm0_borrow.sv']
TB = 'rtl/test/hbm_accel/su_cp_side_20261006/'
PHYS = 'physical/hbm_su_cp_side_20261006/'
# adopted block shape: launch 2 (pin capture + core), shared-owner seat 1 in / 1 out (replay 2), executor in-block, status 1
SHAPE = dict(OWN_IN=1, OWN_OUT=1, EXEC_IN=0, EXEC_OUT=0, OUT=1)
CANON = ['ENABLE=1', 'SU_ENABLE=1', 'SU_REGISTERED_OUTPUTS=1', 'SU_REGISTERED_STATUS=1', 'SU_REGISTERED_BOUNDARY=1',
         'SU_BALANCED_OWNER_BOUNDARY=1', 'SU_FAST_OWNER_FRONTIER=1', 'SU_PARALLEL_PHASE_VALIDATION=1',
         'SU_CONTROL_TAIL_CUT=1', 'SU_OWNER_VETO_POLARITY=1', 'SU_FOUR_COMBINATIONAL_CUTS=1']
# RTL mutants of the exact bench (file, old, new): each must produce mismatches.
MUTANTS = {
 'M1_fault_final_validity_dropped': (D+'ot_hbm_integrated_su_cp_bind.sv', 'assign fault=fault_g||!v_final;', 'assign fault=fault_g;'),
 'M2_owner_compare_from_core_stage': (SIDE, '=l_q1;\n  wire [191:0]', '=l_q2;\n  wire [191:0]'),
 'M3_shared_owner_inputs_unstaged': (SIDE, '.N(OWN_IN)) s_own_in', '.N(0)) s_own_in'),
 'M4_executor_debt_bypass_dropped': (D+'ot_hbm_integrated_su_cp_association.sv', 'assign exec_owned=phase_valid?executor_g:(associated&&raw_grant&&!rails_bad);', 'assign exec_owned=executor_g&&phase_valid;'),
 'M5_owned_final_validity_dropped': (D+'ot_hbm_integrated_su_cp_bind.sv', 'assign owned=owned_g&&v_final;', 'assign owned=owned_g;'),
 'M6_executor_inputs_one_stage': (SIDE, '.N(EXEC_IN)) s_exec_in', '.N(EXEC_IN+1)) s_exec_in'),
 'M7_status_outputs_unregistered': (SIDE, '.N(OUT)) s_out', '.N(0)) s_out'),
}
LOOPS = [  # name, SIDE, PIN, REPLAY, SIDE_REPLAY, FAULTS, FAULT_BOUND, expect
 ('L1_orig_nofault', 0, 0, 0, -1, 0, 0, 'PASS'), ('L2_side_nofault', 1, 0, 0, -1, 0, 2, 'PASS'),
 ('L3_side_noreplay_nofault_NEG', 1, 0, 0, 0, 0, 2, 'FAIL'), ('L4_orig_faults', 0, 0, 0, -1, 1, 0, 'PASS'),
 ('L5_side_faults', 1, 0, 0, -1, 1, 2, 'PASS'), ('L6_side_faults_bound1_NEG', 1, 0, 0, -1, 1, 1, 'FAIL')]
DETS = [  # name, SIDE, PIN, REPLAY, extra shape override
 ('D_orig', 0, 0, 0, {}), ('D_pin_margin_standalone', 0, 1, 1, {}), ('D_side', 1, 0, 0, {}),
 ('D_side_seat_inblock_info', 1, 0, 0, dict(OWN_IN=0, OWN_OUT=0))]


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
        comp = ['iverilog', '-g2012', f'-Ptb_su_cp_side_exact.CYCLES={cyc}', f'-Ptb_su_cp_side_exact.SEED={seed}', '-o', str(vvp)] + \
               [f'-Ptb_su_cp_side_exact.{k}={v}' for k, v in SHAPE.items()] + CP_SRC + [TB+'tb_su_cp_side_exact.sv']
        return (name, 'exact', expect, [(comp, tree), (['vvp', str(vvp)], tree)])
    for seed in seeds:
        jobs.append(exact_job(f'E_seed{seed}', ROOT, 'PASS', cycles, seed))
    for m, (f, a, b) in MUTANTS.items():
        tree = work/('tree_'+m)
        if tree.exists(): shutil.rmtree(tree)
        for s in CP_SRC + [TB+'tb_su_cp_side_exact.sv']:
            (tree/s).parent.mkdir(parents=True, exist_ok=True); shutil.copy(ROOT/s, tree/s)
        t = (tree/f).read_text(); assert t.count(a) == 1, m; (tree/f).write_text(t.replace(a, b))
        jobs.append(exact_job(m, tree, 'FAIL', cycles//4, seeds[0]))
    def loop_job(name, side, pin, rep, srep, flt, bound, expect, ntx_, det, shape):
        mdir = work/('vl_'+name)
        if mdir.exists(): shutil.rmtree(mdir)
        comp = ['verilator', '--binary', '--timing', '-j', '4', '-Wno-fatal', '-Wno-lint', '-Wno-style', '-Wno-TIMESCALEMOD',
                f'-GSIDE={side}', f'-GPIN={pin}', f'-GREPLAY={rep}', f'-GSIDE_REPLAY={srep}', f'-GFAULTS={flt}', f'-GFAULT_BOUND={bound}',
                f'-GNTX={ntx_}', f'-GSEED={seeds[0]}', f'-GDET={det}'] + [f'-G{k}={v}' for k, v in shape.items()] + \
               ['--top-module', 'tb_su_cp_side_loop', '-Mdir', str(mdir)] + LOOP_SRC + [TB+'tb_su_cp_side_loop.sv']
        return (name, 'det' if det else 'loop', expect, [(comp, ROOT), ([str(mdir/'Vtb_su_cp_side_loop')], ROOT)])
    for name, side, pin, rep, srep, flt, bound, expect in LOOPS:
        jobs.append(loop_job(name, side, pin, rep, srep, flt, bound, expect, ntx, 0, SHAPE))
    for name, side, pin, rep, ov in DETS:
        jobs.append(loop_job(name, side, pin, rep, -1, 0, 0, 'PASS', 200, 1, {**SHAPE, **ov}))
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
        elif 'bound1' in name:  # the 2-edge fault latency is tight: bound 1 must report late detections
            ok = num('late') > 0
        else:                   # no replay: the release handshake must break (CP/owner fault or hang)
            ok = verdict == 'FAIL' and (num('cp_fault') > 0 or num('arb_fault_cycles') > 0 or num('timeouts') > 0 or 'HANG' in text)
        return dict(name=name, kind=kind, expect=expect, verdict=verdict, ok=ok, summary=summary)
    with cf.ThreadPoolExecutor(12) as ex:
        res = list(ex.map(run, jobs))
    for r in res:  # deterministic per-transaction latency
        if r['kind'] == 'det':
            m = re.search(r'tx=(\d+) done=(\d+).*?sum_tx_cycles=(\d+)', r['summary'])
            r['cycles_per_tx'] = int(m[3])/int(m[2]) if m and int(m[2]) else None
    rec = dict(schema='hbm.su-cp-side.bench.v1', shape=SHAPE, source_sha256={s: sha(ROOT/s) for s in LOOP_SRC + [TB+'tb_su_cp_side_exact.sv', TB+'tb_su_cp_side_loop.sv']},
               cycles=cycles, ntx=ntx, seeds=seeds, results=res, all_expected=all(r['ok'] for r in res),
               mutants={k: dict(file=v[0], old=v[1], new=v[2]) for k, v in MUTANTS.items()})
    (out/'bench.json').write_text(json.dumps(rec, indent=1)+'\n')
    for r in res: print(('OK  ' if r['ok'] else 'BAD ')+r['name'], r['verdict'], 'expect', r['expect'], r.get('cycles_per_tx', ''), '|', r['summary'][:260])
    print('ALL_EXPECTED', rec['all_expected'])
    return 0 if rec['all_expected'] else 1


def route_argv(job, threads, tag):
    base = json.loads((ROOT/'results/physical/hbm_cp_pin_margin_20261006/r1/argv.json').read_text())
    a = list(base)
    def setv(opt, val):
        a[a.index(opt)+1] = str(val)
    setv('--top', 'ot_hbm_su_cp_side')
    setv('--sdc-append', PHYS+'io_vclk_m.sdc')
    setv('--hold-margin-ns', '0.030')
    setv('--nickname-tag', tag)
    setv('--keep-workdir', f'{job}/work'); setv('--output', f'{job}/physical.json')
    out = []; i = 0
    while i < len(a):
        if a[i] == '--param' or a[i] == '--source':
            i += 2; continue
        if a[i] == '--step-tcl' and a[i+1].startswith('POST_IO_PLACEMENT='):
            out += ['--step-tcl', 'POST_IO_PLACEMENT='+PHYS+'post_io.tcl']; i += 2; continue
        if a[i] == '--orfs-var' and a[i+1].startswith('NUM_CORES='):
            out += ['--orfs-var', f'NUM_CORES={threads}']; i += 2; continue
        out.append(a[i]); i += 1
    for s in CP_SRC:
        if not s.endswith('su_cp_context.sv'): out += ['--source', s]
    out += ['--param', 'ENABLE=1'] + sum((['--param', f'{k}={v}'] for k, v in SHAPE.items()), [])
    out += ['--step-tcl', 'PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl',
            '--step-tcl', 'PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl']
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
    res = dict(schema='hbm.su-cp-side.signoff.v1', clock_ps=833.333, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
               io='die/seat ports 0.2T+150 ps, in-block executor inputs 0.15T / outputs 0.5T, vs vclk at measured mean insertion; -min 0', post_sdc={p: sha(ROOT/p) for p in post},
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
    b = sub.add_parser('bench'); b.add_argument('--out', default='results/rtl/hbm_su_cp_inside_20261006/bench_r1')
    b.add_argument('--work', default='/tmp/sucpin-bench'); b.add_argument('--cycles', type=int, default=400000)
    b.add_argument('--ntx', type=int, default=3000); b.add_argument('--seeds', type=int, nargs='+', default=[1, 7])
    r = sub.add_parser('route'); r.add_argument('--job', required=True); r.add_argument('--threads', type=int, default=16)
    r.add_argument('--tag', default='claude_su_cp_side_r1')
    s = sub.add_parser('signoff'); s.add_argument('--orfs', required=True); s.add_argument('--output', required=True)
    x = ap.parse_args()
    if x.cmd == 'bench': sys.exit(bench(x.out, x.work, x.cycles, x.ntx, x.seeds))
    if x.cmd == 'route': sys.exit(route(x.job, x.threads, x.tag))
    signoff(x.orfs, x.output)
