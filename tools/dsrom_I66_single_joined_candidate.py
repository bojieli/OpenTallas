"""Single visibility-anchored candidate and lossless proposed user32 encoding.
This constructs a software plan. Actual deadline requires the existing strict
PHW10 enrollment/accepted-read gate; this module cannot manufacture a journal.
"""
import argparse
import json
from pathlib import Path
import dsrom_I66_common_gather_proposal as C
import dsrom_I66_consumer_deadline as D

FIELDS = [('generation',32), ('operation_sequence',32), ('owner_stage',6),
          ('packet_kind',3), ('packet_ordinal',3), ('payload_bits',18),
          ('rank',2), ('user_low',16), ('user_high',16)]


def encode_header(fields):
    expected = {n for n, w in FIELDS if n not in ('user_low', 'user_high')} | {'user'}
    if set(fields) != expected:
        raise ValueError('exact candidate header fields')
    user = fields['user']
    if type(user) is not int or not 0 <= user < 2**32:
        raise ValueError('source candidate user32 identity')
    values = dict(fields, user_low=user & 65535, user_high=user >> 16)
    result = 0
    for name, width in FIELDS:
        value = values[name]
        if type(value) is not int or not 0 <= value < 2**width:
            raise ValueError('candidate header width')
        result = (result << width) | value
    return result


def decode_header(word):
    if type(word) is not int or not 0 <= word < 2**128:
        raise ValueError('candidate header128')
    fields = {}
    for name, width in reversed(FIELDS):
        fields[name] = word & ((1 << width) - 1)
        word >>= width
    fields['user'] = fields.pop('user_low') | (fields.pop('user_high') << 16)
    return fields


def candidate():
    p = C.proposal()
    p['scope'] = 'ONE_VISIBILITY_ANCHORED_SOURCE_MODEL_CANDIDATE_NOT_ACTUAL_DEADLINE'
    p['arbitration']['credit_release'] = 'actual home visibility plus positive captured feedback/CDC; no separately reserved downstream shortcut'
    p['wire_identity_gap'] = {
        'candidate_user_bits': 32, 'header_bits': sum(w for _,w in FIELDS),
        'encoding_fields_MSB_to_LSB': FIELDS,
        'reserved16_reassigned_to_user_high16': True,
        'old_command_bits': 221, 'new_command_bits': 237,
        'command_flits_at256': 1, 'header_flit_count_unchanged': True,
        'extra_command_staging_bits_per_disjoint_copy': 16,
        'replay_comparator_encode_CRC_cost_priced': False,
        'new_copy_count_and_overlap_with_frozen_context_unselected': True,
        'no_truncation': True, 'RTL_encoder_implemented': False,
        'required_gate': 'source-qualified command/header encode/decode, CRC, replay identity and reset/wrap ownership'}
    p['calendar_entry'] = 'dsrom_I66_visibility_anchored_calendar.replay with source-qualified offered slots, positive reply/visibility/credit-return providers'
    p['actual_deadline_entry'] = 'dsrom_I66_consumer_deadline.enrolled_join: exact current source/binary/program/field and compiled callbacks, actual source-aligned X tags, reviewed shared service slots'
    p['extra_frozen_context_cost'] = {'bits': 46, 'feedback_BUF_lower_bound': 92,
                                     'outside_R49_baseline': True,
                                     'clock_reset_PG_remote_copies_unpriced': True}
    return p


def actual_deadline(provenance, slots_path, service_path):
    # No bypass for a software schedule, historical binary, or standalone cone.
    return D.enrolled_join(provenance, slots_path, service_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--enrollment', type=Path)
    parser.add_argument('--slots', type=Path)
    parser.add_argument('--service', type=Path)
    args = parser.parse_args()
    if args.enrollment:
        if not args.slots or not args.service:
            parser.error('actual deadline requires enrolled accepted journal and reviewed slots/service')
        result = actual_deadline(json.loads(args.enrollment.read_text()), args.slots, args.service)
    else:
        result = candidate()
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
