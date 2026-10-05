"""Architecture reference only: fail-closed, single-entry L0 QK-to-PV retention."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def canonical(desc):
    if desc['layer'] != 0 or desc['mode'] != 'WINDOW_FP8' or desc['pos'] < 127:
        return None
    roles = {'qk': dict(ts=512, ks=1, k=512, nout=128, tiles=4),
             'pv': dict(ts=1, ks=32, k=128, nout=512, tiles=16)}
    fields = roles.get(desc['role'])
    if fields is None or any(desc[k] != v for k, v in fields.items()):
        return None
    if desc['js'] != 0 or desc['hg'] != 1 or not desc['mmode'] or desc['wbase'] != 0:
        return None
    return tuple(desc[k] for k in ('user', 'layer', 'pos', 'region_base', 'region_count', 'stack', 'step_epoch', 'source_epoch', 'mode')) + (desc['pos']-127, 128, 15)


class Retention:
    """One line, no contexts or mutable rows shared during a replay."""
    def __init__(self):
        self.key = None
        self.armed = False

    def invalidate(self):
        self.key = None
        self.armed = False

    def complete_qk(self, desc, *, complete_rows, engine_idle, drained, fault=False):
        self.invalidate()
        key = canonical(desc)
        if desc['role'] == 'qk' and key and complete_rows == 128 and engine_idle and drained and not fault:
            self.key, self.armed = key, True

    def accept_pv(self, desc, *, drained, mutation_pending, fresh_generation):
        hit = self.armed and desc['role'] == 'pv' and canonical(desc) == self.key and drained and not mutation_pending and fresh_generation
        self.invalidate()  # single-use; a miss takes ordinary refill, never readiness
        return bool(hit)


def build():
    path = 'results/rtl/hdc_v41x_fullshape_program_bind_rope_hbm.json'
    program = json.loads((ROOT/path).read_text())['instruction_trace']
    qk = next(x for x in program if x['tag'] == 'L0.scores')
    pv = next(x for x in program if x['tag'] == 'L0.pv')
    between = [x for x in program if qk['pc'] < x['pc'] < pv['pc']]
    assert not any({'KT0', 'KR0', 'KVQ'} & set(x['writes']) for x in between)
    assert not any(x['unit'] == 2 and x['fields'].get('dst') in (2,3) for x in between)
    sources = [path, 'rtl/chip/ot_chip_v41x_attn_desc_lifecycle.sv',
               'rtl/chip/ot_chip_v41x_window_kv_prefetch.sv',
               'rtl/chip/ot_chip_v41x_window_refill_schedule.sv',
               'rtl/chip/ot_chip_v41x_die.sv', 'tools/v41_window_retention_contract.py']
    return dict(schema='opentallas.v41.window_retention_contract.v1', status='proposal_no_RTL_change',
                approved_scope='opt-in single-L0 experiment; root approved', proposed_scope='single-L0 QK followed once by same-content PV',
                qk=qk, pv=pv, between=between,
                identity_fields=['user','layer','pos','first_row','row_count','final_mask','format','stack','region_base','region_count','step_epoch','source_epoch'],
                raw_descriptor_not_key=['tiles','k','nout','ts','ks'],
                hard_validators=['exact QK/PV signatures','L0 only','128complete rows','all writes completed','prior replay engine idle and return queues drained','fresh lifecycle generation'],
                invalidation_events=['accepted block write before completion','accepted prime','any external write into region','region/stack/config change','new step or layer','reset/fault','replacement prefetch','generation wrap before quiescent drain'],
                proposed_resource_cost=dict(additional_payload_bytes=0, provisional_metadata_bits=320, queue_entries=0,
                                            compare_register_cycles=1, stage_ready_cycles_after_accept_min=1,
                                            physical_cost='Wide equality must be registered locally; timing/area unmeasured'),
                benefit=dict(skipped_sectors=2176, skipped_rows=128,
                             standalone_ideal_refill_cycles=4608,
                             claim='Avoid one refill only; shared-HBM savings unknown, never skip P preload or PV arithmetic'),
                source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources})

if __name__ == '__main__':
    (ROOT/'results/contracts/v41_window_retention_contract.json').write_text(json.dumps(build(),indent=2)+'\n')
