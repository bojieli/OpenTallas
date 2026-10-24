#!/usr/bin/env python3
"""KV-P3b 10-23: stage 2 of plan v3.4 = v3.3 (host TX FDI split-bus fix) + COORD R3: ft stations at most
budgets.ft_station_max_um = 750 um apart (emit_v31.ST_MAX; v3.3 used the 1.2 mm reach)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_v33  # noqa: E402,F401
import emit_v31  # noqa: E402

emit_v31.ST_MAX = 750.0

if __name__ == '__main__':
    emit_v31.main()
