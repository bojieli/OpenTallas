#!/usr/bin/env python3
"""DIE-HEAD-28 10-29: repo-relative strict-bind manifest for a PREPARED HEAD source copy (Codex prepare_source_bind.py
layout: s81_head_top_nonansi.sv + generated wrappers + source_plan.json + straps.json + pads.json).

  head_source_bind_manifest.py SRC_DIR OUT.f        (run from the repo root; RTL entries are repo-relative)

Manifest = die top + every generated wrapper in SRC_DIR + every plan type `sources` entry + tools/s81_head/
head_portbind_extra.f + the clock-landing closure tools/die_plan/gen_phys.landing_rtl takes for the kits (DIE-HEAD-7
10-28: ot_dp_clk_landing*.sv and, transitively, rtl/common/ot_meso_fifo.sv).  The Codex copy hard-coded only the two
landing files, so the SOURCE7 strict bind (unit 3445572) failed on the one unresolved child ot_meso_ohor.  No other
entry changes; every repo entry must exist and be repo-relative."""
import json
import sys
from pathlib import Path

sys.path.insert(0, 'tools/die_plan')
import gen_phys as GP  # noqa: E402


def build(src_dir):
    src_dir = Path(src_dir).resolve()
    plan = json.loads((src_dir / 'source_plan.json').read_text())
    leaf = sorted({s for t in plan['partition_types'].values() for s in t.get('sources', [])})
    extra = [ln.split('#')[0].strip() for ln in Path('tools/s81_head/head_portbind_extra.f').read_text().splitlines()
             if ln.split('#')[0].strip()]
    wrappers = sorted(f for f in src_dir.glob('*.sv') if f.name not in ('s81_head_top.sv', 's81_head_top_nonansi.sv'))
    land = [str(f) for f in GP.landing_rtl('.', '\n'.join(f.read_text() for f in wrappers))]
    repo = sorted(set(leaf + extra + land))
    bad = [s for s in repo if Path(s).is_absolute() or not Path(s).is_file()]
    if bad:
        raise SystemExit('manifest entries must be existing repo-relative files: %s' % bad)
    return [str(src_dir / 's81_head_top_nonansi.sv')] + [str(f) for f in wrappers] + repo, land


if __name__ == '__main__':
    fl, land = build(sys.argv[1])
    Path(sys.argv[2]).write_text('\n'.join(fl) + '\n')
    print('MANIFEST %d entries, landing closure %s' % (len(fl), land))
