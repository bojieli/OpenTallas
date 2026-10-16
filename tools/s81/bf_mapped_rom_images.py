#!/usr/bin/env python3
"""Convert declared external synthetic ROM stimuli to the real macro's via mask.

No DUT callback or arithmetic. The original C++ table is used only offline to
form immutable ROM contents for the physical 4096x274 mux8 macro model.
"""
from pathlib import Path
import hashlib,json,re


def write_images(cpp, out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    table=cpp.split('extern "C" void v41rt_rom_read',1)[1]
    banks=[[0]*8192 for _ in range(2)]
    count=0
    for number,body in re.findall(r'case (\d+): (.*?) break;',table):
        number=int(number);value=0
        for i,v in re.findall(r'q\[(\d+)\]=0x([0-9a-fA-F]+)u;',body):value|=int(v,16)<<(32*int(i))
        assert value < 1<<274
        banks[number//8192][number%8192]=value;count+=1
    assert count>0
    records={}
    for bank in range(2):
        for parity in range(2):
            rows=[0]*512
            for addr in range(4096):
                value=banks[bank][2*addr+parity];row,sel=divmod(addr,8)
                for bit in range(274):rows[row]|=((value>>bit)&1)<<(8*bit+sel)
            name=f'bf{"b" if bank else ""}_{parity}.viamap.hex'
            data=''.join(f'{v:0548x}\n' for v in rows)
            (out/name).write_text(data);records[name]=hashlib.sha256(data.encode()).hexdigest()
    rec={'scope':'external immutable synthetic ROM stimulus, actual mapped model consumes via mask',
         'model':'physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v',
         'input_cpp_sha256':hashlib.sha256(cpp.encode()).hexdigest(),'nonzero_table_rows':count,'images':records}
    (out/'manifest.json').write_text(json.dumps(rec,indent=2)+'\n');return rec
