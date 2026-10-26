"""Extract the current compiler's cold-INIT inputs without inventing an epoch."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
calendar_bytes = (root / 'calendar.json').read_bytes()
calendar = json.loads(calendar_bytes)
program = calendar['program']
end_embedding = program['emb_send'][1]
embedding = [row for row in calendar['messages']
             if row['seg'] == 1 and row['src'] == 'K'
             and row['rx_port'] == 2 and row['kind'] in (6, 7)
             and program['emb_send'][0] <= row['cyc'] <= end_embedding]
assert len(embedding) == 64
assert program['embed']['rope'] and program['embed']['cycles'] == 1627
assert calendar['status_ofs'] == 41
packet = {
    'schema': 'opentallas.qwen.current-cold-init-inputs.v1',
    'scope': 'current source compiler model and canonical INIT event; no physical date',
    'source': {
        'calendar_sha256': hashlib.sha256(calendar_bytes).hexdigest(),
        'image_sha256': hashlib.sha256((root / 'd2d_cal_image.svh').read_bytes()).hexdigest(),
        'remote_run': 'ot-gold1:/srv/opentallas-scratch/claude/codex-qdie-2000/qchain_r53_seam/rope1627_model',
        'compiler_unit': 'oth-ubuntu-4748-1792731778',
    },
    'current_model': {
        'embedding_cycles': program['embed']['cycles'],
        'embedding_header_send': program['emb_header_send'],
        'embedding_send': program['emb_send'],
        'embedding_last_receive_calendar': max(row['rx_out'] for row in embedding),
        'rope_send': program['rope_send'],
        'first_layer_start': program['layers'][0]['start'],
        'token_period': program['token_period'],
        'admission': program['admission'],
        'die_stages': calendar['die_stages'],
    },
    'init_event': {
        'T_port': 0, 'T_argument': 0, 'DH_stage': 0, 'DH_user': 0,
        'init_u0': 1, 'INIT_FIRST': 52, 'INIT_CNT': 3,
        'context_identity': 'actual checked cold user0 host_tag token/position and image epoch',
        'once_per_admission': True,
        'ordinary_stage0_arguments': [128, 256],
        'ordinary_stage0_init_u0': 0,
        'reference': 'be5612758 tools/qwen_static_schedule/mu_cold_prefix.py; current selector 9e6fd413f',
    },
    'current_binding': {
        'head_descriptor': program['program_records']['head_descriptor'],
        'context_after_result': program['program_records']['context_after_result'],
        'cold_context_record': None,
        'cold_T_segment_launch': None,
        'INIT_external_DH_date': None,
        'provider_safe_sample': None,
        'forwarded_epoch': None,
        'qualified': False,
    },
    'required_date_equation': (
        'INIT_external_DH + actual_DH_to_provider_sample_age = '
        'actual_final_embedding_receive_pin + source-bound_provider_safe_margin'),
    'reason_no_date': (
        'Current compiler emits periodic token-run rows and an admission AUTH/WITNESS interval, '
        'but head_descriptor is null and selected SYSFACE starts only T segment0. '
        'The cold user0 context/prefetch launch and actual consumer edge ledger are absent. '
        'The receive-calendar edge1619 is not a physical provider pin date. '
        'Do not copy historical INIT-to-L0 age334 or infer every stage0 as INIT.'),
}
(root / 'packet.json').write_text(json.dumps(packet, indent=2) + '\n')
print(json.dumps({'packet': str(root / 'packet.json'),
                  'embedding_receive_calendar_last': packet['current_model']['embedding_last_receive_calendar'],
                  'INIT_external_DH_date': None, 'qualified': False}))
