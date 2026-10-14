import json
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from hgi_e2e.scratch import reserve, bind_mtp_directory


def test_whole_program_reserves_zero_inputs_strides_and_writes():
    meta = {'records': [
        {'eff': {'A': [0, 1024, 1, 0, 1, 'VM']}},
        {'eff': {'A': [2048, 256, 4, 512, 2, 'VM']}},
        {'eff': {'B': [4096, 20000, 1, 0, 1, 'HBM']}},
    ]}
    vm0 = bytearray(32768 * 4)
    struct.pack_into('<I', vm0, 30000 * 4, 1)
    vmw = struct.pack('<II', 24000, 0)
    plan = reserve(meta, vm0, vmw, reserved=[26000], words=16384, vm_words=32768)
    assert plan['base'] >= 4095 and plan['base'] + plan['words'] <= 24000
    assert plan['base'] % 256 == 0


def test_refuses_tail_that_caused_mtp_fused_fault():
    # The old harness base 256064 cannot fit HC_PRE_NORM D5120: 2*D+2 words.
    assert 256064 + 2 * 5120 + 2 > 262144
    with pytest.raises(ValueError, match='no 16384-word'):
        reserve({'records': [{'eff': {'A': [0, 256064, 1, 0, 1, 'VM']}}]}, b'', b'')


def test_binding_changes_only_reserved_host_words_and_meta(tmp_path):
    meta = {'schema': 'opentallas.hgi_e2e.export_mtp.v1',
            'records': [{'eff': {'A': [0, 4096, 1, 0, 1, 'VM']}}],
            'image_sha256': 'immutable-image'}
    (tmp_path / 'meta.json').write_text(json.dumps(meta))
    (tmp_path / 'vm0.bin').write_bytes(b'\0' * 16384)
    (tmp_path / 'vmw.bin').write_bytes(b'')
    original = [f'{i:08x}' for i in range(128)]
    (tmp_path / 'host.mem').write_text('\n'.join(original) + '\n')
    plan = bind_mtp_directory(tmp_path)
    host = (tmp_path / 'host.mem').read_text().splitlines()
    assert host[:96] == original[:96] and host[98:] == original[98:]
    assert int(host[96], 16) == plan['base'] and int(host[97], 16) == 16384
    assert json.loads((tmp_path / 'meta.json').read_text())['image_sha256'] == 'immutable-image'
