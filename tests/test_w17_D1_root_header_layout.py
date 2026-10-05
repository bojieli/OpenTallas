import copy
import json
from pathlib import Path
import pytest
from tools.w17_D1_root_header_layout import pod_size,parse_layout,check_anchors
from tools.w17_D1_reset_fault_attribution import verify_pins
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'results/uarch/w17_D1_union_contributor_capture_plan_20261002'


def header(body):
    return '''class alignas(VL_CACHE_LINE_BYTES) Fake___024root final {
public:
// CELLS
Cell* __PVT__cell;
// DESIGN SPECIFIC STATE
'''+body+'\nstd::string trailing;\n};\n'


def test_nested_group_alignment_and_tail_padding():
    x=parse_layout(header('''struct {
CData a;
struct {
SData s;
IData i;
};
CData c;
};
struct {
QData q;
};'''))
    assert x['pointer_cells']==1
    assert {k:v['offset'] for k,v in x['fields'].items()}==dict(a=8,s=12,i=16,c=20,q=24)
    assert x['parsed_prefix_bytes']==32


def test_wide_arrays_preserve_unpacked_stride_and_alignment():
    x=parse_layout(header('''struct {
CData a;
VlUnpacked<SData, 128> users;
VlUnpacked<IData, 128> tags;
VlWide<4> valid;
};'''))
    assert x['fields']['users']['offset']==10
    assert x['fields']['tags']['offset']==268
    assert x['fields']['valid']['offset']==780
    assert x['fields']['valid']['bytes']==16
    assert pod_size('VlUnpacked<VlWide<4>, 2>')==(32,4)


@pytest.mark.parametrize('type_name',['UnknownType','VlWide<0>','VlUnpacked<CData, 0>','double','CData*'])
def test_unsupported_layout_fails_closed(type_name):
    with pytest.raises(ValueError):
        parse_layout(header('struct {\n'+type_name+' wrong;\n};'))


def test_root_base_or_unrecognized_prefix_rejected():
    with pytest.raises(ValueError):
        parse_layout(header('struct {\nCData a;\n};').replace('final {','final : Base {'))
    with pytest.raises(ValueError):
        parse_layout(header('struct {\nCData a;\n};').replace('Cell* __PVT__cell;','QData hidden;'))


def test_duplicate_promoted_names_rejected():
    with pytest.raises(ValueError):
        parse_layout(header('struct {\nCData x;\nstruct {\nCData x;\n};\n};'))


def test_one_byte_wrong_offset_rejects_machine_code_anchors():
    offsets=json.loads((E/'offsets.json').read_text())
    fields={v['member']:v for v in offsets.values()}
    check_anchors(fields)
    fields=copy.deepcopy(fields)
    fields[offsets['fault_r']['member']]['offset']+=1
    with pytest.raises(ValueError,match='anchor'):check_anchors(fields)


def test_plan_all_union_contributors_and_unavailable_code():
    plan=json.loads((E/'plan.json').read_text())
    assert set(plan['inspection']['all_KV_contributors'])=={
        'unsupported_read','bad_block','rope_fault','descriptor_fault',
        'pf_fault','merge_fault','schedule_fault'}
    assert plan['inspection']['prefetch_fault_code']['actual_code'] is None
    assert plan['inspection']['prefetch_fault_code']['availability']=='UNAVAILABLE_NO_STORED_GENERATED_MEMBER'
    assert not plan['GDB']['inferior_started']
    assert plan['GDB']['offline_exit']==0
    assert plan['admission']['fresh_GO_required']
    assert plan['inspection']['replays']==1
    assert plan['scope']['fulltoken'] is False
    assert plan['scope']['original_PC24_cause']=='UNOBSERVED'


def test_capture_has_only_memory_reads_and_no_execution():
    script=(E/'capture_contributors.gdb').read_text()
    commands=[line.strip() for line in script.splitlines() if line.strip() and not line.startswith('#')]
    assert not any(line.split()[0] in ('run','start','starti','attach','call') for line in commands)
    assert all(line.startswith(('set $frame','set $root','set $primeframe'))
               for line in commands if line.startswith('set $'))
    assert "'+0x91d" in script and "'+0x599" in script
    assert 'disable 2' in script
    offsets=json.loads((E/'offsets.json').read_text())
    for label,value in offsets.items():
        assert value['offset_hex'] in script
    assert script.count('D1_FIRST_PRIME_READY_SAMPLE')==8
    verify_pins(E,json.loads((E/'artifact_SHA256.json').read_text()))


def test_disassembly_independent_prime_anchors():
    text=(E/'prime_actor_disassembly.txt').read_text()
    assert '0x2802a' in text and '0x5f104' in text
    assert 'fd86:' in text and '[rbp-0x28]' in text and '[rax+0x40]' in text


def test_virtual_layout_rejected_even_without_base_class():
    with pytest.raises(ValueError,match="virtual"):
        parse_layout(header('struct {\nCData a;\n};')+'\nvirtual void unsafe();\n')
