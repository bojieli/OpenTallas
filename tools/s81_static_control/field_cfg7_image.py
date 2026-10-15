"""Map source CFG48 words to the existing seven native CFG4096x72 banks.

The native sequencer uses linear address phase*25+word, bank=address>>12,
row=address&4095. Only allocated source phases are accepted by this compiler;
unused physical rows contain zero and confer no valid phase identity.
layout='il7' (FILL-S2 2026-10-15) is the image of the sequencer at LAYOUT 1: word k of phase p in bank k % 7, row
4p + k // 7 (the combinational phase*25 address leaves the sequencer's pin path; same words, same read edges).
"""
from pathlib import Path
import argparse, hashlib, json

ROWS = 4096
BANKS = 7
PHASE_WORDS = 25


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encode_bank(words):
    if len(words) != ROWS or any(type(w) is not int or not 0 <= w < 1 << 48 for w in words):
        raise ValueError('exactly4096 native48bit payload rows required')
    physical = [0] * (ROWS // 8)
    for addr, word in enumerate(words):
        if word == 0:
            continue
        for bit in range(48):
            physical[addr // 8] |= ((word >> bit) & 1) << (8 * bit + addr % 8)
    return physical


def decode_bank(physical):
    if len(physical) != ROWS // 8 or any(w < 0 or w >= 1 << 576 for w in physical):
        raise ValueError('native MUX8 array geometry required')
    return [0 if physical[a // 8] == 0 else
            sum(((physical[a // 8] >> (8 * bit + a % 8)) & 1) << bit
                for bit in range(72)) for a in range(ROWS)]


def emit(source, out, *, phase_count, PHW, source_binding, layout='linear'):
    source, out = Path(source), Path(out)
    if not 1 <= PHW <= 10 or not 1 <= phase_count <= 1 << PHW:
        raise ValueError('allocated source phase count/PHW required')
    if not source_binding or source_binding.get('cfg_sha256') != sha(source):
        raise ValueError('actual source CFG binding/hash required')
    words = [int(line, 16) for line in source.read_text().splitlines()]
    if len(words) != phase_count * PHASE_WORDS:
        raise ValueError('missing or surplus canonical phase words')
    if any(not 0 <= w < 1 << 48 for w in words):
        raise ValueError('native CFG48 payload overflow')
    if (PHASE_WORDS << PHW) > ROWS * BANKS:
        raise ValueError('native7bank capacity exceeded')
    out.mkdir(parents=True, exist_ok=False)
    images = []
    if layout not in ('linear', 'il7'):
        raise ValueError('layout linear | il7')
    if layout == 'il7' and (PHASE_WORDS > 4 * BANKS or (4 << PHW) > ROWS):
        raise ValueError('il7 layout needs 25 <= 28 words and 4 rows per phase')
    padded = words + [0] * (ROWS * BANKS - len(words))
    if layout == 'il7':
        banked = [[0] * ROWS for _ in range(BANKS)]
        for g, w in enumerate(words):
            ph, k = divmod(g, PHASE_WORDS)
            banked[k % BANKS][4 * ph + k // BANKS] = w
    for bank in range(BANKS):
        payload = banked[bank] if layout == 'il7' else padded[bank * ROWS:(bank + 1) * ROWS]
        physical = encode_bank(payload)
        if decode_bank(physical) != payload:
            raise ValueError('native physical mask readback differs from source CFG')
        path = out / f'cfg{bank}.viamap.hex'
        path.write_text(''.join(f'{word:0144x}\n' for word in physical))
        images.append(dict(bank=bank, path=path.name, sha256=sha(path)))
    receipt = dict(abi='opentallas.s81.cfg7-native.v1', source=source_binding,
                   phase_count=phase_count, PHW=PHW, words_per_phase=PHASE_WORDS,
                   allocated_words=len(words), resident_words=ROWS * BANKS,
                   physical_macros=BANKS, macro='ot_rom_4096x72_m8', payload_bits=48,
                   spare_bits=24, ROM_ECC=False, layout=layout,
                   **(dict(bank='word%7', row='4*phase+word//7', sequencer_param='LAYOUT=1') if layout == 'il7' else
                      dict(linear_address='phase*25+word', bank='linear_address>>12', row='linear_address&4095')),
                   bank_select_registered=True, images=images,
                   complete_source_readback=True, native_execution_qualified=False)
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--binding', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--phase-count', type=int, required=True)
    p.add_argument('--PHW', type=int, required=True)
    p.add_argument('--layout', choices=('linear', 'il7'), default='linear')
    a = p.parse_args()
    emit(a.source, a.out, phase_count=a.phase_count, PHW=a.PHW,
         source_binding=json.loads(a.binding.read_text()), layout=a.layout)
