"""Mechanism witnesses only; synthetic buses never qualify a native S81 die."""
import copy
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vm_relay_stages as V
DRS = V.DRS


def fixture():
    buses = []
    for i, stages in enumerate((2, 3, 5, 7, 11)):
        src = dict(inst=f't{i}', port='out')
        dst = dict(inst=f't{i+1}', port='in')
        buses.append(dict(id=DRS.bus_id(src['inst'], src['port'], dst['inst'], dst['port']),
                          src=src, dst=dst, width=64, stages=stages,
                          domain='stream_1p2', eq_age_group=None))
    plan = DRS.make_doc('s81', dict(id='mechanism-only', commit='synthetic-source'),
                        1e6/1200, 455, buses)
    ids = [b['id'] for b in buses]
    paths = dict(schema=V.SCHEMA, plan_digest=plan['digest'], plan=copy.deepcopy(plan['plan']),
                 legs=dict(write=[ids[:2], [ids[4]]], read_request=[[ids[2]]],
                           read_return=[[ids[3]]], commit=[[ids[4]]]))
    return plan, paths


class RelayPaths(unittest.TestCase):
    def test_consecutive_paths_and_worst_leg_not_average(self):
        plan, paths = fixture()
        cost, compiled = V.bind(plan, paths)
        self.assertEqual((cost['write'], cost['read'], cost['commit']), (11, 12, 11))
        self.assertEqual(cost['write_plus_read'], 23)
        self.assertEqual(compiled['digest'], plan['digest'])
        self.assertFalse(cost['native_qualified'])
        self.assertEqual(set(compiled['compiled']['used_by']), {b['id'] for b in plan['buses']})

    def test_selected_ledger_preserves_core_charge_and_tracks_table(self):
        import json
        import tempfile
        import mtp_ledger_1016 as ledger
        plan, paths = fixture()
        rows = [dict(design='s81', status=status, group=group,
                     per_workload={w: dict(e2e_loss_pct=value) for w in ('ar', 'mtp')})
                for status, group, value in (('accepted', 'VM.RELAY', 99),
                                            ('accepted', 'VM.READ', 7),
                                            ('proposed', 'VM.A2_COMMIT_REMAINDER', 2),
                                            ('proposed', 'VM.RELAY', 88))]
        price = {w: dict(upper_every_node=dict(e2e_loss_pct=3)) for w in ('ar', 'mtp')}
        with tempfile.TemporaryDirectory() as d:
            planfile, pathsfile = Path(d)/'plan.json', Path(d)/'paths.json'
            DRS.write(planfile, plan)
            pathsfile.write_text(json.dumps(paths))
            with patch.object(ledger.RP, 'price', return_value=price) as priced:
                report, compiled = ledger.selected_plan_summary(planfile, pathsfile, dict(rows=rows), 89)
            priced.assert_called_once_with(11, 12)
        rate = report['rates']['mtp']
        self.assertEqual(rate['ledger_unchanged']['accepted_loss_pct'], 106)
        self.assertEqual(rate['ledger_unchanged']['proposed_loss_pct'], 90)
        self.assertEqual(rate['baseline_without_vmrelay']['accepted_loss_pct'], 7)
        self.assertEqual(rate['baseline_without_vmrelay']['proposed_loss_pct'], 2)
        self.assertEqual(rate['candidate_composed_loss_pct'], 12)
        self.assertFalse(rate['selected_relay_candidate']['accepted'])
        self.assertEqual(compiled['compiled']['loaded_digest'], plan['digest'])
        self.assertFalse(report['native_qualified'])

    def test_explicit_zero_stage_is_preserved(self):
        plan, paths = fixture()
        bus = plan['buses'][4]
        bus['stages'] = 0
        plan['digest'] = DRS.digest(plan['buses'])
        paths['plan_digest'] = plan['digest']
        cost, compiled = V.bind(plan, paths)
        self.assertEqual(cost['commit'], 0)
        self.assertIn(bus['id'], compiled['compiled']['used_by'])

    def test_missing_bus_fails_including_missing_zero_stage(self):
        plan, paths = fixture()
        paths['legs']['commit'] = [['absent.out -> absent.in']]
        with self.assertRaises(DRS.MissingBus): V.bind(plan, paths)

    def test_stale_source_or_changed_stage_fails(self):
        plan, paths = fixture()
        for mutation in ('source', 'stage'):
            changed = copy.deepcopy(plan)
            if mutation == 'source': changed['plan']['commit'] = 'different'
            else:
                changed['buses'][0]['stages'] += 1
                changed['digest'] = DRS.digest(changed['buses'])
            with self.assertRaises(DRS.RelayStagesError): V.bind(changed, paths)

    def test_coverage_domain_disconnected_and_unpadded_reject(self):
        for mutation in ('coverage', 'domain', 'gap', 'padding', 'problems', 'missing_leg'):
            plan, paths = fixture()
            if mutation == 'coverage': plan['coverage'] = 'relayed_only'
            elif mutation == 'domain': plan['buses'][0]['domain'] = 'serial_0p9'
            elif mutation == 'gap': paths['legs']['write'] = [[plan['buses'][0]['id'], plan['buses'][2]['id']]]
            elif mutation == 'padding':
                for b in plan['buses'][:2]: b['eq_age_group'] = 'same-age'
            elif mutation == 'problems': plan['problem_count'] = 1
            else: del paths['legs']['read_return']
            plan['digest'] = DRS.digest(plan['buses'])
            paths['plan_digest'] = plan['digest']
            with self.assertRaises(DRS.RelayStagesError, msg=mutation): V.bind(plan, paths)


if __name__ == '__main__': unittest.main()
