#!/usr/bin/env python3
# Operational runner: leave proof search running without an arbitrary subprocess deadline.
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import strap_lec as SL
orig=SL.run_lec
def run_unbounded(work,files,libs,gold,gate,seq,image,timeout,leaves=()):
    return orig(work,files,libs,gold,gate,seq,image,None,leaves)
SL.run_lec=run_unbounded
sys.exit(SL.main())
