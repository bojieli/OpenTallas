"""OFF-by-default test encoding of accepted256B resident descriptors.

AW27 is an existing RTL parameter, priced at 5be9f42d2 before this gate.
This fragment interface cannot admit full residence or qualify physical ports.
The original AW24 loader stays byte-identical.
"""
import hashlib
from pathlib import Path
from w19_payload_loader import logical_records


def descriptor(row, expert_id, *, enable=False, address_bits=24):
    if not enable:
        raise ValueError('Resident fragment experiment is OFF')
    if address_bits not in (24, 27):
        raise ValueError('Only baseline24 and prebuild27 are qualified for this test')
    if row.get('expert_range') != [0,384] or type(expert_id) is not int or not 0 <= expert_id < 384:
        raise ValueError('Actual routed expert identity required')
    for k in ('rank','stack','sm','cfg_base_line','cfg_exp_lines','cfg_off','cfg_lines','payloads','resident_first_byte','resident_last_exclusive','byte_length','expert_stride_bytes'):
        if type(row.get(k)) is not int or row[k] < 0:
            raise ValueError('Invalid physical owner/address field: '+k)
    if not (row['rank'] < 96 and row['stack'] < 4 and row['sm'] < 32):
        raise ValueError('Invalid physical owner')
    sm=row['sm'];home=int(sm%8>=4)+2*int(sm//8>=2)
    if row['stack'] != home:
        raise ValueError('SM stack differs from placed quadrant')
    p=row['payloads'];stride=row['expert_stride_bytes']
    if not p or row['byte_length'] != p*256 or row['cfg_lines'] != p*2:
        raise ValueError('Require accepted256B two-line payloads')
    if stride != row['cfg_exp_lines']*128 or stride <= 0:
        raise ValueError('Expert stride differs from actual resident map')
    if row['resident_last_exclusive'] != row['resident_first_byte']+383*stride+p*256:
        raise ValueError('Affine resident extent changed')
    base=row['cfg_base_line'];off=row['cfg_off'];lines=row['cfg_lines']
    if off+lines > row['cfg_exp_lines'] or any(row[k] > 65535 for k in ('cfg_exp_lines','cfg_off','cfg_lines')):
        raise ValueError('16bit descriptor/segment overflow')
    if row['resident_first_byte'] != (base+off)*128:
        raise ValueError('Base/offset fails resident map roundtrip')
    first=(base+expert_id*row['cfg_exp_lines']+off)*4
    if base >= 1<<(address_bits-2) or first+lines*4 > 1<<address_bits:
        raise ValueError('Physical address overflow; no modulo/rebase/reload')
    return dict(first_sector=first,sector_count=lines*4,cfg_base=base,cfg_exp_lines=row['cfg_exp_lines'],cfg_off=off,cfg_lines=lines,
                address_bits=address_bits,fragment_only=True,resident_admitted=False)


def load_fragment(source, directory, row, expert_id, *, expected_sha256, enable=False, address_bits=24):
    """Preload once, full-address keys; no fetch-time reload or alias service."""
    d=descriptor(row,expert_id,enable=enable,address_bits=address_bits)
    source=Path(source);directory=Path(directory)
    digest=lambda:hashlib.sha256(source.read_bytes()).hexdigest()
    if digest()!=expected_sha256:raise ValueError('Logical source hash changed')
    keys=[];values=[];count=0
    for record in logical_records(source):
        if count>=row['payloads']:raise ValueError('Extra logical payload')
        padded=record+bytes(120)
        for j in range(8):
            keys.append(f"{d['first_sector']+count*8+j:08x}\n")
            values.append(f'{int.from_bytes(padded[j*32:(j+1)*32],"little"):064x}\n')
        count+=1
    if count!=row['payloads'] or digest()!=expected_sha256:raise ValueError('Missing/changed logical payload')
    paths=[directory/'sparse_keys.hex',directory/'sparse_values.hex']
    if any(p.exists() for p in paths):raise ValueError('Refusing to overwrite resident image')
    created=[]
    try:
        for path,text in zip(paths,(''.join(keys),''.join(values))):
            with path.open('x') as f:created.append(path);f.write(text)
    except BaseException:
        for path in created:path.unlink()
        raise
    return dict(d,physical_record_bytes=256,compact_adapter=False,logical_sha256=expected_sha256,
                image_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
