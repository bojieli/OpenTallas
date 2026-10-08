#!/usr/bin/env python3
"""Price pinned production-parent measurements in the existing timing composer.

Conditional, default-off analytical composition only. Reuses the completed
exact/integration measurements; never runs RTL or writes adopted lever records.
"""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import dsrom_1m_allmeasured as A
import dsrom_reindex_parent_model as U

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'results/rtl/dsrom_reindex_parent_20261005'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def compose():
    gate_path = EVIDENCE / 'gather_r8_PASS/gather.json'
    integration_path = EVIDENCE / 'integration_r9_PASS/record.json'
    gate, integration = json.loads(gate_path.read_text()), json.loads(integration_path.read_text())
    assert gate['status'] == 'pass' and gate['backpressure']['pass_']
    assert len(gate['runs']) == 20
    assert integration['pass'] and len(integration['runs']) == 6
    for name, expected in gate['source_sha256'].items():
        if name.endswith('.sv') or name.endswith('.v'):
            assert sha(ROOT / name) == expected, 'source changed: ' + name
    old_path = A.RC / 'gather.json'
    kc8_path = ROOT / 'results/rtl/dsrom_reindex_kc8_20261005/gate_PASS/gather.json'
    old = json.loads(old_path.read_text())['worst_rank']['cycles']
    # The retained KC8 record is a component reference, not the adopted input.
    kc8_record = json.loads(kc8_path.read_text())
    assert kc8_record['status'] == 'pass'
    kc8 = kc8_record['worst_rank']['cycles']
    cycles = gate['worst_rank']['cycles']
    assert (old, kc8, cycles) == (757, 738, 739)
    model = U.model()
    assert model['area']['control_cell_cap_um2'] == 37452.2 and not model['default_enabled']
    args = lambda: SimpleNamespace(rec=A.REC, out=None, baseline='recovery', recovery=A.RECOVERY,
                                    window='s81', hop_tier='light_fec')
    before = A.compose(args(), write_output=False)
    changed = {}

    def price(value):
        rows = []
        def hook(g, patcher, base_patches, info):
            for layer in A.M.REINDEX:
                name = f'L{layer}.attn.idx.score'
                nd = g.nodes[name]
                # _apply already accounts for gather, scorer settle/latency;
                # later streaming-domain pipeline costs stay in this node.
                assert 'wire_in' not in nd and 'wire_out' not in nd
                current = nd['issue'] + nd['depth'] + nd['ctrl']
                replacement = current + (value-old)/A.M.CLK
                patcher.put(name, replacement,
                    f'defaultOFF production gather {value} vs composer input {old} cycles; all scorer/streaming/CDC terms retained')
                rows.append(dict(node=name, gather_cycles=value, composer_gather_cycles=old,
                                 before_us=current*1e6, after_us=replacement*1e6,
                                 gather_delta_cycles=value-old))
        record = A.compose(args(), graph_hook=hook, write_output=False)
        changed[str(value)] = rows
        return record

    reference, parent = price(kc8), price(cycles)
    # Verify the +1-cycle charge survives composition, without charging it on
    # top of the still-adopted 757-cycle reader or changing any other nodes.
    for r, p in zip(changed[str(kc8)], changed[str(cycles)]):
        assert abs((p['after_us']-r['after_us'])-1e6/A.M.CLK) < 1e-10
    same_rank = {r['name']: r for r in integration['runs']}
    off, on = same_rank['default_off_r3'], same_rank['parent_slots_r3']
    observed = [dict(job=a['job'], position=a['pos'], default_off_done=a['done'],
                     parent_done=b['done'], observed_delta_cycles=b['done']-a['done'],
                     keys=a['keys']) for a,b in zip(off['job'],on['job'])]
    pins = [gate_path, integration_path, old_path, kc8_path, ROOT/'tools/dsrom_reindex_parent_compose.py',
            ROOT/'tools/dsrom_reindex_parent_model.py', ROOT/'tools/uarch_model.py']
    return dict(default_enabled=False, adopted=False, parent_qualified=False,
        physical_status='route_r9 pending; component reports cannot substitute full-parent qualification',
        cap_um2=37452.2, period_ps=833.333, SS_setup_uncertainty_ps=60, FF_hold_uncertainty_ps=25,
        input_sha256={str(p.relative_to(ROOT)):sha(p) for p in pins},
        baseline_composer_inputs=before['inputs'], composer_tools=before['tool_sha256'],
        measured_gather_cycles=cycles, retained_KC8_cycles=kc8, composer_production_input_cycles=old,
        added_cycles_vs_KC8=cycles-kc8, gather_delta_cycles_vs_production=cycles-old,
        reindex_nodes=changed[str(cycles)], token_component_delta_vs_KC8_us=4e6/A.M.CLK,
        same_rank_stage_observations=observed,
        stage_scope='Existing two-job fullshape directed stage measurements: scorer stand-in, unchanged golden mdrop/globalIDs; no fresh replay and no native S81 qualification',
        stage_delta_is_not_assumed_one_cycle=True,
        baseline=dict(AR_us=before['AR_us'], MTP=before['MTP']),
        conditional_KC8_reference=dict(AR_us=reference['AR_us'], MTP=reference['MTP']),
        conditional_production_parent=dict(AR_us=parent['AR_us'], MTP=parent['MTP']))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    assert not a.out.exists(), 'preserve original records'
    rec = compose()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=2) + '\n')
    print(json.dumps({k:rec[k] for k in ('measured_gather_cycles','added_cycles_vs_KC8','gather_delta_cycles_vs_production','cap_um2','token_component_delta_vs_KC8_us','same_rank_stage_observations')}, indent=2))
