#!/usr/bin/env python3
"""Link source-produced DS-HBM SM kernels and emit real MX1 install events.

This is the SRAM64 SM program linker, not a native690 SU encoder. Input is
unrelocated compiler output for the actual 32 SMs of one die. No arithmetic
qualification or hardware installation acknowledgement is manufactured here.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

KINDS = ('swapin','swapout','embed','layer','head','seed','demb','dsa','dsb','dhead','markov')
SHAPE = dict(hidden=5120, vocabulary=129280, layers=40, draft_block=5,
             verify_columns=6, position_bits=20, token_bits=17, tp=96, sm_per_die=32)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source(item, base):
    p = (base / item['path']).resolve()
    if digest(p) != item['sha256']:
        raise ValueError('source payload hash mismatch: '+item['path'])
    return p

def link(manifest, out):
    manifest, out = Path(manifest), Path(out)
    m = json.loads(manifest.read_text())
    if m.get('schema') != 'opentallas.dshbm.mtp.unlinked_sram64.v1':
        raise ValueError('source-produced unlinked SRAM64 compiler manifest required')
    if m.get('shape') != SHAPE or m.get('arithmetic_contract') != 'chunk8':
        raise ValueError('selected full-shape chunk8 contract required; reduced images refused')
    if m.get('word_bits') != 64 or m.get('imw') != 14:
        raise ValueError('actual SM SRAM64/IMW14 contract required')
    if not m.get('compiler_sources') or not m.get('checkpoint_sources'):
        raise ValueError('compiler and released checkpoint provenance required')
    provenance = {}
    for item in m['compiler_sources']+m['checkpoint_sources']:
        p = source(item,manifest.parent)
        provenance[str(p)] = digest(p)
    # Branch opcodes are read from the compiler's pinned ISA, never guessed.
    isa_path = source(m['isa'],manifest.parent)
    definitions = ast.parse(isa_path.read_text())
    ops = next(ast.literal_eval(n.value) for n in definitions.body
               if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OPS' for t in n.targets))
    branch = (ops['BRA'],ops['BNZ'])
    provenance[str(isa_path)] = digest(isa_path)
    if len(branch) != 2 or len(set(branch)) != 2 or any(type(x)!=int or not 0<=x<256 for x in branch):
        raise ValueError('exact BRA/BNZ opcodes required')
    images = [[] for _ in range(32)]
    entries = {}; extents = {}; missing = []; pc = 0
    for kind in KINDS:
        raw = m.get('kernels',{}).get(kind)
        if raw is None:
            missing.append(kind); continue
        if len(raw) != 32:
            raise ValueError(kind+': actual 32 SM payloads required')
        code = []
        for sm,item in enumerate(raw):
            if item['sm'] != sm:
                raise ValueError('SM order or duplicate ownership')
            p = source(item,manifest.parent)
            words = [int(x,16) for x in p.read_text().split()]
            if not words or any(x<0 or x>>64 for x in words):
                raise ValueError('invalid SRAM64 source words')
            for w in words:
                if w>>56 in branch and (w&0xffffffff)>=len(words):
                    raise ValueError('kernel-relative branch outside owned source')
            code.append(words); provenance[str(p)] = digest(p)
        span = max(map(len,code))
        if pc+span > 1<<14:
            raise ValueError('actual IMW14 SRAM capacity exhausted')
        entries[kind] = pc; extents[kind] = span
        for sm,words in enumerate(code):
            relocated = [(w&~0xffffffff)|((w&0xffffffff)+pc) if w>>56 in branch else w for w in words]
            images[sm].extend(relocated+[0]*(span-len(words)))
        pc += span
    # Only complete images may enable the backend's all-eleven admission gate.
    # Partial images remain useful compiler output but emit no installation.
    out.mkdir(parents=True,exist_ok=False)
    artifacts = {}
    for sm,words in enumerate(images):
        p = out/f'prog_s{sm}.hex'
        p.write_text(''.join(f'{w:016x}\n' for w in words)); artifacts[p.name] = digest(p)
    events = [dict(install_kind=i,install_pc=(entries[k]<<32)|entries[k],
                   kernel=k,pc_each_half=entries[k]) for i,k in enumerate(KINDS)] if not missing else []
    (out/'install_events.json').write_text(json.dumps(events,indent=2)+'\n')
    result = dict(schema='opentallas.dshbm.mtp.linked_sram64.v1',shape=SHAPE,
        source_manifest_sha256=digest(manifest),source_sha256=provenance,
        entries=entries,kernel_extents=extents,imem_words=pc,word_bits=64,
        missing_kernels=missing,installable=not missing,artifacts=artifacts,
        numerical_qualified=False,hardware_installed=False,
        mutable_SRAM_SECDED_required=True,control_storage='plain MX1 flops',
        native690_SU_binding='separate; not encoded or silently substituted',
        cycles='sum actual kernel receipts plus9 ordered backend cycles per launch; no missing latency substituted')
    (out/'program.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();r=link(a.source,a.out)
    print(json.dumps({k:r[k] for k in ('installable','missing_kernels','imem_words')}))
