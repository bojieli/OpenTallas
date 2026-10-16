"""Exact primitive admission and actual Yosys/OpenSTA graph mutants.

The small generic Liberty is a deliberate timing-graph fixture, never physical
or metastability sign-off. No production clock or timing library is changed.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import async_gray_fifo_constraints as A
import clock_entry_constraints as C

ROOT = Path(__file__).resolve().parents[2]
YOSYS = os.environ.get('YOSYS', str(Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'))
STA = os.environ.get('OPENSTA', str(Path.home()/'.local/opentallas-tools/opensta-be771a0/bin/sta'))


def spec():
    return dict(clock='multiple_cts_roots', kind='tile', top='ot_hbm_svc_async_fifo',
                clock_port='rd_clk', clock_ports=['rd_clk','wr_clk'], sources=list(A.SOURCES),
                params=dict(WIDTH=2,DEPTH=4), clock_data_paths='async_gray_fifo',
                clock_relationship=copy.deepcopy(A.RELATIONSHIP),
                clock_entry_domains=dict(
                    core=dict(ratio=[1,1], ports=['rd_clk'], inputs=['rd_rst_n','rd_ready'],
                              outputs=['rd_valid','rd_data','rd_underflow']),
                    hbm=dict(ratio=[3072000,2499999], ports=['wr_clk'], inputs=['wr_rst_n','wr_valid','wr_data'],
                             outputs=['wr_ready','wr_overflow'])))


class Admission(unittest.TestCase):
    def test_exact_source_native_policy(self):
        s=spec(); record=A.load(s,ROOT)
        self.assertEqual(record['depth'],4)
        text=C.generate(s,ROOT)
        self.assertIn('ot_ag_crossing $start $pin',text)
        self.assertIn('ot_ag_payload $start',text)
        self.assertIn('set_max_delay -ignore_clock_latency 773.333',text)
        self.assertIn('set_min_delay -ignore_clock_latency 0.0',text)
        self.assertIn('missing finite bounded',text)
        self.assertIn('OT_MULTI_ROOT OWNERSHIP PASS',text)
        self.assertNotIn('set_false_path',text)
        self.assertNotIn('set_clock_groups',text)
        self.assertIn('ot_io_hbm -period 1024.000000000',C.clocks(s,833.333))

    def test_unsupported_parents_parameters_roots_and_ownership_refused(self):
        for mutate in (
            lambda s:s.update(top='ot_hbm_svc_vm_kshare'),
            lambda s:s['params'].update(DEPTH=16),
            lambda s:s['params'].update(DEPTH=True),
            lambda s:s['params'].update(WIDTH=0),
            lambda s:s['params'].update(MUT=0),
            lambda s:s['clock_relationship'].update(hbm_period_ps=1000),
            lambda s:s['clock_entry_domains']['hbm'].update(ratio=[1,1]),
            lambda s:s['clock_entry_domains']['hbm']['inputs'].remove('wr_valid'),
            lambda s:s['clock_ports'].reverse(),
            lambda s:s.update(clock='hybrid_entries'),
            lambda s:s['sources'].append('rogue.sv'),
        ):
            s=spec();mutate(s)
            with self.subTest(spec=s),self.assertRaises(ValueError): C.generate(s,ROOT)

    def test_binary_pointer_and_one_stage_source_mutants_refused(self):
        path=next(iter(A.SOURCES))
        for old,new in [('wr_gray<=(wr_next>>1)^wr_next','wr_gray<=wr_next'),
                        ('rd_gray_w2<=rd_gray_w1','rd_gray_w2<=rd_gray')]:
            with tempfile.TemporaryDirectory()as tmp:
                root=Path(tmp)
                for f in A.SOURCES:
                    out=root/f;out.parent.mkdir(parents=True,exist_ok=True)
                    out.write_text((ROOT/f).read_text().replace(old,new))
                self.assertNotEqual((root/path).read_bytes(),(ROOT/path).read_bytes())
                with self.assertRaisesRegex(ValueError,'reviewed source changed'):C.generate(spec(),root)


def fixture_lib(module):
    funcs={'$_AND_':'A & B','$_OR_':'A | B','$_XOR_':'A ^ B','$_NOT_':'!A','$_MUX_':'(A & !S) | (B & S)'}
    rows=['library(probe) { delay_model : table_lookup; time_unit : "1ps"; capacitive_load_unit(1,ff); nom_voltage : 0.7; nom_temperature : 25; nom_process : 1;']
    seen=set()
    for c in module['cells'].values():
        typ=c['type']
        if typ in seen or typ=='$scopeinfo':continue
        seen.add(typ); ff=typ.startswith('$_DFF')
        rows += [f'cell("{typ}") {{area : 1;']
        if ff:
            assert typ in ('$_DFF_P_','$_DFF_PN0_'),typ
            rows += ['ff(IQ,IQN){clocked_on : "C";next_state : "D";'+('clear : "!R";'if typ=='$_DFF_PN0_'else'')+'}']
        for p,d in c['port_directions'].items():
            rows += [f'pin({p}){{direction : {d};']
            if d=='input':
                rows += ['capacitance : 1;']
                if p=='C':rows += ['clock : true;']
                if ff and p in ('D','R'):
                    for kind,val in ([('setup_rising',2),('hold_rising',1)]if p=='D'else[('recovery_rising',2),('removal_rising',1)]):
                        rows += ['timing(){related_pin : "C";timing_type : '+kind+';rise_constraint(scalar){values("'+str(val)+'");}fall_constraint(scalar){values("'+str(val)+'");}}']
            else:
                rows += ['function : "'+('IQ'if ff else funcs[typ])+'";']
                if typ=='$_DFF_PN0_':
                    rows += ['timing(){related_pin : "R";timing_type : clear;timing_sense : positive_unate;cell_rise(scalar){values("3");}cell_fall(scalar){values("3");}rise_transition(scalar){values("1");}fall_transition(scalar){values("1");}}']
                for inp in (['C']if ff else[k for k,v in c['port_directions'].items()if v=='input']):
                    rows += ['timing(){related_pin : "'+inp+'";'+('timing_type : rising_edge;timing_sense : positive_unate;'if ff else'timing_sense : non_unate;')+'cell_rise(scalar){values("3");}cell_fall(scalar){values("3");}rise_transition(scalar){values("1");}fall_transition(scalar){values("1");}}']
            rows += ['}']
        rows += ['}']
    return '\n'.join(rows+['}'])


def graph_probe(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    synth='read_verilog -sv -DSYNTHESIS '+ ' '.join(str(ROOT/f)for f in A.SOURCES)
    synth+='; hierarchy -top ot_hbm_svc_async_fifo -chparam WIDTH 2 -chparam DEPTH 4; synth -top ot_hbm_svc_async_fifo -flatten -noabc; dffunmap; abc -g simple; clean; write_json '+str(out/'fifo.json')
    p=subprocess.run([YOSYS,'-Q','-T','-p',synth],text=True,capture_output=True)
    (out/'synth.log').write_text(p.stdout+p.stderr)
    if p.returncode:raise AssertionError(p.stdout+p.stderr)
    original=json.loads((out/'fifo.json').read_text());module=original['modules']['ot_hbm_svc_async_fifo']
    (out/'probe.lib').write_text(fixture_lib(module))
    cases=[]
    for name in ('normal','bypass_second_stage','binary_pointer','payload_into_pointer','wrong_input_domain','missing_root'):
        data=copy.deepcopy(original);m=data['modules']['ot_hbm_svc_async_fifo']
        def drive(qname, qi, dname, di):
            qb=m['netnames'][qname]['bits'][qi]; db=m['netnames'][dname]['bits'][di]
            targets=[c for c in m['cells'].values()if c['type'].startswith('$_DFF')and c['connections']['Q']==[qb]]
            assert len(targets)==1,targets
            targets[0]['connections']['D']=[db]
        if name=='bypass_second_stage':drive('wr_gray_r2',0,'wr_gray',0)
        if name=='binary_pointer':drive('wr_gray_r1',0,'wr_bin',1)
        if name=='payload_into_pointer':drive('rd_bin',0,'mem[0]',0)
        jp=out/(name+'.json');vp=out/(name+'.v');jp.write_text(json.dumps(data))
        p=subprocess.run([YOSYS,'-Q','-T','-p',f'read_json {jp}; write_verilog -noattr -noexpr {vp}'],capture_output=True,text=True)
        if p.returncode:raise AssertionError(p.stdout+p.stderr)
        generated=C.generate(spec(),ROOT).rsplit('\not_ce_apply\n',1)[0]
        body=f'read_liberty {{{out}/probe.lib}}\nread_verilog {{{vp}}}\nlink_design ot_hbm_svc_async_fifo\n'+C.clocks(spec(),833.333)+generated
        body+='\nset ins [dict create rd_rst_n core rd_ready core wr_rst_n hbm wr_valid '+('core'if name=='wrong_input_domain'else'hbm')+' {wr_data[0]} hbm {wr_data[1]} hbm]\n'
        body+='set outs [dict create rd_valid core rd_underflow core {rd_data[0]} core {rd_data[1]} core wr_ready hbm wr_overflow hbm]\n'
        if name=='missing_root':body+='delete_clock [get_clocks ot_entry_1]\n'
        body+='if {[catch {ot_ce_leaf_ownership $ins $outs} message]} {puts stderr $message;exit 1}\nputs ACTUAL_FIFO_GRAPH_PASS\nexit 0\n'
        tp=out/(name+'.tcl');tp.write_text(body)
        p=subprocess.run([STA,'-exit',str(tp)],text=True,capture_output=True)
        log=p.stdout+p.stderr;(out/(name+'.log')).write_text(log)
        if name=='normal':
            if p.returncode or 'ACTUAL_FIFO_GRAPH_PASS'not in log:raise AssertionError(log)
            if 'async_control_pins=34'not in log:raise AssertionError('actual async reset controls lost: '+log)
        else:
            if not p.returncode or 'ACTUAL_FIFO_GRAPH_PASS'in log:raise AssertionError('bad crossing admitted: '+log)
            if 'OT_ASYNC_GRAY:'not in log and 'OT_MULTI_ROOT:'not in log:raise AssertionError('unexpected mutant failure: '+log)
        cases.append(dict(case=name,exit=p.returncode,tail=log.splitlines()[-2:]))
    receipt=dict(scope='actual synthesized WIDTH2 DEPTH4 primitive graph with generic fixture Liberty; no physical/native parent qualification',source=A.load(spec(),ROOT),cases=cases)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


@unittest.skipUnless(Path(YOSYS).exists()and Path(STA).exists(),'Yosys0.68 and OpenSTA fixture tools required')
class ActualGraph(unittest.TestCase):
    def test_actual_primitive_and_five_structural_mutants(self):
        with tempfile.TemporaryDirectory()as tmp:
            result=graph_probe(tmp)
            self.assertEqual(len(result['cases']),6)


if __name__=='__main__':
    import sys
    if len(sys.argv)==3 and sys.argv[1]=='--probe':print(json.dumps(graph_probe(sys.argv[2]),indent=2))
    else:unittest.main()
