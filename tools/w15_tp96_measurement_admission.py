"""Admission prerequisites only; never builds, launches or retries a campaign."""
import hashlib
import json
import subprocess
from pathlib import Path

LEGACY_SOURCE='250dfa5a92575f77f5bdb98d60b65c27d3932a7f'
ARCHIVE_RELATIVE='results/rtl/w15_tp96_terminal_run1_20261001'
LEGACY_ARCHIVE=Path('/home/ubuntu/w15b-tp96-exact-20261001')/ARCHIVE_RELATIVE
COMMIT_RECEIPT=Path('/tmp/claude-1000/w15b_codex_sram_20261001/tp96_terminal_commit.json')
PREFLIGHT_RELATIVE='results/uarch/w15_tp96_measurement_preflight_20261001.json'
sha=lambda b:hashlib.sha256(b).hexdigest()
REQUIRED_SOURCE_PATHS={
    'tools/uarch_model.py','tools/hdc_golden.py','tools/w15_collectives.py',
    'tools/w15_tp96_exact.py','tools/w15_tp96_preflight.py',
    'tools/w15_tp96_measurement_preflight.py','tools/w15_tp96_measurement_admission.py',
    'results/uarch/economics.json','results/uarch/economics_levers.json',
    'results/floorplan/hbm_gpu/v41_hbm_die.json',
    'results/rtl/w15_tp96_w19_prerequisites_input_20261001.json'}

def check_preflight(root,preflight,rtl_sources=()):
    root=Path(root)
    assert preflight['schema']=='w15_tp96_measurement_preflight_v1'
    assert preflight['ranks']==96 and preflight['packages']==48
    assert preflight['measurement']['bits']==64 and preflight['measurement']['protocol_bits']==16
    assert preflight['negative_contract']['required_rejecting_endpoints']==96
    assert preflight['campaign_launched'] is False
    assert REQUIRED_SOURCE_PATHS|set(rtl_sources)<=set(preflight['source_sha256']),'incomplete source/model preflight'
    for name,h in preflight['source_sha256'].items():
        assert sha((root/name).read_bytes())==h,'source/model preflight mismatch: '+name
    return True

def check_legacy_archive(root,archive=LEGACY_ARCHIVE,commit=None):
    """Require committed terminal evidence, never infer exit from an observation timeout."""
    archive=Path(archive)
    assert (archive/'validation.json').is_file(),'legacy terminal validation absent'
    m=json.loads((archive/'manifest.json').read_text())
    r=json.loads((archive/'record.json').read_text())
    v=json.loads((archive/'validation.json').read_text())
    assert m['source_commit']==r['source_commit']==v['source_commit']==LEGACY_SOURCE
    assert m['latency_measurement']['qualified'] is False and v['composed_latency_qualified'] is False
    assert r['passed'] and v['functional_exact_gate_passed'],'legacy functional FAIL requires diagnosis, not a measurement-only retry'
    assert set(r['cases'])=={'normal','stalled','bad_order','bad_tag'} and all(c['passed'] for c in r['cases'].values())
    assert v['source_model_fixture_binding_verified'] and v['binary_binding_verified']
    assert sha((archive/'outputs.tar.gz').read_bytes())==m['archive_sha256']
    if commit is None:
        receipt=json.loads(COMMIT_RECEIPT.read_text())
        assert receipt['source_commit']==LEGACY_SOURCE and receipt['archive_sha256']==m['archive_sha256']
        commit=receipt['commit']
    # Main or the owned evidence branch may supply this commit; immutable blobs must match.
    for name in ['manifest.json','record.json','validation.json','outputs.tar.gz']:
        b=subprocess.check_output(['git','show',commit+':'+ARCHIVE_RELATIVE+'/'+name],cwd=root)
        assert b==(archive/name).read_bytes(),'legacy committed archive mismatch: '+name
    return dict(commit=commit,source_commit=LEGACY_SOURCE,archive_sha256=m['archive_sha256'],latency_qualified=False)
