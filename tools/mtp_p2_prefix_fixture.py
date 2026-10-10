"""Deterministic BF16-widened numerical vehicle; not released expert evidence."""
import random,struct
from pathlib import Path
r=random.Random(417)
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def bits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def value(x):return struct.unpack('<f',struct.pack('<I',x))[0]
rows=[]
for e in range(3):
    row=[((r.randrange(2)<<31)|(r.randrange(120,133)<<23)|(r.randrange(128)<<16)) for i in range(1280)]
    row[0]=0x80000000 # +0 then three -0 must remain +0; copy-first mutant differs.
    rows.append(row)
gold=[]
for i in range(1280):
    y=0.0
    for e in range(3):y=f32(y+value(rows[e][i]))
    gold.append(bits(y))
Path('inputs.hex').write_text(''.join(f'{x:08x}\n' for row in rows for x in row))
Path('gold.hex').write_text(''.join(f'{x:08x}\n' for x in gold))
