#!/usr/bin/env python3
"""Audit actual source/contract membership without treating cancellation as retirement."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAKEOVER = Path('/home/ubuntu/claude-takeover-20261007')
STATE = Path('/home/ubuntu/.local/state/closure_loop/jobs')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', default='results/arch/hbm_native_1013/uncovered_source_audit_2240.json')
    a = p.parse_args()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    contract = json.loads((ROOT / 'results/arch/hier_contract_1011/r25gq.json').read_text())
    jobs = [json.loads(p.read_text()) for p in sorted(STATE.glob('*.json'))]
    def job_rows(blocks):
        return [{'job': j['name'], 'block': j['spec']['block'], 'status': j['status'],
                 'source_commit': j['spec']['source']['commit'], 'reason': j.get('reason'),
                 'state_file_sha256': hashlib.sha256((STATE / (j['name'] + '.json')).read_bytes()).hexdigest()}
                for j in jobs if j.get('spec', {}).get('block') in blocks]
    paths = ['tools/hbm_accel_die_fp.py', 'tools/hbm_sm_compaction_1013.py',
             'results/arch/hier_contract_1011/r25gq.json',
             'results/arch/hbm_native_1013/vm/component.json',
             'results/arch/hbm_native_1013/sm/component.json',
             'rtl/hbm_accel/generic/hgi_mtp_native.sv',
             'rtl/hbm_accel/generic/vm/b2/ot_vms_bank.sv',
             'rtl/hbm_accel/generic/vm/b2/ot_vms_slice.sv',
             'rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv',
             'physical/hbm_mtp/rtl/ot_gpu_rf_visibility_fence_p.sv',
             'physical/ref_tile/stn_slice8_no3_rt/spec.json',
             'physical/ref_tile/stn_slice5_no3_rt/spec.json']
    sources = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    historical = ['hfd_vm_nw_w_t1', 'hfd_vm_se_e_t0', 'hfd_vm_sw_e_t2',
                  'hfd_vm_sw_e_t3', 'hfd_vm_sw_s', 'hfd_vm_sw_w_t4']
    cp = ['vm_cp_' + n for n in ['root', 'slice2', 'slice3', 'fw0', 'fw1', 'fw2', 'fw3',
          'fe0', 'fe1', 'fe2', 'fe3', 'rb', 'rb2', 'rt', 'rt2', 'rwa', 'rwb', 'rwt', 're']]
    rows = []
    for element in historical:
        slots = [s['name'] for s in contract['slots'] if s.get('cell') == element]
        rows.append({'element': element, 'contract_slots': slots,
                     'classification': 'HISTORICAL_VM8_REQUIREMENT_CONTRACT_MIGRATION_OPEN',
                     'source_replacement_candidate': cp,
                     'replacement_evidence': 'el1011-hbm-vm8.log 2026-10-12 COLLECT positively specifies 36 grid subtiles -> 25 vm_cp instances/19 kits; closed vm_cp views exist, but v12 contract retains grid slots.',
                     'cancelled_only_excluded': False, 'requirement_complete': False,
                     'next_action': 'Migrate actual die instance/slot/seam bindings to the complete qualified vm_cp composition; preserve historical closed views and original failures.'})
    rows.append({'element': 'ot_hgi_vm_unit', 'classification': 'CENTRAL_B2_INSTANCE_REPLACED_NATIVE_ENDPOINT_REQUIREMENT_ACTIVE',
                 'native_master': 'ot_vms_slice', 'source': 'tools/hbm_accel_die_fp.py:r25gq_b2 drop_blocks hb_hgi_vm and four quadrant slices',
                 'contract_slots': [s['name'] for s in contract['slots'] if s.get('cell', '').startswith('hfd_hgi_vms')],
                 'bench_golden_retained': True, 'requirement_complete': False,
                 'queue_contract': {'monolithic_LQ': 8, 'native_RRS_WRS': 3, 'native_lane_credits': 10,
                                    'formula': '4 + 2*RRS/WRS', 'LQ16_native_adopted': False},
                 'next_action': 'Compose actual SU LQ8 client + local four-sector prefetch with native B2 slice; golden LQ16 benchmark alone does not change native queue parameters.'})
    sm = json.loads((ROOT / 'results/arch/hbm_native_1013/sm/component.json').read_text())
    fc = [c for c in sm['children'] if '_fc_' in c['logical_module']]
    rows.append({'element': 'ot_hbm_accel_smh_front_c', 'classification': 'SOURCE_EXPANDS_INTO_NINE_REAL_CHILDREN',
                 'source_define': 'OT_SMH_FC_HIER', 'source_commit': sm['source_commit'],
                 'children': [{k: c.get(k) for k in ['instance', 'logical_module', 'view_job', 'view_lef', 'closure_status']} for c in fc],
                 'no_hardened_parent': True, 'requirement_complete': False,
                 'next_action': 'Use nine closed child views with actual placement, deskew, per-child clocks and native production bench; do not route the obsolete monolithic implementation.'})
    for suffix in ('eg', 'wg'):
        element = 'ot_hbm_accel_smh_tile_' + suffix
        recent = next(j for j in jobs if j['name'] == 'smh_tile_' + suffix + '_ref-r16-f6ee9d6d1')
        rows.append({'element': element, 'classification': 'LIVE0_REAL_PHYSICAL_REQUIREMENT',
                     'latest_actual_job': recent['name'], 'latest_actual_status': recent['status'],
                     'reason': recent.get('reason'), 'own_logic_candidate': 'sm_own_logic/extraction.json',
                     'retained_Q_bits_per_tile': 995, 'retained_Q_bits_per_SM': 15920,
                     'requirement_complete': False, 'next_action': 'Repair ANT-0008 route invalidation, harden retained own leaf and all actual per-child clock/seam/PG assignments.'})
    for element, blocks, classification, action in [
        ('ot_hbm_native_frame_station_rb_NO3', ['ot_hbm_native_frame_station_rb_NO3', 'ot_hbm_w2_stn_slice8', 'ot_hbm_w2_stn_slice5'],
         'HARDENED_SLICE_SUCCESSORS_EXIST_PARENT_REQUIREMENT_OPEN',
         'Bind actual five NO3 slice views and retained hub into a full parent, fix source hard-child shadowing, assign measured phases and actual slot before parent submission.'),
        ('hfd_mtp_x', ['hfd_mtp_x', 'hfd_mtp_x_stop', 'hgi_mtp_native'],
         'CURRENT_HB_MTP_NATIVE_MASTER_CLOSED_HISTORICAL_RAW_MASTER_REPLACED',
         'Preserve CLOSED hgi_mtp_native physical views; verify exact current CP facade source and physical PG/clock assignment at hb_mtp while root collects DS MTP arithmetic jobs.'),
        ('ot_gpu_rf_visibility_fence', ['ot_gpu_rf_visibility_fence', 'ot_gpu_rf_visibility_fence_p'],
         'PIPELINED_REAL_SUCCESSOR_CLOSED_ACTUAL_DIE_ASSIGNMENT_OPEN',
         'Preserve closed pipelined fence; bare fence has 4096-bit combinational passthrough. Bind actual retained RF ACK/capture interface and slot, inspect closed source parameters and views before any reroute.')]:
        rows.append({'element': element, 'classification': classification, 'jobs': job_rows(blocks),
                     'cancelled_only_excluded': False, 'requirement_complete': False,
                     'contract_slots': [s['name'] for s in contract['slots'] if s.get('cell') in blocks],
                     'next_action': action})
    result = {'schema': 'opentallas.hbm.uncovered_source_audit.v1', 'source_commit': commit,
              'source_sha256': sources, 'contract_version': contract['version'], 'rows': rows,
              'rule': 'Cancellation, historical registry owner, die_used=false and absence of a slot never establish retirement. A positive source replacement still requires actual native endpoint coverage.',
              'physical_acceptance_claim': False, 'ledger_changed': False, 'gates_changed': False}
    path = ROOT / a.out; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'rows': len(rows), 'source_commit': commit, 'out': a.out}))


if __name__ == '__main__':
    main()
