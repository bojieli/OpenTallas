"""Fail-closed LEC and extracted-clock insertion gates for modern legacy kits.

Invoked inside the kit's admitted ORFS container. Old receipts are retained;
only a newly produced EQUIVALENT or TT+FF global-routing PASS can advance.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
# The generated runner invokes this standalone kit tool with Python -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))


def retain(path):
    if path.exists():
        path.rename(path.with_name(path.name + f'.previous.{time.time_ns()}'))


def load(path):
    receipt = json.loads(path.read_text())
    if not isinstance(receipt, dict):
        raise ValueError(f'malformed gate receipt: {path}')
    return receipt


# S81-CORES-R25 10-27 (LEC-FPREG-4 ask b): per-kit LEC settings a recipe may set in config.mk.  Allowlist only;
# OT_LEC_RAW_BASE_STEPS = finite-prefix base cases (c6e4bfa53; each prefix constant is proved, never assumed).
# OT_LEC_RESET_CYCLES is NOT here: lec.py gates it on KIT/reset_contract.json.
LEC_ENV_KEYS = {'OT_LEC_RAW_BASE_STEPS': (0, 16)}


def lec_env(kit):
    cfg = Path(kit) / 'config.mk'
    text = cfg.read_text() if cfg.is_file() else ''
    env = {}
    for key, (lo, hi) in LEC_ENV_KEYS.items():
        found = re.findall(r'^export\s+' + key + r'\s*=\s*(\S+)\s*$', text, re.M)
        if len(found) > 1:
            raise ValueError(f'{key} set {len(found)} times in config.mk')
        if found:
            if not re.fullmatch(r'\d+', found[0]) or not lo <= int(found[0]) <= hi:
                raise ValueError(f'{key} = {found[0]!r} outside {lo}..{hi}')
            env[key] = found[0]
    # DIE-S81-85 11-09: the kit's recorded proof policy (KIT/lec_options.json, gen_core_kit_legacy / gen_phys) beats an
    # unset shell; a shell value that differs from the kit is refused (the same rule as lec_async.sh kit_lec_options).
    opt = Path(kit) / 'lec_options.json'
    if opt.is_file():
        d = json.loads(opt.read_text())
        if not isinstance(d, dict) or set(d) != {'superset_vec'} or type(d['superset_vec']) is not bool:
            raise ValueError('lec_options.json must be exactly {"superset_vec": bool}')
        want = '1' if d['superset_vec'] else '0'
        have = os.environ.get('OT_LEC_SUPERSET_VEC')
        if have not in (None, '') and (have == '1') != (want == '1'):
            raise ValueError(f'OT_LEC_SUPERSET_VEC={have} differs from the kit proof policy lec_options.json ({want})')
        if want == '1':
            env['OT_LEC_SUPERSET_VEC'] = '1'
    return env


def policy_context(kit, base, settings):
    """Use sign-off's existing core/partition IO references and typed hold context."""
    import signoff as so
    disc = so.discover(base, kit=kit, sdc=kit / 'constraint.sdc')
    ctx = load(Path(disc['sdc_lint_ctx'])) if disc.get('sdc_lint_ctx') else {}
    core = so.hard_core_latency_contract(disc)
    ff = ctx.get('insertion_ff_ps')
    if ff is None:
        raise ValueError('G2 has no declared per-corner FF reference; regenerate the kit')
    ff = float(ff) / float(ctx.get('time_unit_ps') or 1.0)
    if not math.isfinite(ff) or ff <= 0:
        raise ValueError('G2 declared FF reference is not positive and finite')
    tt = float(ctx['insertion_ps']) / float(ctx.get('time_unit_ps') or 1.0)
    if any(not math.isfinite(value) or abs(value-float(settings[key])) > 1e-6
           for key, value in (('OT_VCLK_TT', tt), ('OT_VCLK_FF', ff))):
        raise ValueError('G2 declared IO references disagree with the actual kit corner bindings')
    mode = 'bound-ff' if core else 'rebind'
    policy = dict(ff_vclk=mode, ff_vclk_bound_ps=ff if core else None)
    if not core:
        policy['insertion_bound'] = dict(tt=float(ctx['insertion_ps']), ff=ff,
                                        tol=float(ctx.get('insertion_tol_ps', so.INSERTION_TOL_PS)))
    return disc, ctx, policy


def hold_ff_blocks(kit):
    """FLOW-30 11-04 (COORD 06:35 (1), OWNER 11-03 only sign-off blocks): G2 hold_ff at GRT is ADVISORY, measured and
    recorded in grt_policy.json; routed FF hold at sign-off decides.  'export OT_G2_HOLD_GATE = 1' restores the stop."""
    cfg = Path(kit) / 'config.mk'
    text = cfg.read_text() if cfg.is_file() else ''
    return (os.environ.get('OT_G2_HOLD_GATE') == '1'
            or re.search(r'^export\s+OT_G2_HOLD_GATE\s*=\s*1\s*$', text, re.M) is not None)


SETUP_CONTINUE_PS = 50.0


def setup_continue_ps(kit):
    """KW-FIX-16 11-05 (COORD class G2-TT-SETUP, OWNER 11-03 targets not gates): a G2 TT setup miss on GRT RC no worse
    than this many ps is ADVISORY -- the kit routes on and routed sign-off (with its post-route repair) decides; a
    deeper miss is structural and still stops before the pair census.  Measured 11-05 wave: small misses -5.7/-7.08/
    -44.24 ps, structural ones -92 ps and worse.  'export OT_G2_SETUP_GATE = 1' (env or config.mk) restores the old
    stop at any negative WNS; 'export OT_G2_SETUP_CONTINUE_PS = <ps>' moves the window."""
    cfg = Path(kit) / 'config.mk'
    text = cfg.read_text() if cfg.is_file() else ''
    def get(key):
        found = re.findall(r'^export\s+' + key + r'\s*=\s*(\S+)\s*$', text, re.M)
        return os.environ.get(key, found[-1] if found else None)
    if get('OT_G2_SETUP_GATE') == '1':
        return 0.0
    raw = get('OT_G2_SETUP_CONTINUE_PS')
    try:
        value = SETUP_CONTINUE_PS if raw is None else float(raw)
    except ValueError:
        raise ValueError(f'OT_G2_SETUP_CONTINUE_PS not a number: {raw!r}')
    if not math.isfinite(value) or value < 0:
        raise ValueError(f'OT_G2_SETUP_CONTINUE_PS must be finite and >= 0: {raw!r}')
    return value


def policy_session(kit, corner, base, disc, ctx, policy):
    """Append the existing signoff policy to the already loaded GRT session.

    postcts_gate loads exact libraries, calibrated RC, SDC, FF core-tap overlay,
    propagated clocks and global-route parasitics. Do not load or estimate them
    again. The standard IO overlay, forwarded-ring/FT exclusions and exhaustive
    CPPR pair census are generated by signoff.py, not a second local policy.
    """
    import signoff as so
    ftd = load(Path(disc['ft_ports'])) if disc.get('ft_ports') else None
    target = so.pair_target_file(disc, corner.lower())
    text = so.session_tcl(corner.lower(), [], False, ff_vclk=policy['ff_vclk'],
        ff_bound_ps=policy.get('ff_vclk_bound_ps'), ft_decl=ftd,
        hold_in_min=ctx.get('hold_in_min_ps'), hold_out_min=ctx.get('hold_out_min_ps'),
        hold_in_min_ports=ctx.get('hold_in_min_ports_ps'),
        hold_out_min_ports=ctx.get('hold_out_min_ports_ps'), tap_window=ctx.get('tap_window_ps'),
        pair_targets=target is not None, fwd_ring=so.fwd_ring_inputs((kit/'constraint.sdc').read_text()))
    anchor = 'so DESIGN [current_design]'
    if text.count(anchor) != 1:
        raise ValueError('signoff G2 session anchor changed')
    definitions = so.SESSION_TCL.split('@TIMING_LIBRARIES@', 1)[0]
    tail = text[text.index(anchor):]
    # A known blocking data failure cannot reach DRT; do not spend a full pair census
    # on a rejected prototype. Positive candidates still require both censuses.
    # FF hold is advisory (hold_ff_blocks): the session runs on to the pair census.
    # TT setup: only a miss deeper than setup_continue_ps stops (KW-FIX-16); a small miss runs on to the census.
    stop = ''
    if corner == 'TT':
        thr = setup_continue_ps(kit)
        stop = ('set ot_g2_wns [so_ps [sta::worst_slack_cmd max]]\n'
                f'if {{$ot_g2_wns ne "nan" && $ot_g2_wns < {-thr:.2f}}} {{\n'
                '  so G2_REQUIRED_FAIL setup_tt\n  so DONE 1\n  exit\n}\n')
    elif hold_ff_blocks(kit):
        stop = ('if {[sta::worst_slack_cmd min] < 0} {\n'
                '  so G2_REQUIRED_FAIL hold_ff\n'
                '  so DONE 1\n  exit\n}\n')
    if tail.count('so_timing STD\n') != 1:
        raise ValueError('signoff standard-overlay timing anchor changed')
    tail = tail.replace('so_timing STD\n', 'so_timing STD\n' + stop)
    out = kit / 'grt_policy' / corner.lower()
    out.mkdir(parents=True, exist_ok=True)
    tail = tail.replace('/out/', str(out) + '/')
    if target is not None:
        tail = tail.replace('/sdc/pair_targets.txt', str(target))
    return (f'source {{{kit / "postcts_gate.tcl"}}}\n'
            'if {$ot_pg_mode ne "global_routing"} {error "G2 policy requires global-route RC"}\n'
            + definitions + f'so CORNER {corner}\nso PARASITICS global_routing\n' + tail)


def unexpanded_child_clock_advisory(clock):
    """Pre-signoff only: measured raw pairs pass; child ETMs await their tag."""
    coverage = clock.get('endpoint_model_coverage') or {}
    return (clock.get('verdict') == 'NOT RUN' and clock.get('raw_clock_verdict') == 'PASS'
            and all(isinstance(coverage.get(c), dict) and
                    (coverage[c].get('verdict') == 'PASS' or
                     (coverage[c].get('verdict') == 'NOT RUN' and
                      coverage[c].get('status') == 'UNEXPANDED_CHILD_ETM')) for c in ('tt', 'ff'))
            and any(coverage[c].get('status') == 'UNEXPANDED_CHILD_ETM' and
                    coverage[c].get('verdict') == 'NOT RUN' for c in ('tt', 'ff')))


def policy_record(corners, policy, hold_blocks=False, setup_continue=0.0):
    """Apply the existing sign-off setup/standard-hold/pair-skew checks only.  A measured hold_ff FAIL is advisory unless
    hold_blocks; a measured setup_tt FAIL no worse than -setup_continue ps is advisory (KW-FIX-16); NOT RUN (standard
    overlay not applied, no FF reference) still stops; only the pre-signoff child ETM metadata case is advisory."""
    import signoff as so
    for c in ('tt', 'ff'):
        x = corners[c]
        if not x.get('done') or x.get('parasitics') != 'global_routing':
            raise ValueError(f'{c.upper()} G2 policy session incomplete or not global-route RC')
        if not x.get('periods') or any(not math.isfinite(float(v)) or abs(float(v)-so.PERIOD_PS)>1e-6
                                       for v in x['periods'].values()):
            raise ValueError(f'{c.upper()} G2 policy clock period differs from 833 ps')
        for key in ('sdc_wns_max', 'std_wns_max', 'std_wns_min'):
            if x.get(key) is None or not math.isfinite(float(x[key])):
                raise ValueError(f'{c.upper()} G2 {key} NOT RUN/nonfinite')
        for name in ('insertion_pinflops', 'insertion_all'):
            measurement = x.get(name) or {}
            if not measurement.get('n') or any(measurement.get(key) is None
                    or not math.isfinite(float(measurement[key])) for key in ('min', 'max', 'mean')):
                raise ValueError(f'{c.upper()} G2 {name} NOT RUN/nonfinite')
        if x.get('ck_errors') is None or not math.isfinite(float(x['ck_errors'])):
            raise ValueError(f'{c.upper()} G2 clock arrival coverage NOT RUN/nonfinite')
        ps = x.get('pair_skew') or {}
        missing = (ps.get('counts') or {}).get('no_clock_arrival')
        if missing is None or not math.isfinite(float(missing)) or missing < 0:
            raise ValueError(f'{c.upper()} G2 pair coverage NOT RUN/nonfinite')
        for k in ('max', 'min'):
            ck = ps.get('checks', {}).get(k, {})
            for key in ('n', 'worst_abs_ps', 'verify_ps'):
                if ck.get(key) is None or not math.isfinite(float(ck[key])):
                    raise ValueError(f'{c.upper()} G2 pair {k} {key} NOT RUN/nonfinite')
            if ck['n'] <= 0 or ck['worst_abs_ps'] < 0 or ck['verify_ps'] < 0:
                raise ValueError(f'{c.upper()} G2 pair {k} malformed counts/skew')
    rec = dict(corners=corners, policy=policy)
    so.evaluate(rec)
    wanted = {k: rec['checks'][k] for k in ('setup_tt', 'hold_ff')}
    # Insertion is already checked above under the exact gate/info contract.
    # Reuse sign-off's pair checker without introducing another mean band.
    clock_rec = dict(corners=corners, policy={k:v for k,v in policy.items() if k != 'insertion_bound'})
    so.evaluate(clock_rec)
    wanted['clock'] = clock_rec['checks']['clock']
    # This is a G2 prototype receipt, never a SIGNED record: DRC/antenna and
    # routed sign-off are deliberately not claimed or required here.
    advisory = [] if hold_blocks else ['hold_ff']
    if unexpanded_child_clock_advisory(wanted['clock']):
        advisory.append('clock')  # COORD05:01: routed sign-off still qualifies child ETMs.
    st = wanted['setup_tt']
    w = st.get('wns_ps')
    if (st['verdict'] == 'FAIL' and setup_continue > 0 and w is not None and math.isfinite(float(w))
            and float(w) >= -setup_continue):
        advisory.append('setup_tt')
    return dict(schema='opentallas.grt_policy.v1', parasitics='global_routing',
                policy=dict(period_ps=so.PERIOD_PS, uncertainty_setup_ps=so.UNC_SETUP_PS,
                            uncertainty_hold_ps=so.UNC_HOLD_PS, pair_skew_max_ps=so.PAIR_SKEW_MAX_PS,
                            setup_continue_ps=setup_continue, **policy),
                checks=wanted, advisory=advisory,
                verdict='PASS' if all(x['verdict']=='PASS' or (k in advisory and (x['verdict']=='FAIL' or
                                        (k == 'clock' and unexpanded_child_clock_advisory(x))))
                                      for k, x in wanted.items()) else 'FAIL')


GRT_LAYER_RE = re.compile(r'\[INFO GRT-0021\] Max routing layer:\s*(\S+?)\.?\s*$', re.M)
CFG_LAYER_RE = re.compile(r'^\s*(?:override\s+)?(?:export\s+)?MAX_ROUTING_LAYER\s*[:?]?=\s*(\S+)\s*$', re.M)


def grt_layer_check(kit):
    """KW-FIX-30 11-07 (COORD 14:48, DIE-QC-90 NK vR5b): GRT reads the routing layer stored in the ODB at floorplan, so a
    MAX_ROUTING_LAYER raised or lowered in config.mk after floorplan is silently ignored (do-route ran GRT at M6 with
    config.mk M7).  -> None (config.mk names no layer: nothing to compare), else {config, grt, log}; raises ValueError
    when 5_1_grt.log has no GRT-0021 line or its layer differs from config.mk (fail closed)."""
    kit = Path(kit)
    try:
        cfg = (kit / 'config.mk').read_text(errors='replace')
    except OSError:
        return None
    want = CFG_LAYER_RE.findall(cfg)
    if not want:
        return None
    want = want[-1]
    logs = sorted((kit / 'run/logs/asap7').glob('*/base/5_1_grt.log'))
    if not logs:
        raise ValueError(f'GRT layer check: no 5_1_grt.log (config.mk MAX_ROUTING_LAYER {want})')
    got = GRT_LAYER_RE.findall(logs[-1].read_text(errors='replace'))
    if not got:
        raise ValueError(f'GRT layer check: {logs[-1].name} has no GRT-0021 Max routing layer line')
    if got[-1] != want:
        raise ValueError(f'GRT-0021 Max routing layer {got[-1]} != config.mk MAX_ROUTING_LAYER {want}: the ODB keeps '
                         f'the floorplan layer; set the layer at floorplan and rebuild from floorplan')
    return dict(config=want, grt=got[-1], log=str(logs[-1]))


def run(kit, stage, netlist=None, execute=subprocess.run):
    kit = Path(kit)
    marker = kit / ('FAIL_PREFLOOR' if stage == 'lec' else 'FAIL_POSTCTS')
    timing_receipt = kit / 'grt_policy.json' if stage == 'grt' else None
    try:
        if stage == 'lec':
            netlist = Path(netlist)
            tool = kit / 'lec.py'
            if not tool.is_file() or not netlist.is_file():
                raise ValueError('missing LEC tool or synthesized netlist')
            out = kit / 'lec'
            out.mkdir(exist_ok=True)
            receipt = out / 'lec.json'
            retain(receipt)
            log = kit / 'lec_run.log'
            retain(log)
            env = dict(os.environ, **lec_env(kit))
            with log.open('w') as stream:
                result = execute([sys.executable, '-I', str(tool), str(kit), '--netlist', str(netlist),
                                  '--out', str(out)], stdout=stream, stderr=subprocess.STDOUT, env=env)
            verdict = load(receipt).get('verdict')
            if result.returncode != 0 or verdict != 'EQUIVALENT':
                raise ValueError(f'LEC {verdict}, exit {result.returncode}')
            print('OT_LEGACY_GATE LEC EQUIVALENT')
            return 0
        if stage != 'grt':
            raise ValueError(f'unknown gate {stage}')
        layer = grt_layer_check(kit)
        if layer:
            print(f'OT_LEGACY_GATE GRT layer {layer["grt"]} = config.mk MAX_ROUTING_LAYER')
        candidates = list((kit / 'run/results/asap7').glob('*/base/5_1_grt.odb'))
        if len(candidates) != 1:
            raise ValueError('expected exactly one real 5_1_grt.odb')
        config = (kit / 'config.mk').read_text()
        settings = {}
        for key in ('OT_VCLK_TT', 'OT_VCLK_FF', 'LAYER_PARASITICS_FILE'):
            matches = re.findall(r'^export\s+' + key + r'\s*=\s*(\S+)\s*$', config, re.M)
            if len(matches) != 1:
                raise ValueError(f'missing or ambiguous {key}')
            settings[key] = matches[0]
        if any(not math.isfinite(float(settings[k])) or float(settings[k]) <= 0
               for k in ('OT_VCLK_TT', 'OT_VCLK_FF')):
            raise ValueError('nonpositive corner insertion bound')
        rc_path = Path(settings['LAYER_PARASITICS_FILE'])
        # /work is the canonical mounted kit path in production; tests may use
        # a temporary kit directory with the same generated config contents.
        rc_file = kit / rc_path.relative_to('/work') if rc_path.is_relative_to('/work') else rc_path
        if not rc_file.is_file():
            raise ValueError('missing configured calibrated RC file')
        if not (kit / 'postcts_gate.tcl').is_file():
            raise ValueError('missing postcts gate')
        import core_clock_band
        band_policy = core_clock_band.band_policy(kit)
        import signoff as so
        disc, ctx, policy = policy_context(kit, candidates[0].parent, settings)
        retain(timing_receipt)
        corners = {}
        for corner in ('TT', 'FF'):
            receipt = kit / f'postcts_gate_{corner.lower()}.json'
            log = kit / f'postcts_gate_{corner}.log'
            retain(receipt)
            retain(log)
            env = dict(os.environ, **settings, OT_POSTCTS_GRT='1', OT_CORNER=corner,
                       ODB=str(candidates[0]), OT_POSTCTS_TOL='20.0')
            session = kit / f'grt_policy_{corner.lower()}.tcl'
            retain(session)
            session.write_text(policy_session(kit, corner, candidates[0].parent, disc, ctx, policy))
            with log.open('w') as stream:
                result = execute(['openroad', '-exit', str(session)],
                                 env=env, stdout=stream, stderr=subprocess.STDOUT)
            d = load(receipt)
            numeric = [float(d[k]) for k in ('bound_ps', 'dev_ps', 'tol_ps', 'pinreg_mean_ps')]
            band_info = (band_policy == 'info' and d.get('band_policy') == 'info'
                         and d.get('band_verdict') == 'INFO')
            band_ok = (d['dev_ps'] <= d['tol_ps']
                       and abs(d['pinreg_mean_ps'] - d['bound_ps']) <= d['tol_ps'])
            # KW-FIX-4 / OWNER 11-03 (only sign-off blocks): a measured band miss the gate marked ADVISORY is reported
            # and the route continues; OT_POSTCTS_BAND_GATE=1 (seen by postcts_gate.tcl too) restores the blocking band.
            band_adv = (os.environ.get('OT_POSTCTS_BAND_GATE') != '1' and d.get('band_verdict') == 'ADVISORY'
                        and not band_ok)
            if band_adv:
                print(f'OT_LEGACY_GATE ADVISORY {corner} insertion band dev {d["dev_ps"]:.2f} > tol {d["tol_ps"]:.1f} '
                      f'(mean {d["pinreg_mean_ps"]:.2f} bound {d["bound_ps"]:.2f}; not a gate, sign-off decides)')
            if (not all(math.isfinite(v) for v in numeric) or not 0 <= d['dev_ps'] or not 0 <= d['tol_ps'] <= 20.0
                    or not (band_ok or band_info or band_adv)
                    or result.returncode != 0 or d.get('verdict') != 'PASS' or d.get('corner') != corner
                    or d.get('parasitics') != 'global_routing' or d.get('pinreg_n', 0) <= 0
                    or abs(float(d['bound_ps']) - float(settings[f'OT_VCLK_{corner}'])) > 1e-6):
                raise ValueError(f'{corner} global-routing insertion gate failed: {d.get("verdict")} exit {result.returncode}')
            measured = so.parse_session(log.read_text(errors='replace'))
            parsed = so.corner_result(measured)
            if measured['kv'].get('G2_REQUIRED_FAIL'):
                key = measured['kv']['G2_REQUIRED_FAIL']
                # KW-FIX-37 11-08 (COORD, OWNER 11-03 only sign-off blocks): a deep G2 setup miss is logged and the kit routes
                # on; routed sign-off decides.  OT_G2_SETUP_GATE=1 restores the stop; a hold_ff stop stays the blocking mode.
                blocking = key != 'setup_tt' or setup_continue_ps(kit) == 0.0
                fail = dict(schema='opentallas.grt_policy.v1', verdict='FAIL' if blocking else 'ADVISORY',
                            parasitics='global_routing', failed=key, corner=corner,
                            setup_wns_ps=parsed.get('std_wns_max'), hold_wns_ps=parsed.get('std_wns_min'),
                            clock='NOT RUN (data failure stopped redundant pair census)')
                timing_receipt.write_text(json.dumps(fail, indent=1) + '\n')
                if not blocking:
                    print(f'OT_LEGACY_GATE ADVISORY G2 {key} setup WNS {parsed.get("std_wns_max")} ps at global-route RC, '
                          'pair census skipped (not a gate, sign-off decides)')
                    return 0
                raise ValueError(f'G2 {key} failed before pair census: {fail}')
            parsed['clock_endpoint_coverage'] = so.consumed_clock_model_coverage(
                kit / f'postcts_gate_{corner.lower()}.libraries.json', disc,
                parsed.get('clock_endpoint_masters'), parsed.get('clock_endpoint_mapping_errors'))
            corners[corner.lower()] = parsed
        result = policy_record(corners, policy, hold_ff_blocks(kit), setup_continue_ps(kit))
        timing_receipt.write_text(json.dumps(result, indent=1) + '\n')
        for k in result['advisory']:
            if (result['checks'][k]['verdict'] == 'FAIL' or
                    (k == 'clock' and unexpanded_child_clock_advisory(result['checks'][k]))):
                print(f'OT_LEGACY_GATE ADVISORY G2 {k} {so._detail(k, result["checks"][k])} (not a gate, sign-off decides)')
        if result['verdict'] != 'PASS':
            why = '; '.join(f'{k}: {v["verdict"]} {so._detail(k, v)}'
                            for k, v in result['checks'].items()
                            if v['verdict'] != 'PASS' and not (k in result['advisory'] and v['verdict'] == 'FAIL'))
            raise ValueError(f'G2 timing policy failed: {why}')
        print('OT_LEGACY_GATE GRT TT/FF insertion + standard timing + CPPR pair skew PASS')
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        with marker.open('a') as stream:
            stream.write(f'legacy {stage} gate: {error}\n')
        print(f'OT_LEGACY_GATE {stage} FAIL: {error}', file=sys.stderr)
        return 5 if stage == 'lec' else 6


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('kit')
    p.add_argument('stage', choices=('lec', 'grt'))
    p.add_argument('--netlist')
    a = p.parse_args()
    return run(a.kit, a.stage, a.netlist)


if __name__ == '__main__':
    raise SystemExit(main())
