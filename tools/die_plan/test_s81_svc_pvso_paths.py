import copy
import json
import pytest
import s81_svc_pvso_paths as P
import bound_macro_paths as B


def fixture(tn, heads=16, scan_read_pipe=False):
    specs = P.specifications(tn, heads, scan_read_pipe)
    contents = [dict(inst=x[0], module=x[-1], lef='macro.lef', origin_um=[i, 7],
                     outline_um=[51.432,20.808], orient='R0') for i,x in enumerate(specs)]
    leaves = {}
    for _, actual, ab, mod, params, _, _ in specs:
        leaves[ab] = f'    // as-built {ab}\n    {mod} #('+', '.join(f'.{k}({v})' for k,v in params.items())+f') {actual} (\n    );\n'
    return {'contents':contents}, ''.join(leaves.values())


@pytest.mark.parametrize('tn',list(P.CASES))
def test_exact31_project_preserves_logical_geometry_provenance(tn,tmp_path,monkeypatch):
    t,b=fixture(tn);raw={'partition_types':{tn:t}};before=copy.deepcopy(raw)
    (tmp_path/'cut.sv').write_text(b);fl=tmp_path/'kit_rtl.f';fl.write_text(str(tmp_path/'cut.sv')+'\n')
    (tmp_path/'kit_rtl.json').write_text(json.dumps({'bound_module':'cut'}))
    monkeypatch.setenv('OT_S81_SVC_PVSO_PATHS','0')
    default,rec=B.project(raw,{tn:str(fl)});assert default is raw and not rec          # opt-out
    monkeypatch.delenv('OT_S81_SVC_PVSO_PATHS',raising=False)                          # default ON (COORD 11-19)
    out,rec=B.project(raw,{tn:str(fl)});assert len(rec[tn]['rows'])==31
    assert raw==before
    for old,new in zip(t['contents'],out['partition_types'][tn]['contents']):
        assert {k:v for k,v in new.items() if k not in ('physical_inst','physical_master')}==old
        assert new['physical_master']==old['module']
        assert new['physical_inst']==dict((r['inst'],r['physical_inst']) for r in rec[tn]['rows'])[old['inst']]
    assert 'u_u_u_pbuf_mem' in out['partition_types'][tn]['contents'][-1]['physical_inst']


@pytest.mark.parametrize('mutation',['missing','ambiguous','wrong_shape','wrong_master','partial_plan'])
def test_refuses_unresolved_or_ambiguous_actual_contract(mutation):
    tn=next(iter(P.CASES));t,b=fixture(tn);line=b.split('    );\n')[0]+'    );\n'
    if mutation=='missing': b=b.replace(line,'')
    elif mutation=='ambiguous':b+=line
    elif mutation=='wrong_shape':b=b.replace('.W(341)','.W(340)',1)
    elif mutation=='wrong_master':t['contents'][0]['module']='wrong'
    else:t['contents'].pop()
    with pytest.raises(ValueError):P.resolve(tn,t,b)


def test_other_type_unaffected():
    assert P.resolve('svc_hi_dsdv_svc_rs__t3',{},'')==[]


@pytest.mark.parametrize("scan_read_pipe", [False, True])
def test_h8_projection_uses_selected_qmem_and_scan_shapes(scan_read_pipe):
    tn = next(iter(P.CASES))
    t, bound = fixture(tn, heads=8, scan_read_pipe=scan_read_pipe)
    t["verilog_defines"] = ["OT_SVC_H8"] + (["OT_SVC_ATT_RDPIPE"] if scan_read_pipe else [])
    assert len(P.resolve(tn, t, bound)) == 31
    with pytest.raises(ValueError, match=r"u_qmem_mem.DEPTH"):
        P.resolve(tn, t, bound.replace(".DEPTH(8), .W(512)", ".DEPTH(16), .W(512)"))
    wrong = "dsdv_svc_mem_la" if scan_read_pipe else "dsdv_svc_mem_lr"
    actual = "dsdv_svc_mem_lr" if scan_read_pipe else "dsdv_svc_mem_la"
    with pytest.raises(ValueError, match=r"u_sw_mem"):
        P.resolve(tn, t, bound.replace(actual, wrong))
