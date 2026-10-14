"""Physical failures and cancellations remain outstanding requirements."""
import collections
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from elements import Elements, LIVE, REDESIGN
from test_element_registry import Describer, Flow


def model():
    m=Elements.__new__(Elements);m.desc=Describer();m.area={};m.flow=Flow()
    return m


def job(status,name='trial'):
    return Elements.reduce(dict(name=name,status=status,spec=dict(block='parent'),metrics={}))


class StatusCoverageTests(unittest.TestCase):
    def test_actual_56_row_misclassification_snapshot(self):
        rows=json.loads((Path(__file__).parent/'fixtures/cancelled_label_audit_20261014.json').read_text())
        categories=collections.Counter()
        for r in rows:
            j=Elements.reduce(dict(name=r['latest_job'],status=r['actual_state'],commit_full=r['source_commit'],
                                  reason=r['actual_reason'],spec=dict(block=r['element']),metrics={}))
            category=model().element(r['element'],[j],{}, {})['category']
            categories[category]+=1
            self.assertEqual(category,'cancelled only' if r['actual_state']=='CANCELLED' else 'needs redesign (no live job)',r['element'])
        self.assertEqual(categories,{'cancelled only':19,'needs redesign (no live job)':37})

    def test_all_live_stage_states_and_physical_failures(self):
        for status in LIVE:
            with self.subTest(status=status):
                self.assertEqual(model().element('parent',[job(status)],{}, {})['category'],'first trial in flight')
                self.assertEqual(model().element('parent',[job('EARLY_FAIL_HOLD','old'),job(status)],{}, {})['category'],'failed, re-running')
        for status in REDESIGN:
            with self.subTest(status=status):
                self.assertEqual(model().element('parent',[job('CANCELLED','old'),job(status)],{}, {})['category'],'needs redesign (no live job)')

    def test_unknown_and_diagnostic_states_never_imply_cancellation_or_closure(self):
        for status in ('UNKNOWN_NEW_STATE','SMOKE_OK'):
            r=model().element('parent',[job('CANCELLED','old'),job(status)],{}, {})
            self.assertEqual(r['category'],'flow failure (no live job)')
            self.assertIn(status,r['via'])
        self.assertEqual(model().element('parent',[],{}, {})['category'],'flow failure (no live job)')
        self.assertEqual(model().element('parent',[job('CANCELLED')],{}, {})['category'],'cancelled only')

    def test_cancelled_successor_audit_covers_every_original_requirement(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/cancelled_label_audit_20261014.json').read_text())
        audit=json.loads((Path(__file__).resolve().parents[2]/'results/fleet_viz/cancelled_requirements_20261014.json').read_text())
        expected={r['element']:r['source_commit'] for r in fixture if r['actual_state']=='CANCELLED'}
        self.assertEqual(len(audit['rows']),19)
        self.assertEqual({r['element']:r['source_commit'] for r in audit['rows']},expected)
        for row in audit['rows']:
            self.assertEqual(row['requirement_status'],'OPEN')
            self.assertFalse(row['retired'])
            self.assertFalse(row['parent_qualified'])
            self.assertTrue(row['missing'])
            self.assertTrue(row['evidence'])
        self.assertEqual(set(audit['missing_successor']),{r['element'] for r in audit['rows'] if not r['successors']})

    def test_frontend_totals_include_cancelled_requirements(self):
        node=shutil.which('node')
        self.assertIsNotNone(node,'frontend count regression requires node')
        source=(Path(__file__).parent/'index.html').read_text()
        # Execute the shipped share-safe summary render, stopping before detail DOM work.
        start=source.index('const NOCOUNT =');end=source.index('  const rowsOK =',start)
        script="""let out={}; const SAFE=true;
const ED={cats:['needs redesign (no live job)','cancelled only','superseded'],targets:['Qwen ROM'],t:0,
summary:{'Qwen ROM':{'needs redesign (no live job)':37,'cancelled only':19,'superseded':1}}};
const EF={}; const ECOL={}; const $=()=>({hidden:false}); const lsw=()=>{};
const setHTML=(el,s)=>{}; const setText=(el,s)=>out.text=s; const esc=x=>x; const ago=x=>'now';
"""+source[start:end]+"}\nrenderElements(); console.log(JSON.stringify(out));"
        result=subprocess.run([node,'-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['text'],'0 of 56 closed · 56 open (not counted: 1 superseded) · as of now')

if __name__=='__main__':unittest.main()
