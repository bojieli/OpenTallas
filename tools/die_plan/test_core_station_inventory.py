import hashlib
import pytest
from core_station_inventory import native_banks
from soft_cs_placement import prepare, emit

RTL='''module x(input clk,rst_n);\nreg [3:0] g_u_cst_ve_gd_s_0_u_q;\nalways @(posedge clk) g_u_cst_ve_gd_s_0_u_q <= 0;\nwire [3:0] alias_q = g_u_cst_ve_gd_s_0_u_q;\nreg g_u_cst_ve_gd_s_0_u_eq;\nalways @(posedge clk or negedge rst_n) g_u_cst_ve_gd_s_0_u_eq <= 0;\nendmodule'''

def plan():
    b=native_banks(RTL)[0]
    return {'outline_um':[100,100], 'clock':{'soft_reg_banks':[dict(id=b['id'],cell_glob=b['cell_glob'],source='nativeRTL:'+hashlib.sha256(RTL.encode()).hexdigest()+'#'+b['id'],bit_sites_um=[[2*i,0] for i in range(5)],bit_site_cell_um=[1,.27])]}}

def test_actual_payload_valid_not_alias():
    b=native_banks(RTL)[0]
    assert b['flops']==5 and b['resettable_flops']==1
    assert len(b['rtl_scalars'])==5

def test_no_procedural_driver_fails():
    with pytest.raises(ValueError,match='driver'): native_banks(RTL.replace('g_u_cst_ve_gd_s_0_u_q <=','something_else <='))

def test_wrong_clock_fails():
    with pytest.raises(ValueError,match='clock'): native_banks(RTL.replace('posedge clk','posedge foreign'))

def test_source_bound_exact_manifest():
    rows,globs=prepare(plan(),RTL)
    assert len(rows)==1 and globs=={'*g_u_cst_ve_gd_s_0_u_*'}
    out='\n'.join(emit(rows))
    assert out.index('foreach bank $banks')<out.index('foreach move $moves')
    assert 'actual mapped count' in out and 'exceeds footprint' in out

@pytest.mark.parametrize('mutant',['count','source','partial','broad'])
def test_bad_manifest_refuses(mutant):
    p=plan();r=p['clock']['soft_reg_banks'][0]
    if mutant=='count':r['bit_sites_um'].pop()
    elif mutant=='source':r['source']='nativeRTL:stale'
    elif mutant=='partial':r['cell_glob']='*g_u_cst_ve_gd_s_0_u_q'
    else:r['cell_glob']='*'
    text=RTL
    if mutant=='broad':text+='\nreg g_u_cst_y_gd_s_0_u_q; always @(posedge clk) g_u_cst_y_gd_s_0_u_q <= 0;'
    with pytest.raises(ValueError):prepare(p,text)

def test_absent_metadata_legacy_noop():
    assert prepare({},'irrelevant')==([],set()) and emit([])==[]

@pytest.mark.parametrize('mode',['ok','count','footprint','offrow','overlap'])
def test_actual_tcl_atomic_preflight(tmp_path,mode):
    import shutil, subprocess
    from soft_cs_placement import TCL
    if not shutil.which('tclsh'): pytest.skip('tclsh unavailable')
    setup=r'''
set ff_dbu 1000;set ff_sw 10;set ff_x0 0;set ff_y0 0;set ff_x1 100000;set ff_y1 100000;set ff_rh 270
set ff_orient [dict create 0 R0];set ff_explicit_occ {};set is_n 0;set writes 0
set is_fh [open /dev/null w]
proc master {m args} {switch $m {getName {return DFF} getWidth {return 1000} getHeight {return 270} isBlock {return 0}}}
proc cell {name m args} {global writes;switch $m {getName {return $name} getMaster {return master} setLocation {incr writes} setPlacementStatus {} setOrient {}}}
interp alias {} c0 {} cell g_u_cst_ve_gd_s_0_u_q0
interp alias {} c1 {} cell g_u_cst_ve_gd_s_0_u_q1
proc block {m} {return {c0 c1}}
set ff_blk block
proc ff_hits_explicit {args} {return 0}
'''
    count=1 if mode=='count' else 2
    sites=['{0 0}','{2 0}'][:count]
    if mode=='offrow':sites[1]='{2 0.1}'
    if mode=='overlap':sites[1]='{0.5 0}'
    width=.5 if mode=='footprint' else 1
    call='is_soft_cs_banks {{bank {*g_u_cst_ve_gd_s_0_u_*} {'+' '.join(sites)+'} '+str(width)+' .27}}'
    script=tmp_path/'probe.tcl';script.write_text(setup+TCL+'\nset rc [catch {'+call+'} msg]\nputs "RESULT $rc $writes $is_n $msg"\n')
    run=subprocess.run(['tclsh',str(script)],text=True,capture_output=True,check=True)
    if mode=='ok':assert 'RESULT 0 2 2' in run.stdout
    else:assert 'RESULT 1 0 0' in run.stdout


def test_real_kit_entry_preserves_and_suppresses_centroid(tmp_path,monkeypatch):
    import json
    import kit_istations as KI
    # Native marker is an ordinary wire in real flattened leaf bodies.
    text=RTL.replace('endmodule','wire w_u_vp_g_ln_0_u_cst_hi_marker;\nendmodule')
    t=plan(); b=native_banks(text)[0]
    t['clock']['soft_reg_banks'][0]['source']='nativeRTL:'+hashlib.sha256(text.encode()).hexdigest()+'#'+b['id']
    t['internal_stations']=[dict(conn='core:u_lf.u_ve.u_m.a_val|core:u_lf.u_vs',launch='core:u_lf.u_ve.u_m.a_val',capture='u_lf.u_vs',bits=4,regs_um=[[10,10]])]
    p=tmp_path/'plan.json';p.write_text(json.dumps({'partition_types':{'test':t}}))
    bound=tmp_path/'bound.sv';bound.write_text(text)
    (tmp_path/'kit_rtl.json').write_text(json.dumps(dict(files=[str(bound)],bound_module='bound')))
    original=KI.core_pin_stations
    monkeypatch.setattr(KI,'core_pin_stations',lambda tn,t,txt,*a:txt+'\n// upstream harmless rewrite\n')
    KI.main([str(p),'test',str(tmp_path)])
    result=bound.read_text();tcl=(tmp_path/'istations.tcl').read_text()
    assert result.count('(* keep = 1 *)')==2
    assert 'is_soft_cs_banks {{' in tcl
    assert not any(line.startswith('is_place ') and 'cst:ve' in line for line in tcl.splitlines())
