"""KVPC-R 10-23 (OT_KV_PC_R3=a|b, default off): the r3 PC kits (qkd_kvs_pc_r3a 270.0 x 356.4 / r3b 302.4 x 356.4) narrow
the PC die slot, keep the PHY face abutted, move o_grp N -> E, and leave every default design point unchanged."""
import importlib
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def load(**env):
    keep = {k: os.environ.get(k) for k in ('OT_KV_PC_R3', 'OT_KV_PC_SR13', 'OT_KV_PC_H_R3')}
    try:
        for k in keep:
            os.environ.pop(k, None)
        os.environ.update(env)
        import kv_static_die as KSD
        return importlib.reload(KSD)
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_default_unchanged():
    K = load()
    assert K.PC_R3 is None
    assert K.pc_slot('pc') == (270.0, 302.4) and K.pc_slot('pc_h') == (270.0, 302.4)
    assert K.KIT_FACE['qkd_kvs_pc']['o_grp'] == 'N' and K.KIT_FACE['qkd_kvs_pc_h']['o_grp'] == 'N'
    K = load(OT_KV_PC_SR13='1')
    assert K.pc_slot('pc') == (390.96, 358.56) and K.pc_slot('pc_h') == (390.96, 358.56)


@pytest.mark.parametrize('v,w', [('a', 272.16), ('b', 304.56), ('r4a', 207.36), ('r4b', 228.96)])
def test_r3_slot_and_face(v, w):
    K = load(OT_KV_PC_R3=v, OT_KV_PC_SR13='1')
    assert K.pc_slot('pc') == (w, 358.56)
    assert K.pc_slot('pc_h') == (390.96, 358.56)          # no PC_H r3 kit yet: sr13 slot kept
    assert K.KIT_FACE['qkd_kvs_pc']['o_grp'] == 'E'
    assert K.KIT_FACE['qkd_kvs_pc_h']['o_grp'] == 'N'
    assert K.pin_face('qkd_kvs_pc', 'i_next') == 'N' and K.pin_face('qkd_kvs_pc', 'o_prev') == 'S'
    # the kit's own outline matches the knob (kit generator constants)
    assert K.PC_R3_KITS[v][1] + 2.16 == pytest.approx(w)


def test_bad_value_refused():
    with pytest.raises(ValueError, match='OT_KV_PC_R3'):
        load(OT_KV_PC_R3='c')


@pytest.mark.parametrize('v,w', [('a', 272.16), ('b', 304.56), ('r4a', 207.36), ('r4b', 228.96)])
def test_pc_h_r3(v, w):
    K = load(OT_KV_PC_R3=v, OT_KV_PC_H_R3='1', OT_KV_PC_SR13='1')
    assert K.pc_slot('pc_h') == (w, 358.56) and K.pc_slot('pc') == (w, 358.56)
    assert K.KIT_FACE['qkd_kvs_pc_h']['o_grp'] == 'E' and K.KIT_FACE['qkd_kvs_pc']['o_grp'] == 'E'


def test_pc_h_r3_needs_pc_r3():
    with pytest.raises(ValueError, match='OT_KV_PC_H_R3'):
        load(OT_KV_PC_H_R3='1')
