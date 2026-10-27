import hashlib
import json
from pathlib import Path
from test_autopilot import Base, ROW, so
from test_signoff_chain import ChainTest


class TestCollect(Base):
    def row(self, runner='/srv/opentallas-scratch2/claude/collector.sh', netlist=''):
        return ROW + ['collect', runner, '8', 'submit', '', '', netlist]

    def test_collect_requires_explicit_collector_and_keeps_goal(self):
        for runner in ['', '/srv/opentallas-scratch2/claude/run_kit.sh']:
            (r,) = self.ap.parse_queue('\t'.join(self.row(runner))).values()
            self.assertIn('explicit collector', r['error'])
        (r,) = self.ap.parse_queue('\t'.join(self.row())).values()
        self.assertEqual(r['error'], '')
        self.assertEqual(self.ap.runner_goal('collect', {'signoff_goals': ['route', 'finish']}), 'collect')

    def test_only_collect_admits_completed_route_and_retains_failure_marks(self):
        p = dict(exists=True, config=True, routed=['6_final.odb'], signoff_dirs=['signoff_failed'],
                 fail_marks=[], runner='/collector.sh')
        self.assertEqual(self.ap.kit_admission_error({'goal': 'collect', 'runner': '/collector.sh'}, p), '')
        self.assertIn('already routed', self.ap.kit_admission_error({'goal': 'finish'}, p))
        self.assertIn('earlier run', self.ap.kit_admission_error({'goal': 'collect', 'runner': '/collector.sh'}, dict(p, fail_marks=['FAIL_POSTCTS'])))
        self.assertIn('existing routed', self.ap.kit_admission_error({'goal': 'collect', 'runner': '/collector.sh'}, dict(p, routed=[])))

    def test_collect_uses_normal_chain_with_explicit_logical_export(self):
        (r,) = self.ap.parse_queue('\t'.join(self.row(netlist='6_final_logic.v'))).values()
        self.assertEqual(r['error'], '')
        calls=[]
        self.ap.launch_unit=lambda u,l,a: calls.append(a) or True
        self.ap.submit({}, r)
        self.assertTrue(r['chain_required'])
        args=calls[0]
        self.assertEqual(args[args.index('--netlist') + 1], '6_final_logic.v')
        self.assertIn('collect', args)
        self.assertEqual(self.ap.classify(so(verdict='SIGNED', ff=1, fails=()), {'exit': 0})[0], 'SIGNED')
        for view in ['../other.v', '/other.v', 'other.json']:
            (r,) = self.ap.parse_queue('\t'.join(self.row(netlist=view))).values()
            self.assertIn('routed_netlist', r['error'])


class TestCollectChain(ChainTest):
    def test_collect_proves_explicit_export_and_preserves_prior_failure(self):
        k,b=self.vehicle()
        (b/'6_final_logic.v').write_text('logical export')
        export = dict(odb_sha256=hashlib.sha256((b/'6_final.odb').read_bytes()).hexdigest(),
                      netlist_sha256=hashlib.sha256((b/'6_final_logic.v').read_bytes()).hexdigest(),
                      command='write_verilog -remove_cells TAPCELL_ASAP7_75t_R 6_final_logic.v',
                      excluded_masters=['TAPCELL_ASAP7_75t_R'], excluded_signal_iterms=0)
        (b/'6_final_logic.v.export.json').write_text(json.dumps(export))
        old=k/'signoff_failed/signoff.json';old.parent.mkdir();old.write_text('{"verdict":"NOT SIGNED"}')
        run,calls=self.runner(k,b)
        self.assertEqual(__import__('signoff_chain').continue_kit(k, 'collector.sh', 'collect', 48, 8, run,
                                                                netlist='6_final_logic.v'), 0)
        self.assertEqual(calls[0][1], 'collector.sh')
        self.assertEqual(calls[0][3], 'collect')
        self.assertEqual(calls[-1][calls[-1].index('--netlist')+1], str(b/'6_final_logic.v'))
        self.assertEqual(old.read_text(), '{"verdict":"NOT SIGNED"}')
        self.assertTrue((b/'6_final.v').exists())

    def test_arbitrary_or_changed_export_cannot_substitute_for_routed_proof(self):
        k,b=self.vehicle()
        (b/'6_final_logic.v').write_text('arbitrary RTL')
        run,calls=self.runner(k,b)
        self.assertEqual(__import__('signoff_chain').continue_kit(k, 'collector.sh', 'collect', 48, 8, run,
                                                                netlist='6_final_logic.v'), 3)
        self.assertFalse(any('--netlist' in c for c in calls))

    def test_changed_route_export_or_signal_exclusion_cannot_pass(self):
        for mutant in ['odb_sha256', 'netlist_sha256', 'excluded_signal_iterms', 'command']:
            k,b=self.vehicle()
            v=b/'6_final_logic.v';v.write_text('export')
            export = dict(odb_sha256=hashlib.sha256((b/'6_final.odb').read_bytes()).hexdigest(),
                          netlist_sha256=hashlib.sha256(v.read_bytes()).hexdigest(),
                          command='write_verilog -remove_cells TAPCELL 6_final_logic.v',
                          excluded_masters=['TAPCELL'], excluded_signal_iterms=0)
            export[mutant] = 1 if mutant == 'excluded_signal_iterms' else 'changed'
            v.with_suffix('.v.export.json').write_text(json.dumps(export))
            run,calls=self.runner(k,b)
            self.assertEqual(__import__('signoff_chain').continue_kit(k, 'collector.sh', 'collect', 48, 8, run,
                                                                    netlist=v.name), 3)
            self.assertFalse(any('--netlist' in c for c in calls))
