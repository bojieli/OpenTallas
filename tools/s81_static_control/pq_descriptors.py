"""PW-loaded real PQ command descriptors. No fixture fields or timing inference.

Owners supply the actual phase-ROM identity, native scalar addresses, and a
measured command-pin-to-observed-END duration. Missing physical/static-control
and operand bindings remain explicit dispatch blockers, even when image encoding
is useful for the component hardware gate.
"""
from pathlib import Path
import hashlib
import json
import argparse
FIELDS=[('ph',9),('np',3),('xbase',19),('xps',19),('obase',19),('ops',19),('fmt',2)]


def encode_descriptors(rows, phase_width=9):
    if phase_width not in (9,10):
        raise ValueError("actual supported PQ phase width9 or10 required")
    fields=[(key,phase_width if key=="ph" else width) for key,width in FIELDS]
    native_bits=81+phase_width
    if not isinstance(rows,list) or not 1<=len(rows)<=64:
        raise ValueError('one to64 actual PQ descriptors required')
    words=[(7<<25)|len(rows)]
    for index,row in enumerate(rows):
        if set(row)!=set(k for k,_ in FIELDS)|{'observed_end_edges','native_tag'}:
            raise ValueError('every actual native field and observed END duration required')
        cfg=0;shift=0
        for key,width in fields:
            value=row[key]
            if type(value)is not int or not 0<=value<1<<width:
                raise ValueError('native PQ field bounds: '+key)
            cfg|=value<<shift;shift+=width
        duration=row['observed_end_edges']
        if type(duration)is not int or not 3<=duration<1<<24:
            raise ValueError('actual command-to-observed-END24 required')
        tag=row['native_tag']
        if type(tag)is not int or not 0<=tag<4:raise ValueError('actual compiler-selected native tag2 required')
        packed=cfg|(duration<<native_bits)|(tag<<(native_bits+24))
        words.extend((index<<28)|(page<<25)|((packed>>(24*page))&((1<<24)-1)) for page in range(5))
    words.append((7<<25)|(1<<24)|len(rows))
    return words


def compile_descriptors(request,root):
    rows=[];rejected=[];blocked=[]
    phase_width=request.get("phase_width",9)
    for item in request.get('descriptors',[]):
        name=item.get('id','<missing>')
        try:
            evidence=item['evidence']
            if not evidence:raise ValueError('actual source and measured timing evidence missing')
            for record in evidence:
                path=Path(root)/record['path']
                if hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:
                    raise ValueError('source-bound PQ evidence changed')
            if item['timing_boundary']!='sequencer_cmd_pin_to_observed_pq_END':
                raise ValueError('internal or fixture duration cannot be an endpoint deadline')
            if item['phase_rom_bound'] is not True or item['native_operand_bound'] is not True:
                raise ValueError('actual phase-ROM and operand producer binding required')
            row=item['fields'];encode_descriptors([row],phase_width=phase_width);rows.append(row)
            if item.get('physical_phase_qualified')is not True:blocked.append(name+': physical phase unqualified')
            if item.get('static_internal_pq_qualified')is not True:blocked.append(name+': internal PQ calendar unqualified')
            if item.get('count_live_profile_qualified')is not True:blocked.append(name+': count-live fill/drain unqualified')
        except (KeyError,ValueError,TypeError,OSError)as exc:rejected.append(name+': '+str(exc))
    if not rows:rejected.append('no actual PQ descriptors')
    return dict(command_table_eligible=not rejected,dispatch_eligible=not rejected and not blocked,
                qualified=False,rows=rows if not rejected else [],rejected=rejected,blockers=blocked,
                pw_words=encode_descriptors(rows,phase_width=phase_width)if not rejected else [],phase_width=phase_width,
                descriptor_abi=('s81.pq.command-endpoint.pw36.v1' if phase_width==9 else 's81.pq.command-endpoint.phw10.pw36.v2'),go_extra_edges=1,
                pin_origin='sampled cmd85 to registered f_iss GO plus1')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--request',type=Path,required=True)
    ap.add_argument('--root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    result=compile_descriptors(json.loads(a.request.read_text()),a.root)
    a.out.mkdir(parents=True,exist_ok=True);(a.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    if result['command_table_eligible']:(a.out/'descriptor.hex').write_text(''.join(f'{x:09x}\n' for x in result['pw_words']))
    raise SystemExit(0 if result['dispatch_eligible']else 2)

if __name__=='__main__':main()
