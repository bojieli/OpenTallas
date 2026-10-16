"""Serialize fixed issue metadata; actual source decoder retains command fields.

cmd380 packing is rtl/physical/ot_qfd_tt_ctlm_split.sv assign cmd, and
SU482 is rtl/qwen_split/qfd_seq_su.sv assign su. This consumer deliberately
contains no independent command decoder: its issue_v must replace the REAL
internal issue equation before those packers and argmax folding state.
"""
from .calendar import ScheduleError


def rows(calendar, stage, own, period_fs, phase_fs, stop_cycle):
    if own not in (1,2) or period_fs<=0 or not 0<=phase_fs<period_fs:
        raise ScheduleError('invalid native owner/clock')
    result=[]
    for issue in calendar['issues']:
        if issue['stage']!=stage or issue['unit'] not in (own,0):continue
        if issue['unit']==0:
            terminal=[e for e in calendar['events'] if e['stage']==stage and e['pc']==issue['pc'] and e.get('kind')=='owner_end' and e.get('owner')==own]
            if len(terminal)!=1:
                raise ScheduleError('actual END requires one native per-owner fin event')
            time=terminal[0]['time_fs']
        else:
            time=issue['time_fs']
        if time<phase_fs or (time-phase_fs)%period_fs:
            raise ScheduleError('actual decoded issue not aligned to assigned issuer clock')
        cycle=(time-phase_fs)//period_fs
        if not 2<=cycle<1<<32 or not 0<=issue['pc']<4096:
            raise ScheduleError('issue exceeds startup/PC/counter bounds')
        if result and cycle<=result[-1]['cycle']:
            raise ScheduleError('native decoder cannot issue twice in one edge')
        result.append(dict(pc=issue['pc'],unit=issue['unit'],cycle=cycle))
    if own==1:
        targets=set()
        for event in calendar['events']:
            if event['stage']!=stage or event.get('kind')!='copy_issue':continue
            target=event['target_pc']
            matching=[i for i in result if i['pc']==target and i['unit']==1]
            if len(matching)!=1 or target in targets:
                raise ScheduleError('copy event must name one distinct actual upcoming ME command')
            if not event.get('rtl_instance') or not event.get('rtl_module') or not event.get('requires') or not event.get('produces'):
                raise ScheduleError('copy event lacks native engine/operand/commit attribution')
            time=event['time_fs']
            if time<phase_fs or (time-phase_fs)%period_fs:
                raise ScheduleError('copy issue does not align to actual scheduler clock')
            cycle=(time-phase_fs)//period_fs
            command=int(event['cp56_hex'],16)
            if not 0<=command<1<<56 or not command&1 or not 1<=(command>>49)<=64:
                raise ScheduleError('copy descriptor exceeds actual CP56 source encoding')
            if not 2<=cycle<matching[0]['cycle']:
                raise ScheduleError('copy must issue before its actual consuming ME command')
            targets.add(target)
            result.append(dict(pc=target,unit=3,cycle=cycle,cp56_hex=f'{command:014x}'))
        if len(targets)>3:raise ScheduleError('copy controls exceed three actual PW stores')
        result.sort(key=lambda e:e['cycle'])
        if any(a['cycle']==b['cycle'] for a,b in zip(result,result[1:])):
            raise ScheduleError('copy and engine operations conflict on actual issue edge')
    if not result or result[-1]['unit']!=0 or result[-1]['cycle']!=stop_cycle:
        raise ScheduleError('actual compiled END must end each owner calendar at stop_cycle')
    for n,r in enumerate(result):
        packed=r['cycle'] | (r['pc']<<32) | (r['unit']<<44) | ((n==len(result)-1)<<46)
        r['hex']=f'{packed:012x}'
    return result


def pw_image(calendar, stage, me_clock, su_clock, program_words):
    """Load owner stores with separately phase-bound ME/SU terminal cycles."""
    if not 0<=stage<64 or not 0<program_words<61:
        raise ScheduleError('calendar reservation requires actual program below instruction61')
    me=rows(calendar,stage,1,me_clock['period_fs'],me_clock['phase_fs'],me_clock['stop_cycle'])
    su=rows(calendar,stage,2,su_clock['period_fs'],su_clock['phase_fs'],su_clock['stop_cycle'])
    if len(me)>8 or len(su)>20:
        raise ScheduleError('native stage exceeds physically reserved ME8/SU20 calendar stores')
    out=[dict(address=1016,data_hex=f'{((0x43414c31<<32)|me_clock["stop_cycle"]):016x}'),
         dict(address=1018,data_hex=f'{((0x43414c32<<32)|su_clock["stop_cycle"]):016x}')]
    for base,records in ((976,me),(984,su)):
        out.extend(dict(address=base+n,data_hex=f'{int(r["hex"],16):016x}') for n,r in enumerate(records))
    copies=[r for r in me if r['unit']==3]
    out.extend(dict(address=1019+n,data_hex=f'{int(r["cp56_hex"],16):016x}') for n,r in enumerate(copies))
    seal=(0x43414c53<<32)|(program_words<<18)|(stage<<12)|(len(su)<<6)|len(me)
    out.append(dict(address=1017,data_hex=f'{seal:016x}'))
    return out
