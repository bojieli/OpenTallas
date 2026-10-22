import json
from pathlib import Path
import subprocess
import sys

from qualification import carry_unqualified


def test_no_new_false_metadata_leaves_legacy_output_unchanged():
    assert carry_unqualified({}) == {}
    assert carry_unqualified({'schema':'legacy','masters':{}}) == {}


def test_false_source_contract_survives_sta_targets_manifest_and_report(tmp_path):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'qwen_tp8'))
    import die_sta_libs as sta
    import die_clock_check as clock_report
    contract = dict(schema='source-clock',qualification=False,source='actual-source.sv',source_sha256='a'*64)
    views = dict(real={'L':{}},**sta.clock_qualification(contract))
    cl = tmp_path/'libs';cl.mkdir()
    (cl/'views.json').write_text(json.dumps(views))
    for c in ('tt','ff','ss'):
        (cl/f'clocks_{c}.tcl').write_text('create_clock -name stream -period 833.333\n'
            'set_clock_latency -source -clock [get_clocks stream] -100 [get_pins {leaf/ck}]\n')
    geom = tmp_path/'geom';geom.mkdir()
    (geom/'clknets.tsv').write_text('root/pll_r0\tleaf/ck\tL\t0\t0\n')
    out = tmp_path/'out'
    subprocess.run([sys.executable,str(Path(__file__).with_name('qwen_compute_dieclk_prep.py')),
                    '--geom',str(geom),'--clocks-dir',str(cl),'--out',str(out)],check=True,capture_output=True)
    targets = json.loads((out/'targets.json').read_text())
    manifest = carry_unqualified(targets)
    dump = tmp_path/'dump.tsv';dump.write_text('R\troot/pll_r0\t0\t0\t0\t0\n')
    report = clock_report.report(dump,targets=out/'targets.json')
    for artifact in (views,targets,manifest,report):
        assert artifact['physical_qualification_eligible'] is False
        assert artifact['qualification']['scope'] == 'MODEL_ONLY'
