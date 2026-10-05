"""Fresh native-only plan: Docker cgroup plus inherited in-container RLIMIT_AS."""
import hashlib
from pathlib import Path

import w17_manifest_bound_relink_plan as previous

EVIDENCE = 'results/rtl/w17_rlimit_bound_native_relink_20261002'
GO_SCHEMA = 'w17.existing_public_ports.rlimit_relink_GO.v1'
ENTRY = 'tools/w17_relink_rlimit_entry.py'
validate_local_identity = previous.validate_local_identity


def build(root):
    p = previous.build(root)
    cmd = p['future_container_argv']
    bad = f'as={4 << 30}:{4 << 30}'
    index = cmd.index(bad)
    if cmd[index - 1] != '--ulimit':
        raise ValueError('exact failed command binding')
    del cmd[index - 1:index + 1]
    image_index = cmd.index(p['image'])
    cmd[image_index:image_index] = ['--volume', 'VERIFIED_CAP_ENTRY:/launcher/entry.py:ro']
    image_index = cmd.index(p['image'])
    cmd[image_index + 1:image_index + 1] = ['python3', '/launcher/entry.py']
    p['AS_enforcement'] = dict(bytes=4 << 30, soft_equals_hard=True,
                               mechanism='resource.setrlimit(RLIMIT_AS) before any tool subprocess/exec',
                               entry=ENTRY, entry_sha256=hashlib.sha256((root / ENTRY).read_bytes()).hexdigest(),
                               effective_getrlimit_verified=True, no_lower_inherited_cap_relaxation=True,
                               cgroup_memory_swap_CPU_pids_verified_before_compiler=True)
    p['tool_environment_prerequisite'] = dict(
        retained_GCC_driver_sha256='2360901d864cf10bfd6296e261cb2c14053552a80377761ab07146ec9ec9a2c0',
        image_Python='3.10.12; resource extension present, metadata inspected',
        original_archives='13 archives,5853 x86_64 ET_REL objects,GCC11.4 comments,no LTO',
        actual_link_ABI_gate='PENDING; metadata compatibility does not prove link success')
    p['prerequisites'] += ['fresh RLIMIT-specific GO; both old manifest-only/config GO schemas rejected',
                           'readonly separately source-pinned cap entry; native inputs remain byte-identical',
                           'effective RLIMIT/cgroup receipt and exact GCC driver SHA printed before compiler exec']
    return p
