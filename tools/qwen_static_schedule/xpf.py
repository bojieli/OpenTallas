"""Serialize compiler-reserved XPF arms without consulting execution traces."""
from .calendar import ScheduleError, pins


def arm_table(calendar, stage_schedule, route, root):
    pins(root, route['source_sha256'])
    stage = stage_schedule['stage']
    if not 0 <= stage < 64:
        raise ScheduleError('stage exceeds actual six-bit register')
    if calendar['program_sha256'][stage] != stage_schedule['program_sha256']:
        raise ScheduleError('XPF address plan differs from actual compiled stage')
    period = route['clock_period_fs']
    phase = route['clock_phase_fs']
    if period <= 0 or not 0 <= phase < period:
        raise ScheduleError('invalid assigned XPF clock')
    assigned_edges = route['arm_transport_edges'] + route['tap_internal_edges']
    if route['tap_internal_edges'] != 3 or route['arm_transport_edges'] < 0:
        raise ScheduleError('native tap requires its actual three internal edges')
    occupied = set()
    rows = []
    for record in stage_schedule['producer_records']:
        if not 0 <= record['arm_before_pc'] < 4096 or not 0 <= record['producer_unit'] < 4:
            raise ScheduleError('producer identity exceeds actual PC/unit width')
        bits = int(record['xpf_hex'], 16)
        if not 0 <= bits < 1 << 72:
            raise ScheduleError('descriptor exceeds actual XPF width')
        xb, xc, xk = (bits >> 1) & ((1 << 24)-1), (bits >> 25) & 4095, (bits >> 37) & 4095
        split, nk = (bits >> 49) & 15, (bits >> 53) & ((1 << 18)-1)
        required = {xb+c*xc+k*xk for c in range(1 << split) for k in range(nk)}
        covered = set()
        earliest = None
        for event in calendar['events']:
            if event['stage'] != stage or event['pc'] not in record['producer_pcs'] or event.get('kind') != 'vm_write_tap':
                continue
            if not 0 < event['lanes'] <= 64 or event['stride'] not in (0, 1) or event['mask'] >> event['lanes']:
                raise ScheduleError('unsupported native write-tap vector')
            touched = {event['address']+lane*event['stride'] for lane in range(event['lanes']) if event['mask'] & (1 << lane)} & required
            if touched:
                covered.update(touched)
                earliest = event['time_fs'] if earliest is None else min(earliest, event['time_fs'])
        if covered != required:
            raise ScheduleError('compiled native producer writes do not cover entire X epoch')
        issue = [i for i in calendar['issues'] if i['stage'] == stage and i['pc'] == record['arm_before_pc'] and i['unit'] == record['producer_unit']]
        if len(issue) != 1 or earliest < issue[0]['time_fs']:
            raise ScheduleError('invalid compiled producer issue/write ordering')
        for time in (earliest, issue[0]['time_fs']):
            if time < phase or (time-phase) % period:
                raise ScheduleError('XPF observer requires source events aligned to assigned clock/phase')
        first = (earliest-phase)//period
        issue_cycle = (issue[0]['time_fs']-phase)//period
        arm = first-assigned_edges
        while arm in occupied:
            arm -= 1
        if not 0 <= arm < (1 << 32) or not 0 <= issue_cycle < (1 << 32) or not first < (1 << 32):
            raise ScheduleError('insufficient compiler startup region or actual counter width')
        occupied.add(arm)
        packed = (first << 156) | (issue_cycle << 124) | (arm << 92) | (stage << 86) | (record['producer_unit'] << 84) | (record['arm_before_pc'] << 72) | bits
        rows.append(dict(record, arm_cycle=arm, issue_cycle=issue_cycle, first_write_cycle=first,
                         cfg_data_hex=f'{packed:047x}'))
    if len(rows) > 8:
        raise ScheduleError('compiled arms exceed actual eight-record physical bank')
    return rows
