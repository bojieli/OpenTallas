import copy
import pytest
import dv_lower as D
import dv_lower_mat as M
import dv_lower_vec as V
import programme_lower as L
import programme_store as P


def test_user_operands_read_their_own_native_banks_and_preserve_windows():
    w = D.su_word(nout=1, nin=8, a=16, asi=1, bsrc=1, b=32, bsi=1,
                  c=48, csi=1, dst=1, d=64, dsi=1, red=1, rb=D.W_SC|7)
    vm, cr = {}, {}
    for u in range(4):
        for i in range(8):
            vm[u*4096+16+i] = 100*u+i
            cr[u*2048+32+i] = 1000*u+i
    for u in range(4):
        f = D.su_unpack(L.relocate_instruction(w,u))
        # Independent native decoder bit slices (vm8q 14-bit element addresses).
        word = L.relocate_instruction(w,u)
        a, b, d = (word>>38)&0xffffff, (word>>111)&0xffffff, (word>>270)&0xffffff
        assert [vm[a+i] for i in range(8)] == [100*u+i for i in range(8)]
        assert [cr[b+i] for i in range(8)] == [1000*u+i for i in range(8)]
        assert d == 64+u*4096 and f['rb'] == D.W_SC|7
        # A copied user-zero payload reads a different user's real data.
        if u:
            assert [vm[16+i] for i in range(8)] != [vm[a+i] for i in range(8)]
    xw = D.su_word(nout=1,nin=8,a=0,dst=1,d=D.W_X|128,dsi=1)
    assert D.su_unpack(L.relocate_instruction(xw,3))['d'] == D.W_X|128


@pytest.mark.parametrize('kwargs', [dict(a=4092,asi=1),dict(bsrc=1,b=2044,bsi=1),dict(dst=1,d=4092,dsi=1),dict(asrc=1)])
def test_unqualified_or_crossing_operand_is_rejected(kwargs):
    with pytest.raises(ValueError):
        L.relocate_instruction(D.su_word(nout=1,nin=8,**kwargs),1)


def test_actual_twelve_slice_s8_instruction_and_table_shapes():
    own=D.ownership(slice_rtl='s8')
    assert sorted(V.qkv_roles(own)) == [1,3,5,6,8,10]
    vm,cr=V.vm_map_vec(own),V.crom_map(own)
    isa=V.isa_vec()
    for sid in range(12):
        bl=own['residual']['blocks_per_slice'][sid]
        ssq=D.su_word(nout=len(bl),nin=128,a=vm['X']['base'],aso=128,asi=1,
                       red=1,redsq=1,rb=D.W_SC|bl[0],rso=12)
        img=V.image(sid,V.words(sid,own,vm,cr,isa,att=[0,1,2,3]),ssq)
        records=[dict(eaddr=a,payload=f'{w:0256x}') for a,w in D.prog_words(img)]
        result=L.prog_users(records)
        assert len(result)==4 and all(len(r)==6 for r in result)
        assert [r['payload_hex'] for r in result[0]] == [r['payload'] for r in records]
        assert result[0] != result[3]
        for u,rows in enumerate(result):
            for row in rows:
                value=int(row['payload_hex'],16)
                assert value>>969 == 0 and ((value>>457)&((1<<55)-1))==0
    layout=M.btab_layout(own)
    counts=tuple(sum((e['words']+3)//4 for n,p in layout.items() if n!='lm_head' for e in p.get(s,[])) for s in range(12))
    assert counts==P.BTAB_COUNTS==(16,18,16,18,16,18,18,16,14,12,14,12)
    # Legacy slice2's first six table counts must not silently package s8.
    assert counts[:6] != (18,16,18,16,18,16)


def test_missing_stage_or_slice_never_becomes_zero_tables():
    with pytest.raises(ValueError,match='36'):
        L.compile_inputs(dict(schema='opentallas.qwen.native-table-streams.v1',stages=[]))
    with pytest.raises(ValueError,match='missing native slice'):
        L.stage_tables(1,{}, {}, [])
    rows=[dict(eaddr=i,payload='0') for i in range(6)]
    rows[-1]['eaddr']=0
    with pytest.raises(ValueError,match='distinct'):
        L.prog_users(rows)
