import copy
import hashlib
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'tools' / 'die_plan'))
import native_source_banks as N
import soft_cs_placement as S


def fixture():
    text = 'module top(input clk, input [1:0] d);\nreg [1:0] r;\nalways @(posedge clk) r <= d;\nendmodule\n'
    sha = hashlib.sha256(text.encode()).hexdigest()
    bank = dict(id='r', source='nativeRTL:'+sha+'#r', source_kind='OTHER_REG',
                actual_register_declaration='reg [1:0] r;', driver_statements=['always @(posedge clk) r <= d;'],
                live_referenced_scalar_count=2, live_referenced_scalar_ids=['r[1]', 'r[0]'], constant_masks=[])
    manifest = dict(schema='opentallas.native_source_banks.v1', source_rtl_sha256=sha, banks=[bank])
    row = dict(id='r', source=bank['source'], cell_glob='*r*', bit_sites_um=[[1, 0], [3, 0]], bit_site_cell_um=[1, 1])
    return text, manifest, row


def test_explicit_source_order_and_private_preservation():
    text, manifest, row = fixture()
    rows, globs = S.prepare({'clock': {'soft_reg_banks': [row]}}, text, native_manifest=manifest)
    assert rows[0]['native_scalars'] == ['r[1]', 'r[0]']
    assert globs == {'*r*'}
    kept, wrappers = N.preserve(text, manifest, {})
    assert '(* keep = 1 *) reg [1:0] r;' in kept
    assert '(* keep' not in text and wrappers == {}


@pytest.mark.parametrize('fault', ['source', 'missing', 'duplicate', 'driver', 'sites', 'no_geometry'])
def test_bad_source_contract_fails(fault):
    text, m, row = fixture()
    if fault == 'source': m['source_rtl_sha256'] = '0'*64
    if fault == 'missing': m['banks'][0]['live_referenced_scalar_ids'][0] = 'r[2]'
    if fault == 'duplicate': m['banks'][0]['live_referenced_scalar_ids'][0] = 'r[0]'
    if fault == 'driver': m['banks'][0]['driver_statements'] = ['r <= wrong;']
    if fault == 'sites': row['bit_sites_um'].pop()
    rows = [] if fault == 'no_geometry' else [row]
    with pytest.raises(ValueError):
        S.prepare({'clock': {'soft_reg_banks': rows}}, text, native_manifest=m)


def test_native_array_masks_hash_and_preservation():
    text, m, row = fixture()
    wrapper = "module mem; reg [1:0] mem [1:0]; always @(posedge clk) begin mem[0][1:0] <= {d[0:0], 1'b0}; mem[1][1:0] <= {d[1:1], 1'b0}; end endmodule"
    text += '\nmem inst();\n'
    sha = hashlib.sha256(text.encode()).hexdigest()
    m['source_rtl_sha256'] = sha
    b = m['banks'][0]
    b['source'] = row['source'] = 'nativeRTL:'+sha+'#r'
    b.update(native_instance='inst', source_kind='ARRAY', register_stem='inst/\\mem', actual_register_declaration='reg [1:0] mem [1:0];',
             live_referenced_scalar_ids=['inst/\\mem[1][1]', 'inst/\\mem[0][1]'],
             constant_masks=[dict(word=0, ranges=[[0, 0]], value=0), dict(word=1, ranges=[[0, 0]], value=0)],
             native_array_definition=dict(module='mem', register='mem', width=2, words=2, sha256=hashlib.sha256(wrapper.encode()).hexdigest()))
    assert S.prepare({'clock': {'soft_reg_banks': [row]}}, text, native_manifest=m, wrapper_sources={'mem': wrapper})[0][0]['native_scalars'] == b['live_referenced_scalar_ids']
    assert '(* keep = 1 *)' in N.preserve(text, m, {'mem': wrapper})[1]['mem']
    with pytest.raises(ValueError, match='hash'):
        S.prepare({'clock': {'soft_reg_banks': [row]}}, text, native_manifest=m, wrapper_sources={'mem': wrapper+' '})
    b['constant_masks'][0]['value'] = 1
    with pytest.raises(ValueError, match='contradicts'):
        S.prepare({'clock': {'soft_reg_banks': [row]}}, text, native_manifest=m, wrapper_sources={'mem': wrapper})
    b['constant_masks'][0]['value'] = 0
    b['constant_masks'][0]['ranges'] = [[0, 1]]
    with pytest.raises(ValueError, match='inventory'):
        S.prepare({'clock': {'soft_reg_banks': [row]}}, text, native_manifest=m, wrapper_sources={'mem': wrapper})


TCL_FIXTURE = r'''
set ff_blk block; set ff_dbu 1; set ff_orient [dict create 0 R0]
set ff_sw 1; set ff_x0 0; set ff_y0 0; set ff_x1 10; set ff_y1 10; set ff_rh 1
set ff_explicit_occ {}; set is_n 0; set is_fh stdout; set moves {}
proc ff_hits_explicit {args} {return 0}
proc master {method args} {
  switch $method {isBlock {return 0} getName {return DFFHQNx1} getWidth - getHeight {return 1}}
}
proc block {method args} {
  switch $method {getInsts {return {cell_z cell_a}} getNets {return {net1 net0}}}
}
proc cell_z {method args} {inst z $method {*}$args}
proc cell_a {method args} {inst a $method {*}$args}
proc inst {id method args} {
  switch $method {
    getMaster {return master} getName {return $id}
    setLocation {lappend ::moves [list $id {*}$args]}
    setPlacementStatus - setOrient {}
  }
}
proc net1 {method args} {switch $method {getName {return {top/r[1]}} getITerms {return term1}}}
proc net0 {method args} {switch $method {getName {return {top/r[0]}} getITerms {return term0}}}
proc term1 {method args} {switch $method {getIoType {return OUTPUT} getInst {return cell_z}}}
proc term0 {method args} {switch $method {getIoType {return OUTPUT} getInst {return cell_a}}}
'''


@pytest.mark.parametrize('fault', [None, 'merged', 'missing', 'ambiguous', 'overlap'])
def test_scalar_q_bijection_and_atomic_moves(fault):
    text, m, row = fixture()
    rows, _ = S.prepare({'clock': {'soft_reg_banks': [row]}}, text, native_manifest=m)
    setup = TCL_FIXTURE
    if fault == 'merged': setup += '\nproc term0 {method args} {switch $method {getIoType {return OUTPUT} getInst {return cell_z}}}\n'
    if fault == 'missing': setup += '\nproc net0 {method args} {switch $method {getName {return wrong} getITerms {return term0}}}\n'
    if fault == 'ambiguous': setup += '\nproc net0 {method args} {switch $method {getName {return {other/r[1]}} getITerms {return term0}}}\n'
    if fault == 'overlap': rows[0]['bit_sites_um'][1] = (1, 0)
    code = setup + '\n' + S.TCL + '\nset rc [catch {\n' + S.emit(rows)[1] + '\n} message]\n'
    code += 'puts [list RESULT $rc $moves $message]\n'
    result = subprocess.run(['tclsh'], input=code, text=True, capture_output=True, check=True)
    assert not result.stderr, result.stderr
    if fault:
        assert 'RESULT 1 {}' in result.stdout, result.stdout
    else:
        assert 'RESULT 0 {{z 1 0} {a 3 0}}' in result.stdout, result.stdout


def test_absent_manifest_legacy_noop():
    assert S.prepare({}, 'module empty; endmodule') == ([], set())
    assert N.preserve('original', None, {'m': 'wrapper'}) == ('original', {'m': 'wrapper'})


@pytest.mark.parametrize('footprint,success', [(2, True), (0.5, False)])
def test_inverted_q_cluster_is_placed_or_refused_atomically(footprint, success):
    text, manifest, row = fixture()
    row['bit_sites_um'] = [[1, 0], [4, 0]]
    row['bit_site_cell_um'][0] = footprint
    rows, _ = S.prepare({'clock': {'soft_reg_banks': [row]}}, text, native_manifest=manifest)
    setup = TCL_FIXTURE + r'''
proc master_inv {method args} {switch $method {getName {return INVxp67} getWidth - getHeight {return 1}}}
proc inv_x {method args} {
  switch $method {
    getMaster {return master_inv} getName {return inverter_x} getITerms {return {term1 ia}}
    setLocation {lappend ::moves [list inverter_x {*}$args]}
    setPlacementStatus - setOrient {}
  }
}
proc term1 {method args} {switch $method {getSigType {return SIGNAL} getIoType {return OUTPUT} getInst {return inv_x}}}
proc ia {method args} {switch $method {getSigType {return SIGNAL} getIoType {return INPUT} getNet {return net_ff}}}
proc net_ff {method args} {switch $method {getName {return internal_ff_qn} getITerms {return ff_qn}}}
proc ff_qn {method args} {switch $method {getIoType {return OUTPUT} getInst {return cell_z}}}
'''
    code = setup + '\n' + S.TCL + '\nset rc [catch {\n' + S.emit(rows)[1] + '\n} message]\n'
    code += 'puts [list RESULT $rc $moves $message]\n'
    result = subprocess.run(['tclsh'], input=code, text=True, capture_output=True, check=True)
    assert not result.stderr, result.stderr
    expected = 'RESULT 0 {{z 1 0} {inverter_x 2 0} {a 4 0}}' if success else 'RESULT 1 {}'
    assert expected in result.stdout, result.stdout


def test_private_wrapper_copies_only(tmp_path):
    kit = tmp_path/'kit'
    kit.mkdir()
    private = kit/'044_m.sv'
    private.write_text('module m; endmodule')
    outside = tmp_path/'m.sv'
    outside.write_text('module m; endmodule')
    manifest = dict(banks=[dict(source_kind='ARRAY', native_array_definition=dict(module='m'))])
    assert N.kit_wrappers(kit, dict(files=[str(private)]), manifest)[0] == {'m': 'module m; endmodule'}
    with pytest.raises(ValueError, match='kit-local'):
        N.kit_wrappers(kit, dict(files=[str(outside)]), manifest)
    with pytest.raises(ValueError, match='unique'):
        N.kit_wrappers(kit, dict(files=[str(private), str(outside)]), manifest)
    hardlink = kit/'hardlinked_copy.sv'
    hardlink.hardlink_to(private)
    with pytest.raises(ValueError, match='private inode'):
        N.kit_wrappers(kit, dict(files=[str(private)]), manifest)
    hardlink.unlink()
    private.unlink()
    private.symlink_to(outside)
    with pytest.raises(ValueError, match='kit-local'):
        N.kit_wrappers(kit, dict(files=[str(private)]), manifest)
