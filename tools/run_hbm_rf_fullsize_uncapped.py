#!/usr/bin/env python3
"""Additive uncapped physical driver; original driver and RTL unchanged."""
import run_abi3_physical as D
import run_abi3_physical_aligned_guarded as G
# Preserve every engineering comparison and timing constraint. Only costly
# synthesis/route subprocess elapsed-time limits are removed.
D.synth_timeout_seconds=lambda:None
D.flow_timeout_seconds=lambda:None
if __name__=='__main__':raise SystemExit(G.main())
