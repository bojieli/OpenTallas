import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_current_reset_construction as P
import uarch_model_qwen_current_reset as U


def test_selected_live_source_not_obsolete_draft():
    m=U.qwen_rom_current_reset_price()
    assert m['unified_model_join']['baseline_import']=='uarch_model'
    assert m['live_source']['commit']=='752fffd8a7dd31742f383ca59b89598db51d7222'
    assert m['live_model']['corridor']['width_um']==96.768
    assert m['live_model']['corridor']['remaining_tracks']==184
    assert m['finite_construction']['final_cell_ceiling_um2']==125000
    assert m['source_inventory']['clock_bits']==109984
    assert m['source_inventory']['reset_bits']==58160
    assert m['source_inventory']['mapped_counts'] is None
    assert m['live_map']['additional_maps_launched']==0
    assert m['admission']['contextual_SSFF'] is False
    assert m['admission']['cold_KV_calendar_is_production'] is False


def test_characterized_root_has_finite_wire_load_and_no_timing_credit():
    m=P.price()
    assert m['provider']['root_nominal_area_um2']==pytest.approx(1.25388)
    assert m['provider']['launch_join_area_um2']==pytest.approx(.08748)
    assert m['provider']['external_reset_deassert_minmax_ps']==[100,780]
    assert m['provider']['external_reset_low_pulse_min_ps']==330
    assert m['launch_constraints']['setup_uncertainty_ps']==60
    assert m['launch_constraints']['hold_uncertainty_ps']==25
    assert m['launch_constraints']['steady_added_cycles']==0
    assert m['nominal_RC']['signal_cap_fF_per_um']>0
    assert m['nominal_RC']['signal_resistance_ohm_per_um']>0
    for corner in ('ss','ff'):
        t=m['provider_LUT_envelopes'][corner]
        assert 0<t['release_before_distribution_minmax_ps'][0]<t['release_before_distribution_minmax_ps'][1]
        assert t['pad_slew_minmax_ps'][1]<=80
        assert t['last_pad_slew_minmax_ps'][1]<=80


@pytest.mark.parametrize('slew,cap',[(0,4),(81,4),(5,1),(5,9)])
def test_no_table_extrapolation(slew,cap):
    with pytest.raises(ValueError,match='extrapolation'):
        P.interpolate(([5,80],[2,8],[[1,2],[3,4]]),slew,cap)


def test_interpolation_and_finite_integer_tree():
    assert P.interpolate(([5,80],[2,8],[[1,2],[3,4]]),42.5,5)==pytest.approx(2.5)
    assert P.tree_count(58070)['levels_leaf_to_root']==[7259,908,114,15,2,1]
    assert P.tree_count(51824)['buffers']==7406


def fixture():
    cells={};bit=10
    def add(name,kind,con):cells[name]=dict(type=kind,connections=con)
    for i in range(16):
        add('reset'+str(i),P.ASR,dict(CLK=[2],RESETN=[3],SETN=['1'],D=['0'],QN=[bit]));bit+=1
        add('plain'+str(i),'DFFHQNx1_ASAP7_75t_R',dict(CLK=[2],D=['0'],QN=[bit]));bit+=1
    for i in range(90):
        add('meta'+str(i),P.ASR,dict(CLK=[2],RESETN=[500],SETN=['1'],D=['0'],QN=[bit]));bit+=1
    add('old_meta_root',P.BUF,dict(A=[3],Y=[500]))
    for i in range(12):add('macro'+str(i),'ot_rom_4096x266_m8' if i<10 else 'ot_sram_1r1w_128x256_m1_r2c2',dict(clk=[2]))
    return dict(cells=cells,ports=dict(clk_stream=dict(direction='input',bits=[2]),reset_stream_n=dict(direction='input',bits=[3]),ib_go=dict(direction='input',bits=[4])),netnames={})


def test_construct_copies_map_and_prices_finite_buffers_and_wires(tmp_path):
    net=fixture();before=copy.deepcopy(net)
    r=P.construct(net)
    assert net==before
    assert r['actual_reset_FF']==16 and r['metadata_FF']==90
    assert r['macro_CLK_sinks']==12
    assert r['nominal_wire_cap_fF']>0
    assert r['nominal_wire_elmore_bound_ps']>0
    assert r['max_branch_load_fF']<=46.08
    assert r['max_branch_slew_ps']<=320
    assert r['physical_admission'] is False
    assert r['startup_two_edges_is_conditional_on_complete_distribution_timing'] is True
    assert r['net']['cells']['old_meta_root']['type']==P.BUF
    P.write_verilog(r,tmp_path/'context.v')
    assert 'ot_qwen_rom_reset_parent_provider #(.RESET_CONTEXT(1))' in (tmp_path/'context.v').read_text()


def test_setn_load_is_not_silently_discarded():
    net=fixture();net['cells']['reset0']['connections']['RESETN']=['1'];net['cells']['reset0']['connections']['SETN']=[3]
    r=P.construct(net)
    assert r['actual_reset_pin_classes']=={'RESETN':15,'SETN':1}


def test_missing_metadata_rejects_graph_without_altering_input():
    net=fixture();del net['cells']['meta0'];before=copy.deepcopy(net)
    with pytest.raises(ValueError,match='binding failed'):P.construct(net)
    assert net==before


def test_failed_terminal_cannot_construct_or_restart_map(tmp_path):
    work=tmp_path/'work';work.mkdir()
    (work/'terminal.json').write_text(json.dumps(dict(status='FAIL_SOURCE_MAP_RETAINED')))
    run=subprocess.run([sys.executable,str(P.ROOT/'tools/qwen_rom_current_reset_construction.py'),'--out',str(tmp_path/'out'),'--construct-existing-map',str(work)],capture_output=True,text=True)
    assert run.returncode!=0 and 'single map not complete/PASS' in run.stderr
    assert not (tmp_path/'out'/'constructed-context-r1.v').exists()


def test_provider_literal_protocol_defaultoff_and_owned_ready(tmp_path):
    if not shutil.which('iverilog'):pytest.skip('iverilog unavailable')
    cells='''module DFFASRHQNx1_ASAP7_75t_R(input CLK,RESETN,SETN,D,output wire QN);
reg q; assign QN=~q; always @(posedge CLK or negedge RESETN or negedge SETN) if(!RESETN) q<=0; else if(!SETN) q<=1; else q<=D; endmodule
module INVx1_ASAP7_75t_R(input A,output Y);assign Y=~A;endmodule
module BUFx4_ASAP7_75t_R(input A,output Y);assign Y=A;endmodule
module AND3x1_ASAP7_75t_R(input A,B,C,output Y);assign Y=A&B&C;endmodule
module tb;
reg clk=0,rst=1,ready=0,go=0; wire release_n,launch,bypass_n,bypass_go;
ot_qwen_rom_reset_parent_provider #(.RESET_CONTEXT(1)) dut(clk,rst,ready,go,release_n,launch);
ot_qwen_rom_reset_parent_provider baseline(clk,rst,ready,go,bypass_n,bypass_go);
always #5 clk=~clk;
integer accept=0; always @(posedge clk) if(launch) accept<=accept+1;
initial begin
#1 rst=0;go=1; #1;
if(release_n!==0 || launch!==0 || bypass_n!==0 || bypass_go!==1) $fatal;
#5 rst=1; // deassert between edges, after first clock while reset held
@(posedge clk); #1; if(release_n!==0 || launch!==0) $fatal;
@(posedge clk); #1; if(release_n!==1 || launch!==0 || accept!==0) $fatal;
ready=1; @(posedge clk); #1; if(accept!==1) $fatal;
ready=0; #1; if(launch!==0) $fatal;
rst=0; #1; if(release_n!==0) $fatal;
go=0;rst=1;
@(posedge clk); @(posedge clk); #1;ready=1;
@(posedge clk); #1; if(accept!==1 || launch!==0) $fatal; // no queue/replay of previous start
$display("PASS_LITERAL_PROVIDER_ONLY");$finish;
end endmodule
'''
    (tmp_path/'tb.v').write_text(cells)
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(tmp_path/'sim'),str(tmp_path/'tb.v'),str(P.ROOT/P.PROVIDER)],check=True,capture_output=True)
    result=subprocess.run(['vvp',str(tmp_path/'sim')],check=True,capture_output=True,text=True)
    assert 'PASS_LITERAL_PROVIDER_ONLY' in result.stdout


def test_published_assessment_is_failed_and_hashes_byte_exact():
    path=P.ROOT/P.OUT/'single-map-assessment-r1.json'
    if not path.exists():pytest.skip('assessment not generated yet')
    a=json.loads(path.read_text())
    assert a['original_terminal']['status']=='FAIL_SOURCE_MAP_RETAINED'
    assert a['scopeinfo_metadata_cells']>0
    assert a['endpoint_survival']['ROM_capture']['status']=='FAIL_RETAINED'
    assert a['endpoint_survival']['address_producer']['status']=='FAIL_RETAINED'
    assert a['macro_counts']=={'ot_rom_4096x266_m8':10,'ot_sram_1r1w_128x256_m1_r2c2':2}
    assert a['source_distribution_buffers']==76
    assert a['actual_mapped_FF_counts']['distributed_metadata_reset_FF']!=90
    assert not a['physical_admission'] and a['additional_maps_launched']==0
    for filename,row in a['original_files'].items():
        path=P.LIVE/filename
        if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']


def test_current_mapped_pin_census_hash_and_sum():
    path=P.ROOT/P.OUT/'mapped-loads-r1.json'
    assert path.exists()
    import gzip
    receipt=json.loads(path.read_text())
    raw=(P.ROOT/P.OUT/'mapped-sink-census-r1.json.gz').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==receipt['census_sha256']
    rows=json.loads(gzip.decompress(raw))
    assert len(rows)==receipt['census_records']
    assert receipt['groups']['logic_clock']['pins']==102287
    assert receipt['groups']['ROM_clock']['pins']==10
    assert receipt['groups']['KV_clock']['pins']==2
    for group,total in receipt['groups'].items():
        selected=[r for r in rows if r['group']==group]
        assert len(selected)==total['pins']
        for c in ('ss','ff'):
            assert sum(r['nominal_pin_cap_fF'][c] for r in selected)==pytest.approx(total[c+'_cap_fF'])
    assert receipt['mapped_survival_qualified'] is False


def test_all_source_and_artifact_pins_match_current_checkout():
    receipt=P.ROOT/P.OUT
    for path,digest in json.loads((receipt/'sourcepins-r1.json').read_text())['sha256'].items():
        assert hashlib.sha256((P.ROOT/path).read_bytes()).hexdigest()==digest,path
    for name,digest in json.loads((receipt/'artifact-sha256-r1.json').read_text()).items():
        assert hashlib.sha256((receipt/name).read_bytes()).hexdigest()==digest,name


def test_latest_graph_corrects_named_wire_inference_and_prices_missing_replicas():
    g=P.reconcile_graph()
    assert g['actual_ROM_capture_FFs']==2560 and g['actual_early_select_FFs']==5
    assert g['mask_FFs']=={'required':80,'actual':30,'missing':50}
    assert g['bank_strobe_FFs']=={'required':5,'actual':2,'missing':3}
    fix=g['minimum_replica_preservation']
    assert fix['additional_ASR_FFs']==53
    assert fix['nominal_cell_area_um2']==pytest.approx(20.09124)
    assert fix['metadata_reset_FFs']==90
    assert fix['repaired_clock_FFs']==102340
    assert fix['RTL_or_mapped_replica_restoration_performed'] is False
    assert g['admission']['second_map'] is False
    for c in ('ss','ff'):
        caps=P.library(c)[2]
        assert fix['added_pin_load_fF'][c]['CLK']==pytest.approx(53*caps[(P.ASR,'CLK')]['cap_fF'])


def test_launch_is_one_real_mapped_D_sink_with_priced_join_wire():
    p=P.price()
    assert p['provider']['actual_ib_go_first_mapped_sink']['pin']=='D'
    assert p['provider']['actual_ib_go_first_mapped_sink']['cell']==P.ASR
    for c,t in p['provider_LUT_envelopes'].items():
        assert t['launch_driver_wire32um_cap_fF']>P.library(c)[2][(P.ASR,'D')]['cap_fF']
        assert t['launch_join_rise_minmax_ps'][0]>0
        assert t['launch_join_slew_minmax_ps'][1]<=80
    assert p['admission']['contextual_SSFF'] is False


def test_actual_allocation_covers_every_mapped_clock_sink_with_finite_routes():
    import gzip
    receipt=P.ROOT/P.OUT
    r=json.loads((receipt/'asbuilt-finite-allocation-receipt-r1.json').read_text())
    raw=(receipt/'asbuilt-finite-allocation-r1.json.gz').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==r['allocation_sha256']
    graph=json.loads(gzip.decompress(raw))
    assert sum(c['type']==P.BUF for c in graph['added_primitive_cells'].values())==r['added_buffers']
    sinks=json.loads(gzip.decompress((receipt/'mapped-sink-census-r1.json.gz').read_bytes()))
    clocks=[s for s in sinks if s['group'] in ('logic_clock','ROM_clock','KV_clock')]
    assert len(clocks)==102287+10+2
    for sink in clocks:
        assert sink['pin'] in graph['original_cell_pin_edits'][sink['instance']]
    for pins in graph['original_cell_pin_edits'].values():
        assert set(pins)<= {'CLK','clk','RESETN','SETN','A','D'}
    assert len(graph['wire_edges'])==r['wire_edges']
    assert all(0<e['length_um']<=128 for e in graph['wire_edges'])
    assert r['nominal_wire_cap_fF']>0 and r['nominal_wire_elmore_bound_ps']>0
    assert r['max_branch_load_fF']<=46.08
    assert r['max_branch_slew_ps']<=320
    for counts in r['unique_new_branch_nets_crossing_vertical_cuts'].values():
        assert counts.get('clock',0)<=64 and counts.get('reset',0)<=64
    assert r['nominal_area_after_preservation53_um2']<125000
    assert r['final_area_includes_preservation_distribution'] is False
    assert r['current_PDN_cut_capacity_measured'] is False
    assert r['physical_admission'] is False and r['new_RTL_or_map_run'] is False
