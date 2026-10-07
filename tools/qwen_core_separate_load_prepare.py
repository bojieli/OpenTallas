#!/usr/bin/env python3
"""Real controller prep with specialized opaque interfaces and opt-in LOAD cut."""
import sys
from pathlib import Path
import qwen_rom_core_ctx_claude as C
import qwen_core_separate_load as S
import qwen_core_opaque_interfaces as O

def main():
    enabled='--separate-load' in sys.argv
    if enabled:sys.argv.remove('--separate-load')
    out=Path(sys.argv[sys.argv.index('--out')+1])
    if enabled:
        original=C.core_text
        C.core_text=lambda *a,**k:S.apply(original(*a,**k))
    C.main()
    prep=out/'prepare.ys'
    if enabled:
        lines=prep.read_text().splitlines()
        prep.write_text('\n'.join(x+' -chparam DEC_LA_SEPARATE_LOAD 1' if x.startswith('hierarchy ') else x for x in lines)+'\n')
    O.rewrite(prep)

if __name__=='__main__':main()
