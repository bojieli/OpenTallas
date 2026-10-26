#!/usr/bin/env python3
"""KV-P3b 10-23: stage 2 of plan v3.3 = emit_v31 on the v3.3 as-built view (import plan_v33 patches plan_v31)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_v33  # noqa: E402,F401
import emit_v31  # noqa: E402

if __name__ == '__main__':
    emit_v31.main()
