#!/usr/bin/env python3
"""Qwen ROM token bench on the PARTITIONED core (qwen-missing 2026-10-07).

Builds the exactness harness's Qwen ROM plain-AR STREAM4 die (tools/exactness/qwen_rom_fulltoken.py) with the core
replaced by ot_qwen_rom_core_part (tools/qwen_missing/emit_partition.py): the controller (die master
qfd_sp_constants_sequencer), the matrix-engine spine (qfd_sp_tree_top) and the stream unit (qfd_sp_su64_sfu) as
three modules wired across the partition boundary.  The die files' four issue-stall observation counters read the
controller's state through core.<net>; in the partitioned build they read core.u_ctrl.<net> (copies of the two die
files, nothing else changed).  Everything else -- fixtures, host, checks -- is the harness's.

    partition_token.py build --variant part|base --build DIR [--jobs 16] [--dcu N --duc N --comp 0|1]
    partition_token.py run   --build DIR --work DIR --stages L0|full [--max-cycles N]
--dcu / --duc put pin stations on the controller -> unit / unit -> controller nets of the partition and --comp 1
adds the split-exact compensation (rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv); --comp 0 with
stations is the negative (must fail).  The build records its station configuration in build/STN.json.
The 'base' variant is the unmodified harness build from this tree (the same-tree reference for the comparison).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "exactness"))
sys.path.insert(0, str(ROOT / "tools" / "qwen_missing"))
import qwen_rom_fulltoken as F  # noqa: E402
import emit_partition as P  # noqa: E402

CTRL_NETS = ("st", "nx_v", "d_unit", "me_wsrc", "kv_gate", "su_ready", "su_idle", "me_idle", "d_barrier")


BASE_EMIT = F.EMIT.emit          # the unpatched core emitter (F.EMIT and P.EMIT are the same module object)
SPLIT_RTL = ROOT / "rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv"
STN = dict(dcu=0, duc=0, comp=1, su_ml=0, gq=0)


def part_core(text: str) -> str:
    core = BASE_EMIT(text)
    part = P.emit_part(core, **STN).replace("module ot_qwen_rom_core_part #(", "module ot_qwen_rom_core #(", 1)
    out = P.emit_ctrl(core) + "\n" + part + "\n" + SPLIT_RTL.read_text()
    if STN.get("gq"):
        out += "\n" + (ROOT / "rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_gq.sv").read_text()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", choices=("build", "relink", "run"))
    ap.add_argument("--variant", choices=("part", "base"), default="part")
    ap.add_argument("--build", type=Path, required=True)
    ap.add_argument("--work", type=Path)
    ap.add_argument("--stages", choices=("L0", "L3", "head", "full"), default="L0")
    ap.add_argument("--threads", type=int, default=16)
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--dcu", type=int, default=0, help="ctrl -> unit pin stations (sequencer OS + unit IS)")
    ap.add_argument("--duc", type=int, default=0, help="unit -> ctrl pin stations (unit OS + sequencer IS)")
    ap.add_argument("--comp", type=int, default=1, help="1: split-exact compensation; 0: stations only (negative)")
    ap.add_argument("--su-ml", type=int, default=0, help="qwen-rtl-finish: SU lane memory latency ML (the re-cut SU "
                    "master's far constant ROM: IS + OS + CRX)")
    ap.add_argument("--gq", type=int, default=0, help="kv-die: unit-side go queues of GQ entries (ot_qfd_split_gq.sv); "
                    "0 = the issue shell of ot_qfd_split_exact.sv")
    ap.add_argument("--max-cycles", type=int, default=0, help="L0 cycle guard (default: the harness's; stations "
                    "add issue gaps)")
    a = ap.parse_args()
    if a.max_cycles:
        F.L0_MAX_CYCLES = a.max_cycles
    STN.update(dcu=a.dcu, duc=a.duc, comp=a.comp, su_ml=a.su_ml, gq=a.gq)
    bld = a.build.resolve()
    if a.phase == "run":
        sys.exit(F.run(bld, a.work.resolve(), a.stages, a.threads))
    if a.phase == "relink":      # host-only change on an existing build (the die / coll / tile archives are reused)
        st = []
        F.link(bld, st)
        print("relinked", st)
        return
    if a.variant == "part":
        F.EMIT.emit = part_core
        orig = F.die_sources
        gen = ROOT / "build" / "qwen_missing_part" / bld.name
        gen.mkdir(parents=True, exist_ok=True)

        def die_sources():
            out = []
            for f in orig():
                t = f.read_text()
                if re.search(r"\bcore\.\w", t):    # a hierarchical read of the core instance (not 'score.')
                    n = 0
                    for net in CTRL_NETS:
                        t, k = re.subn(rf"\bcore\.{net}\b", f"core.u_ctrl.{net}", t)
                        n += k
                    if n == 0 or re.search(r"\bcore\.(?!u_ctrl\.)\w", t):
                        raise SystemExit(f"{f}: core reference pattern changed")
                    g = gen / f.name
                    g.write_text(t)
                    out.append(g)
                else:
                    out.append(f)
            return out
        F.die_sources = die_sources
    F.build(bld, a.jobs)
    import json
    (bld / "STN.json").write_text(json.dumps(dict(variant=a.variant, **STN), indent=1) + "\n")


if __name__ == "__main__":
    main()
