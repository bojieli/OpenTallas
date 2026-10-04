#!/usr/bin/env python3
"""Explicit row-decoder successor of the retained FAST/PP runtime launcher.

Select existing rowfix pair/element sources, without changing their defaults or
the retained launcher/archives. No clock, arithmetic, geometry or PG changes.
Use a fresh --work directory; old archives remain evidence of the old source.
"""
from pathlib import Path
import sys

import w17_current_fastpp_die_rt_cli_v4 as cli

base = cli.base
REPLACEMENTS = {
    base.ROOT / 'rtl/v41rom/ot_v41_rom_elem_w10.sv':
        base.ROOT / 'rtl/v41rom/ot_v41_rom_elem_w10_rowfix_prepare.sv',
    base.ROOT / 'rtl/v41die/ot_v41_pair_w17w10.sv':
        base.ROOT / 'rtl/v41die/ot_v41_pair_w17w10_rowfix_prepare.sv',
}


def compiler_argv(cmd):
    result = cli.compiler_argv(cmd)
    if result and 'verilator' in Path(result[0]).name.lower():
        result = [str(REPLACEMENTS.get(Path(arg), arg)) for arg in result]
        if '--top-module' in result and result[result.index('--top-module') + 1] == 'ot_v41_pair_w17w10':
            if any(arg.startswith('-GFIX_SECOND_ROW_INDEX=') for arg in result):
                raise ValueError('rowfix successor owns the pair decoder selection')
            result.append('-GFIX_SECOND_ROW_INDEX=1')
    return result


_run = cli._original_run
_sources = base.all_sources
_build = base.build


def all_sources():
    return sorted(set(REPLACEMENTS.get(p, p) for p in _sources()) | {Path(__file__).resolve()})


def build(args):
    # The retained builder skips existing archives. Refuse that shortcut here:
    # a legacy model cannot acquire corrected-source provenance by relinking.
    work = Path(args.work)
    if work.exists() and any(work.iterdir()):
        raise ValueError('rowfix successor requires a fresh work directory; preserve existing artifacts')
    return _build(args)


def run(cmd, log, cwd=None):
    return _run(compiler_argv(cmd), log, cwd)


base.all_sources = all_sources
base.build = build
base.run = run

if __name__ == '__main__':
    sys.exit(base.main())
