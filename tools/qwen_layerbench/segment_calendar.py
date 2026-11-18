"""Place LOCAL SEG commands without changing fixed ME/END issue dates.

Decode later segments continue the base-0 fixed calendar (fixed_issue_dense_pw
start selection). LOCAL SEG must put the controller at its next candidate before
that candidate's existing fixed issue. The controller skips each SU in SKIP edges.
"""
class SegmentCalendarError(ValueError):
    pass


def segment_window(plan, segment, constants):
    base=segment['base']
    heads=[p for p in plan if p.get('unit') in (0,1) and p.get('pc') is not None]
    previous=max((p for p in heads if p['pc']<base),key=lambda p:p['pc'])
    following=min((p for p in heads if p['pc']>=base),key=lambda p:p['pc'])
    skipped=[p['pc'] for p in plan if p.get('unit')==2 and base<=p['pc']<following['pc']]
    # END also keeps the DEP guard used by ctlm_image.plan_stage's END rule.
    end_guard=constants['DEP'] if following['kind']=='END' else 0
    ready_cost=constants['SEG_TO_HEAD']+constants['CTRL_FIRST']+len(skipped)*constants['SKIP']
    lower=max(segment['at'],previous['at']+1)
    upper=following['at']-end_guard-ready_cost
    if lower>upper:
        raise SegmentCalendarError(f'SEG{base}: no legal controller interval [{lower},{upper}]')
    return dict(base=base,earliest_pulse=lower,latest_pulse=upper,
                previous_pc=previous['pc'],previous_fixed_issue=previous['at'],
                first_next_pc=following['pc'],first_next_kind=following['kind'],
                first_next_fixed_issue=following['at'],skipped_su_pcs=skipped,
                controller_ready_cost=ready_cost,consumer_guard=end_guard,
                controller_ready_deadline=following['at']-end_guard,
                original_pulse=segment['at'])


def validate_segment_pulse(window,pulse):
    if not window['earliest_pulse']<=pulse<=window['latest_pulse']:
        raise SegmentCalendarError(f'SEG{window["base"]}: pulse{pulse} outside legal interval '
                                   f'[{window["earliest_pulse"]},{window["latest_pulse"]}]')
    ready=pulse+window['controller_ready_cost']
    if ready>window['controller_ready_deadline']:
        raise SegmentCalendarError('controller misses the unchanged fixed consumer')
    return ready


def place_segments(plan,constants,relay,occupied):
    used=set(occupied);placements=[]
    for segment in (p for p in plan if p['kind']=='SEG'):
        window=segment_window(plan,segment,constants)
        selected=None
        for pulse in range(window['earliest_pulse'],window['latest_pulse']+1):
            issue=pulse-constants['LOC_EDGES']
            if issue not in used:
                selected=(pulse,issue);break
        if selected is None:
            raise SegmentCalendarError(f'SEG{segment["base"]}: no free command edge inside legal interval')
        pulse,issue=selected;ready=validate_segment_pulse(window,pulse);used.add(issue)
        placements.append(dict(window,pulse=pulse,issue_edge=issue,
                               edge_w5=issue+relay['R_CMD'],shift=pulse-window['original_pulse'],
                               controller_ready=ready,
                               fixed_consumer_slack=window['controller_ready_deadline']-ready))
    return placements
