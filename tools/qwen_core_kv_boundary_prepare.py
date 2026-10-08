#!/usr/bin/env python3
"""Prepare the real fullshape banked-KV / registered-flush controller."""
import sys
from pathlib import Path
import qwen_core_separate_load_prepare as P
import qwen_core_kv_boundary as K

def main():
    if '--separate-load' not in sys.argv:raise SystemExit('KV successor requires separate-load')
    original=P.S.apply
    P.S.apply=lambda text:K.apply(original(text))
    out=Path(sys.argv[sys.argv.index('--out')+1])
    P.main()
    prep=out/'prepare.ys';lines=prep.read_text().splitlines()
    prep.write_text('\n'.join(x+' -chparam DEC_LA_KV_BANK 1' if x.startswith('hierarchy ') else x for x in lines)+'\n')

if __name__=='__main__':main()
