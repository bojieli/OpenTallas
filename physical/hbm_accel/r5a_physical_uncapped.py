#!/usr/bin/env python3
"""R5a-only uncapped synthesis/route entry point; preserve shared launchers.

Admission and NUM_CORES still govern host capacity. The owner prohibits guessed
wall-time ceilings for this 1.3M-cell element. The inherited driver's six-hour
route and two-hour synthesis defaults must not kill a progressing job.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import run_abi3_physical as driver
import run_abi3_physical_aligned as aligned


def main():
    # subprocess.run(timeout=None) waits for actual completion. These overrides
    # apply only to this process, leaving pinned driver files byte-identical.
    driver.flow_timeout_seconds = lambda: None
    driver.synth_timeout_seconds = lambda: None
    return aligned.main()


if __name__ == "__main__":
    sys.exit(main())
