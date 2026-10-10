"""Minimum source-bound producer/descriptor gate, not a whole-transformer run."""
import hashlib
import json
from pathlib import Path
import numpy as np
from hgi_sim import ds_native as D, machine as M
from hgi_sim.ds_native_capacity import compiler_layout, emit_gather, chunk_counts, register_gather_scratch
from hgi_sim.qwen_compiler import Builder
from hgi_sim.records import Rec, encode_program, decode_program


def run():
    D.TABLE_OFF['RGCNT'] = 0
    D.CK_CAP[0] = 2048*2048
    original = D.Layout()
    receipts = []
    for k in (512, 2048):
        lay, allocation = compiler_layout(original, k, True)
        lower = object.__new__(D.Lower); lower.lay = lay
        b = Builder(None)
        def add(r, rd, wr, run=True):
            if not run:
                r = Rec('CTL', 'NOP', tag=r.tag, family=r.family)
            b.add(r, rd if run else [], wr if run else [])
        emit_gather(lower, add, dict(elems=k*512,src=D.SOURCES[0]), 0, True, True, allocation)
        decoded = decode_program(encode_program(b.recs))
        owned = next(r for r in decoded if r.unit == 'IDX')
        assert owned.desc['O'].n == owned.desc['R'].n == owned.desc['A'].n == k
        assert len(chunk_counts(k)) == k//64
        # Worst-owner adversarial original selected order, not an ascending substitute.
        ids = ((np.arange(k,dtype=np.uint32)//8)*768+np.arange(k,dtype=np.uint32)%8)
        ids = ids[np.random.default_rng(20261010+k).permutation(k)]
        expected_local = (ids//768)*8+ids%8
        assert int(expected_local.max()) < 2048
        checked = 0
        for rank in range(96):
            die = M.Die(rank,M.Hbm()); die.vm=np.full(8*1024*1024//4,0xdeadbeef,dtype=np.uint32)
            die.vm[owned.desc['A'].base:owned.desc['A'].base+k] = ids
            machine = M.Machine([die])
            M.u_idx_owned(machine,owned,0)
            got = die.vm[owned.desc['O'].base:owned.desc['O'].base+k]
            assert np.array_equal(got, expected_local if rank==0 else np.zeros(k,np.uint32))
            reverse = die.vm[owned.desc['R'].base:owned.desc['R'].base+k]
            assert np.array_equal(reverse,np.arange(k,dtype=np.uint32)*96)
            assert np.array_equal(die.vm[owned.desc['D'].base:owned.desc['D'].base+2],[k,k//2])
            # Inverse slot-major positions recover selected IDs in the original order.
            assert np.array_equal(ids,(got[reverse//96]//8)*768+got[reverse//96]%8) if rank==0 else True
            checked += 2*k+2
            if rank==0:
                owned.desc['O'].n=64
                try:
                    M.u_idx_owned(machine,owned,0)
                except M.Fault:
                    pass
                else:
                    raise AssertionError('Old On64 must refuse the real worst-owner shape')
                owned.desc['O'].n=k
        receipts.append(dict(selected_rows=k,max_owned=k,rounds=k//2,owner_capacity=k,
            source_rows_per_rank=2048,source_max_global_id=int(ids.max()),
            source_vehicle='Adversarial generic source extent, not a released DS1M selected-list distribution',
            counts_words=k//64,checked_words=checked,descriptor_hex=owned.encode().hex(),
            program_sha256=hashlib.sha256(encode_program(b.recs)).hexdigest(),
            selected_sha256=hashlib.sha256(ids.tobytes()).hexdigest(),
            idx_input_bytes=4*k,idx_output_bytes_per_rank=8*k+8,
            old_on64_extra_padding_bytes_per_rank=4*(k-64),
            slot_scratch_bytes_per_rank=96*k*512*4,
            scope='Actual encoded OWNED component plus original-order slot-major reconstruction; fallback DMA transport not executed'))
    # Default record generation remains byte identical, including O.n64.
    lower.lay=original
    one=[]; two=[]
    lower.row_gather_sw(lambda r,*args:one.append(r),dict(elems=512*512,src=D.SOURCES[0]),0,True)
    emit_gather(lower,lambda r,*args:two.append(r),dict(elems=512*512,src=D.SOURCES[0]),0,True)
    assert encode_program(one)==encode_program(two)
    # The original head failure is reproduced without expensive transformer work.
    h=M.Hbm()
    try:h.view(D.GBASE,2048)
    except M.Fault:pass
    else:raise AssertionError('Unregistered scratch must fault')
    register_gather_scratch(h,D.GBASE,96,2)
    h.view(D.GBASE+96*2*2048-2048,2048)[:]=np.arange(2048,dtype=np.uint8)
    try:h.view(D.GBASE+96*2*2048,32)
    except M.Fault:pass
    else:raise AssertionError('Scratch end overflow must fault')
    root=Path(__file__).resolve().parent
    return dict(schema='opentallas.hgi_sim.native_capacity.minimum.v1',status='pass',cases=receipts,
        default_byte_identical=True,negative_on64='fault',negative_scratch_missing='fault',negative_scratch_end='fault',
        qualified=False,reason='Producer capacity/order only; native frontend, physical IDX and consumer timing remain separate',
        source_sha256={str(p.relative_to(root.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [root/'ds_native.py',root/'machine.py',root/'ds_native_capacity.py',root/'ds_vm8_allocation.py',root/'ds_native_capacity_gate.py']})


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
