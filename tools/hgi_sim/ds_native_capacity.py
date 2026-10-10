"""Explicit, off-default native gather producer sizing; no runtime selection change.

The caller supplies the actual Lower/Layout and opts in to an admitted K. This
emits the existing software fallback records with O.n=K, resized count storage,
and a single epoch's selected byte range. Native frontend binding remains separate.
"""
import copy
import numpy as np
from hgi_sim.ds_vm8_allocation import plan, check_record


def compiler_layout(source_layout, selected_rows, enabled=False):
    if not enabled:
        return copy.deepcopy(source_layout), None
    if selected_rows not in (512, 2048):
        raise ValueError('Only explicitly sized K512/K2048 producer fixtures are admitted')
    source = copy.deepcopy(source_layout)
    source.SIZES = dict(source.SIZES)
    source.SIZES['RGCNT'] = max(source.SIZES['RGCNT'], (selected_rows+63)//64)
    allocation = plan(source, selected_rows)
    target = copy.deepcopy(source)
    target.vm = dict(allocation['new_bases'])
    target.end = allocation['scratch']['end']//4
    for span in allocation['spans']:
        target.SIZES[span['name']] = span['words']
    return target, allocation


def emit_gather(lower, add, op, rank, head, enabled=False, allocation=None):
    if not enabled:
        return lower.row_gather_sw(add, op, rank, head)
    k = op['elems']//512
    if allocation is None or k != allocation['max_selected']:
        raise ValueError('Actual emitted selection does not match the sized producer')
    chunks = (k+63)//64
    def sized_add(record, reads, writes, run=True):
        if record.tag == 'row_gather.owned':
            record.desc['O'].n = k
        if record.tag == 'row_gather.counts':
            record.desc['A'].n = chunks
            record.desc['O'].n = chunks
        if record.tag.startswith('row_gather.place'):
            q = int(record.tag[len('row_gather.place'):])
            record.desc['O'].base = q*64*2048
            writes = ['selected_vm_epoch']
        if record.tag.startswith('row_gather.selected_fence'):
            reads = writes = ['selected_vm_epoch']
        check_record(record, allocation)
        add(record, reads, writes, run)
    lower.row_gather_sw(sized_add, op, rank, head)


def chunk_counts(selected_rows):
    """Actual HBM RGCNT source payload, including the final partial chunk."""
    return np.array([min(64, selected_rows-i) for i in range(0, selected_rows, 64)], dtype=np.uint32)


def register_gather_scratch(hbm, base, group, slots, row_words=512):
    """Register the exact slot-major fallback extent; preserve overlap failures."""
    if group != 96 or not 0 < slots <= 2048 or row_words != 512:
        raise ValueError('Unqualified software gather scratch geometry')
    data = np.zeros(group*slots*row_words, dtype=np.uint32)
    hbm.add(base, data, 'GROWS_SLOT_MAJOR')
    return data
