"""Retain W19 collective costs after HA2 rejection; no new candidate or gain."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDY = 'results/uarch/hbm_accelerator_study_20261003/ladder_model.py'
TERMINAL = 'results/rtl/hbm_accel_ha2_20261003/terminal_045cc7411.json'
VERDICT = 'results/rtl/hbm_accel_ha2_20261003/measured_composition.json'
OUT = 'results/uarch/hbm_retained_collective_composition_20261003/model.json'


def validate_rejection(terminal, verdict):
    if terminal['source_commit'] != verdict['source_commit']:
        raise ValueError('terminal and composition source differ')
    if (terminal['exact']['gather_verdict'], terminal['exact']['gather_packet_checks'],
            terminal['exact']['gather_mismatches']) != ('PASS', 27648, 0):
        raise ValueError('exact measured snapshot evidence required')
    rows = verdict['rows']
    if len(rows) != 1 or rows[0]['verdict'] != 'REJECT_SNAPSHOT_CANDIDATE' or rows[0]['adopted']:
        raise ValueError('rejected candidate cannot be adopted')
    if rows[0]['contribution_to_adopted_composition'] is not None:
        raise ValueError('rejected HA2 has no composition credit')
    actual = terminal['measurements']['gather']
    if [r['last_ns'] for r in actual] != rows[0]['measured_gather_last_ns']:
        raise ValueError('measurement/verdict disagreement')
    if terminal['measurements']['whole_allreduce_ns'] is not None:
        raise ValueError('new whole collective measurement requires separate source review')
    return actual


def build(root=ROOT):
    root = Path(root)
    blobs = {p: (root / p).read_bytes() for p in (STUDY, TERMINAL, VERDICT)}
    if hashlib.sha256(blobs[STUDY]).hexdigest() != '5266d81b537fe18edd427f853bdb25c6b6533c3c65e7dafc2ac3bedb0378125f':
        raise ValueError('frozen W19 authority changed')
    terminal, verdict = [json.loads(blobs[p]) for p in (TERMINAL, VERDICT)]
    measurements = validate_rejection(terminal, verdict)
    spec = importlib.util.spec_from_file_location('_retained_w19', root / STUDY)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    passes = []
    for P, source in m.VERIFY_PARTS.items():
        parts = dict(source)
        # R0c is the service correction only. Never call or apply the R2 or
        # dependent R3a candidate savings in this active composition.
        boundaries = parts['barrier'] / (m.W19_BOUNDARY_CYC / m.F_FAST * 1e6)
        fetch = m.ROUTED_FETCHES * (m.FETCH_NS['central'] + m.FETCH_CDC_NS + m.FETCH_STALL_NS - m.FETCH_NS['postponed']) / 1000
        fence = boundaries * m.SERVICE_CYC_PER_BOUNDARY / m.F_FAST * 1e6
        assert parts['collective'] > 0
        passes.append(dict(positions=P, retained_W19_parts_us=parts,
            retained_collective_us=parts['collective'], baseline_total_us=sum(parts.values()),
            R0c_first_access_extra_us=fetch, R0c_ACK_fence_owner_extra_us=fence,
            conditional_service_corrected_total_us=sum(parts.values()) + fetch + fence,
            HA2_saving_us=0, dependent_R3a_saving_us=0))
    draft = dict(m.DRAFT_PARTS)
    rows = []
    for context, scale in [('1M', 1.0), ('200K', m.CTX_200K_RATIO)]:
        ar = passes[0]['conditional_service_corrected_total_us'] * scale
        for name, tau_by_gamma in m.TAU.items():
            for gamma, tau in tau_by_gamma.items():
                verify = passes[gamma]['conditional_service_corrected_total_us'] * scale
                draft_us = sum(draft.values()) * scale
                rows.append(dict(context=context, acceptance_dataset=name, gamma=gamma,
                    tau_source_assumption=tau, conditional_AR_us=ar,
                    conditional_verify_us=verify, retained_draft_us=draft_us,
                    conditional_MTP_step_us=verify + draft_us,
                    conditional_AR_tokens_s=1e6/ar,
                    conditional_MTP_tokens_s=tau*1e6/(verify+draft_us)))
    result = dict(schema='opentallas.hbm.retained-collective-composition.v1',
        status='RETAINED_BASELINE_MODEL_HA2_MEASURED_REJECT_NO_ACCELERATOR_GAIN',
        adopted=False, published_accelerator_rate=None, measured_whole_token_rate=None,
        collective_authority='W19 TP96: W15b P48 NVLS fits plus original payload/serialization terms',
        retained_fixed_terms=dict(gather_ns=m.W19_COLL_FIT['ag_fixed_cyc']/m.W19_COLL_FIT['hz']*1e9,
            allreduce_ns=m.W19_COLL_FIT['ar_fixed_cyc']/m.W19_COLL_FIT['hz']*1e9,
            note='already contained in W19 collective subtotals; never add again'),
        retained_AR_collective_count=m.W19_COLL_COUNT,
        verify_passes=passes, retained_draft_parts_us=draft,
        retained_draft_collective_us=draft['collective'], conditional_rows=rows,
        rejected_HA2=dict(source_commit=terminal['source_commit'], measurements=measurements,
            exact_packet_checks=27648, estimated_459ns_eligible=False,
            candidate_550ns_benefit_eligible=False, saving_us=0,
            whole_allreduce_measured=False, CDC_refresh_system_unmeasured=True,
            reason='measured snapshot is slow; reducer elaboration incomplete; no matched payload slope or contextual physical gain'),
        no_gain_for=['HA2/R2 direct links', 'dependent R3a cut-through', 'other unqualified ladder rungs'],
        scope=['retained historical measured-fit composition, not a new full-token measurement',
            'R0c service inputs and 200K scaling remain model assumptions',
            'draft retains original W19 service scope; no accelerated collective fraction applied',
            'current native engine/interface completion and contextual timing remain required'],
        input_sha256={p:hashlib.sha256(b).hexdigest() for p,b in blobs.items()})
    for p in ('tools/hbm_retained_collective_composition.py', 'tools/uarch_model.py'):
        result['input_sha256'][p] = hashlib.sha256((root/p).read_bytes()).hexdigest()
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--verify', action='store_true')
    args = ap.parse_args(); payload = json.dumps(build(), indent=2, sort_keys=True) + '\n'
    p = ROOT / OUT
    if args.verify:
        if p.read_text() != payload: raise ValueError('source/record drift')
    else:
        p.parent.mkdir(parents=True, exist_ok=True); p.write_text(payload)
    print('PASS retained baseline collective pricing; HA2 gain excluded')
