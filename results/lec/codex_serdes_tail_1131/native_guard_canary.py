"""PREP ONLY: cached native guard diagnostic; full comparison defaults OFF.

No matcher, solver, source RTL, reset, or gate changes. Every source invariant
and loaded-field relation must survive the existing simultaneous induction.
"""
import collections
import hashlib
import json
import itertools
import os
import sys
from pathlib import Path

sys.path.insert(0, '/m')
import lec

ROOT = Path('/candidate')
PACKET = json.loads((ROOT / 'candidate.json').read_text())
EVENTS = {'full_equivalence': 'NOT_RUN', 'original_replay_untouched': True}


def save():
    (ROOT / 'events.json').write_text(json.dumps(EVENTS, indent=1) + '\n')


def names_digest(names):
    return hashlib.sha256('\n'.join(sorted(names)).encode()).hexdigest()


def resume(L, work, conflicts, log, *args, **kwargs):
    work = Path(work)
    elements = lec.slang_elements(work / 'gold.aliases.json')
    watched = []
    for unit in range(3):
        base = f'ff:u_dut.u_bound.u_core.u_dec.u_syn.g_bm[{unit}].u_bm'
        watched += [base + '.th[5][50]', base + '.th[5][51]']
        watched += [base + f'.d[2][{bit}]' for bit in range(130, 148)]
    EVENTS['native_source_element_metadata'] = {key: elements.get(key) for key in watched}
    save()
    lec.normalize_gold_elements(L, elements, log)
    lec.json_alias_keys(L, log, work=work)
    lec.slang_element_keys(L, log, work=work)
    lec.alias_arrays(L, log, work=work)
    EVENTS['profile_transfer'] = lec.transfer_profile(
        L, json.loads(Path('/baseline/old_hyp.json').read_text()), log)
    EVENTS['baseline_tail_seed'] = lec.apply_hints(
        L, PACKET['baseline_tail_pairing_to_preserve'], work, conflicts, log,
        propose_only=True)
    lec.noreset_filter(L, log, collections.Counter(), work, conflicts)
    EVENTS['baseline_joint'] = lec.prove_profile(L, work, conflicts, log)
    EVENTS['baseline_tail_retained'] = [
        h for h in PACKET['baseline_tail_pairing_to_preserve']
        if L.hyp.get((h[0], h[1])) == tuple(h[2])]
    save()
    if len(EVENTS['baseline_tail_retained']) != 3:
        raise lec.LecError('original positive tail pairings not reproduced')
    m, _ = L.build(with_compare=True, with_hyp=True)
    baseline = set(m.onames)
    EVENTS['baseline_points'] = len(m.onames)
    EVENTS['baseline_names_sha256'] = names_digest(baseline)
    save()
    if len(m.onames) != 59356 or len(baseline) != 59356:
        raise lec.LecError('original 59356 canonical points not reproduced')
    (ROOT / 'baseline_point_names.json').write_text(json.dumps(sorted(baseline)) + '\n')
    del m

    hints = PACKET['all_hints']
    invariant = PACKET['families']['encoder_header']['control_invariant_candidate']
    # Native cons proposals prove preservation but apply_hints does not check
    # their base. Read the actual native all-X reset propagation before adding
    # the constraint; never assume the source reset assignments were reached.
    if not hasattr(L, 'rst_val'):
        lec.noreset_classify(L)
    reset_values = [L.rst_val.get(('gold', key), (None, None))[0]
                    for key in invariant[2]]
    possible = list(itertools.product(*[
        [v] if v in (0, 1) else [0, 1] for v in reset_values]))
    allowed = {tuple(row) for row in invariant[3]}
    outside = [list(row) for row in possible if row not in allowed]
    EVENTS['encoder_cons_reset_base'] = {
        'native_values': dict(zip(invariant[2], reset_values)),
        'possible_assignments': len(possible), 'outside_allowed': outside,
        'source_expected': [0, 0, 0, 0, 0]}
    save()
    if outside or reset_values != [0, 0, 0, 0, 0]:
        raise lec.LecError('native reset state does not establish encoder invariant base')
    EVENTS['control_invariant_seed'] = lec.apply_hints(
        L, [invariant], work, conflicts, log, propose_only=True)
    EVENTS['positive_seed'] = lec.apply_hints(
        L, hints, work, conflicts, log, propose_only=True)
    save()
    if EVENTS['control_invariant_seed']['applied'] != 1:
        raise lec.LecError('source control invariant was not accepted as candidate')
    if EVENTS['positive_seed']['applied'] != 10:
        raise lec.LecError('all ten source loaded candidates were not accepted')
    snapshot = dict(L.hyp)
    EVENTS['controls'] = {}
    for family, spec in PACKET['families'].items():
        controls = spec['native_controls']
        event = EVENTS['controls'][family] = {}
        event['reset_true_guard'] = lec.apply_hints(
            L, [controls['reset_true_guard']], work, conflicts, log, propose_only=True)
        save()
        if (event['reset_true_guard']['applied'] or
                len(event['reset_true_guard']['loaded_refused']) != 1):
            raise lec.LecError(f'{family}: reset-live guard did not refuse')
        L.hyp = dict(snapshot)
        wrong = controls['wrong_constant']
        event['wrong_constant_seed'] = lec.apply_hints(
            L, [wrong], work, conflicts, log, propose_only=True)
        if event['wrong_constant_seed']['applied'] != 1:
            raise lec.LecError(f'{family}: wrong constant control not exercised')
        m, _ = L.build(with_compare=False, with_hyp=True)
        name = 'hyp:gold:' + wrong[1]
        index = m.onames.index(name)
        m.outs = [m.outs[index]]
        m.onames = [name]
        target = ROOT / ('negative_' + family)
        target.mkdir(exist_ok=True)
        event['wrong_constant_status'] = lec.prove(
            m, target, conflicts, log, tag='wrong_constant', single_cap=1)
        save()
        if event['wrong_constant_status'].get(name) != 'differs':
            raise lec.LecError(f'{family}: native wrong constant did not differ')
        del m
        L.hyp = dict(snapshot)

    EVENTS['joint'] = lec.prove_profile(L, work, conflicts, log)
    EVENTS['loaded_retained'] = [
        h[1] for h in hints
        if L.hyp.get((h[0], h[1]), (None,))[0] == 'loaded']
    save()
    if EVENTS['joint']['dropped'] or len(EVENTS['loaded_retained']) != 10:
        raise lec.LecError('new/saved profile did not remain jointly inductive')
    m, _ = L.build(with_compare=True, with_hyp=True)
    EVENTS['final_points'] = len(m.onames)
    EVENTS['missing_baseline_points'] = sorted(baseline - set(m.onames))
    EVENTS['final_names_sha256'] = names_digest(set(m.onames))
    save()
    if EVENTS['missing_baseline_points']:
        raise lec.LecError('original canonical comparison points were lost')
    # Preserve the actual surviving profile for a later canonical continuation.
    # These files confer no trust: the continuation must repeat native reset
    # base checks and joint induction before using them, including cons base.
    (ROOT / 'surviving_hyp.json').write_text(json.dumps([
        [side, key, list(hint)] for (side, key), hint in sorted(L.hyp.items())]) + '\n')
    (ROOT / 'surviving_cons.json').write_text(json.dumps([
        ['cons', side, list(keys), list(allowed)]
        for side, keys, allowed in L.cons]) + '\n')
    del m
    if os.environ.get('HEAD_FULL_COMPARE') != '1':
        EVENTS['verdict'] = 'NATIVE_GUARD_DIAGNOSTIC_COMPLETE_ONLY'
        save()
        print(json.dumps(EVENTS), flush=True)
        raise SystemExit(0)


lec.PROVE_JOBS = 4
lec.correspond = resume
try:
    result = lec.check('/work', out='/out', reuse=True)
    EVENTS['full_equivalence'] = result.get('verdict')
    EVENTS['canonical_final'] = {
        k: result.get(k) for k in ('verdict', 'counts', 'reason', 'reset_contract', 'kept_registers')}
    save()
    print(json.dumps(EVENTS), flush=True)
    sys.exit(0 if result.get('verdict') == 'EQUIVALENT' else 1)
except Exception as error:
    EVENTS['error'] = repr(error)
    save()
    raise
