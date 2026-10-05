#!/usr/bin/env python3
"""Extract the retained DS20 installer's address book without compiling images.

Allocation bases delimit conservative ownership envelopes, not exact blob sizes.
The frozen emitter has no workspace allocator: neither alignment gaps nor the
partition installer's zero padding are made available to another compiler.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECIPES = {
    'v41_hbm.py': '69798a0034eaeaee91d30907fa4b34ac4848d757abfbe941398af2e80523b153',
    'v41_dspark.py': '49cede655f035171558b93680a0ba38a8a6730d4338d22b1b6307ac1bfb4da5f',
    'v41_dspark_connected.py': '4b86ca8369964ba981da17cb6116fc8577230ed0b546cd939c4199c809e4eb20',
}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def extract(installed_path, *, verify_images=False):
    installed_path = Path(installed_path).resolve()
    installed = json.loads(installed_path.read_text())
    if installed.get('schema') != 'opentallas.ds_hbm.simulator20_source.v1':
        raise ValueError('actual installed simulator20 source manifest required')
    if installed['topology'] != dict(dies=2, sms_per_die=2,
                                    partitions_per_die=2, sector_words=2097152):
        raise ValueError('unsupported installed topology; no guessed aperture')
    if installed.get('position_extent') != 32 or installed.get('full_shape') is not False:
        raise ValueError('this extraction is specific to the frozen CTX32 recipe')
    name = installed['origin_manifest']
    if Path(name).name != name:
        raise ValueError('origin must be an installed sibling file')
    origin_path = installed_path.parent / name
    if sha(origin_path) != installed['origin_sha256']:
        raise ValueError('installed origin checksum mismatch')
    origin = json.loads(origin_path.read_text())
    if (origin.get('schema') != 'opentallas.ds_hbm_dspark_connected_images.v1'
            or (origin['tp'], origin['nsm'], origin['imw']) != (2, 2, 14)
            or installed['entries'] != origin['entries']
            or installed['layout'] != origin['layout']):
        raise ValueError('installed layout/linked entries do not match emitter')
    for name, digest in RECIPES.items():
        historical = [v for p, v in origin['sources'].items() if Path(p).name == name]
        if historical != [digest] or sha(ROOT/'tools/gpu_sys'/name) != digest:
            raise ValueError('frozen allocation recipe changed: ' + name)
    capacity = 2 * 2097152 * 32
    extent = origin['mem_bytes']
    if type(extent) is not int or not 0 < extent <= capacity or extent % 4096:
        raise ValueError('invalid original backed image extent')
    layout = sorted(origin['layout'].items(), key=lambda p: p[1])
    addresses = [a for _, a in layout]
    if (not addresses or any(type(a) is not int or a < 4096 or a >= extent
                             or a % 128 for a in addresses)
            or len(set(addresses)) != len(addresses)):
        raise ValueError('invalid/duplicate emitted allocation bases')
    for name, digest in origin['artifacts'].items():
        if Path(name).name != name or installed['artifacts'].get(name) != digest:
            raise ValueError('source image checksum lineage mismatch: ' + name)
        if verify_images and sha(installed_path.parent/name) != digest:
            raise ValueError('retained source image checksum mismatch: ' + name)
    # Only the sizes stated literally by the frozen recipe are exact here.
    sizes = dict(X=2560, PRE=128, CTR=128, CTOK=140, SEL=128, NSEL=128,
                 MIX=128, Z=1024, Y=640, EA=1792, ERW=3072, EKV=3584,
                 IDXP=256, ARG=64, ZROW=64, COL=origin['column_layout']['slots']
                 * origin['column_layout']['stride'], ROWQ=40960, ROWMIX=7680,
                 DLOG=80800, YS=640)
    allocations = []
    for i, (name, base) in enumerate(layout):
        end = layout[i+1][1] if i+1 < len(layout) else extent
        size = sizes.get(name)
        if name.startswith(('WIN', 'CKV', 'IK', 'DSK')) and name[len(name.rstrip('0123456789')):].isdigit():
            size = 2048
        if name.startswith('SLOT') and name[4:].isdigit():
            size = 8192
        if name.startswith('DBLK') and name[4:].isdigit():
            size = 512
        if size is not None and base + size > end:
            raise ValueError('literal mutable allocation exceeds next owner: ' + name)
        allocations.append(dict(name=name, base=base, end=end,
                                bounds='conservative ownership envelope including padding',
                                kind='mutable' if size is not None else 'reservation',
                                exact_payload_end=base+size if size is not None else None))
    entries = origin['entries']
    if any(type(pc) is not int or not 0 <= pc < origin['imem_words'] for pc in entries.values()):
        raise ValueError('linked entry outside installed program')
    pins = {str(installed_path): sha(installed_path), str(origin_path): sha(origin_path)}
    for name in RECIPES:
        path = ROOT/'tools/gpu_sys'/name
        pins[str(path)] = sha(path)
    for name in ('tools/ds20_installer_book.py',
                 'tools/gpu_sys/prepare_ds_hbm_simulator20.py',
                 'rtl/gpu_sys/ot_gpu_sys_glue.sv',
                 'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cluster20.sv'):
        pins[str(ROOT/name)] = sha(ROOT/name)
    book = dict(schema='opentallas.ds20.installed_workspace.v1',
                producer='tools/gpu_sys/v41_dspark_connected.py',
                memory_bytes=capacity, original_image_bytes=extent,
                die_local=True, identical_layout_dies=[0, 1], position_extent=32,
                occupied=[dict(kind='reservation', base=0, end=extent,
                               owner='original source image and runtime allocations')],
                workspaces=[], allocation_envelopes=allocations,
                index_local_sources={}, source_pins=pins,
                image_artifact_pins=origin['artifacts'],
                image_bytes_verified=verify_images,
                unassigned_padding=dict(base=extent, end=capacity,
                    workspace_authorized=False),
                missing_bindings=['installer workspace reservation',
                    '512 FP32 final score producer span', '512 U32 ID producer span',
                    'linked normal gather parent entry', 'private CMD descriptor bank',
                    'linked W2 parent entry'],
                existing_index=dict(partial_scores=dict(base=origin['layout']['IDXP'],
                    end=origin['layout']['IDXP']+256, words_per_sm=32,
                    final_scores_resident=False),
                    selection=dict(base=origin['layout']['SEL'],
                        end=origin['layout']['SEL']+128,
                        semantics='32 shared-memory attention-list addresses, not U32 IDs')),
                production_installation_complete=False)
    linked = dict(schema='opentallas.ds20.installed_linked_entries.v1',
                  entries=entries, imem_words=origin['imem_words'],
                  programs={n: h for n, h in origin['artifacts'].items()
                            if n.startswith('prog_')},
                  normal_gather_entry_pcs=[], w2_entry_pcs=[],
                  private_descriptor_banks=[], source_pins=pins)
    return book, linked


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--installed', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--verify-images', action='store_true')
    a = p.parse_args()
    book, linked = extract(a.installed, verify_images=a.verify_images)
    a.out.mkdir(parents=True, exist_ok=False)
    for name, record in [('workspace.json', book), ('linked_entries.json', linked)]:
        (a.out/name).write_text(json.dumps(record, indent=2)+'\n')
