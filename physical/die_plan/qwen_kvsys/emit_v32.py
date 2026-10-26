#!/usr/bin/env python3
"""KV-P3 10-23: stage 2 of plan v3.2 = emit_v31 on the v3.2 as-built view (import plan_v32 patches plan_v31)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_v32  # noqa: E402,F401  (patches plan_v31.rewrite_asbuilt / assign_blocks)
import emit_v31  # noqa: E402

if __name__ == '__main__':
    emit_v31.main()
