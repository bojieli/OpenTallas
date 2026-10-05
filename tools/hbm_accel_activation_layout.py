#!/usr/bin/env python3
"""Source/compiler bit layout for the opt-in static 2048-bit activation port.

No numerical conversion: only copies existing BF16 and code/exponent bits.
The NC-sized FP4 half-plane is fixed, including when fewer columns are active.
"""
import argparse
import json

XC = 3152
BLOCK_BITS = 266
HALF_BITS = 1064
BF16_BITS = 1024
PORT_BITS = 2048
FORMATS = {0: 'bf16', 1: 'fp8', 2: 'fp4'}


def fmt_name(fmt):
    name = FORMATS.get(fmt, fmt)
    if name not in FORMATS.values():
        raise ValueError(f'Unsupported activation format {fmt}')
    return name


def fields(fmt, active, nc=8):
    """Yield (original_bit, packed_bit, width) for every consumed field."""
    fmt = fmt_name(fmt)
    if not 1 <= active <= nc:
        raise ValueError('Active columns must be in 1..NC')
    for col in range(active):
        if fmt == 'bf16':
            yield col * XC + 8 * BLOCK_BITS, col * BF16_BITS, BF16_BITS
        else:
            for block in range(8 if fmt == 'fp4' else 4):
                yield (col * XC + block * BLOCK_BITS,
                       (block // 4) * nc * HALF_BITS + col * HALF_BITS + (block % 4) * BLOCK_BITS,
                       BLOCK_BITS)


def beat_groups(fmt, active, nc=8):
    groups = set()
    for _, dst, width in fields(fmt, active, nc):
        groups.update(range(dst // PORT_BITS, (dst + width - 1) // PORT_BITS + 1))
    return sorted(groups)


def pack_fragment(original, fmt, active, nc=8):
    packed = 0
    for src, dst, width in fields(fmt, active, nc):
        packed |= ((original >> src) & ((1 << width) - 1)) << dst
    return packed


def unpack_used(packed, fmt, active, nc=8):
    original = 0
    for src, dst, width in fields(fmt, active, nc):
        original |= ((packed >> dst) & ((1 << width) - 1)) << src
    return original


def check_map(nc=8):
    rows = []
    for active in range(1, nc + 1):
        for fmt in FORMATS.values():
            src_bits, dst_bits = set(), set()
            for src, dst, width in fields(fmt, active, nc):
                a, b = set(range(src, src + width)), set(range(dst, dst + width))
                assert not (src_bits & a) and not (dst_bits & b), (fmt, active)
                src_bits.update(a); dst_bits.update(b)
            assert len(src_bits) == len(dst_bits)
            # Bit-only inverse, not arithmetic or a replacement numerical oracle.
            word = int.from_bytes(bytes(range(256)) * 13, 'little')
            masked = sum(((word >> src) & ((1 << width) - 1)) << src
                         for src, _, width in fields(fmt, active, nc))
            assert unpack_used(pack_fragment(word, fmt, active, nc), fmt, active, nc) == masked
            rows.append(dict(active=active, fmt=fmt, used_bits=len(src_bits),
                             groups=beat_groups(fmt, active, nc), bijective=True))
    return rows


def model(nc=8):
    return dict(scope='Prebuild static map; no measured gain or physical closure',
                default_xmap=0, nc=nc, streaming_target_ps=833.333333,
                setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                macs_per_cycle_delta=0, added_latency_cycles=0,
                added_state_bits=0, added_muxes=0, added_demuxes=0,
                added_sram_macros=0, inherited_sram_macros=nc * 4 * 4,
                inherited_activation_storage_bits=nc * 4 * 4 * 128 * 256,
                writer_bytes_per_cycle=256, writer_data_bits_per_cycle=2048,
                writer_boundary_bits=2048 + 7 + 7 + 1,
                inherited_leaf_read_bits_per_cycle=nc * 4 * 4 * 256,
                static_field_fanout=1, leaf_replicas=nc * 4,
                logical_cell_area_delta_um2=0,
                wire_stage_delta=0, existing_write_landing_edges=8,
                routing='Rewired existing 2048-bit port and masks; actual source-to-leaf wires/corridor not qualified.',
                root='Per-format fixed wiring views only; physical caller/format selection remains existing producer obligation.',
                required_tracks=2048, channel_capacity=None,
                area_fit='No new leaf logic/state; routed placement/wire fit remains unmeasured.',
                runtime_format_mux_added=False, option3B_built=False,
                load_law='Actual beats/address * addresses + 1; must measure each sequence and overlap with PQ.',
                layout_check=check_map(nc))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model', required=True)
    args = ap.parse_args()
    from pathlib import Path
    Path(args.model).write_text(json.dumps(model(), indent=2) + '\n')


if __name__ == '__main__':
    main()
