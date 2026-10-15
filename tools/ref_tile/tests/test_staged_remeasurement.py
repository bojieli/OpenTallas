import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import source_binding as SB

class StagedRemeasurement(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.run=Path(self.tmp.name)/'run';(self.run/'src').mkdir(parents=True)
        source=b'module actual; endmodule\n';(self.run/'src/actual.v').write_bytes(source)
        entries=[dict(path='actual.v',sha256=hashlib.sha256(source).hexdigest(),source='worktree',kind='file',git_blob='blob')]
        self.script=self.run.parent/'original.sh'
        self.script.write_text('C=$R/routes/gate/work/orfs; B=$(ls -d $C/results/asap7/*/base | head -1)\n[ $FRC -eq 0 ] || exit 0\nif true; then\n  make DESIGN_CONFIG=x cts" > $R/cts.log\nfi\necho GATE_DONE\n')
        self.b=dict(schema=SB.SCHEMA,files=entries,manifest_sha256=SB.canonical_digest(entries),commit=None,
                    remote_script_sha256=hashlib.sha256(self.script.read_bytes()).hexdigest(),archive_sha256='archive')
        (self.run/'src/SOURCE_COMMIT').write_text('snapshot-sha256:'+self.b['manifest_sha256'])
        base=self.run/'routes/gate/work/orfs/results/asap7/actual/base';base.mkdir(parents=True)
        for n in ['1_2_yosys.v','3_2_place_iop.odb','4_1_cts.odb','4_cts.sdc']:(base/n).write_text('actual '+n)
        (self.run/'routes/gate/work/orfs/config.mk').write_text('actual physical config')
        canonical=SB.staged_measurement_script(self.script.read_text(),self.run).encode()
        (self.run/'staged_remeasurement.sh').write_bytes(canonical)
        self.log=('GATE_TOOL_IMAGE_ID=sha256:'+'a'*64+' GATE_TOOL_IMAGE_DIGESTS=[]\nRECOVERY_STAGED_REMEASUREMENT\nGATE_DONE\n').encode();(self.run/'staged_remeasurement.log').write_bytes(self.log)
        self.receipt=dict(schema='opentallas.ref_tile.staged_remeasurement.v1',original_archive_stdout='unavailable',tool_image_identity='sha256:'+'a'*64,
            original_script_sha256=self.b['remote_script_sha256'],manifest_sha256=self.b['manifest_sha256'],
            artifacts_sha256=SB.staged_measurement_artifacts(self.run),measurement_script_sha256=hashlib.sha256(canonical).hexdigest(),
            measurement_log_sha256=hashlib.sha256(self.log).hexdigest(),new_measurement_only=True,physical_thresholds='unchanged')
        (self.run/'staged_remeasurement.json').write_text(json.dumps(self.receipt))
    def recover(self):return SB.recover_staged_remeasurement(self.b,self.run,self.script,self.log)
    def admission(self, binding):
        import pre_route_gate as PG
        kd=self.run/'kit';kd.mkdir(exist_ok=True)
        (kd/PG.CLOCK_RESULT).write_text(json.dumps(dict(source_binding=binding,clock={'cts':True})))
        why=[]
        with patch.object(PG.SB,'validate',return_value=(True,'bound')):
            result=PG.kit_gate_evidence(kd,why=why)
        return result,why
    def test_admission_requires_verified_new_log_without_archive_flag(self):
        b=self.recover();b['staged_measurement_log']=self.log.decode()
        result,why=self.admission(b);self.assertIsNotNone(result,why)
        self.assertNotIn('remote_archive_verified',result['source_binding'])
    def test_admission_rejects_missing_new_log(self):
        result,why=self.admission(self.recover());self.assertIsNone(result);self.assertIn('persisted log',why[0])
    def test_admission_rejects_changed_new_log(self):
        b=self.recover();b['staged_measurement_log']=(self.log+b'changed').decode()
        result,why=self.admission(b);self.assertIsNone(result);self.assertIn('receipt mismatch',why[0])
    def test_admission_rejects_changed_receipt(self):
        b=self.recover();b['staged_measurement_log']=self.log.decode();b['staged_remeasurement']['tool_image_identity']='wrong'
        self.assertIsNone(self.admission(b)[0])
    def test_admission_legacy_still_requires_archive(self):
        self.assertIsNone(self.admission(self.b)[0])
    def test_complete_rehash_accepts_only_new_evidence(self):
        b=self.recover();self.assertNotIn('remote_archive_verified',b)
        self.assertTrue(SB.staged_remeasurement_matches_log(b,self.log))
        self.assertFalse(SB.staged_remeasurement_matches_log(b,self.log+b'changed'))
    def test_legacy_default_still_requires_original_archive_stdout(self):
        with self.assertRaisesRegex(ValueError,'archive verification'):SB.recover_verified_snapshot(self.b,self.run/'src',self.log,self.script.read_bytes())
    def test_changed_source_rejected(self):
        (self.run/'src/actual.v').write_text('changed')
        with self.assertRaises(ValueError):self.recover()
    def test_missing_source_rejected(self):
        (self.run/'src/actual.v').unlink()
        with self.assertRaises(ValueError):self.recover()
    def test_sidecar_digest_rejected(self):
        self.b['manifest_sha256']='changed'
        with self.assertRaises(ValueError):self.recover()
    def test_marker_rejected(self):
        (self.run/'src/SOURCE_COMMIT').write_text('wrong')
        with self.assertRaisesRegex(ValueError,'SOURCE_COMMIT'):self.recover()
    def test_original_script_rejected(self):
        self.script.write_text('changed')
        with self.assertRaisesRegex(ValueError,'script digest'):self.recover()
    def test_new_script_rejected(self):
        (self.run/'staged_remeasurement.sh').write_text('fake logs')
        with self.assertRaisesRegex(ValueError,'canonical'):self.recover()
    def test_odb_rejected(self):
        p=next(self.run.rglob('4_1_cts.odb'));p.write_text('changed physical tree')
        with self.assertRaisesRegex(ValueError,'receipt differs'):self.recover()
    def test_missing_odb_rejected(self):
        next(self.run.rglob('4_1_cts.odb')).unlink()
        with self.assertRaisesRegex(ValueError,'physical artifact'):self.recover()
    def test_log_rejected(self):
        (self.run/'staged_remeasurement.log').write_bytes(self.log+b'fake')
        with self.assertRaisesRegex(ValueError,'persisted measurement log'):self.recover()
    def test_caller_boolean_is_not_receipt(self):
        self.assertFalse(SB.staged_remeasurement_matches_log(dict(self.b,staged_remeasurement=True),self.log))
    def test_reported_flow_error_rejected(self):
        with self.assertRaisesRegex(ValueError,'flow error'):SB.staged_measurement_image(self.log+b'GATE_FLOWERR actual failure\n')
        self.assertFalse(SB.staged_remeasurement_matches_log(self.recover(),self.log+b'GATE_FLOWERR actual failure\n'))
    def test_nonzero_flow_status_rejected(self):
        with self.assertRaisesRegex(ValueError,'nonzero flow status'):SB.staged_measurement_image(self.log+b'GATE_FLOW_RC=2\n')
    def test_image_identity_required(self):
        with self.assertRaisesRegex(ValueError,'image identity'):SB.staged_measurement_image(b'GATE_DONE\n')
    def test_altered_image_receipt_rejected(self):
        self.receipt['tool_image_identity']='sha256:'+'b'*64
        (self.run/'staged_remeasurement.json').write_text(json.dumps(self.receipt))
        with self.assertRaisesRegex(ValueError,'receipt differs'):self.recover()
    def test_altered_image_log_rejected(self):
        log=self.log.replace(b'a'*64,b'b'*64)
        with self.assertRaisesRegex(ValueError,'receipt differs'):SB.recover_staged_remeasurement(self.b,self.run,self.script,log)
    def test_duplicate_run_rejected(self):
        with self.assertRaisesRegex(ValueError,'already has a receipt'):SB.run_staged_remeasurement(self.b,self.run,self.script)
    def test_requested_route_and_overlay_failures_remain(self):
        with patch.object(SB,'git_files',return_value={'actual.v':b'changed route source'}):
            ok,_=SB.validate(self.recover(),self.run/'src',self.run/'src',commit='requested',route_overlay=False)
        self.assertFalse(ok)
        with patch.object(SB.overlay_module(),'capture_plan',side_effect=ValueError('overlay changed')):
            ok,_=SB.validate(self.recover(),self.run/'src',self.run/'src')
        self.assertFalse(ok)
if __name__=='__main__':unittest.main()
