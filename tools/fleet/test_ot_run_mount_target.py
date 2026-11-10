"""Actual-device admission: root bind refusal and exact target capacity."""
import os
import pathlib
import subprocess
from unittest import mock
from test_ot_run_scratch_disk import m, fake_bin

PROBE = '''OT_SCRATCH_FREE /srv/opentallas-scratch 400 1
OT_SCRATCH_FREE /srv/opentallas-scratch2 9 0
OT_SCRATCH_FREE /srv/opentallas-scratch3 400 1
OT_SCRATCH_DEV /srv/opentallas-scratch 1
OT_SCRATCH_DEV /srv/opentallas-scratch2 2
OT_SCRATCH_DEV /srv/opentallas-scratch3 1
OT_DIR_DEV 1
OT_ROOTFS 20 400
OT_DIR_ONROOT 1
'''

def test_root_bind_is_not_capacity_or_eligible_target():
    with mock.patch.object(m, 'ROOT_SCRATCH_ROOTS', ()):
        status = m.scratch_disk({'disk_gb': 400}, None, PROBE, 'intel1')
        assert status['disk_gb'] == 9 and 'floor' in m.host_refusal(status)
        row = m.scratch_disk({'disk_gb': 400}, '/srv/opentallas-scratch3/claude/a', PROBE, 'intel1')
        assert 'ROOT filesystem' in m.host_refusal(row)

def test_exact_dedicated_device_does_not_borrow_roomier_sibling():
    out = PROBE.replace('OT_DIR_DEV 1', 'OT_DIR_DEV 2').replace('OT_DIR_ONROOT 1', 'OT_DIR_ONROOT 0')
    out += 'OT_SCRATCH_FREE /srv/opentallas-scratch4 800 0\nOT_SCRATCH_DEV /srv/opentallas-scratch4 3\n'
    row = m.scratch_disk({'disk_gb': 9}, '/srv/opentallas-scratch2/claude/a', out)
    assert row['disk_gb'] == 9 and row['scratch_disk_gb'] == 9
    assert 'floor' in m.host_refusal(row)

def test_device_match_handles_noncanonical_symlink_path():
    out = PROBE.replace('scratch2 9', 'scratch2 90').replace('OT_DIR_DEV 1', 'OT_DIR_DEV 2').replace('OT_DIR_ONROOT 1', 'OT_DIR_ONROOT 0')
    row = m.scratch_disk({'disk_gb': 90}, '/some/symlink/a', out)
    assert row['disk_dev'] == '2' and not m.host_refusal(row)

def test_explicit_root_exception_keeps_host_floor():
    with mock.patch.object(m, 'ROOT_SCRATCH_ROOTS', ('/srv/opentallas-scratch3',)):
        row = m.scratch_disk({'disk_gb': 400}, '/srv/opentallas-scratch3/claude/a', PROBE, 'intel1')
        assert row['scratch_second'] and row['disk_gb'] == 250
        assert not m.host_refusal(row)


def test_job_host_disk_guard_is_removed_hub_floor_stays():
    """OWNER 11-09: one disk check only, the hub-side per-disk floor; no second check on the job host at launch"""
    assert not hasattr(m, 'disk_guard_sh') and not hasattr(m, 'rootfs_floor_sh')
    assert 'DISK GUARD: root fs' not in open(m.__file__).read().split('def host_refusal', 1)[0].split('# v12 SCRATCH2', 1)[0]
    base = dict(rootfs_free_gb=100, rootfs_floor_gb=150, rootfs_pct=97, host_name='epyc4', scratch_disk='/s2', scratch_disk_gb=500,
                scratch_second=False, free_gb=100, disk_gb=500)
    assert m.host_refusal(dict(base, dir_onroot=True))                  # a job on root is refused below the floor
    assert not m.host_refusal(dict(base, dir_onroot=False))             # a job on the separate scratch disk is admitted
