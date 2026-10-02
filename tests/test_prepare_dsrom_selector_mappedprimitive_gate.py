import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import prepare_dsrom_selector_mappedprimitive_gate as P
import verify_dsrom_selector_mappedprimitive_completion as K
import preflight_dsrom_selector_mappedprimitive_gate as F


def good(mode=0,stop=None):
    e=P.expected();s={x['index']:x for x in e['steps']};a={x['index']:x for x in e['async_events']};lines=[]
    for key in e['marker_order'][:stop]:
        if key[0]=='S':
            x=s[int(key[1:])];lines.append(f"PRIMITIVE_STEP_PASS mode={mode} index={x['index']} payload={x['payload']} flag={x['flag']} reset={x['reset']}")
        else:
            x=a[int(key[1:])];lines.append(f"PRIMITIVE_ASYNC_PASS mode={mode} index={x['index']} reset={x['reset']}")
    return '\n'.join(lines)


def mutant(mode):
    m=P.expected()['mutants'][str(mode)]
    prefix=good(mode,m['prefix_steps']+m['prefix_async_events'])
    return prefix+'\n'+f"PRIMITIVE_DIFF mode={mode} kind={m['kind']} phase={m['phase']} index={m['index']} expected={m['expected']} actual={m['actual']}"


class PrimitiveGate(unittest.TestCase):
    def test_model_precedes_probe_and_is_not_engine_revision(self):
        m=json.loads((P.BASE/'component_model.json').read_text())
        self.assertFalse(m['compile_GO']);self.assertFalse(m['physical_admitted'])
        self.assertEqual(m['engine_state_or_stage_or_port_increment'],0)
        area=[.2916,.37908,2*.04374,6*.10206,2*.08748,.04374]
        self.assertAlmostEqual(sum(area),m['component_cell_area_um2'])
        self.assertEqual(m['full_gate_preservation']['fault_cases'],15)
        self.assertFalse(m['clock_root_contract']['fixture_clock_capture_credit'])
        self.assertAlmostEqual(m['clock_root_contract']['FF_clock_pin_sum_fF'],1.025162)

    def test_every_official_cell_byte_preserved_and_no_standin(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'package';P.prepare(out)
            for name in P.LIB_NAMES:self.assertEqual((out/'library'/name).read_bytes(),(P.LIB/name).read_bytes())
            for path,h in json.loads((out/'artifact_manifest.json').read_text()).items():self.assertEqual(P.sha((out/path).read_bytes()),h)
            plan=json.loads((out/'sourceplan.json').read_text())
            self.assertEqual(len(plan['source_inventory']),4)
            self.assertTrue(plan['official_library_sources_byte_identical'])
            self.assertFalse(plan['fullshape_selector_and_transport_qualification'])

    def test_source_exact_master_counts_and_output_polarity(self):
        source=(P.ROOT/P.TEMPLATE).read_text();m=json.loads((P.BASE/'component_model.json').read_text())
        for master,count in m['component_source_cells'].items():
            self.assertEqual(len(re.findall(r'\b'+master+r'\s+\w+\(',source)),count)
        self.assertIn('.A(pqn),.Y(payload)',source)
        self.assertIn('.RESETN(reset_to_cell),.SETN(setn),.QN(fqn)',source)
        self.assertNotIn('always',source) # cells supply all storage; no behavioral FF replacement.
        self.assertNotIn('$readmemh("assertions',source)
        self.assertNotIn('.D(want_',source)

    def test_settle_schedule_and_checks_no_reset_masked(self):
        source=(P.ROOT/P.TEMPLATE).read_text()
        self.assertIn('#1;sample("RISE",steps)',source)
        self.assertIn('#1;sample("FALL",steps)',source)
        self.assertIn('#1;events=events+1;sample("ASYNC",events)',source)
        self.assertIn('input logic actual',source)
        self.assertIn('actual!==wanted',source)
        self.assertIn('IMMUTABLE_PRIMITIVE_INPUT_IMAGE',source)
        self.assertIn('$finish;\n        #1;',source)
        self.assertEqual(1+415+1+415+1,833)

    def test_independent_expected_all_inputs_and_exact_counts(self):
        e=P.expected()
        self.assertEqual(len(e['steps']),33);self.assertEqual(len(e['async_events']),7)
        self.assertEqual(33*7+7*3,252)
        self.assertEqual(len(e['marker_order']),40)
        self.assertEqual(e['steps'][9],dict(index=9,payload=0,flag=0,reset=0))
        self.assertEqual(e['steps'][25],dict(index=25,payload=0,flag=0,reset=0))
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'package';P.prepare(out)
            self.assertEqual((out/'inputs.mem').read_text(),''.join(f'{i%4:08x}\n' for i in range(32)))

    def test_strict_normal_completion_and_order(self):
        log=good()+'\n'+K.FINAL
        self.assertEqual(K.verify(log,0)['assertions'],252)
        lines=log.splitlines()
        bad=[log+'\n'+K.FINAL,log.replace('steps=33','steps=32'),log.replace('payload=0','payload=1',1),
             '\n'.join(lines[1:]),'\n'.join([lines[1],lines[0]]+lines[2:]),
             log.replace('mode=0','mode=1',1),log+'\nPRIMITIVE_FOREIGN_PASS']
        for text in bad:
            with self.subTest(text=text[-100:]),self.assertRaises(ValueError):K.verify(text,0)

    def test_real_difference_and_independent_mutant_binding(self):
        for mode in (1,2,3):
            self.assertEqual(K.verify(mutant(mode),mode)['status'],'EXPECTED_PRIMITIVE_DIFF')
            for text in [mutant(mode).replace('expected=0','expected=1'),mutant(mode).replace('actual=1','actual=0'),
                         mutant(mode).replace('index='+str(P.expected()['mutants'][str(mode)]['index'])+' expected','index=99 expected'),
                         mutant(mode)+'\n'+mutant(mode).splitlines()[-1],
                         'PRIMITIVE_DIFF malformed\n'+mutant(mode),mutant(mode)+'\n'+K.FINAL,
                         mutant(mode).replace('mode='+str(mode),'mode=9')]:
                with self.subTest(mode=mode,text=text),self.assertRaises(ValueError):K.verify(text,mode)
            with self.assertRaises(ValueError):K.verify(mutant(mode),mode,returncode=1)

    def test_crash_and_absent_diff_never_success(self):
        for mode in (1,2,3):
            for text in ('%Error: crash',good(mode),'PRIMITIVE_MUTANT_NO_DIFFERENCE',''):
                with self.assertRaises(ValueError):K.verify(text,mode)

    def test_fresh_replay_exact_all_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a';b=Path(d)/'b';P.prepare(a);P.prepare(b)
            self.assertEqual((a/'artifact_manifest.json').read_bytes(),(b/'artifact_manifest.json').read_bytes())
            self.assertEqual((a/'artifact_manifest.json').read_bytes(),(P.BASE/'package/artifact_manifest.json').read_bytes())

    def test_preflight_package_mutations_refused(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a';P.prepare(a)
            self.assertEqual(F.verify_package(a),7)
            (a/'inputs.mem').write_text('00000000\n'*32)
            with self.assertRaises(ValueError):F.verify_package(a)

    def test_GO_template_is_component_only_and_not_permission(self):
        g=json.loads((P.BASE/'parent_GO_template.json').read_text())
        self.assertFalse(g['approved'])
        self.assertFalse(g['physical_or_integrated_admission'])
        self.assertIsNone(g['prepared_commit_fullSHA'])
        self.assertIsNone(g['fresh_host_headroom_and_resource_lease_receipt'])

    def test_future_compile_policy_no_pilot_caps_or_blanket_warning_ignore(self):
        p=json.loads((P.BASE/'compile_plan.json').read_text())
        self.assertEqual(p['FSIZE'],'infinity')
        self.assertIsNone(p['wall_or_CPU_time_cap'])
        self.assertIsNone(p['per_process_AS_cap'])
        self.assertIn('-Wno-SPECIFYIGN',p['compile_argv'])
        self.assertNotIn('-Wno-fatal',p['compile_argv'])
        self.assertFalse(p['fullshape_selector_gate_replaced'])


if __name__=='__main__':unittest.main()
