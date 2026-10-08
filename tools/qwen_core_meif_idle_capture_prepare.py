#!/usr/bin/env python3
"""Prepare fullshape MEIF speculative capture with complete pending-packet hold."""
import sys
from pathlib import Path
import qwen_core_kv_boundary_prepare as K
import qwen_core_meif_idle_capture as Q

def main():
    original=K.K.apply
    K.K.apply=lambda text:Q.apply(original(text))
    out=Path(sys.argv[sys.argv.index('--out')+1]);K.main()
    prep=out/'prepare.ys'
    prep.write_text('\n'.join(x+' -chparam DEC_LA_MEIF_IDLE_CAPTURE 1' if x.startswith('hierarchy ') else x for x in prep.read_text().splitlines())+'\n')

if __name__=='__main__':main()
