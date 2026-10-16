"""Encode actual S81 fixed-issue PW36 records; gate native dispatch separately."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81_compile_schedule'))
from compile_calendar import compile_program,validate_evidence,issuer_done_row,ISSUE_TO_CMD_PIN_EDGES


def encode_program(rows,stage,phase):
    if type(stage)is not int or not 0<=stage<128 or type(phase)is not int or not 0<=phase<4:
        raise ValueError('actual stage7 and clock phase2 required')
    if not 1<len(rows)<=128:
        raise ValueError('nonempty native calendar plus END must fit128 rows')
    end=[r for r in rows if r['engine']==15];kit=[r for r in rows if r['engine']==14]
    commands=[r for r in rows if r['engine']<14]
    if len(end)!=1 or len(kit)>1 or not commands:
        raise ValueError('one END, at most one KIT and actual commands required')
    slots=set();done_slots=set()
    for r in rows:
        if any(type(r[k])is not int or r[k]<0 for k in ('engine','arg','issue','done')):
            raise ValueError('integer native calendar fields required')
        if r['engine'] not in list(range(16)) or r['arg']>=1<<24 or max(r['issue'],r['done'])>=1<<24:
            raise ValueError('calendar field exceeds actual native width')
        if r['engine']<14:
            # Rows may carry the owner's measured command-pin -> done-pin latency;
            # the done row must then be exactly issue + 1 + latency (every engine).
            if 'pin_to_pin' in r and r['done']!=issuer_done_row(r['issue'],r['pin_to_pin']):
                raise ValueError('done row must equal issue + 1 + command-pin -> done-pin latency')
            if r['done']<=r['issue'] or r['done']>=end[0]['issue']:
                raise ValueError('native completion must precede fixed END')
            for target,key in [(slots,(r['engine'],r['issue'])),(done_slots,(r['engine'],r['done']))]:
                if key in target:raise ValueError('native pin event collision')
                target.add(key)
        elif r['arg'] or r['done'] or r['engine']==14 and r['issue']>=end[0]['issue']:
            raise ValueError('invalid KIT/END metadata')
    header=(len(rows)<<9)|(phase<<7)|stage
    writes=[(0,(3<<26)|header)]
    for index,r in enumerate(rows):
        packed=r['arg']|(r['engine']<<24)|(r['issue']<<28)|(r['done']<<52)
        writes += [(index,(page<<26)|((packed>>(26*page))&((1<<26)-1))) for page in range(3)]
    writes.append((0,(3<<26)|(1<<25)|header))
    return dict(length=len(rows),stage=stage,start_phase=phase,rows=rows,
                writes=[dict(address=a,data=d,word=(a<<28)|d) for a,d in writes],
                command_abi='opentallas.s81.cmd84.v1',pw_abi='opentallas.s81.fixed-pw36.v1',
                pin_origin='one stream clock after sampled job_v',seal_to_arm_stream_cycles=129,qualified=False)


def validate_launches(rows,launches):
    """Check the compiler-owned two-context launch edges, never choose edges."""
    if not isinstance(launches,list) or not launches:
        raise ValueError('explicit immutable context_launch_cycles required')
    if any(type(t)is not int or t<0 for t in launches) or launches!=sorted(set(launches)):
        raise ValueError('context launch edges must be distinct sorted integers')
    if any((t-launches[0])%4 for t in launches):
        raise ValueError('context launches must retain the programmed stream phase')
    end=next(r['issue']for r in rows if r['engine']==15)
    issue=set();done=set();kit=set()
    for j,t in enumerate(launches):
        if j>=2 and t<=launches[j-2]+end:
            raise ValueError('compiler launch overwrites a live physical context')
        for r in rows:
            if r['engine']<14:
                for occupied,key in [(issue,(t+r['issue'],r['engine'])),(done,(t+r['done'],r['engine']))]:
                    if key in occupied:raise ValueError('cross-context native pin event collision')
                    occupied.add(key)
            if r['engine']==14:
                # Fixed fast->serial alternating mailbox requires enough
                # source separation to observe each toggle; production must
                # also supply its measured physical phase/launch contract.
                edge=t+r['issue']
                if any(abs(edge-old)<4 for old in kit):
                    raise ValueError('KIT launch violates fixed serial return spacing')
                kit.add(edge)
    return launches

def emit_native(program,binding,contract,stage,phase,root=ROOT):
    """No unsupported endpoint, constant or physical phase may emit dispatch."""
    rejected=[]
    checked=compile_program(program,binding,contract,root)
    if not checked['dispatch_eligible']:
        rejected.append('native operand/service calendar is incomplete')
    clock=contract.get('native_clock_epoch',{})
    try:
        if clock.get('physical_phase_qualified')is not True or clock.get('phase_modulus_stream')!=4:
            raise ValueError('actual bounded/resettable physical clock epoch missing')
        validate_evidence(clock.get('evidence'),root)
    except (ValueError,KeyError,TypeError,OSError)as exc:rejected.append(str(exc))
    rows=[]
    for op in program['ops']:
        owner=binding.get('jobs',{}).get(op['id'],{})
        try:
            if owner.get('command_abi')!='opentallas.s81.cmd84.v1' or owner.get('integration_ready')is not True:
                raise ValueError('native endpoint command integration missing')
            if owner.get('timing_boundary')!='sequencer_cmd_pin_to_done_pin':
                raise ValueError('internal/fixture timings cannot become command-pin calendar')
            if owner.get('clock_domain')!='stream':
                raise ValueError('serial endpoint needs actual fixed-phase command adapter')
            arg=owner['arg']
            if type(arg)is not int or not 0<=arg<1<<24:raise ValueError('actual owned native arg24 missing')
            validate_evidence(owner.get('evidence'),root)
            latency=owner['duration_cycles']
            if op['end']!=issuer_done_row(op['start'],latency):
                raise ValueError('scheduled done row is not issue + 1 + measured pin-to-pin latency')
            rows.append(dict(id=op['id'],engine=op['port'],arg=arg,issue=op['start'],
                             done=issuer_done_row(op['start'],latency),pin_to_pin=latency))
        except (ValueError,KeyError,TypeError,OSError)as exc:rejected.append(op['id']+': '+str(exc))
    for name,tensor in binding.get('tensors',{}).items():
        if tensor.get('source')=='resident_constant' and tensor.get('native_boot_bound')is not True:
            rejected.append(name+': resident constant lacks actual boot/ROM producer')
        if tensor.get('source')=='external_input' and (tensor.get('external_boundary')not in ('phy','off_chip') or tensor.get('native_ingress_bound')is not True):
            rejected.append(name+': input lacks actual external boundary ingress')
    if rejected:return dict(status='STATIC_NATIVE_PROGRAM_BLOCKED',dispatch_eligible=False,rejections=rejected,writes=[],qualified=False)
    stop=max(r['done']for r in rows)+2
    if 'kit_cycle'in binding:rows.append(dict(engine=14,arg=0,issue=binding['kit_cycle'],done=0))
    rows.append(dict(engine=15,arg=0,issue=stop,done=0))
    try:
        encoded=encode_program(rows,stage,phase)
        encoded['context_launch_cycles']=validate_launches(rows,binding.get('context_launch_cycles'))
    except ValueError as exc:return dict(status='STATIC_NATIVE_PROGRAM_BLOCKED',dispatch_eligible=False,rejections=[str(exc)],writes=[],qualified=False)
    return dict(encoded,status='STATIC_NATIVE_PROGRAM_COMPILED',dispatch_eligible=True,
                note='Actual RTL replay and physical timing still required; compilation alone is not qualification.')
