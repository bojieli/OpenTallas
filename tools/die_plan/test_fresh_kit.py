"""Actual station realization and pinned compact form through the fresh factories."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fresh_kit as F
import compact_coll_form as C
from test_kit_istations import BOUND


def test_partition_realizes_all_stations_before_generation(tmp_path):
    source = F.HERE.parents[1]
    plan = tmp_path / 'plan.json'
    plan.write_text(json.dumps(dict(partition_types=dict(t=dict(
        buses=[dict(name='i_a', dir='in', width=1, kind='data')], contents=[],
        internal_stations=[dict(conn='bus:i_a', from_um=[0, 0], to_um=[10, 20],
                                regs_um=[[j+1, 0] for j in range(8)])])))))
    import kit_topology as KT
    bound=tmp_path/'bound';bound.mkdir()
    KT.write_bind_receipt(json.loads(plan.read_text()),bound)
    out = tmp_path / 'fresh'
    def run(cmd, **kwargs):
        name = Path(cmd[2]).name
        if name == 'kit_topology.py':
            return subprocess.run(cmd, **kwargs)
        if name == 'bind.py':
            rtl = Path(cmd[cmd.index('--kit')+1]); rtl.mkdir()
            (rtl / 't_part_bound.sv').write_text(BOUND)
            (rtl / 'kit_rtl.json').write_text(json.dumps(dict(bound_module='t_part_bound',
                files=[str(rtl / 't_part_bound.sv')])) )
            (rtl / 'kit_rtl.f').write_text(str(rtl / 't_part_bound.sv')+'\n')
        if name == 'gen.py':
            sv = (out / 'rtl/t_part_bound.sv').read_text()
            assert sv.count('u_ist_i_a_') == 8
            assert '.a(i_a_is7_q[0])' in sv
            kit = out / 'gen/t'; kit.mkdir(parents=True)
            (kit/'freeze.json').write_text(json.dumps(dict(module='t_part')))
        if any('/work/rtl_lint.py' in str(c) for c in cmd):
            (out/'gen/t/kit_hierarchy.json').write_text(json.dumps(dict(problems=[],required_expected=8,required_matched=8)))
        if name == 'plan_review.py':
            (out / 'review/die_cores.png').write_bytes(b'fixture-render')
        return subprocess.CompletedProcess(cmd, 0, 'fixture factory\n')
    r = F.prepare(source, 'partition', plan, out, type_name='t',
                  overrides=dict(bind_out=str(tmp_path/'bound'), reset_mode='native'), run=run)
    assert r['verdict'] == 'PREPARED'
    assert (out / 'rtl/istations.tcl').exists()
    assert r['review'] == 'NOT REVIEWED'
    with pytest.raises(ValueError, match='already exists'):
        F.prepare(source, 'partition', plan, out, type_name='t',
                  overrides=dict(bind_out='bound', reset_mode='native'), run=run)
    with pytest.raises(ValueError, match='unsupported fields'):
        F.prepare(source, 'partition', plan, tmp_path/'bad', type_name='t',
                  overrides=dict(bind_out='bound', reset_mode='native', shell_overlay='cp old/*.py .'), run=run)
    assert not (tmp_path/'bad').exists()


def test_compact_form_keeps_current_runner_and_explicit_pinned_rtl(tmp_path, monkeypatch):
    source = tmp_path / "source"; source.mkdir()
    kit = tmp_path / 'kit'; kit.mkdir(); (kit/'rtl').mkdir()
    (kit/'freeze.json').write_text(json.dumps(dict(module='dsfd_coll_lane_e_safe8_ntf',
        outline_um=[295.92,444.96],pins=2143,insertion_ps=405,insertion_ff_ps=340)))
    (kit/'pdn.tcl').write_text('define_pdn_grid -pins {M6}\nadd_pdn_connect -layers {M5 M6}\nmacro -halo {2.0 2.0}\n')
    (kit/'config.mk').write_text('export MACRO_PLACE_HALO = 4.32 4.32\n')
    (kit/'grt_pre_core.tcl').write_text('# current generated hook\n')
    (kit/'run_kit.sh').write_text('# current released runner\n')
    # Exercise real immutable Git reads/hash checks with a tiny source cohort.
    data = {}
    for name in C.SOURCE_FILES:
        path = source / 'rtl/dsrom_sys/s81_ph' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('// pinned RTL '+name+'\n')
        data[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (source/'physical/common_flow').mkdir(parents=True)
    (source/'physical/common_flow/clock_split_km.tcl').write_text('# selected cohort KM helper\n')
    for args in (['init','-q'], ['add','.'], ['-c','user.name=Test','-c','user.email=test@example.test',
                                         'commit','-qm','fixture source']):
        subprocess.run(['git','-C',str(source),*args],check=True)
    revision = subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    monkeypatch.setattr(C, 'SOURCE_REVISION', revision)
    monkeypatch.setattr(C, 'SOURCE_FILES', data)
    ckpin = tmp_path/'ckpin.tcl'; ckpin.write_text('# exact private landing helper\n')
    monkeypatch.setattr(C, 'CLOCK_PIN_SHA256', hashlib.sha256(ckpin.read_bytes()).hexdigest())
    C.replay(source, kit, ckpin)
    assert (kit/'run_kit.sh').read_text() == '# current released runner\n'
    assert '-halo {2.0 1.08}' in (kit/'pdn.tcl').read_text()
    cfg = (kit/'config.mk').read_text()
    assert 'OT_CKKM_K = 32' in cfg and 'BUFx24_ASAP7_75t_R' in cfg
    receipt = json.loads((kit/'source_overlay.json').read_text())
    for name, digest in receipt['sha256'].items():
        assert hashlib.sha256((kit/'rtl'/Path(name).name).read_bytes()).hexdigest() == digest
    assert 'set_routing_layers -signal M2-M6 -clock M4-M5' in (kit/'grt_pre_core.tcl').read_text()
