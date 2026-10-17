"""Source-bound dense1024PW+8DW image for the real ascending HOST loader.

Actual PW0 clears the receiving control stores. Footer1023 seals them after
all calendar/CP/XPF rows. Its capability is derived from the actual source
native instruction and is covered by the authorized whole-image digest.
"""
import hashlib
import json
from pathlib import Path
from .calendar import ScheduleError
from .issue_rom import pw_image
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


def build(program_bytes,descriptors,calendar,stage,me_clock,su_clock,xpf_rows,xpf_stop):
    program=[int(word,16)for word in program_bytes.decode().split()]
    if not 0<len(program)<61 or any(not 0<=w<1<<1024 for w in program):
        raise ScheduleError('dense image program exceeds real instruction reservation')
    pins=calendar.get('program_sha256',{})
    pin=pins.get(stage) if isinstance(pins,dict) else (pins[stage] if stage<len(pins) else None)
    if pin!=hashlib.sha256(program_bytes).hexdigest():
        raise ScheduleError('dense calendar is not bound to actual source program bytes')
    if len(descriptors)!=8 or any(not 0<=w<1<<64 for w in descriptors):
        raise ScheduleError('dense image needs eight explicit actual descriptor words')
    if not 1<=len(xpf_rows)<=4 or not 0<xpf_stop<1<<32:
        raise ScheduleError('dense image needs actual1..4 XPF records and stop32')
    image=[0]*1024
    for pc,word in enumerate(program):
        for beat in range(16):image[pc*16+beat]=(word>>(beat*64))&((1<<64)-1)
    for write in pw_image(calendar,stage,me_clock,su_clock,len(program)):
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
                PW_count=1024,DW_count=8,authorized_digest_hex=f'{digest:016x}',
                writes=writes,footer_hex=f'{image[1023]:016x}',
                status='SOURCE_FORMAT_ONLY_UNTIL_NATIVE_MICROCALENDAR_PHYSICAL_AND_RECEIVER_WITNESSES')
