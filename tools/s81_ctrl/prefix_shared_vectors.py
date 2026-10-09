"""Scoped full1280 synthetic mechanism; golden calls preserve all four adds."""
import sys,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hdc_golden import add,to_bf16
import numpy as np
inputs=np.array([int(x,16) for x in Path('inputs.hex').read_text().split()],dtype=np.uint32).reshape(3,1280)
inputs[:,0]=[0x3f800000,0x3b800000,0]
shared=np.full(1280,0x3b800000,dtype=np.uint32)
y=np.zeros(1280,dtype=np.float32)
for e in range(3):y=add(y,inputs[e].view(np.float32))
y=to_bf16(add(y,shared.view(np.float32))).view(np.uint32)
Path('inputs.hex').write_text(''.join(f'{x:08x}\n' for x in inputs.flat))
Path('shared.hex').write_text(''.join(f'{x:08x}\n' for x in shared))
Path('final.hex').write_text(''.join(f'{x:08x}\n' for x in y))
