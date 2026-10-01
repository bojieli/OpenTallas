#!/usr/bin/env python3
"""CLI-only companion: preserve pinned driver and split Verilator jobs operand."""
import re,sys
import w17_current_fastpp_die_rt as base

def compiler_argv(cmd):
    out=list(map(str,cmd))
    if out and 'verilator' in out[0].lower():
        corrected=[]
        for token in out:
            m=re.fullmatch(r'-j([1-9][0-9]*)',token)
            corrected.extend(['-j',m.group(1)] if m else [token])
        out=corrected
    return out

_original_run=base.run
def run(cmd,log,cwd=None):return _original_run(compiler_argv(cmd),log,cwd)
base.run=run
all_sources=base.all_sources
if __name__=='__main__':sys.exit(base.main())
