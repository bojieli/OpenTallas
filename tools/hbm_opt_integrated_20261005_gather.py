#!/usr/bin/env python3
"""Compile two normal W15 gathers into one installed, leased DS20 workspace.

The installer supplies the pinned memory/spans and linked command entry. This
module allocates only inside that installer's existing workspace pool. It never
uses empty image bytes as an allocation proof, generates payloads, or issues a
hardware grant. Runtime ownership still requires the shared borrower to drain.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import inspect
from pathlib import Path
from types import SimpleNamespace


PROVIDER_PATH = 'rtl/gpu_sys/ot_gpu_sys_glue.sv'
PROVIDER_MODULE = 'ot_gpu_memsys_adapter'
PARENT_PATH = 'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cluster20.sv'
OWNER_HOOK = 'g_on.g_die[d].g_cdc[0].u_x -> g_on.g_die[d].u_mem'
GATHER_BYTES = 393216
PLANE_BYTES = GATHER_BYTES // 2
RESULT_BYTES = 512 * 4


def field(value, bits, name):
    if type(value) is not int or not 0 <= value < (1 << bits):
        raise ValueError('missing/out-of-range installed field: ' + name)
    return value


def interval(span, capacity):
    lo = field(span['base'], 32, 'base')
    hi = field(span['end'], 33, 'end')
    if lo % 64 or hi % 64 or not lo < hi <= capacity:
        raise ValueError('unaligned/out-of-capacity installed span')
    return lo, hi


def reserve_extent(workspaces, occupied, size, capacity):
    """First-fit in explicit installed workspace ranges, excluding every owner.

    A result is a compiler address choice, never a runtime lease acknowledgement.
    The caller includes live producer spans and previous reservations in occupied.
    """
    if any(s.get('kind') not in ('program', 'weight', 'mutable', 'source', 'reservation')
           for s in occupied):
        raise ValueError('typed installed occupied spans required')
    if any(s.get('kind') != 'workspace' for s in workspaces):
        raise ValueError('typed existing workspace pool required')
    used = sorted(interval(s, capacity) for s in occupied)
    for lo, hi in sorted(interval(s, capacity) for s in workspaces):
        at = lo
        for start, stop in used:
            if stop <= at or start >= hi:
                continue
            if at + size <= start:
                break
            at = max(at, stop)
        if at + size <= hi:
            return {'kind': 'reservation', 'base': at, 'end': at + size}
    raise ValueError('existing installed workspace has no disjoint extent')


# Frozen actual allocator implementation in the retained 924acd58a installer.
ALLOCATOR_SHA256 = '69798a0034eaeaee91d30907fa4b34ac4848d757abfbe941398af2e80523b153'


def extend_installer_recipe(program, *, partitions, memory_words):
    """Call the EXISTING Program.put on its live post-build installer object.

    This additive recipe hook runs before the original image emitter. It does
    not rebuild checkpoints or kernels. Old allocations and payload objects are
    retained; only explicit new reservations extend mem_bytes. The caller's
    existing emitter materializes these ranges. Reservation is not a producer,
    runtime lease, linked CMD bank, or proof that NS2 contains 96 index ranks.
    """
    if (partitions, memory_words) != (2, 2097152):
        raise ValueError('actual retained DS20 NS2/MEM_WORDS2097152 required')
    allocator = next((c for c in type(program).__mro__
                      if c.__name__ == 'Program'), None)
    if allocator is None:
        raise ValueError('existing Program allocator object required')
    path = Path(inspect.getsourcefile(allocator.put))
    if hashlib.sha256(path.read_bytes()).hexdigest() != ALLOCATOR_SHA256:
        raise ValueError('original Program.put source pin changed')
    capacity = partitions * memory_words * 32
    old_layout = dict(program.a)
    old_mem_bytes = field(program.mem_bytes, 32, 'installed mem_bytes')
    old_cursor = field(program.cur, 32, 'existing allocator cursor')
    old_payloads = [dict(mm) for mm in program.mem]
    # The old entire image prefix stays untouched, including historical pads.
    # The tail becomes authorized ONLY through these explicit put calls.
    cursor = (max(old_cursor, old_mem_bytes) + 63) // 64 * 64
    sizes = [('HBM_INDEX_GATHER_ARENA', GATHER_BYTES, 'workspace'),
             ('HBM_INDEX_RESULT_SINK', RESULT_BYTES, 'workspace'),
             ('HBM_INDEX_CMD_DESCRIPTOR', 64, 'mutable')]
    if any(name in old_layout for name, _, _ in sizes):
        raise ValueError('normal-gather successor already allocated')
    new_end = cursor + sum(size for _, size, _ in sizes)
    emitter_end = (new_end + 4095) // 4096 * 4096
    if old_mem_bytes <= 0 or emitter_end > capacity:
        raise ValueError('explicit successor reservations exceed installed capacity')
    for mm in old_payloads:
        if any(type(a) is not int or a < 0 or a + len(b) > old_mem_bytes
               for a, b in mm.items()):
            raise ValueError('original payload outside actual image prefix')
    program.cur = cursor
    reservations = []
    for name, size, kind in sizes:
        base = program.put(name, size, align=64)
        if base != cursor:
            raise ValueError('existing allocator successor changed address recipe')
        reservations.append(dict(name=name, kind=kind, base=base, end=base+size,
                                 requested_bytes=size, allocator='Program.put'))
        cursor += size
    if any(program.a[k] != v for k, v in old_layout.items()) or any(
            set(mm) != set(old) or any(mm[a] is not old[a] for a in old)
            for mm, old in zip(program.mem, old_payloads)):
        raise ValueError('original allocation/payload objects changed')
    program.mem_bytes = emitter_end
    return dict(schema='opentallas.ds20.normal_gather.recipe_successor.v1',
                allocator_path=str(path), allocator_sha256=ALLOCATOR_SHA256,
                original_mem_bytes=old_mem_bytes, original_cursor=old_cursor,
                memory_bytes=capacity, emitted_mem_bytes=emitter_end,
                allocations=reservations, original_layout=old_layout,
                producer_enrolled=False, normal_gather_entry_enrolled=False,
                private_CMD_bank_enrolled=False, runtime_lease_granted=False,
                scope='explicit new reservations; original source/math untouched')


def extend_saved_installer_recipe(workspace_path, allocator_path):
    """Run frozen Program.put on the terminal installer's real allocation book.

    Restore ONLY put's cur/a state, protecting the entire emitted image prefix.
    No checkpoint/model import, build_images replay, payload generation or old
    byte writes. Reservations are real successor recipe authority, not proof
    that the provider has installed the successor or has a 96x512 producer.
    """
    workspace_path, allocator_path = Path(workspace_path), Path(allocator_path)
    raw = workspace_path.read_bytes()
    book = json.loads(raw)
    allocator_raw = allocator_path.read_bytes()
    if hashlib.sha256(allocator_raw).hexdigest() != ALLOCATOR_SHA256:
        raise ValueError('frozen Program.put source pin changed')
    if (book.get('schema') != 'opentallas.ds20.installed_workspace.v1'
            or book.get('memory_bytes') != 2*2097152*32
            or book.get('producer') != 'tools/gpu_sys/v41_dspark_connected.py'
            or book.get('workspaces') != []):
        raise ValueError('actual original DS20 installer book required')
    old_end = field(book['original_image_bytes'], 32, 'original image bytes')
    occupied = book['occupied']
    if occupied != [dict(kind='reservation', base=0, end=old_end,
                         owner='original source image and runtime allocations')]:
        raise ValueError('original entire image prefix ownership required')
    layout = {a['name']: a['base'] for a in book['allocation_envelopes']}
    if len(layout) != len(book['allocation_envelopes']):
        raise ValueError('duplicate original emitted allocation names')
    if any(type(a) is not int or not 0 <= a < old_end for a in layout.values()):
        raise ValueError('invalid original emitted allocation base')
    # Execute the original source node, not a reimplemented allocator.
    tree = ast.parse(allocator_raw, filename=str(allocator_path))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Program')
    node = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'put')
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(allocator_path), 'exec'), namespace)
    state = SimpleNamespace(cur=old_end, a=dict(layout))
    allocations = []
    sizes = [('HBM_INDEX_GATHER_ARENA', GATHER_BYTES, 'workspace'),
             ('HBM_INDEX_RESULT_SINK', RESULT_BYTES, 'workspace'),
             ('HBM_INDEX_CMD_DESCRIPTOR', 64, 'mutable')]
    if old_end % 4096 or old_end+sum(n for _,n,_ in sizes)>book['memory_bytes']:
        raise ValueError('explicit successor exceeds actual backing aperture')
    for name, size, kind in sizes:
        if name in state.a:
            raise ValueError('successor already reserved')
        base = namespace['put'](state, name, size, align=64)
        allocations.append(dict(name=name, kind=kind, base=base, end=base+size,
                                requested_bytes=size, allocator='Program.put'))
    successor = dict(book)
    successor['workspaces'] = [a for a in allocations if a['kind']=='workspace']
    successor['occupied'] = occupied + [a for a in allocations if a['kind']=='mutable']
    successor['recipe_successor'] = dict(
        allocator_path=str(allocator_path), allocator_sha256=ALLOCATOR_SHA256,
        original_book_sha256=hashlib.sha256(raw).hexdigest(),
        initial_cursor=old_end, cursor_authority='protect whole original emitted image prefix',
        allocations=allocations, emitted_image_bytes=(state.cur+4095)//4096*4096,
        original_layout_preserved=all(state.a[k]==v for k,v in layout.items()),
        old_image_bytes_rewritten=0, payload_generation=False,
        original_emitter_hook='extend_installer_recipe before existing emit_images',
        actual_provider_image_installed=False, producer_enrolled=False,
        linked_entry_enrolled=False, private_CMD_bank_enrolled=False)
    successor['unassigned_padding'] = dict(base=state.cur, end=book['memory_bytes'],
                                          workspace_authorized=False)
    successor['workspace_producer'] = 'tools/hbm_opt_integrated_20261005_gather.py'
    successor['workspace_producer_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    successor['required_vm_address_bits'] = (book['memory_bytes']//64-1).bit_length()
    successor['missing_bindings'] = [b for b in book['missing_bindings']
                                     if b != 'installer workspace reservation']
    successor['production_installation_complete'] = False
    return successor


def require_index_producer(book, artifacts):
    """Do not promote NS2 IDXP/SEL or small formatter fixture to full geometry."""
    p = book.get('index_producer')
    if not p or p.get('rank_count') != 96 or p.get('candidates_per_rank') != 512:
        raise ValueError('actual Sagan 96-rank/512-score-and-literal-ID producer missing')
    if p.get('score_dtype') != 'FP32' or p.get('id_dtype') != 'U32':
        raise ValueError('literal separate FP32 score/U32 ID producer required')
    if p.get('source_path') not in artifacts or p.get('source_phase_path') not in artifacts:
        raise ValueError('actual producer source/phase not pinned')
    if p.get('scores_span_name') != 'scores' or p.get('ids_span_name') != 'ids':
        raise ValueError('actual source-phase score/ID span association required')


def compile_normal_gather(installation, root):
    """Emit private loader words and literal normal-DMA commands from an image.

    This is the missing compiler half of the opt-in owner binding. An actual
    source-pinned installer book and linked parent entry are mandatory; the
    currently published DS20 parent has no normal-W15 lease/launch hook yet.
    """
    root = Path(root)
    artifacts = installation.get('source_artifacts')
    if not artifacts:
        raise ValueError('missing installed source/image authority')
    for name, digest in artifacts.items():
        p = root / name
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            raise ValueError('missing/changed installed source: ' + name)
    for name in (PROVIDER_PATH, PARENT_PATH):
        if name not in artifacts:
            raise ValueError('selected existing provider/parent source not pinned: ' + name)
    def pinned_json(key):
        name = installation.get(key)
        if name is None:
            raise ValueError('actual installed binding missing: ' + key)
        if name not in artifacts:
            raise ValueError('installer/linked source not pinned: ' + name)
        return json.loads((root / name).read_text())
    book = pinned_json('workspace_path')
    linked = pinned_json('linked_entries_path')
    if book.get('schema') != 'opentallas.ds20.installed_workspace.v1':
        raise ValueError('typed actual installer workspace book required')
    capacity = field(book['memory_bytes'], 33, 'memory_bytes')
    if not 0 < capacity <= (1 << 32):
        raise ValueError('existing MREQ address aperture required')
    occupied = list(book['occupied'])
    # The book comes from the actual installer, including dynamic mutable spans.
    # Zero-filled image contents or the historical W19 policy are not substitutes.
    producer = book['producer']
    if producer not in artifacts:
        raise ValueError('actual workspace installer source not pinned')
    require_index_producer(book, artifacts)
    workspace_producer = book.get('workspace_producer')
    if workspace_producer not in artifacts or artifacts[workspace_producer] != book.get('workspace_producer_sha256'):
        raise ValueError('actual successor workspace emitter source not pinned')
    sources = book['index_local_sources']
    score = interval(sources['scores'], capacity)
    ids = interval(sources['ids'], capacity)
    if score[1] - score[0] != 2048 or ids[1] - ids[0] != 2048:
        raise ValueError('selected 512 literal FP32-score/U32-ID source words required')
    for span in (sources['scores'], sources['ids']):
        if span.get('kind') != 'source':
            raise ValueError('typed actual local source span required')
        if span['producer'] not in artifacts:
            raise ValueError('actual local producer source not pinned')
        occupied.append(span)
    if max(score[0], ids[0]) < min(score[1], ids[1]):
        raise ValueError('separate score/ID source spans overlap')
    gathered = reserve_extent(book['workspaces'], occupied, GATHER_BYTES, capacity)
    result = reserve_extent(book['workspaces'], occupied + [gathered], RESULT_BYTES, capacity)
    # The actual installed address aperture, not W15's historical WA=12.
    wa = field(linked['normal_gather_vm_address_bits'], 6, 'normal_gather_vm_address_bits')
    if not 13 <= wa <= 26:
        raise ValueError('installed W15 WA must cover arena within 32-bit byte aperture')
    for span in (sources['scores'], sources['ids'], gathered, result):
        if span['end'] // 64 > (1 << wa):
            raise ValueError('installed span exceeds linked W15 VM-word aperture')
    entry = field(installation['entry_pc'], 32, 'entry_pc')
    if entry not in linked['normal_gather_entry_pcs']:
        raise ValueError('actual linked normal-gather parent entry missing')
    program_path, command_path = installation['program_path'], installation['command_path']
    if program_path not in artifacts or command_path not in artifacts:
        raise ValueError('actual installed program/command image not pinned')
    program = (root / program_path).read_text().split()
    commands = [int(w, 16) for w in (root / command_path).read_text().split()]
    if entry >= len(program):
        raise ValueError('linked entry outside installed program')
    bank = field(installation['descriptor_loader_base'], 8, 'descriptor_loader_base')
    if bank + 8 > 256 or any(commands[bank:min(bank + 8, len(commands))]):
        raise ValueError('descriptor overwrites live CMD64 words')
    if [bank, bank + 8] not in linked['private_descriptor_banks']:
        raise ValueError('linked installer did not reserve this private loader bank')
    # No new public opcode: existing CP launches the actual linked entry.
    # Eight private words captured by the priced normal-gather owner binding.
    words = [entry, score[0] | (ids[0] << 32), gathered['base'] | (gathered['end'] << 32),
             result['base'] | (result['end'] << 32), capacity,
             96 | (512 << 16) | (32 << 32), 0, 0]
    if any(w >= (1 << 64) for w in words):
        raise ValueError('private descriptor exceeds CMD64 encoding aperture')
    return dict(default_enabled=False, provider_path=PROVIDER_PATH,
                provider_module=PROVIDER_MODULE, parent_path=PARENT_PATH,
                owner_hook=OWNER_HOOK, entry_pc=entry,
                loader_words=[{'address': bank + n, 'data': w} for n, w in enumerate(words)],
                gathered_extent=gathered, result_extent=result,
                command_address_unit_bytes=64, provider_address_unit_bytes=1,
                w15_vm_address_bits=wa, exclusive_borrowers=['index', 'SU', 'W2'],
                formatter_module='ot_hbm_accel_index_w15_planemajor_formatter',
                formatter_binding=dict(base_vm_word=gathered['base'] // 64,
                    extent_vm_words=GATHER_BYTES // 64, rank_words=32,
                    id_plane_vm_word_offset=PLANE_BYTES // 64,
                    layout='plane-major', address_unit_bytes=64),
                normal_commands=[
                    dict(mode=1, topk=0, GW=1, src=score[0] // 64, n=32,
                         dst=gathered['base'] // 64, plane='scores'),
                    dict(mode=1, topk=0, GW=1, src=ids[0] // 64, n=32,
                         dst=(gathered['base'] + PLANE_BYTES) // 64, plane='IDs')],
                layout='plane-major: 96*32 score words, then96*32 ID words',
                runtime_lease_required=True, hardware_reservation_granted=False,
                source_sha256=artifacts, production_installation_complete=False,
                rate_credit=False, physical_admitted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--installation', type=Path)
    action.add_argument('--extend-installed-book', type=Path)
    parser.add_argument('--allocator', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.extend_installed_book:
        if args.allocator is None:
            parser.error('--allocator actual pinned Program source required')
        compiled = extend_saved_installer_recipe(args.extend_installed_book, args.allocator)
    else:
        compiled = compile_normal_gather(json.loads(args.installation.read_text()),
                                         args.installation.parent)
    with args.out.open('x') as f:
        json.dump(compiled, f, indent=2)
        f.write('\n')
