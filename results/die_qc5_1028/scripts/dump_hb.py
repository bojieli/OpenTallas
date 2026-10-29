#!/usr/bin/env python3
"""DIE-QC-5 diagnostic: run main die_sta_related unchanged, but pickle the per-endpoint-path (setup, hold) records that
main passes to hold_buffer_model (classes intra/seam), plus intra_bits.  usage: dump_hb.py TOOLS_DIE_PLAN OUT.pkl -- ARGS"""
import sys, pickle
tools, outp = sys.argv[1], sys.argv[2]
args = sys.argv[sys.argv.index("--") + 1:]
sys.path.insert(0, tools)
import die_sta_related as dsr
store = {}
orig = dsr.hold_buffer_model
def wrap(tt, ff, bits=None, hb=dsr.HB4, part_bits=None):
    store.setdefault("calls", []).append(dict(tt=dict(tt), ff=dict(ff), bits=bits, part_bits=part_bits, hb=hb))
    return orig(tt, ff, bits=bits, hb=hb, part_bits=part_bits)
dsr.hold_buffer_model = wrap
try:
    dsr.main(args)
finally:
    pickle.dump(store, open(outp, "wb"))
