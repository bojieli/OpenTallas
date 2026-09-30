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
import hdc_qwen_fullshape_isa as QI
from hdc_qwen_fullshape_placement import CONFIG, LOCK, GROUPS, TP, placement

W = I.W_LANES
TMAX = 8192


def vm_map(h=4096, ff=12288 // TP, nh=32 // TP, kv=8 // TP, hd=128):
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

    def __init__(self, report, die, matrix_rows=None):
        if not 0 <= die < TP:
            raise ValueError('TP die out of range')
        # This layer has no lm_head, so the 16-bit descriptor row0 is zero.
        # The 75,968-row vocabulary offset needs a wider head descriptor later.
        self.tp, self.die, self.row0 = TP, die, 0
        self.H, self.L, self.NH, self.KV, self.HD, self.FF = 4096, 1, 32 // TP, 8 // TP, 128, 12288 // TP
        self.norm_fold = True
        self.half, self.GUB, self.groups, self.eps = 64, 128, GROUPS, 1e-6
        self.kv_v0 = self.KV * TMAX * self.HD
        rows = report['matrices_per_die'][:4] if matrix_rows is None else matrix_rows
        self.mat = {(0, name): {'base': row['base'], 'n': row['rows'],
                                'k': row['k_per_split'], 'tiles': row['rounds'],
                                'split': row['split'],
                                'scale_base': row.get('scale_base', row['base'])}
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


def insert_post_tp_scales(program, vm, bases):
    """Scale each rank-folded raw o/down partial once, before residual add."""
    out, index = [], 0
    for f in program:
        out.append(f)
        if f.get('_coll', (None,))[0] == P.COLL_ALLREDUCE:
            if index >= len(bases):
                raise ValueError('more TP reductions than post-fold scales')
            out.append(dict(unit=I.UNIT_SU, barrier=1, su_nout=1, su_nin=4096,
                            a_base=vm['T1'], a_si=1, c_src=I.SRC_ALT,
                            c_base=bases[index], c_si=1, mc=I.MC_C,
                            dst=I.DST_VM, d_base=vm['T1'], d_si=1))
            index += 1
    if index != len(bases):
        raise ValueError('post-fold scale count differs from TP reductions')
    return out


def profile(die, matrix_rows=None, post_scale_bases=None):
    place = placement()
    vm, vm_elems = vm_map()
    lay = LayerZero(place, die, matrix_rows)
    with program_geometry(vm):
        program = P.build_program(lay, layers=[0], embed=False, head=False, scale_bases=True)
        if post_scale_bases is not None:
            program = insert_post_tp_scales(program, vm, post_scale_bases)
        program = split_collectives(program)
    encoded = [QI.encode_instruction(f) for f in program]
    for f, word in zip(program, encoded):
        decoded = QI.decode_instruction(word)
        for key, value in f.items():
            if not key.startswith('_') and decoded[key] != value:
                raise ValueError(f'ISA round trip failed: {key}')
    words, desc = QI.encode_segments(program)
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
    blockers = ['fullshape G6144 DYN_TTILES integration with this program remains unrun',
                'core VM must provision the reported full-context element count',
                'TP2 norm-folded INT8 matrix payloads and constant payloads are not emitted',
                'KV needs layer paging before 36-layer execution',
                'lm_head die-1 row0=75968 exceeds the TP descriptor 16-bit row0 field',
                'NW18 token and argmax path, ROM depths, and PAW12 integration remain untested']
    sources = [Path(__file__), Path(P.__file__), Path(I.__file__),
               Path(QI.__file__),
               Path(__file__).with_name('hdc_qwen_fullshape_placement.py')]
    return {'schema': 'opentallas.qwen-o4-fullshape-first-layer-program.v1',
            'status': 'profile_only', 'die': die, 'tp': TP,
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
            'post_tp_scale_instructions': 0 if post_scale_bases is None else len(post_scale_bases),
            'allreduce_segments': sum((x & 3) == P.COLL_ALLREDUCE for x in desc),
            'program_hex': [f'{x:0256x}' for x in words],
            'descriptor_hex': [f'{x:016x}' for x in desc],
            'blockers': blockers,
            'claim_boundary': 'First-layer ISA address and encode/decode profile only; no weights, golden trace, or RTL execution.'}


def profile_lm_head(die, matrix_row, final_norm_base, chunk_words=512):
    """Chunk one TP2 vocabulary half with independent code and scale bases."""
    place = placement()
    vm, vm_elems = vm_map()
    lay = LayerZero(place, die)
    lay.row0 = die * (151936 // TP)
    lay.cb['final'] = final_norm_base
    lay.mat['lm_head'] = {'base': matrix_row['base'], 'scale_base': matrix_row['scale_base'],
                          'n': 151936 // TP, 'k': matrix_row['k_per_split'],
                          'tiles': matrix_row['rounds'], 'split': matrix_row['split']}
    with program_geometry(vm):
        program = P.build_program(lay, layers=[], embed=False, head=True,
                                  wchunk=chunk_words, scale_bases=True)
    words, desc = QI.encode_segments(program)
    if len(words) >= 1 << 12 or len(desc) != 1:
        raise ValueError('lm_head stage exceeds PAW12 or has wrong segment count')
    chunks = [f for f in program if f['unit'] == I.UNIT_ME and not f.get('me_wsrc')]
    if not chunks or any(f['me_tiles'] * f['me_k'] * I.INTERLEAVE > chunk_words for f in chunks):
        raise ValueError('lm_head chunk exceeds code-word window')
    if any(f['me_nout'] >= 1 << I.N for f in chunks):
        raise ValueError('lm_head chunk exceeds legacy count field')
    return {'schema': 'opentallas.qwen-o4-lm-head-tp2-program.v1',
            'die': die, 'row0': lay.row0, 'required_token_bits': 18,
            'program_words': len(words), 'segment_count': len(desc),
            'program_hex': [f'{word:0256x}' for word in words],
            'descriptor_hex': [f'{word:016x}' for word in desc],
            'chunks': [{'code_base': f['me_wbase'], 'scale_base': f['me_wcs'],
                        'first_row': f.get('me_row0', 0), 'rows': f['me_nout'],
                        'rounds': f['me_tiles']} for f in chunks],
            'vm_elems': vm_elems,
            'claim_boundary': 'lm_head ISA chunk and row-offset profile only; no logits or RTL token pass.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--die', type=int, choices=range(TP), required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    report = profile(args.die)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(f"wrote {report['program_words']} words, {report['segment_count']} segments to {args.out}")


if __name__ == '__main__':
    main()
