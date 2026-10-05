"""Admission checks for the opt-in physical endpoint characterization."""
import sys
import hashlib
import json
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from run_abi3_physical import FlowError, w11_controller_endpoint_commands, prepare_w11_orfs_endpoint_netlist


def configuration():
    return dict(top='ot_v41_attn_eng_ctl_phys',
                parameters=dict(BREG=1, D=512, NSTAGE=2, PHYS=1, REPL=2),
                preserve_w11_controller_endpoints=True)


def test_default_has_no_synthesis_commands():
    assert w11_controller_endpoint_commands({}) == []
    block = configuration()
    block['preserve_w11_controller_endpoints'] = False
    assert w11_controller_endpoint_commands(block) == []


@pytest.mark.parametrize('parameter', ['BREG', 'D', 'NSTAGE', 'PHYS', 'REPL'])
def test_rejects_different_geometry(parameter):
    block = configuration()
    block['parameters'][parameter] = 0
    with pytest.raises(FlowError):
        w11_controller_endpoint_commands(block)


def test_rejects_production_engine():
    block = configuration()
    block['top'] = 'ot_hdc_v41x_attn'
    with pytest.raises(FlowError):
        w11_controller_endpoint_commands(block)


def test_orfs_default_does_not_read_or_write(tmp_path):
    assert prepare_w11_orfs_endpoint_netlist({}, tmp_path, tmp_path) is None
    assert not list(tmp_path.iterdir())


def test_orfs_requires_guarded_host_netlist(tmp_path):
    with pytest.raises(FlowError):
        prepare_w11_orfs_endpoint_netlist(configuration(), tmp_path, tmp_path)


@pytest.mark.parametrize('invalid', [None, 'count', 'digest', 'verdict'])
def test_orfs_copies_only_full_size_identity_checked_netlist(tmp_path, invalid):
    netlist = b'module endpoint(input clk); endmodule\n'
    (tmp_path / 'mapped.v').write_bytes(netlist)
    guard = dict(verdict='passed', threshold=270418, expected_sequential=338023,
                 observed_sequential=340305,
                 normalized_netlist_sha256=hashlib.sha256(netlist).hexdigest())
    if invalid == 'count': guard['observed_sequential'] = 102065
    if invalid == 'digest': guard['normalized_netlist_sha256'] = 'invalid'
    if invalid == 'verdict': guard['verdict'] = 'aborted'
    (tmp_path / 'w11_endpoint_guard.json').write_text(json.dumps(guard))
    if invalid:
        with pytest.raises(FlowError):
            prepare_w11_orfs_endpoint_netlist(configuration(), tmp_path, tmp_path)
        assert not (tmp_path / 'w11_endpoint_mapped.v').exists()
    else:
        result = prepare_w11_orfs_endpoint_netlist(configuration(), tmp_path, tmp_path)
        assert (tmp_path / 'w11_endpoint_mapped.v').read_bytes() == netlist
        assert result['mapped_netlist_sha256'] == guard['normalized_netlist_sha256']
