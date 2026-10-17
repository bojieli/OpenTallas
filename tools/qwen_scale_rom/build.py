#!/usr/bin/env python3
"""Bind pinned released TP8 scale bytes to every actual physical slab ROM.

No quantization, golden computation, runtime bank switch or result injection.
The resident address permutation is lossless concatenation of36layer images
and head; the compiler's actual command producer must use the emitted bases.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_isa as ISA
from qwen_split.b2_frame import group_at

TP, GROUPS, LANES, DEPTH, BANKS = 8, 3072, 16, 4096, 16
REVISION = 'b968826d9c46dd6066d109eabc6255188de91218'
LOCK_SHA = '5cd6273118054c4a9140682bcd7a32488d8697db26bedf5d7ece8de99e141607'
INDEX_SHA = 'f9fdbcb91c23971c13ec5d5f2573d2349e8f61f2f049371ec699281748fdb1bc'
SPREAD = [sum(((v >> b) & 1) << (8*b) for b in range(8)) for v in range(256)]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked_image(path, expected_sha, expected_words):
    stat = path.stat()
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected_sha:
        raise ValueError(f'released payload hash mismatch: {path}')
    lines = payload.splitlines()
    if len(lines) != expected_words or any(len(line) != 64 for line in lines):
        raise ValueError(f'actual256-bit scale image shape mismatch: {path}')
    try:
        words = [int(line, 16) for line in lines]
    except ValueError as error:
        raise ValueError(f'non-hex scale image: {path}') from error
    if path.stat() != stat:
        raise ValueError(f'actual source changed during import: {path}')
    return words


def matrix_requests(fields, count, bandf=1):
    """Native frame address semantics; BANDF2 moves positions, preserving group addresses."""
    split = fields['me_split']
    ports = GROUPS >> split
    if bandf == 2 and fields['me_nout'] and not 7 <= split <= 11:
        raise ValueError('b2 production output requires nonempty TP8 split7..11')
    if not fields['me_nout'] or not ports:
        return []
    result = []
    for tile in range(fields['me_tiles']):
        for interleave in range(8):
            nb = tile * ports * LANES * 8 + interleave * LANES
            for position in range(24):
                group = group_at(split, position, bandf)
                if group is None:
                    continue
                if group >= ports or nb + group * LANES * 8 >= fields['me_nout']:
                    continue
                address = fields['me_wcs'] + nb // LANES + group * 8
                if not 0 <= address < count:
                    raise ValueError(f'active native scale request outside actual image: {address}/{count}')
                result.append((position, address))
    return result


def program_record(path, count, expected_scale_bases=None, bandf=1):
    result = []
    for pc, line in enumerate(path.read_text().splitlines()):
        f = ISA.decode(int(line, 16))
        if f['unit'] == 1 and not f['me_wsrc'] and f['me_nout']:
            requests = matrix_requests(f, count, bandf)
            result.append(dict(pc=pc, local_scale_base=f['me_wcs'], nout=f['me_nout'],
                               split_log2=f['me_split'], tiles=f['me_tiles'],
                               request_count=len(requests),
                               min_address=min(a for _, a in requests), max_address=max(a for _, a in requests),
                               active_port_slots=sorted({p for p, _ in requests})))
    bases = [r['local_scale_base'] for r in result]
    if expected_scale_bases is not None and bases != expected_scale_bases:
        raise ValueError(f'emitted program scale bases differ from pinned physical layout: {path}: {bases}')
    return dict(path=str(path), sha256=sha(path), decoded_scale_operations=result)


def mask_rows(words):
    rows = []
    for row in range(512):
        physical = 0
        for sub in range(8):
            word = words[8*row+sub]
            # The real physical model uses column=8*bit+sub; spare10bits are0.
            for byte in range(32):
                physical |= SPREAD[(word >> (8*byte)) & 255] << (64*byte+sub)
        rows.append(physical)
    return rows


def check_mask(rows, words):
    # Independent bit-level readback of the actual macro's physical bitlines.
    for address, expected in enumerate(words):
        row, sub = divmod(address, 8)
        observed = sum(((rows[row] >> (8*bit+sub)) & 1) << bit for bit in range(266))
        if observed != expected:
            raise ValueError(f'physical via-map readback mismatch: word {address}')


def build(banks_root, output, ranks, bandf=1):
    output.mkdir(parents=True, exist_ok=False)
    lock = ROOT / 'compiler/models/qwen3-8b/checkpoint_source.json'
    if sha(lock) != LOCK_SHA:
        raise ValueError('repository released-checkpoint lock differs')
    record = dict(schema='opentallas.qwen-tp8-native-scale-rom.v1', checkpoint_revision=REVISION,
                  checkpoint_lock_sha256=LOCK_SHA, checkpoint_index_sha256=INDEX_SHA,
                  tp=TP, groups=GROUPS, result_frame=bandf, macro='ot_rom_4096x266_m8', banks_per_port=16,
                  source_bytes_requantized=False, instances_per_rank=384,
                  address_contract='resident_base+actual emitted me_wcs+nb/16+group*8',
                  sources={}, ranks=[], native_layer_qualified=False,
                  remaining=['actual producer must use emitted resident bases',
                             'native frame/controller and physical views must bind these masks'])
    for rank in ranks:
        destination = output / f'rank{rank}'
        destination.mkdir()
        resident, stages = [], []
        for layer in list(range(36)) + ['head']:
            directory = banks_root / (f'head_images/rank{rank}' if layer == 'head' else f'images/layer{layer}/die{rank}')
            mp = directory / ('head_rom.json' if layer == 'head' else f'layer{layer}_rom.json')
            meta = json.loads(mp.read_text())
            count = 1200 if layer == 'head' else 816
            if (meta['tp'], meta['die'], meta['checkpoint_revision'], meta['checkpoint_lock_sha256']) != (8, rank, REVISION, LOCK_SHA):
                raise ValueError(f'wrong released stage identity: {mp}')
            if layer != 'head' and meta['layer'] != layer:
                raise ValueError(f'wrong layer identity: {mp}')
            path = directory / 'matrix_scale_bf16.hex'
            words = checked_image(path, meta['image_sha256']['matrix_scale_bf16.hex'], count)
            program = banks_root / (f'token_source_plan/head_program_rank{rank}.hex' if layer == 'head' else f'fused_images/layer{layer}/die{rank}/program.hex')
            pr = program_record(program, count, [0,384,768,1152] if layer == 'head' else [0,48,336,528], bandf=bandf)
            entry = dict(stage=layer, base=len(resident), words=len(words), image_path=str(path), image_sha256=sha(path),
                         metadata_path=str(mp), metadata_sha256=sha(mp), program=pr)
            stages.append(entry)
            resident.extend(words)
        if len(resident) != 30576 or not any(resident):
            raise ValueError('incomplete or empty resident scale image')
        (destination/'expected_scale_words.hex').write_text(''.join(f'{word:064x}\n' for word in resident))
        masks = destination / 'masks'; masks.mkdir()
        bank_records = []
        for bank in range(BANKS):
            words = resident[bank*DEPTH:(bank+1)*DEPTH]
            words += [0]*(DEPTH-len(words))
            rows = mask_rows(words);check_mask(rows, words)
            path = masks / f'_dense_bank{bank}.viamap.hex'
            path.write_text(''.join(f'{row:0532x}\n' for row in rows))
            bank_records.append(dict(bank=bank, sha256=sha(path), words_nonzero=sum(bool(x) for x in words)))
        instances = []
        for band in range(3):
            for half in range(2):
                for group in range(4):
                    for column in range(4):
                        for bank in range(4):
                            instance = f'qslab_b{band}_h{half}_g{group}_c{column}_b{bank}'
                            global_bank = 4*column+bank
                            path = masks/(instance+'.viamap.hex')
                            os.link(masks/f'_dense_bank{global_bank}.viamap.hex',path)
                            instances.append(dict(instance=instance, port=8*band+4*half+group, column=column,
                                                  local_bank=bank, resident_bank=global_bank,
                                                  sha256=bank_records[global_bank]['sha256']))
        rr = dict(rank=rank, stages=stages, resident_words=len(resident), resident_word_bits=256,
                  expected_words_sha256=sha(destination/'expected_scale_words.hex'), banks=bank_records, instances=instances)
        (destination/'manifest.json').write_text(json.dumps(rr,indent=2)+'\n')
        record['ranks'].append(rr)
        print(f'PASS rank{rank}: exact released30576words,384native macro IDs,37stage programs',flush=True)
    for path in [Path(__file__), ROOT/'tools/qwen_split/b2_frame.py', ROOT/'tools/hdc_isa.py', lock]:
        record['sources'][str(path.relative_to(ROOT))]=sha(path)
    (output/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--banks',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--ranks',default='0,1,2,3,4,5,6,7')
    ap.add_argument('--bandf',type=int,choices=(1,2),default=1)
    a=ap.parse_args();build(a.banks,a.out,[int(rank) for rank in a.ranks.split(',')],a.bandf)
