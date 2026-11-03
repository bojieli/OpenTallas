#!/usr/bin/env python3
"""DIE-KV-61/grt: start_stage_emit.py emit with MAX_ROW_TRIES raised (geometry-only search radius; plan 5fe0aa adp macro
row in hub_Wi leaves no legal 7-flop segment within 40 rows = 10.8 um of one START node cell).  Usage: emit_wide.py TRIES <emit args>"""
import sys
sys.path.insert(0, sys.argv[2]); del sys.argv[2]
import start_stage_emit as E
E.MAX_ROW_TRIES = int(sys.argv.pop(1))
sys.exit(E.main())
