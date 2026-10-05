"""Accepted 256B baseline image from existing golden 136B logical records.

Reuse the unchanged logical parser, not the rejected compact-sector layout.
No runtime arithmetic, new engine, or transport adoption occurs here.
"""
import hashlib
from pathlib import Path
from w19_payload_loader import logical_records


def load_image(source, output, *, expected_sha256, payloads, expert_id,
               base_line, expert_stride_lines, sm_offset_lines):
    source, output = Path(source), Path(output)
    if type(payloads) is not int or not 1 <= payloads <= 65535//2:
        raise ValueError('Payload descriptor exceeds two-line baseline port')
    lines = payloads*2
    if not 0 <= expert_id < 384 or not 0 <= sm_offset_lines <= 65535:
        raise ValueError('Invalid expert/SM descriptor')
    if not 0 <= base_line or not sm_offset_lines+lines <= expert_stride_lines <= 65535:
        raise ValueError('Operation segment outside baseline expert stride')
    first = (base_line+expert_id*expert_stride_lines+sm_offset_lines)*4
    if first+lines*4 > 1<<24:
        raise ValueError('Baseline sector address overflow')
    def source_hash():
        return hashlib.sha256(source.read_bytes()).hexdigest()
    if source_hash() != expected_sha256:
        raise ValueError('Source hash mismatch')
    created = False
    try:
        with output.open('x') as out:
            created = True
            out.write(f'@{first:06x}\n')
            count=0
            for record in logical_records(source):
                if count >= payloads:
                    raise ValueError('Extra record')
                padded=record+bytes(120)
                for index in range(0,256,32):
                    out.write(f'{int.from_bytes(padded[index:index+32],"little"):064x}\n')
                count+=1
            if count != payloads or source_hash() != expected_sha256:
                raise ValueError('Missing record or changed source')
    except BaseException:
        if created: output.unlink()
        raise
    return dict(format='accepted_256B_128weights_8exponents_120pad',source_sha256=expected_sha256,
                image_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),payloads=payloads,
                first_sector=first,sector_count=lines*4,cfg_lines=lines,
                cfg_base=base_line,cfg_exp_lines=expert_stride_lines,cfg_off=sm_offset_lines,
                compact_adapter=False,scope='host loader; existing256B fetch/SM baseline only')
