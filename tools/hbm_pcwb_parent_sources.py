#!/usr/bin/env python3
"""Resolve the additive PCWB service parent's actual compilation sources.

This helper reads files only. It does not build, qualify timing, or select a
production target. Both controller definitions are needed by the parent's
default/original and opt-in command-match generate branches.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from collections.abc import Mapping

ROOT = Path(__file__).resolve().parents[1]
TOP = 'ot_hbm_accel_pcwb_service_stack'
SOURCEBOOK = 'results/uarch/hbm_pcwb_actual_parent_20261005/model.json'
SOURCES = (
    'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
    'rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv',
    'rtl/hbm_accel/service/ot_hbm_accel_stream_pc_wb.sv',
    'rtl/hbm_accel/service/ot_hbm_accel_stream_pc_wb_command_match.sv',
    'rtl/hbm_accel/service/ot_hbm_accel_dskv_wb.sv',
    'rtl/hbm_accel/integration/ot_hbm_pcwb_ca_slots.sv',
    'rtl/hbm_accel/integration/ot_hbm_pcwb_prepaid_column.sv',
    'rtl/hbm_accel/integration/ot_hbm_accel_pcwb_service_stack.sv',
)


def source_hashes(root: Path = ROOT,
                  expected: Mapping[str, str] | None = None) -> dict[str, str]:
    """Hash each actual source in dependency order; reject missing or changed pins."""
    missing = [path for path in SOURCES if not (root / path).is_file()]
    if missing:
        raise ValueError('Missing actual PCWB parent sources: ' + ', '.join(missing))
    hashes = {path: hashlib.sha256((root / path).read_bytes()).hexdigest()
              for path in SOURCES}
    if expected is not None:
        absent = [path for path in SOURCES if path not in expected]
        if absent:
            raise ValueError('Missing sourcebook pins: ' + ', '.join(absent))
        changed = [path for path in SOURCES if hashes[path] != expected[path]]
        if changed:
            raise ValueError('PCWB sourcebook hash mismatch: ' + ', '.join(changed))
    return hashes


def resolve_sources(root: Path = ROOT, *, enable: int = 0,
                    cmd_match_cut: int = 0,
                    sourcebook: str | Path = SOURCEBOOK) -> dict:
    """Resolve actual sources and explicit parent parameters against its price book."""
    if enable not in (0, 1) or cmd_match_cut not in (0, 1):
        raise ValueError('ENABLE and CMD_MATCH_CUT must be 0 or 1')
    hashes = source_hashes(root)
    book_path = root / sourcebook
    book_bytes = book_path.read_bytes()
    book = json.loads(book_bytes)
    if (book.get('schema') != 'opentallas.pcwb.actual_parent_prebuild.v1'
            or book.get('selected_top') != TOP
            or book.get('ENABLE_default') != 0
            or book.get('CMD_MATCH_CUT_default') != 0):
        raise ValueError('PCWB sourcebook top/default selection mismatch')
    pins = book.get('sources')
    required = ('rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv',
                'rtl/hbm_accel/service/ot_hbm_accel_stream_pc_wb_command_match.sv',
                'rtl/hbm_accel/service/ot_hbm_accel_dskv_wb.sv')
    if not isinstance(pins, dict) or any(path not in pins for path in required):
        raise ValueError('PCWB sourcebook lacks frozen CDC/CMD/writer pins')
    changed = [path for path in SOURCES if path in pins and pins[path] != hashes[path]]
    if changed:
        raise ValueError('PCWB sourcebook hash mismatch: ' + ', '.join(changed))
    return {'top': TOP, 'sources': list(SOURCES), 'source_sha256': hashes,
            'parameters': {'ENABLE': enable, 'CMD_MATCH_CUT': cmd_match_cut},
            'controller_module': ('ot_hbm_accel_stream_pc_wb_command_match'
                                  if cmd_match_cut else 'ot_hbm_accel_stream_pc_wb'),
            'sourcebook': str(sourcebook),
            'sourcebook_sha256': hashlib.sha256(book_bytes).hexdigest()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--sourcebook', type=Path, default=Path(SOURCEBOOK))
    parser.add_argument('--enable', type=int, choices=(0, 1), default=0)
    parser.add_argument('--cmd-match-cut', type=int, choices=(0, 1), default=0)
    parser.add_argument('--format', choices=('json', 'paths'), default='json')
    args = parser.parse_args(argv)
    try:
        selection = resolve_sources(args.root, enable=args.enable,
                                    cmd_match_cut=args.cmd_match_cut,
                                    sourcebook=args.sourcebook)
    except (OSError, ValueError, AttributeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    if args.format == 'paths':
        print('\n'.join(SOURCES))
    else:
        print(json.dumps(selection, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
