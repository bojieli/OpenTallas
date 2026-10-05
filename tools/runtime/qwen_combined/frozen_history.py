"""Bind cached Qwen ROM oracle history to the existing REAL_MEM preload ABI.

File transport only. No oracle imports, FP8 conversion, model constructor,
clock, memory response, write acknowledgement or visibility grant. The actual
driver retains its E4M3 decoder and fullshape_context.hpp address mapping.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

KV_WORDS = 2 * 2 * 8192 * 128
KV_BYTES = KV_WORDS * 4
SCHEMAS = {
    'opentallas.qwen-rom-tp4-position-oracle.v1',
    'opentallas.qwen-rom-tp4-position-oracle-gpu.v1',
    # Shared GPU generator; the explicit TP4/shape checks below still apply.
    'opentallas.qwen-tp-position-oracle-gpu.v1',
}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


class FrozenHistory:
    """Use one explicitly pinned, completed oracle position.

    A three-layer frozen baseline can bind those three layers only. Missing
    full-model GPU outputs refuse; nothing here creates or waits for them.
    """
    def __init__(self, root, *, oracle_sha256, position, token):
        self.root = Path(root).resolve(strict=True)
        oracle = self.root / 'oracle.json'
        raw = oracle.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == oracle_sha256, 'frozen oracle identity')
        self.record = json.loads(raw)
        rec = self.record
        require(rec.get('schema') in SCHEMAS and rec.get('status') == 'ISA_golden_only',
                'completed cached position oracle required')
        require((rec.get('tp'), rec.get('groups'), rec.get('kv_format')) == (4, 6144, 'fp8'),
                'full-shape TP4/G6144/FP8 source required')
        require(type(rec.get('layers')) is int and 1 <= rec['layers'] <= 36,
                'recorded decoder layer coverage')
        require(type(position) is int and 0 <= position < 8192 and position in rec['positions'],
                'recorded full-shape position required')
        require(type(token) is int and 0 <= token < 151936, 'released token aperture')
        self.frame = rec['per_position'].get(str(position))
        require(self.frame is not None and self.frame['token'] == token,
                'cached position/token binding')
        self.position, self.token = position, token
        self.oracle_sha256 = oracle_sha256
        self.position_dir = self.root / f'P{position}'

    @classmethod
    def from_baseline(cls, root, baseline):
        """Reuse the source identity already pinned by a passing frozen run.

        Do not substitute a later oracle manifest even if its selected KV rows
        happen to match. The original baseline's complete manifest is the pin.
        """
        rec = json.loads(Path(baseline).read_text())
        require(rec.get('status') == 'pass' and rec.get('source_stable') is True
                and rec.get('configuration') == 'REAL_MEM', 'passing frozen REAL_MEM baseline required')
        design = rec['design_point']
        require((design.get('tp'), design.get('groups_per_die'), design.get('su_width')) == (4, 6144, 64),
                'baseline TP4/G6144/SW64 ports required')
        result = cls(root, oracle_sha256=rec['oracle_json_sha256'],
                     position=rec['position'], token=rec['token'])
        pins = rec['kv_history_sha256']
        require(pins and all(result.frame['kv_pre_sha256'].get(k) == v for k, v in pins.items()),
                'baseline KV file pins differ from frozen oracle')
        result.baseline_pins = pins
        return result

    def source(self, layer, rank):
        require(type(layer) is int and 0 <= layer < self.record['layers'],
                'layer not covered by this cached oracle')
        require(type(rank) is int and 0 <= rank < 4, 'explicit TP4 rank required')
        key = f'L{layer}_die{rank}'
        expected = self.frame['kv_pre_sha256'].get(key)
        require(isinstance(expected, str) and len(expected) == 64, 'recorded KV history hash required')
        if hasattr(self, 'baseline_pins'):
            require(self.baseline_pins.get(key) == expected, 'history outside frozen baseline coverage')
        path = self.position_dir / 'kv_pre' / (key + '.npy')
        require(sha(path) == expected, 'cached history hash differs: ' + key)
        words = np.load(path, mmap_mode='r', allow_pickle=False)
        # The file carries FP32 *bits*. astype would silently accept numeric
        # float/int inputs and destroy that contract. Preserve little-endian
        # u32 bytes exactly, including signed zero and all exponent/mantissa bits.
        require(words.dtype.str == '<u4' and words.shape == (KV_WORDS,) and words.flags.c_contiguous,
                'history must be 4194304 little-endian uint32 bitwords')
        return path, expected, words

    def export(self, output, *, layers):
        """Export selected layers/all four ranks to existing L<n>_die<r>.bin.

        Reuse an identical output; refuse any differing existing bytes. These
        files initialize history before P only. Current-token K/V continues
        through actual kv_we, tagged WR_ACK and the existing END/drain fences.
        """
        layers = tuple(layers)
        require(layers and len(set(layers)) == len(layers), 'unique explicit decoder layers required')
        # Check coverage before creating any outputs.
        for layer in layers:
            require(type(layer) is int and 0 <= layer < self.record['layers'],
                    'layer not covered by this cached oracle')
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        bindings = {}
        for layer in layers:
            for rank in range(4):
                path, expected, words = self.source(layer, rank)
                target = output / f'L{layer}_die{rank}.bin'
                payload_sha = hashlib.sha256(memoryview(words)).hexdigest()
                if target.exists():
                    require(target.is_file() and target.stat().st_size == KV_BYTES and sha(target) == payload_sha,
                            'refuse different existing raw history: ' + str(target))
                else:
                    with target.open('xb') as stream:
                        words.tofile(stream)
                    require(target.stat().st_size == KV_BYTES and sha(target) == payload_sha,
                            'raw history export changed bytes')
                require(sha(path) == expected, 'cached history changed during export')
                bindings[f'L{layer}_die{rank}'] = dict(
                    source=str(path), source_sha256=expected, raw=str(target), raw_sha256=payload_sha,
                    rank=rank, layer=layer, position=self.position, token=self.token,
                    words=KV_WORDS, bytes=KV_BYTES)
        return bindings
