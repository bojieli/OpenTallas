"""Explicit marker rebooking for native pages; command dates/payloads stay exact.

This is a source candidate, never a retirement certificate or a production
calendar. The caller must price the reported marker/reload delays and bind real
consumer retirement before adopting it. The existing compiler is unchanged.
"""
from copy import deepcopy
from .native_csr_image import encode_image


def rebook(image, *, kit_issue, end_issue):
    encode_image(image)
    for value in (kit_issue, end_issue):
        if type(value) is not int or not 0 <= value < 1 << 24:
            raise ValueError('explicit 24-bit KIT/END dates required')
    old = image['rows']
    kits = [i for i, r in enumerate(old) if r['engine'] == 14]
    ends = [i for i, r in enumerate(old) if r['engine'] == 15]
    if len(kits) != 1 or len(ends) != 1 or ends[0] != len(old)-1:
        raise ValueError('one actual KIT and final END required')
    if any(old[i]['arg'] or old[i]['done'] for i in kits+ends):
        raise ValueError('native marker payload/done fields must remain zero')
    normal = [(i, deepcopy(r)) for i, r in enumerate(old) if r['engine'] < 14]
    if not normal or kit_issue <= max(r['done'] for _, r in normal):
        raise ValueError('candidate KIT must follow every native command done edge')
    if kit_issue < old[kits[0]]['issue'] or end_issue < old[ends[0]]['issue']:
        raise ValueError('candidate cannot advance an existing completion marker')
    if end_issue <= kit_issue:
        raise ValueError('END must follow KIT')
    indexed = normal + [(kits[0], dict(old[kits[0]], issue=kit_issue)),
                        (ends[0], dict(old[ends[0]], issue=end_issue))]
    indexed.sort(key=lambda pair: (pair[1]['issue'], pair[1]['engine']))
    result = deepcopy(image)
    result['rows'] = [r for _, r in indexed]
    # Row addresses stay dense; the contents and therefore completion tags move.
    # The order of LEN, BEGIN, SEAL, template and CF writes is retained exactly.
    tag_map = {old_i: new_i for new_i, (old_i, _) in enumerate(indexed)}
    result.update(status='EXPLICIT_MARKER_CANDIDATE', global_schedule_booked=False,
                  lifetime_qualified=False)
    encode_image(result)
    return result, dict(
        row_tag_map=[dict(old=i, new=tag_map[i], engine=old[i]['engine'])
                     for i in range(len(old))],
        command_dates_and_arguments_unchanged=True,
        templates_and_CF_unchanged=True,
        KIT_delay=kit_issue-old[kits[0]]['issue'],
        END_delay=end_issue-old[ends[0]]['issue'],
        hardware_pin_cycles_added=0,
        source_command_latency_added=0,
        lifecycle_qualified=False,
        required_adoption=['actual consumer retirement fence',
                           'new row tags through all completion consumers',
                           'priced reload and HOST/KS resource calendar'])
