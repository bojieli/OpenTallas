"""Off-default, source-layout-driven allocation helper for the native selected-VM successor.

C occupies [0,4MiB), B's optional window [4MiB,4.25MiB), and actual compiler
scratch follows the window. Capacities admit K2048; this does not change runtime K
or prove a producer/consumer implementation. Default calls preserve the program.
"""
import copy
from dataclasses import asdict
from hgi_sim.records import decode_one, encode_program

MIB = 1 << 20
VM_BYTES = 8*MIB
WINDOW_BASE = 4*MIB
WINDOW_BYTES = 128*512*4
SCRATCH_BASE = WINDOW_BASE + WINDOW_BYTES


def plan(source_layout, max_selected=2048):
    if not 1 <= max_selected <= 2048:
        raise ValueError('selected capacity outside qualified sizing envelope')
    sizes = dict(source_layout.SIZES)
    for name in ('SC', 'E', 'EB'):
        sizes[name] = max(sizes[name], 128+max_selected)
    for name in ('SELT', 'OWNL'):
        sizes[name] = max(sizes[name], max_selected)
    canonical = [n for n in sizes if n not in ('ea','eg_kv','eg_rows')] + source_layout.ALIAS_SPAN
    new, spans, cur = {}, [], SCRATCH_BASE//4
    for name in canonical:
        cur = ((cur+63)//64)*64
        count = sizes.get(name, 2304 if name.endswith(('.g','.u')) else source_layout.SIZES['x'])
        new[name] = cur
        spans.append(dict(name=name, old_base=source_layout.vm[name], new_base=cur, old_words=source_layout.SIZES.get(name,count), words=count))
        cur += count
    new['CANDT'] = new['zpart']; new['GALL'] = new['ea']
    if cur*4 > VM_BYTES:
        raise ValueError('scratch exceeds8MiB')
    return dict(vm_bytes=VM_BYTES,max_selected=max_selected,selected=dict(base=0,bytes=4*MIB),
                window=dict(base=WINDOW_BASE,bytes=WINDOW_BYTES),scratch=dict(base=SCRATCH_BASE,end=cur*4),
                spans=spans,new_bases=new,required_score_words=128+max_selected,
                qualified=False,reason='Capacity/bounds only; native producer, consumer ACK/ECC and physical gates required')


def relocate_word(address, allocation):
    for span in allocation['spans']:
        if span['old_base'] <= address < span['old_base']+span['old_words']:
            return span['new_base']+address-span['old_base']
    raise ValueError(f'VM address {address} outside actual source allocation')


def _vm_last(desc):
    return desc.base + (desc.m-1)*(desc.stride or desc.n) + (0 if desc.ibcast else (desc.n-1)*(desc.istride or 1))


def check_record(record, allocation, both_selected=False):
    for name, desc in record.desc.items():
        if desc.space == 'VM':
            last=_vm_last(desc)
            if desc.base < SCRATCH_BASE//4 or last >= VM_BYTES//4:
                raise ValueError(f'{record.tag}:{name} VM descriptor outside scratch bounds')
            ranges=[(s['new_base'],s['new_base']+s['words']) for s in allocation['spans']]
            if record.tag.startswith('row_gather.'):
                ranges.append((allocation['new_bases']['GALL'],allocation['new_bases']['GALL']+96*2*512))
            if not any(lo <= desc.base <= last < hi for lo,hi in ranges):
                raise ValueError(f'{record.tag}:{name} descriptor exceeds its allocated live buffer')
        if record.unit == 'ATT' and name in ('B','C') and (name=='C' or both_selected):
            if desc.space != 'HBM' or desc.fmt != 'FP32' or desc.stride != 2048:
                raise ValueError('Selected-reader ABI uses SPACE0 byte base, FP32 and2048-byte row stride')
            rows=desc.n
            lo, hi = (0, 4*MIB) if name=='C' else (WINDOW_BASE,SCRATCH_BASE)
            if not lo <= desc.base or desc.base+rows*2048 > hi:
                raise ValueError(f'{record.tag}:{name} selected byte range overlaps another allocation')
    if record.unit=='CTL' and record.op=='LOOP' and record.param & (1<<17):
        if not SCRATCH_BASE//4 <= record.imm_a < VM_BYTES//4:
            raise ValueError('VM-count pointer outside scratch')


def allocate(program, source_layout, enabled=False, both_selected=False, max_selected=2048):
    """Relocate an exported program for fixture generation; never adopt native producer implicitly.

    ATT SPACE0 is preserved as a packed byte-address selected-reader ABI. The caller
    must bind qualified native publication to C and (if requested) populate B's window.
    This helper intentionally makes no producer substitution or runtime K change.
    """
    out=copy.deepcopy(program)
    if not enabled:
        return out, None
    allocation=plan(source_layout,max_selected)
    inventory=[]
    for layer in out['layers']:
        for item in layer['records']:
            r,_=decode_one(bytes.fromhex(item['hex']),0)
            r.tag=item['tag']
            old_pointer=None
            if r.tag.startswith('row_gather.list') and 'I' in r.desc:
                old_pointer=r.desc['I'].base+r.desc['I'].stride
            for desc in r.desc.values():
                if desc.space=='VM':
                    old_last=_vm_last(desc)
                    first=relocate_word(desc.base,allocation)
                    last=relocate_word(old_last,allocation)
                    if last-first != old_last-desc.base:
                        raise ValueError('Descriptor crosses source allocations that changed relative spacing')
                    desc.base=first
            if old_pointer is not None:
                r.desc['I'].stride=relocate_word(old_pointer,allocation)-r.desc['I'].base
            if r.unit=='CTL' and r.op=='LOOP' and r.param & (1<<17):
                r.imm_a=relocate_word(r.imm_a,allocation)
            if r.unit=='ATT':
                if 'C' in r.desc:
                    r.desc['C'].base=0
                    item['reads']=sorted(set(item['reads'])|{'selected_vm_epoch'})
                if both_selected and 'B' in r.desc:
                    r.desc['B'].base=WINDOW_BASE
                    item['reads']=sorted(set(item['reads'])|{'window_vm_epoch'})
            check_record(r,allocation,both_selected)
            item['hex']=encode_program([r]).hex()
            if r.unit=='ATT':
                inventory.append(dict(layer=layer['layer'],tag=r.tag,descriptors={n:asdict(v) for n,v in r.desc.items()}))
    allocation['attention_descriptors']=inventory
    allocation['reuse_contract']='Producer overwrite waits prior epoch finalPV endpoint ACK; one common physical selected range hazard across source IDs, immutable snapshot QK throughPV, contextflush drains readers/writers'
    return out,allocation
