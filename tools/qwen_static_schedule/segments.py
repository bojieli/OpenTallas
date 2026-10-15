"""Lower actual DW64 segment programs into the real fixed outer-sequencer PW store."""
from .calendar import ScheduleError, pins, sha
from pathlib import Path
import json, hashlib
import hdc_qwen_fullshape_isa_w12 as ISA

BASE=961
ROOT=Path(__file__).resolve().parents[2]

class MissingPhysicalProfile(ScheduleError):
    def __init__(self, fields):
        self.missing_fields=sorted(set(fields))
        super().__init__(json.dumps(dict(status='MISSING_PHYSICAL_PROFILE',missing_fields=self.missing_fields)))

def physical_profile(profile, program_bytes):
    required=('period_fs','phase_fs','VM_response_edges','stop_cycle','segments',
              'source_sha256','receipt_path','receipt_sha256')
    missing=[field for field in required if profile.get(field)is None]
    if profile.get('physical_profile_status')!='MEASURED':missing.append('physical_profile_status=MEASURED')
    if missing:raise MissingPhysicalProfile(missing)
    pins(ROOT,profile['source_sha256'])
    rtl='rtl/qwen_sys/static_schedule_20261014/ot_qwen_tp_seq_calendar.sv'
    if rtl not in profile['source_sha256']:raise MissingPhysicalProfile(['source_sha256.'+rtl])
    path=(ROOT/profile['receipt_path']).resolve()
    if not path.is_file()or sha(path)!=profile['receipt_sha256']:
        raise ScheduleError('physical receipt file missing or changed')
    receipt=json.loads(path.read_text())
    missing=[key for key in ('clock_tree','reset_release','seq_relay','VM_path','collective_command_route','collective_payload_route','core_completion_path')
             if receipt.get('qualified_paths',{}).get(key,{}).get('status')!='QUALIFIED']
    if missing:raise MissingPhysicalProfile(['receipt.qualified_paths.'+key for key in missing])
    for name,path in receipt['qualified_paths'].items():
        if name not in ('clock_tree','reset_release','seq_relay','VM_path','collective_command_route','collective_payload_route','core_completion_path'):continue
        absent=[key for key in ('age_fs','evidence_path','evidence_sha256')if path.get(key)is None]
        if absent:raise MissingPhysicalProfile(['receipt.qualified_paths.'+name+'.'+key for key in absent])
        if not isinstance(path['age_fs'],int)or isinstance(path['age_fs'],bool)or path['age_fs']<0:
            raise ScheduleError('invalid measured physical path age: '+name)
        evidence=(ROOT/path['evidence_path']).resolve()
        if not evidence.is_file()or sha(evidence)!=path['evidence_sha256']:
            raise ScheduleError('measured physical evidence missing or changed: '+name)
    if receipt.get('status')!='QUALIFIED'or receipt.get('program_sha256')!=hashlib.sha256(program_bytes).hexdigest():
        raise ScheduleError('physical receipt not qualified for actual program bytes')
    for key in ('period_fs','phase_fs','VM_response_edges','stop_cycle','segments','source_sha256'):
        if receipt.get(key)!=profile[key]:raise ScheduleError('physical receipt/profile mismatch: '+key)
    return profile


def program_segments(program_bytes, descriptors):
    program=[ISA.decode_instruction(int(w,16))for w in program_bytes.split()]
    if not 0<len(program)<60 or len(descriptors)!=8:
        raise ScheduleError('actual program requires1..59 instructions and eight physical DW words')
    result=[];expected_pc=0
    for index,word in enumerate(descriptors):
        d=ISA.decode_descriptor(word,vm_addr_ext=True)
        if d['program_base']!=expected_pc:
            raise ScheduleError('segment descriptor does not cover next actual source PC')
        end=next((p for p in range(expected_pc,len(program))if program[p]['unit']==0),None)
        if end is None:raise ScheduleError('actual segment has no encoded END')
        result.append(dict(index=index,descriptor=word,first_pc=expected_pc,end_pc=end,**d))
        expected_pc=end+1
        if d['kind'] in (0,2):
            if expected_pc!=len(program)or any(descriptors[index+1:]):
                raise ScheduleError('terminal descriptor omits actual operations or has nonzero DW padding')
            break
        if d['kind']!=1:raise ScheduleError('unsupported real collective descriptor kind')
    if not result or len(result)>3 or result[-1]['kind']not in(0,2):
        raise ScheduleError('production outer-sequencer capacity is three segments with real terminal')
    return result


def requires_constant_rom(program_bytes):
    return any(f['unit']==2 and(f['b_src']or f['c_src'])for f in(ISA.decode_instruction(int(w,16))for w in program_bytes.split()))


def pw_image(program_bytes,descriptors,stage,profile):
    segments=program_segments(program_bytes,descriptors)
    requires_cbuf=requires_constant_rom(program_bytes)
    physical_profile(profile,program_bytes)
    if not 0<=stage<64 or len(profile['segments'])!=len(segments):
        raise ScheduleError('outer calendar does not cover actual program segments')
    period=profile['period_fs'];phase=profile['phase_fs'];vrl=profile['VM_response_edges']
    if period<=0 or not 0<=phase<period or vrl<1:
        raise ScheduleError('invalid actual sequencer clock/VM profile')
    stop=profile['stop_cycle'];last_end=-1;out=[];reservations={};collective=[];fifo_events={}
    for segment,timing in zip(segments,profile['segments']):
        k=segment['index'];start=timing['core_start_cycle'];end=timing['core_end_cycle'];kind=segment['kind']
        if not last_end+3<start<end<stop<1<<32:
            raise ScheduleError('core/descriptor fetch windows overlap or exceed stage deadline')
        tx=timing['tx_first_cycle'];rx=timing['rx_first_cycle'];ts=timing['tx_stride'];rs=timing['rx_stride']
        if kind:
            if not min(tx,rx)>end or not 0<ts<65536 or not 0<rs<65536:
                raise ScheduleError('collective windows precede actual core END')
            n=segment['words']if kind==1 else 1
            receive=n if kind==1 else 8
            if max(tx+(n-1)*ts,rx+(receive-1)*rs)>=stop:
                raise ScheduleError('collective transfer exceeds fixed stage stop')
            if kind==1:
                if not 0<segment['words']<=256 or segment['vm_word']+n>1<<20:
                    raise ScheduleError('actual AR descriptor exceeds VM bounds')
                first_read=tx-vrl-1
                if ts!=1:raise ScheduleError('actual VM interface currently requires dense one-edge AR slots')
                if first_read<0 or first_read<=timing['producer_last_visible_cycle']:
                    raise ScheduleError('AR read precedes actual producer write visibility')
                for beat in range(n):
                    for resource,cycle in [('VM_read',first_read+beat*ts),('payload_TX',tx+beat*ts),('VM_write',rx+beat*rs)]:
                        if(resource,cycle)in reservations:raise ScheduleError('actual segment port conflict')
                        reservations[resource,cycle]=(k,beat)
                    arrival=first_read+beat*ts+vrl
                    transmit=tx+beat*ts
                    fifo_events[arrival]=fifo_events.get(arrival,0)+1
                    fifo_events[transmit]=fifo_events.get(transmit,0)-1
            last_end=max(tx+(n-1)*ts,rx+(receive-1)*rs+1)
            collective.append(dict(rtl_instance='seq_su.u_seq.u_seq',rtl_module='ot_qwen_tp_seq_calendar',
                core_cmd_cycle=timing['collective_core_cmd_cycle'],words=n,mode=int(kind==2),tag=k))
        else:
            if tx or rx or ts or rs:raise ScheduleError('END segment has nonzero transport windows')
            last_end=end
        values=[start|(end<<32),tx|(rx<<32),ts|(rs<<16),segment['descriptor']]
        out.extend(dict(address=BASE+4*k+j,data_hex=f'{value:016x}')for j,value in enumerate(values))
    occupancy=0;high_water=0
    for cycle,delta in sorted(fifo_events.items()):
        occupancy+=delta;high_water=max(high_water,occupancy)
        if occupancy<0 or occupancy>4:raise ScheduleError('actual four-word payload queue under/overflow')
    if occupancy:raise ScheduleError('unconsumed actual VM payload at stage end')
    for addr in range(BASE+4*len(segments),973):out.append(dict(address=addr,data_hex='0000000000000000'))
    out.extend([dict(address=973,data_hex=f'{0x53475431<<32|stop:016x}'),
                dict(address=974,data_hex=f'{0x53475453<<32|int(requires_cbuf)<<8|stage<<2|len(segments):016x}'),
                dict(address=975,data_hex='0000000000000000')])
    return dict(writes=out,segments=segments,requires_cbuf=requires_cbuf,queue_high_water=high_water,port_reservations=[dict(resource=r,cycle=c,segment=k,beat=b)for(r,c),(k,b)in sorted(reservations.items())],collective=collective)
