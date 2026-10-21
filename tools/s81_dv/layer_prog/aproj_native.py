"""Real a_proj XS/CAP native command lowering; source-data ownership stays explicit.

Uses the same phase/calendar compiler as the actual XS4/frame/CAP component.
It never emits golden gather data, simulated frame returns, or HOST/KS tokens.
"""
import hashlib
import json
import math
from pathlib import Path


def atomic_chunks(rows, row_limit, template_limit):
    """Pack native issuer rows without placing a job reload inside an atomic span.

    An atomic group's first..last rows define its interval even if other
    engines interleave. Overlapping atomic intervals therefore stay together.
    An interval that cannot fit one real job fails closed.
    """
    spans = {}
    for i, row in enumerate(rows):
        group = row.get('grp')
        if group is not None:
            if group not in spans:
                spans[group] = [i, i]
            spans[group][1] = i
    blocks=[];start=0
    for boundary in range(1, len(rows)+1):
        if not any(lo < boundary <= hi for lo, hi in spans.values()):
            blocks.append(rows[start:boundary]);start=boundary
    chunks=[];current=[];used=set()
    for block in blocks:
        templates={r['tix'] for r in block if 'tix' in r}
        if len(block)>row_limit or len(templates)>template_limit:
            raise ValueError('atomic native command interval exceeds one issuer job; no source-safe split')
        if current and (len(current)+len(block)>row_limit or len(used|templates)>template_limit):
            chunks.append(current);current=[];used=set()
        current+=block;used|=templates
    if current:
        chunks.append(current)
    return chunks


def phase_material(field):
    import v41_die_images_w17w10 as I
    return [v for ph in field.phases for v in I.phase_words(ph)], list(field.stream)


def programme(die, op, ctx, phases, frames, capture):
    import dv_layer_compile as C
    import xs_calendar as XC
    from layer_prog.slice_source import resolve
    from pq_calendar import viamap
    if not phases or not frames or any(f.get('faults') for f in frames if f.get('phase') is not None):
        raise ValueError('native a_proj requires nonempty fault-free actual frame programmes')
    P, S = phases
    if len(P) != 2:
        raise ValueError('native a_proj requires exactly one shared source phase')
    sl = ctx['slice']; sid = die.slices()[sl]['sid']
    selected_source = resolve(die, sl)
    cal = XC.compile_phase(P, S, 0, sid)
    raw_returns = [w[0] for f in frames if f.get('phase') is not None for w in f['ret']]
    if any(t != int(t) for t in raw_returns):
        raise ValueError('native frame return minimum has an unresolved fractional clock phase')
    returns = [int(t) for t in raw_returns]
    if not returns:
        raise ValueError('native a_proj has no actual source return-calendar minimum')
    t0 = int(ctx['t_issue'])
    route = C.ctl_path(die, sl)
    if route['entry_port'] == 'vi':
        raise ValueError('column4 native V-rung target2/3 input minimum is not bound by the line-pin source receipt')
    # ctl_path is a compiler event edge (slice pin + RSTOP_HOP). The current
    # XRT command/config output pin is five edges after that raw slice input.
    xr_pin_age = int(route['edges']) - C.RSTOP_HOP + 5
    if xr_pin_age != route['edges'] - C.RSTOP_HOP + 5 or xr_pin_age < 0:
        raise ValueError('native XS/CAP needs an integral current CTL route age')
    origin = t0 + xr_pin_age
    commands = [(int(t), 2, int(word), 'XS_ISD') for t, word in cal['iss'].items()]
    commands.append((XC.GW_IT, 3, int(capture['cfg_d'], 16), 'CAP_CFG'))
    commands.sort()
    if len({t for t, _, _, _ in commands}) != len(commands):
        # GW and CAP descriptor originally share pin150 in the component;
        # one real CTL face can carry one word. Book CAP one edge earlier.
        commands = [(t-1 if target == 3 else t, target, word, name)
                    for t, target, word, name in commands]
    if len({t for t, _, _, _ in commands}) != len(commands):
        raise ValueError('native a_proj CTL issue collision')
    commands.sort()
    engine = C.ENG['VN'] if sl.endswith('N') else C.ENG['VS']
    templates=[];rows=[];events=[];descriptors=[]
    for rel, target, word, name in commands:
        ti=len(templates);issue=t0+rel
        payload=C.ctl_payload(1 << sid, target, 0, word)
        templates.append((sl+'.'+name+'.'+str(rel), payload))
        rows.append(dict(eng=engine, issue=issue, done=issue+C.SEQ['done_v'], arg=ti,
                         what=sl+' '+name+' target'+str(target)))
        events.append(dict(cycle=issue+route['edges'], inst=sl, port=route['entry_port'],
                           dir='in', kind='CTL', payload='template '+str(ti), tag=name))
        descriptors.append(dict(target=target, relative_pin_edge=rel, native_issue_edge=issue,
                                slice_CTL_pin_edge=issue+route['edges']-C.RSTOP_HOP,
                                XR_output_pin_edge=origin+rel, body160=f'{word:040x}',
                                payload186=f'{payload:047x}', ack_edge=issue+C.SEQ['done_v']))
    # A real static END timestamp may reserve a lifetime beyond V ACKs. This
    # source-derived frame minimum is necessary, not aggregate CAP retirement.
    # The standalone XS4 receipt adds one capture edge; actual shipping XS
    # has no such stage. Resolve the selected source instead of inheriting it.
    last_return_min = origin + max(returns) + int(cal['D']) + selected_source['streamer_added_capture_edges']
    source_floor = max(last_return_min+1, origin+int(cal['end_iter']))
    inherited = int(math.ceil(op['end']))
    floor=max(source_floor,inherited)
    prefix=f'prog/xs/native/{op["id"]}/{sl}'
    packed=cal['packed']
    material={
        'pq_phase0.viamap.hex':viamap(P+[0]*(4096-len(P))),
        'pq_calendar_action.viamap.hex':viamap([v&((1<<72)-1) for v in packed]),
        'pq_calendar_time.viamap.hex':viamap([v>>72 for v in packed]),
    }
    stream=S+[0]*(16384-len(S))
    if len(P)>4096 or len(S)>16384:
        raise ValueError('native a_proj XS source ROM capacity exceeded')
    for b in range(4):material[f'pq_stream{b}.viamap.hex']=viamap(stream[4096*b:4096*(b+1)])
    manifest=dict(schema='opentallas.s81.aproj_native_programme.v1', op=op['id'], slice=sl,
        status='PARTIAL', sealed_programme_held=True, lifetime_qualified=False,
        source='actual frame MAT/phase/stream + xs_calendar.compile_phase; real XRT CTL targets2/3',
        native_rows=len(rows), field_phase=0, frame_operation_tag=capture['flags'], xs_tag=0,
        actual_gather_data_emitted=False, synthetic_frame_returns_emitted=False, HOST_KS_assumed=False,
        route=route, selected_slice_source=selected_source,
        CTL_pin_to_XR_command_pin_edges=5, programme_origin=origin,
        origin_definition='op native issue anchor + ctl_path event age - RSTOP_HOP + source XRT5',
        command_descriptors=descriptors, capture=capture,
        calendar=dict(rows=len(packed), stream_words=cal['nb'], fixed_retire_row=next(
            t for t,r in cal['rows'].items() if r.get('retire_mask')), source_end_iter=cal['end_iter'],
            common_shift_model=cal['D'], compiler_sha256=hashlib.sha256(Path(XC.__file__).read_bytes()).hexdigest()),
        retire_not_before=floor, source_frame_minimum=source_floor,
        source_last_return_pin_minimum=last_return_min,
        inherited_op_end=dict(edge=inherited, qualification='INHERITED_MODEL_ONLY'),
        open=['actual selected VQ/rstopt_xo/ring gather producer programme and ownership',
              'all-frame aggregate FIN/cap5r fixed completion and clock phases',
              'all-frame MAT/config image source assembly and instance binding',
              'whole A/B static schedule and native job/host adoption'],
        gather_source_path=' -> '.join(selected_source['wrapper_chain'] + [selected_source['xg'],
                           selected_source['ring'] + ' gather', selected_source['streamer']]),
        images={n:hashlib.sha256(s.encode()).hexdigest() for n,s in material.items()})
    files={prefix+'/'+n:s for n,s in material.items()}
    files[prefix+'/programme.json']=json.dumps(manifest,indent=1)+'\n'
    return dict(rows=rows,templates=templates,events=events,files=files,atomic=True,
                retire_not_before=floor,lifetime_qualified=False,native_programme=manifest)
