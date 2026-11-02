"""Source-only normal consumer controls. Native log fixtures are not CAD qualification."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tarfile
from types import SimpleNamespace
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hhp_clock_mesh_role as M
import ft_ports as F
import rtl_lint as L
ROOT = HERE.parents[1]


@pytest.fixture(scope='module')
def kit_template(tmp_path_factory):
    kit = tmp_path_factory.mktemp('private_hhp_consumer')
    context = kit / '.private_hhp_clock_mesh'
    context.mkdir()
    with tarfile.open(ROOT / 'results/hhp_historical_boundary_1102/complete_source_capsule_r4.tar.gz') as tar:
        for member in tar.getmembers():
            assert not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
            assert not member.issym() and not member.islnk()
        tar.extractall(context)
    shutil.copytree(ROOT / 'results/hhp_ft_roles_1102/inputs', context / 'inputs')
    shutil.copy2(ROOT / 'results/hhp_historical_boundary_1102/SOURCE_PREP.json', context / 'source_prep.json')
    shutil.copy2(ROOT / 'results/hhp_clock_mesh_role_1102/canonical_master_family.json', context / 'master_receipt.json')
    cert = M.proposal(context / 'capsule_r4', context / 'inputs', context / 'source_prep.json', 'pc_EN_0',
                      enable=True, master_receipt_path=context / 'master_receipt.json')
    (context / 'certificate.json').write_text(json.dumps(cert))
    request = dict(schema=M.REQUEST_SCHEMA, enabled=True, TYPE=M.TYPE, cohort=M.COHORT, part='pc_EN_0',
                   capsule='.private_hhp_clock_mesh/capsule_r4', inputs='.private_hhp_clock_mesh/inputs',
                   source_prep='.private_hhp_clock_mesh/source_prep.json',
                   master_receipt='.private_hhp_clock_mesh/master_receipt.json',
                   certificate='.private_hhp_clock_mesh/certificate.json')
    (context / 'request.json').write_text(json.dumps(request))
    shutil.copytree(context / 'capsule_r4/pc_EN_0/rtl', kit / 'rtl')
    sources = ' '.join('/work/rtl/' + p.name for p in sorted((kit / 'rtl').iterdir()))
    (kit / 'config.mk').write_text(f'export DESIGN_NAME = {M.TYPE}\nexport VERILOG_FILES = {sources}\nexport OT_PRIVATE_HHP_CLOCK_MESH = 1\n')
    return kit


@pytest.fixture
def kit(kit_template, tmp_path):
    shutil.copytree(kit_template, tmp_path / 'kit')
    return tmp_path / 'kit'


def arcs():
    j = json.loads((ROOT / 'results/hhp_clock_mesh_role_1102/pc_EN_0.json').read_text())
    return [dict(cell='u_bound.u_core_' + r['owner'] + '.' + r['cell'], source=r['parent_input'], sink='ck_mesh', kind='clock')
            for r in j['raw_private_edges']]


def native_log():
    cells = {'kvpc0': 'qkd_kvs_pc_h_head_p', 'kvpc1': 'qkd_kvs_pc', 'kvpc2': 'qkd_kvs_pc', 'kvpc3': 'qkd_kvs_pc'}
    return ('Warning: multiple conflicting drivers for ' + M.TYPE + '_bound.\\ck_mesh:\n' +
            ''.join(f'    port ft_ck_o_{k}[0] of cell u_core_{owner} ({module})\n' for owner, module in cells.items() for k in (0, 1)) +
            "ERROR: Found 1 problems in 'check -assert'.\n")


def native_json(derived=None):
    cert = json.loads((ROOT / 'results/hhp_clock_mesh_role_1102/pc_EN_0.json').read_text())
    name = derived or M.TYPE + '_bound'
    ports = {n: dict(direction='output' if n == 'ck_mesh' else 'input', bits=[i+1]) for i, n in enumerate(cert['ports'])}
    cell_types = {'kvpc0': 'qkd_kvs_pc_h_head_p', **{f'kvpc{k}': 'qkd_kvs_pc' for k in (1,2,3)}}
    cells = {}
    for owner, module in cell_types.items():
        connections, directions = {}, {}
        for edge in cert['raw_private_edges']:
            if edge['owner'] != owner or edge['Y'].endswith('__p1'): continue
            connections[edge['A']] = ports[edge['parent_input']]['bits']; directions[edge['A']] = 'input'
            connections[edge['Y']] = ports['ck_mesh']['bits']; directions[edge['Y']] = 'output'
        cells['u_core_' + owner] = dict(type=module, connections=connections, port_directions=directions)
    return dict(modules={M.TYPE: dict(ports=ports, cells={'u_bound': dict(type=name, connections={n:p['bits'] for n,p in ports.items()})}),
                         name: dict(ports=ports, cells=cells)})


def test_normal_ft_explicit_exact_certificate(kit):
    with pytest.raises(F.FtError): F.declaration(arcs(), 'default')
    d = F.declaration(arcs(), 'private', private_clock_mesh_kit=kit)
    assert len(d['ports']) == 5 and len(d['arcs']) == 4
    assert F.verify(d) == []
    M.verify_private_install(kit, d)


@pytest.mark.parametrize('change', ['cell', 'kind', 'source', 'missing', 'duplicate'])
def test_private_ft_graph_controls(kit, change):
    a = arcs()
    if change in ('cell', 'kind', 'source'): a[0][change] = 'data'
    if change == 'missing': a.pop()
    if change == 'duplicate': a.append(a[0])
    with pytest.raises(ValueError): F.declaration(a, 'bad', private_clock_mesh_kit=kit)


@pytest.mark.parametrize('change', ['disabled', 'editedcert', 'extra_source', 'source_mutant', 'wrongtop', 'escape'])
def test_request_and_actual_source_controls(kit, change):
    if change == 'disabled':
        p = kit / 'config.mk'; p.write_text(p.read_text().replace('MESH = 1', 'MESH = 0'))
    if change == 'editedcert':
        p = kit / '.private_hhp_clock_mesh/certificate.json'; j = json.loads(p.read_text()); j['part'] = 'pc_WN_0'; p.write_text(json.dumps(j))
    if change == 'extra_source':
        p = kit / 'config.mk'; p.write_text(p.read_text().replace('export VERILOG_FILES = ', 'export VERILOG_FILES = /work/rtl/rogue.sv ')); (kit / 'rtl/rogue.sv').write_text('module rogue; endmodule')
    if change == 'source_mutant':
        p = kit / 'rtl' / (M.TYPE + '_bound.sv'); p.write_text(p.read_text() + '\nassign ck_mesh = 1\'b0;\n')
    if change == 'wrongtop':
        p = kit / 'config.mk'; p.write_text(p.read_text().replace('DESIGN_NAME = ' + M.TYPE, 'DESIGN_NAME = data'))
    if change == 'escape':
        p = kit / M.REQUEST_FILE; j = json.loads(p.read_text()); j['capsule'] = '../external'; p.write_text(json.dumps(j))
    with pytest.raises((ValueError, FileNotFoundError)): M.validate_private_request(kit)


def test_exact_native_inventory_classification(kit):
    d = M.classify_native_clock_conflict(kit, native_log(), 1, native_json())
    assert len(d['actual_native_public_drivers']) == 8
    assert d['native_check_rc'] == 1


@pytest.mark.parametrize('change', ['wrongnet', 'data_driver', 'missing_driver', 'duplicate_driver', 'extra_problem', 'extra_error', 'wrongmodule', 'wrong_rc'])
def test_native_conflict_controls(kit, change):
    log = native_log(); rc = 1
    if change == 'wrongnet': log = log.replace('\\ck_mesh:', '\\data:')
    if change == 'data_driver': log = log.replace('port ft_ck_o_0[0]', 'port data[0]', 1)
    if change == 'missing_driver': log = '\n'.join(ln for i, ln in enumerate(log.splitlines()) if i != 1) + '\n'
    if change == 'duplicate_driver': log = log.replace('    port ft_ck_o_1[0]', '    port ft_ck_o_0[0]', 1)
    if change == 'extra_problem': log += 'Warning: Wire data is used but has no driver.\n'
    if change == 'extra_error': log += 'ERROR: hierarchy failure\n'
    if change == 'wrongmodule': log = log.replace('(qkd_kvs_pc)', '(data)', 1)
    if change == 'wrong_rc': rc = 2
    with pytest.raises(ValueError): M.classify_native_clock_conflict(kit, log, rc, native_json())


def test_rtl_lint_normal_entry_preserves_native_record(kit, monkeypatch):
    monkeypatch.setattr(L, 'script', lambda *a, **k: 'check -assert\n')
    def native_fixture_run(*a, **k):
        (kit / 'rtl_lint_elaborated.json').write_text(json.dumps(native_json()))
        return SimpleNamespace(returncode=1, stdout=native_log())
    monkeypatch.setattr(L.subprocess, 'run', native_fixture_run)
    monkeypatch.setattr(L, 'yosys_cast_scan', lambda *a: {})
    monkeypatch.setattr(L, 'mapped_cell_errors', lambda *a: [])
    monkeypatch.setattr(L, 'mapped_cells', lambda *a: {})
    assert L.run(kit) == 0
    record = json.loads((kit / 'rtl_lint.json').read_text())
    assert record['verdict'] == 'PASS' and record['native_check_rc'] == 1
    assert record['native_errors'] and len(record['private_clock_mesh']['actual_native_public_drivers']) == 8
    p = kit / 'config.mk'; p.write_text(p.read_text().replace('MESH = 1', 'MESH = 0'))
    assert L.run(kit) == 1
    assert json.loads((kit / 'rtl_lint.json').read_text())['verdict'] == 'FAIL'


def test_normal_generator_stages_complete_data_before_first_ft(kit_template, tmp_path):
    target = tmp_path / 'generated_source_only'
    target.mkdir()
    shutil.copytree(kit_template / 'rtl', target / 'rtl')
    srcs = ['/work/rtl/' + p.name for p in sorted((target / 'rtl').iterdir())]
    cert, _ = M.stage_private_context(target, kit_template / '.private_hhp_clock_mesh', top=M.TYPE, sources=srcs,
                                    synth_blackboxes=())
    d = F.declaration(M.certificate_arcs(cert), 'normal private generator', private_clock_mesh_kit=target)
    M.verify_private_install(target, d)
    # A final generated config edit that blackboxes the genuine HEAD must fail.
    p = target / 'config.mk'; p.write_text(p.read_text() + '\nexport SYNTH_BLACKBOXES = qkd_kvs_pc_h_head_p\n')
    with pytest.raises(ValueError, match='HEAD'): M.validate_private_request(target)


def test_standalone_context_is_independent_of_repository_results(kit_template, monkeypatch):
    monkeypatch.setattr(M, 'ROOT', Path('/definitely/not/a/repository'))
    assert M.validate_private_request(kit_template)[0]['TYPE'] == M.TYPE


@pytest.fixture
def native_partition_fixture(kit_template, tmp_path, monkeypatch):
    kit = tmp_path / 'partition_fixture'
    kit.mkdir()
    shutil.copytree(kit_template / 'rtl', kit / 'rtl')
    # The plugin stages its own context just as the real generator will.
    bundle = tmp_path / 'request_bundle'
    shutil.copytree(kit_template / '.private_hhp_clock_mesh', bundle)
    shutil.copy2(ROOT / 'results/hhp_native_ft_join_1102/BASE_NATIVE_JOIN_RECEIPT.json', bundle / 'base_native_join.json')
    p = bundle / 'request.json'; req = json.loads(p.read_text()); req['base_native_join'] = '.private_hhp_clock_mesh/base_native_join.json'; p.write_text(json.dumps(req))
    (kit / 'macros').mkdir()
    with tarfile.open(ROOT / 'results/hhp_native_ft_join_1102/actual_PC0355_model_fixture.tar.gz') as tar:
        tar.extractall(kit / 'macros')
    srcs = ' '.join('/work/rtl/' + p.name for p in sorted((kit / 'rtl').iterdir()))
    (kit / 'config.mk').write_text(f'export DESIGN_NAME = {M.TYPE}\nexport VERILOG_FILES = {srcs}\nexport EXTRA_UNCHANGED = 123\n')
    for name in ('face_keep_release.tcl', 'face_flops.tcl', 'face_flops_release.tcl', 'cts_post.tcl', 'grt_post.tcl'):
        (kit / name).write_text('# Original normal hook\n')
    (kit / 'pins.json').write_text('[]\n'); (kit / 'port_bind_pins.json').write_text('[]\n'); (kit / 'io.tcl').write_text('# Original ordinary pins remain here\n')
    receipt = json.loads((bundle / 'base_native_join.json').read_text())
    macros = [(r['inst'], r['master'], 'real.lef', 'real_tt.lib', r['x_um'], r['y_um'], r['orient']) for r in receipt['parent_macro_sites']]
    installs = []
    monkeypatch.setattr(F, 'install', lambda kd, decl: installs.append(decl))
    return kit, bundle, macros, installs


def test_exact_normal_partition_native_multiport_hook(native_partition_fixture):
    import kit_contract as K
    kit, bundle, macros, installs = native_partition_fixture
    pins, info = M.install_generated_partition(kit, bundle, M.TYPE, macros)
    assert len(pins) == 5 and len(installs) == 1
    assert {p['layer'] for p in pins} == {'M1', 'M9'}
    assert len(json.loads((kit / 'pins.json').read_text())) == 5
    assert len(K.placed_pins(kit)) == 5  # Existing normal contract checks every emitted native rectangle.
    assert 'EXTRA_UNCHANGED = 123' in (kit / 'config.mk').read_text()
    assert info['HEAD_private_joins'].endswith('native NOT RUN')
    M.verify_private_install(kit, installs[0])


@pytest.mark.parametrize('change', ['wrongpose', 'wrongmodel', 'missingbase', 'headhard'])
def test_normal_partition_native_registration_controls(native_partition_fixture, change):
    kit, bundle, macros, _ = native_partition_fixture
    if change == 'wrongpose':
        a = list(macros[0]); a[4] += .27; macros[0] = tuple(a)
    if change == 'wrongmodel':
        p = kit / 'macros/qkd_kvs_pc.lef'; p.write_text(p.read_text() + '\n# changed real model\n')
    if change == 'missingbase': macros.pop()
    if change == 'headhard': macros.append(('u_core_kvpc0', 'qkd_kvs_pc_h_head_p', 'none', 'none', 0, 0, 'MY'))
    with pytest.raises(ValueError): M.install_generated_partition(kit, bundle, M.TYPE, macros)


def test_actual_derived_module_identity_is_followed(kit):
    name = "$paramod$exact_native_name\\" + M.TYPE + '_bound'
    log = native_log().replace(M.TYPE + '_bound.\\ck_mesh:', name + '.\\ck_mesh:')
    result = M.classify_native_clock_conflict(kit, log, 1, native_json(name))
    assert result['native_elaborated_inventory']['actual_elaborated_module'] == name


@pytest.mark.parametrize('change', ['extra_output', 'data_consumer', 'wrong_input', 'aliased_cut', 'wrapper_consumer'])
def test_complete_actual_json_census_controls(kit, change):
    j = native_json(); top = j['modules'][M.TYPE]; bound = j['modules'][M.TYPE + '_bound']; bit = bound['ports']['ck_mesh']['bits'][0]
    rogue = dict(type='DATA', port_directions={'Y':'output'}, connections={'Y':[bit]})
    if change == 'extra_output': bound['cells']['rogue'] = rogue
    if change == 'data_consumer': bound['cells']['rogue'] = dict(type='DATA', port_directions={'A':'input'}, connections={'A':[bit]})
    if change == 'wrong_input': bound['cells']['u_core_kvpc0']['connections']['ft_ck_i_0'] = [999]
    if change == 'aliased_cut':
        n = next(n for n in bound['ports'] if n != 'ck_mesh'); bound['ports'][n]['bits'] = [bit]
    if change == 'wrapper_consumer': top['cells']['rogue'] = rogue
    with pytest.raises(ValueError): M.actual_native_mesh_inventory(kit, j)
