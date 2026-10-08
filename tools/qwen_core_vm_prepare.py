#!/usr/bin/env python3
"""Prepare paired raw-write/direct-lease core. Requires actual VM caller binding.

This prepares the source prerequisite only. A standalone core route cannot
qualify the moved write collar, original intent, native clock or ACK contract.
"""
import sys
from pathlib import Path
import qwen_core_kv_boundary_prepare as K
import qwen_core_vm_raw_boundary as W
import qwen_core_vm_lease as L

def main():
    enabled='--vm-owned' in sys.argv
    if enabled:
        sys.argv.remove('--vm-owned')
        original=K.K.apply
        K.K.apply=lambda text:L.apply(W.apply(original(text)))
    out=Path(sys.argv[sys.argv.index('--out')+1])
    K.main()
    if enabled:
        prep=out/'prepare.ys'
        prep.write_text('\n'.join(x+' -chparam VM_OWNED_RAW 1 -chparam VM_OWNED_LEASE 1' if x.startswith('hierarchy ') else x for x in prep.read_text().splitlines())+'\n')

if __name__=='__main__':main()
