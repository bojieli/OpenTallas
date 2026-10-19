#!/usr/bin/env python3
"""Mechanism fixture; not the production full-body programme."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/qwen_layerbench'))
from calendar_rom_image import compile_image,emit
segments={k:[] for k in ('boot','init','decode','head')}
for s,n in [('boot',3),('init',3),('decode',390),('head',383)]:
    segments[s]=[(1+i%4000,((i+1)<<80)|((i+7)<<7)|1) for i in range(n)]
r,w=compile_image(segments,'1'*64)
emit(sys.argv[1],r,w)
