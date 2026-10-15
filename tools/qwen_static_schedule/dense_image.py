"""Source-bound dense1024PW+8DW image for the real ascending HOST loader.

Actual PW0 clears the receiving control stores. Footer1023 seals them after
all calendar/CP/XPF rows. Its capability is derived from the actual source
native instruction and is covered by the authorized whole-image digest.
"""
import hashlib
import json
from pathlib import Path
from .calendar import ScheduleError, pins
from .issue_rom import pw_image
from .collective import pw_image as collective_pw_image
from .segments import pw_image as segment_pw_image, MissingPhysicalProfile
from qwen_split.command_abi import pack_me,ROOT
import hdc_qwen_fullshape_isa_w12 as ISA


def native_capability(program,stage):
    native=[(pc,ISA.decode_instruction(word)) for pc,word in enumerate(program)
            if ISA.decode_instruction(word)['unit']==1 and ISA.decode_instruction(word)['me_wsrc']]
    if not native:return False
    if not 1<=stage<=36 or len(native)!=1 or native[0][0]!=11:
        raise ScheduleError('native59 capability requires actual sole PC11 layer dispatch')
    f=native[0][1]
    template=json.loads((ROOT/'results/rtl/qwen_q_export_1014/xpf/static/native380_template.json').read_text())
    if any(v for k,v in f.items()if k.startswith('me_d_')) or pack_me(f)!=int(template['command_hex'],16):
        raise ScheduleError('actual PC11 differs from source-pinned native59 command')
    return True


def validate_program_calendar(program,calendar,stage):
    """Require every encoded operation and its actual operand/result RTL ports."""
    pins(ROOT,calendar.get('source_sha256',{}))
    issues=[i for i in calendar['issues']if i['stage']==stage]
    if len(issues)!=len(program)or sorted(i['pc']for i in issues)!=list(range(len(program))):
        raise ScheduleError('production calendar must issue every actual source PC exactly once')
    for issue in issues:
        decoded=ISA.decode_instruction(program[issue['pc']])
        if issue['unit']!=decoded['unit']:raise ScheduleError('production calendar issue owner differs from actual encoded operation')
        if decoded['unit']==0:continue
        ports=[e for e in calendar['events']if e['stage']==stage and e.get('pc')==issue['pc']]
        if not ports:raise ScheduleError('actual operation lacks operand/result port calendar')
        for event in ports:
            filename=event.get('rtl_source');port=event.get('rtl_port');module=event.get('rtl_module')
            if not filename or filename not in calendar['source_sha256']or not port or not module or not event.get('rtl_instance'):
                raise ScheduleError('actual microevent lacks source-pinned RTL port binding')
            source=(ROOT/filename).read_text()
            import re
            if not re.search(r'\b'+re.escape(port)+r'\b',source)or not re.search(r'\bmodule\s+'+re.escape(module)+r'\b',source):
                raise ScheduleError('emitted event does not map to selected actual RTL module/port')
            if not event.get('requires')and not event.get('produces'):
                raise ScheduleError('actual microevent lacks immutable operand/result identity')


def build(program_bytes,descriptors,calendar,stage,me_clock,su_clock,xpf_rows,xpf_stop,collective_clock=None,segment_profile=None,*,format_only=False):
    program=[int(word,16)for word in program_bytes.decode().split()]
    if not 0<len(program)<60 or any(not 0<=w<1<<1024 for w in program):
        raise ScheduleError('dense image program exceeds real instruction reservation')
    pins=calendar.get('program_sha256',{})
    pin=pins.get(stage) if isinstance(pins,dict) else (pins[stage] if stage<len(pins) else None)
    if pin!=hashlib.sha256(program_bytes).hexdigest():
        raise ScheduleError('dense calendar is not bound to actual source program bytes')
    if len(descriptors)!=8 or any(not 0<=w<1<<64 for w in descriptors):
        raise ScheduleError('dense image needs eight explicit actual descriptor words')
    if not 1<=len(xpf_rows)<=4 or not 0<xpf_stop<1<<32:
        raise ScheduleError('dense image needs actual1..4 XPF records and stop32')
    if segment_profile is None and not format_only:
        raise MissingPhysicalProfile(['segment_profile'])
    if not format_only:validate_program_calendar(program,calendar,stage)
    lowered=None if format_only else segment_pw_image(program_bytes,descriptors,stage,segment_profile)
    image=[0]*1024
    for pc,word in enumerate(program):
        for beat in range(16):image[pc*16+beat]=(word>>(beat*64))&((1<<64)-1)
    for write in pw_image(calendar,stage,me_clock,su_clock,len(program)):
        image[write['address']]=int(write['data_hex'],16)
    if collective_clock is None:
        raise ScheduleError('dense image requires actual fixed collective calendar/route clock')
    period=collective_clock['period_fs'];phase=collective_clock['phase_fs']
    if period<=0 or not 0<=phase<period:
        raise ScheduleError('invalid actual collective scheduler clock')
    collective=[]
    for event in calendar['events']:
        if event.get('kind')!='collective_command' or event['stage']!=stage:continue
        time=event['time_fs']
        if time<phase or (time-phase)%period:
            raise ScheduleError('collective command does not align with actual assigned clock')
        collective.append(dict(event,core_cmd_cycle=(time-phase)//period))
    if lowered is not None:
        actual=[(e['core_cmd_cycle'],e['words'],e['mode'],e['tag'])for e in lowered['collective']]
        supplied=[(e['core_cmd_cycle'],e['words'],e['mode'],e['tag'])for e in collective]
        if actual!=supplied:raise ScheduleError('collective events differ from actual source DW segment operations')
        for write in lowered['writes']:image[write['address']]=int(write['data_hex'],16)
    for write in collective_pw_image(collective,collective_clock['stage_start_cycle'],
            collective_clock['relay_edges'],collective_clock['stop_cycle'],len(program),
            collective_clock['command_pin_edges']):
        image[write['address']]=int(write['data_hex'],16)
    for n,row in enumerate(xpf_rows):
        value=int(row['cfg_data_hex'],16)
        if not 0<=value<1<<188 or not value&1 or (value>>86)&63!=stage:
            raise ScheduleError('dense XPF row exceeds actual188-bit stage encoding')
        for beat in range(3):image[1004+3*n+beat]=(value>>(64*beat))&((1<<64)-1)
    cap=native_capability(program,stage)
    image[1022]=(0x58504654<<32)|xpf_stop
    image[1023]=(0x58504631<<32)|(int(cap)<<12)|(stage<<6)|(len(xpf_rows)<<2)|2
    digest=0x51484f5354505247
    writes=[dict(desc=0,address=n,data_hex=f'{v:016x}')for n,v in enumerate(image)]+[dict(desc=1,address=n,data_hex=f'{v:016x}')for n,v in enumerate(descriptors)]
    for write in writes:
        digest=((digest<<7)|(digest>>57))&((1<<64)-1)
        digest^=int(write['data_hex'],16)^(write['desc']<<10)^write['address']
    return dict(schema='opentallas.qwen-dense-program-image.v1',stage=stage,
                source_program_sha256=pin,fused_native59_capability=cap,
                PW_count=1024,DW_count=8,collective_command_count=len(collective),collective_PW_window=[944,960],authorized_digest_hex=f'{digest:016x}',
                writes=writes,footer_hex=f'{image[1023]:016x}',
                segment_calendar=None if lowered is None else lowered,
                status='FORMAT_FIXTURE_NOT_PRODUCTION_INSTALLABLE'if format_only else 'SOURCE_AND_PHYSICAL_PROFILE_BOUND_RECEIVER_WITNESSES_REQUIRED')
