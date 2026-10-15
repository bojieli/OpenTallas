#!/usr/bin/env python3
import sys
from pathlib import Path
from sfu_control_image import encode
from sfu_vector_calendar import compile_vector
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
for case in range(4):
    count=(4096 if case==0 else 7168)*(4 if case==3 else 1)
    program=compile_vector(words=count,bases=(0,16384,32768,49152,131072),
                           m1=case%3,m2=case%2,ad=case%3,
                           sfu=(1,4,5,0)[case],e1=case%2,e2=case%2)
    words=encode(program)
    if len(words)>4096:raise ValueError('gate image too large')
    words+= [words[-1]]*(4096-len(words))
    (out/f'case{case}.hex').write_text(''.join(f'{word:0436x}\n' for word in words))
