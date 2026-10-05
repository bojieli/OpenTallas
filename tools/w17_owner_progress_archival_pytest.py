"""Opt-in pytest adapter for unchanged historical D1/resource tests; source-only."""
import pytest
import w17_owner_progress_archival_replay as archive
@pytest.fixture(autouse=True)
def committed_archival_inputs(request):
    name=request.module.__name__.split('.')[-1]
    kind={'test_w17_D1_PC24_inputs':'d1','test_w17_owner_progress_resource_r2':'r2'}.get(name)
    if kind:
        module=request.module.m
        saved=dict(module.__dict__)
        archive.bind(module,kind)
        yield
        module.__dict__.clear();module.__dict__.update(saved)
    else:yield
