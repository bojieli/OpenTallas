#!/usr/bin/env python3
"""failure_breakdown.py -- the ONE canonical entry for the hourly failure breakdown (FLOW-NOADV-R2 11-20, COORD).

The real program lives in the hub coordination repo, ~/coord/tools/failure_breakdown.py on intel2 (it reads ~/coord/autopilot/
kit_wave_stages.tsv and rewrites the BREAKDOWN block of ~/coord/RELEASE_TREE.md); it was never part of this repository, so a
checkout or rt/current has no copy.  This wrapper finds it and runs it: locally when ~/coord/tools has it (the hub), else over
ssh on the hub host (OT_COORD_HUB, default intel2).

  python3 -I tools/failure_breakdown.py            run it (rewrites the BREAKDOWN block of RELEASE_TREE.md, as the hourly job does)
  python3 -I tools/failure_breakdown.py --where    print the program that would run, run nothing
"""
import os
import subprocess
import sys

REL = "tools/failure_breakdown.py"


def hub_path(home=None):
    """the local hub copy, or None"""
    p = os.path.join(os.path.expanduser(home or "~"), "coord", REL)
    return p if os.path.isfile(p) else None


def command(argv, home=None, hub=None):
    """-> argv list that runs the real program"""
    local = hub_path(home)
    if local:
        return [sys.executable, "-I", local, *argv]
    host = hub or os.environ.get("OT_COORD_HUB", "intel2")
    return ["ssh", "-o", "ControlPath=none", host, "python3", "-I", f"~/coord/{REL}", *argv]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ["--where"]:
        print(hub_path() or f"ssh {os.environ.get('OT_COORD_HUB', 'intel2')}:~/coord/{REL}")
        return 0
    return subprocess.call(command(argv))


if __name__ == "__main__":
    sys.exit(main())
