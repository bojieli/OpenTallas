"""Metadata and host-only cap tests; no compiler, container or design run."""
import json
from pathlib import Path
import struct
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import inspect_w17_relink_archive_abi as abi
import w17_relink_rlimit_entry as entry


def archive(path, machine=62):
    names = b'\0.shstrtab\0.comment\0'
    comment = b'\0GCC fixture\0'
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    header = struct.pack('<16sHHIQQQIHHHHHH', ident, 1, machine, 1, 0, 0, 64, 0, 64, 0, 0, 64, 3, 1)
    sections = bytes(64) + struct.pack('<IIQQQQIIQQ', 1, 3, 0, 0, 256, len(names), 0, 0, 1, 0)
    sections += struct.pack('<IIQQQQIIQQ', 11, 1, 0, 0, 256 + len(names), len(comment), 0, 0, 1, 0)
    obj = header + sections + names + comment
    ar_header = f"{'fixture.o/':<16}{0:<12}{0:<6}{0:<6}{'100644':<8}{len(obj):<10}`\n".encode()
    path.write_bytes(b'!<arch>\n' + ar_header + obj + (b'\n' if len(obj) % 2 else b''))


def test_archive_metadata_and_wrong_architecture(tmp_path):
    p = tmp_path / 'fixture.a'; archive(p)
    assert abi.inspect(p)['compiler_comments'] == ['GCC fixture']
    archive(p, 183)
    with pytest.raises(ValueError, match='EM_X86_64'):
        abi.inspect(p)


def test_truncated_member_rejected(tmp_path):
    p = tmp_path / 'bad.a'; archive(p); p.write_bytes(p.read_bytes()[:-30])
    with pytest.raises(ValueError, match='bounds'):
        abi.inspect(p)


def test_actual_limits_survive_exec_in_host_test_child():
    code = "import sys,os;sys.path.insert(0,sys.argv[1]);from w17_relink_rlimit_entry import enforce_limits;enforce_limits();os.execv(sys.executable,[sys.executable,'-c','import json,resource;print(json.dumps([resource.getrlimit(resource.RLIMIT_AS),resource.getrlimit(resource.RLIMIT_FSIZE)]))'])"
    got = json.loads(subprocess.check_output([sys.executable, '-c', code, str(ROOT / 'tools')], timeout=5))
    assert got == [[entry.AS_BYTES] * 2, [entry.FILE_BYTES] * 2]


@pytest.mark.parametrize('change', [{'memory.max': 'max'}, {'memory.swap.max': '1'},
                                   {'cpu.max': 'max 100000'}, {'cpu.max': '300000 100000'},
                                   {'pids.max': '65'}])
def test_unenforced_or_relaxed_cgroup_rejected(change):
    good = {'memory.max': str(entry.AS_BYTES), 'memory.swap.max': '0',
            'cpu.max': '200000 100000', 'pids.max': '64'}
    entry.check_cgroup(good, {26, 27})
    with pytest.raises(ValueError):
        entry.check_cgroup({**good, **change}, {26, 27})


def test_lower_existing_hard_cap_is_never_raised():
    code = "import sys,resource;sys.path.insert(0,sys.argv[1]);from w17_relink_rlimit_entry import enforce_limits;resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30));\ntry:enforce_limits()\nexcept ValueError:print('REJECTED')\nelse:raise AssertionError('cap relaxed')"
    assert subprocess.check_output([sys.executable, '-c', code, str(ROOT / 'tools')], timeout=5).strip() == b'REJECTED'
