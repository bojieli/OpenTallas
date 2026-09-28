#!/usr/bin/env python3
"""First-layer Qwen3-8B TP2 program profile, without checkpoint payloads.

The profile emits the existing 1024-bit ISA words and TP segment descriptors
for layer 0, starting with X in VM. It uses a single-layer KV window and
reports the RTL changes still needed before those words can execute.
"""
import argparse
import contextlib
import hashlib
import json
from pathlib import Path

import hdc_isa as I
import hdc_program as P
from hdc_qwen_fullshape_placement import CONFIG, LOCK, GROUPS, placement

W = I.W_LANES
TMAX = 8192


def vm_map(h=4096, ff=6144, nh=16, kv=4, hd=128):
    """Nonoverlapping, 16-element aligned live regions for a full context."""
    # TP segment descriptor has only eight bits for the VM word address.
    # Keep the collective destination in its first 256 words.
    sizes = [('T1', h), ('X', h), ('H', h), ('QKV', (nh + 2 * kv) * hd),
             ('QN', (nh + kv) * hd), ('QR', nh * hd), ('SS', nh + kv),
             ('RS', nh + kv), ('SSX', 1), ('RX', 1), ('M', nh), ('Z', nh),
             ('RZ', nh), ('S', nh * TMAX), ('ATT', nh * hd),
             ('GU', 2 * ff), ('ATTN', nh * hd), ('U', h), ('ACT', ff)]
    base, out = 0, {}
    for name, size in sizes:
        base = (base + W - 1) // W * W
        out[name] = base
        base += size
    return out, (base + W - 1) // W * W


class LayerZero:
    """Shape-only Layout adapter for build_program, with one paged KV layer."""

    def __init__(self, report, die):
        if die not in (0, 1):
            raise ValueError('TP2 die must be 0 or 1')
        # This layer has no lm_head, so the 16-bit descriptor row0 is zero.
        # The 75,968-row vocabulary offset needs a wider head descriptor later.
        self.tp, self.die, self.row0 = 2, die, 0
        self.H, self.L, self.NH, self.KV, self.HD, self.FF = 4096, 1, 16, 4, 128, 6144
        self.half, self.GUB, self.groups, self.eps = 64, 128, GROUPS, 1e-6
        self.kv_v0 = self.KV * TMAX * self.HD
        rows = report['matrices_per_die'][:4]
        self.mat = {(0, name): {'base': row['base'], 'n': row['rows'],
                                'k': row['k_per_split'], 'tiles': row['rounds'],
                                'split': row['split']}
                    for name, row in zip(('qkv', 'o', 'gu', 'down'), rows)}
        # Constant payloads are intentionally absent. These bases reserve
        # ordinary qscale/RMSNorm rows plus a full RoPE table in the profile.
        self.cb = {(0, 'in'): 0, (0, 'qk'): self.H,
                   (0, 'post'): self.H + (self.NH + self.KV) * self.HD,
                   'qscale': 2 * self.H + (self.NH + self.KV) * self.HD,
                   'rope': 2 * self.H + (self.NH + self.KV) * self.HD + 1}

    def k_elem(self, layer, head, token, dim):
        assert layer == 0
        return ((head * (TMAX // W) + token // W) * self.HD + dim) * W + token % W

    def v_elem(self, layer, head, token, dim):
        assert layer == 0
        return self.kv_v0 + (head * TMAX + token) * self.HD + dim


@contextlib.contextmanager
def program_geometry(vm):
    prior = P.VM, P.GR, P.S_STRIDE
    P.VM, P.GR, P.S_STRIDE = vm, GROUPS, TMAX
    try:
        yield
    finally:
        P.VM, P.GR, P.S_STRIDE = prior


def split_collectives(program):
    """Fit 4096-element T1 reductions into the TP descriptor's 8-bit counts."""
    out = []
    for f in program:
        coll = f.get('_coll')
        if coll and coll[0] == P.COLL_ALLREDUCE and coll[2] == 256:
            kind, word, _, row0 = coll
            for offset in (0, 128):
                out.append(dict(f, _coll=(kind, word + offset, 128, row0)))
        else:
            out.append(f)
    return out


def profile(die):
    place = placement()
    vm, vm_elems = vm_map()
    lay = LayerZero(place, die)
    with program_geometry(vm):
        program = split_collectives(P.build_program(lay, layers=[0], embed=False, head=False))
    encoded = [I.encode(**{k: v for k, v in f.items() if not k.startswith('_')}) for f in program]
    for f, word in zip(program, encoded):
        decoded = I.decode(word)
        for key, value in f.items():
            if not key.startswith('_') and decoded[key] != value:
                raise ValueError(f'ISA round trip failed: {key}')
    words, desc = P.encode_segments(program)
    assert encoded == words
    for f in program:
        if f.get('_coll'):
            _, word, count, row0 = f['_coll']
            if word >= 256 or count >= 256 or row0 >= 65536:
                raise ValueError('TP segment descriptor width exceeded')
    if len(words) >= (1 << 12):
        raise ValueError('first-layer program exceeds PAW12')
    if vm_elems > (1 << I.A) or 2 * lay.kv_v0 > (1 << I.A):
        raise ValueError('first-layer VM or KV window exceeds AW24')
    blockers = ['core DYN_TTILES uses power-of-two shift at G6144; exact division required',
                'core VM must provision the reported full-context element count',
                'TP2 norm-folded INT8 matrix payloads and constant payloads are not emitted',
                'KV needs layer paging before 36-layer execution',
                'lm_head die-1 row0=75968 exceeds the TP descriptor 16-bit row0 field',
                'NW18 token and argmax path, ROM depths, and PAW12 integration remain untested']
    sources = [Path(__file__), Path(P.__file__), Path(I.__file__),
               Path(__file__).with_name('hdc_qwen_fullshape_placement.py')]
    return {'schema': 'opentallas.qwen-o4-fullshape-first-layer-program.v1',
            'status': 'profile_only', 'die': die, 'tp': 2,
            'config_sha256': hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
            'checkpoint_lock_sha256': hashlib.sha256(LOCK.read_bytes()).hexdigest(),
            'source_sha256': {str(path.relative_to(CONFIG.parents[3])):
                              hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
            'context_capacity': TMAX, 'groups': GROUPS,
            'isa_address_bits': I.A, 'isa_count_bits': I.N,
            'required_token_bits': 18, 'program_address_bits': 12,
            'vm_elems': vm_elems, 'vm_map': vm,
            'kv_window_elems': 2 * lay.kv_v0,
            'program_words': len(words), 'segment_count': len(desc),
            'allreduce_segments': sum((x & 3) == P.COLL_ALLREDUCE for x in desc),
            'program_hex': [f'{x:0256x}' for x in words],
            'descriptor_hex': [f'{x:016x}' for x in desc],
            'blockers': blockers,
            'claim_boundary': 'First-layer ISA address and encode/decode profile only; no weights, golden trace, or RTL execution.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--die', type=int, choices=(0, 1), required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    report = profile(args.die)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(f"wrote {report['program_words']} words, {report['segment_count']} segments to {args.out}")


if __name__ == '__main__':
    main()
