"""Issuer-only metadata provenance causals; no physical flow is executed."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import source_binding as SB
import pre_route_gate as PG

SHA=lambda data:hashlib.sha256(data).hexdigest()
KIT='hcoll_issuer_r256v8_grid'
SPEC=f'physical/ref_tile/{KIT}/spec.json'


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.DEVNULL).decode().strip()


def put(root,path,value):
    p=root/path;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(value if isinstance(value,bytes) else json.dumps(value,sort_keys=True).encode())


def archive(root,paths):
    out=io.BytesIO()
    with tarfile.open(fileobj=out,mode='w:gz') as tf:
        for path in sorted(paths):
            data=(root/path).read_bytes(); row=tarfile.TarInfo(path);row.size=len(data);row.mtime=0
            tf.addfile(row,io.BytesIO(data))
    return out.getvalue()


@contextlib.contextmanager
def case(variant=None):
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);git(root,'init');git(root,'config','user.name','Test');git(root,'config','user.email','t@example.org')
        old_spec={'name':KIT,'outline':{'w':518.4,'h':432.0}}
        put(root,SPEC,old_spec)
        for i in range(327):put(root,f'rtl/input{i}.sv',f'// physical input{i}\n'.encode())
        for path in SB.METADATA_CLASSIFIER_MODULES:put(root,path,('// canonical '+path+'\n').encode())
        paths=git(root,'ls-files','--others','--exclude-standard').splitlines()
        git(root,'add','.');git(root,'commit','-m','published physical/classifier source');published=git(root,'rev-parse','HEAD')
        git(root,'update-ref','refs/remotes/origin/main',published)
        old_data=archive(root,paths);parent=SB.snapshot(old_data,root,published,root,published,[])
        parent['remote_archive_verified']=True
        parent['consumed']=SB.consumed_record(paths,parent['files'],'physical fixture')
        if variant=='parent_consumed_duplicate':
            parent['consumed']['paths'].append(parent['consumed']['paths'][0])
            parent['consumed']['count']+=1
            parent['consumed']['digest']=SB.canonical_digest(parent['consumed']['paths'])
        if variant=='parent_consumed_hash':
            parent['consumed']['sha256'][paths[0]]='0'*64
        if variant=='parent_consumed_schema':parent['consumed']['schema']='wrong'

        clock={'cts':True,'tt_pin_spread_ps':45.0,'ff_pin_spread_ps':46.7}
        trial={'overflow':0,'rc':'0'}
        old_gate={'schema':'opentallas.ref_tile.gate_result.v2','kit':KIT,'verdict':'FAIL','cts':True,
                  'source_binding':parent,'clock':clock,'trial_route':trial,
                  'items':[{'severity':'FAIL','check':'fill','message':'fill23%'},
                           {'severity':'WARN','check':'clock_rule','message':'native32/clock measured'}]}
        log=('GATE_SOURCE_ARCHIVE_SHA256='+parent['archive_sha256']+'\nGATE_FLOW_RC=0\n').encode()
        if variant=='log_link':log=b'GATE_SOURCE_ARCHIVE_SHA256=wrong\nGATE_FLOW_RC=0\n'
        quartet={'binding':parent,'gate':old_gate,'log':log,'spec':old_spec};refs={}
        for name,value in quartet.items():
            path='packet/original_'+name+('.log' if name=='log' else '.json');put(root,path,value)
            refs[name]={'path':path,'sha256':SHA((root/path).read_bytes())};paths.append(path)
        new_spec=copy.deepcopy(old_spec);new_spec['fill_reason']={'pin_bound':'ROOT-approved full pins and real clock corridors'}
        if variant=='other_field':new_spec['outline']['w']=600
        if variant=='extra_reason':new_spec['fill_reason']['waiver']='unsupported'
        put(root,SPEC,new_spec)
        if variant=='physical':put(root,'rtl/input0.sv',b'changed physical source\n')
        if variant=='helper':put(root,'tools/closure_loop/helper_overlay.py',b'wrong classifier\n')
        git(root,'add','.');git(root,'commit','-m','new metadata input snapshot');frozen=git(root,'rev-parse','HEAD')
        data=archive(root,paths);binding=SB.snapshot(data,root,frozen,root,frozen,[])
        binding['consumed']=SB.consumed_record(paths,binding['files'],'actual metadata input fixture')
        binding['execution_kind']='metadata-classification';binding['remote_archive_verified']=False
        binding['physical_parent']={'binding_sha256':refs['binding']['sha256'],'archive_sha256':parent['archive_sha256'],
                                   'manifest_sha256':parent['manifest_sha256'],'start_commit':published,'original_verdict':'FAIL'}
        modules={path:SHA((root/path).read_bytes()) for path in SB.METADATA_CLASSIFIER_MODULES}
        proof={'execution_kind':'metadata-classification','classification_source_commit':frozen,
               'classification_manifest_sha256':binding['manifest_sha256'],
               'classification_archive_sha256':binding['archive_sha256'],'executed_modules':modules,'published_commit':published}
        put(root,'packet/classification.tar.gz',data);put(root,'packet/execution.json',proof)
        git(root,'add','.');git(root,'commit','-m','classification execution outputs');current=git(root,'rev-parse','HEAD')
        binding['metadata_classification']={'schema':SB.METADATA_CLASSIFICATION_SCHEMA,'parent':refs,
            'archive':{'path':'packet/classification.tar.gz','sha256':SHA(data)},
            'classifier':{'published_commit':published,'executed_modules':modules,
                          'proof':{'path':'packet/execution.json','sha256':SHA((root/'packet/execution.json').read_bytes())}}}
        gate={'schema':'opentallas.ref_tile.gate_result.v2','kit':KIT,'verdict':'WARN','cts':True,
              'execution_kind':'metadata-classification','physical_parent':binding['physical_parent'],'source_binding':binding,'clock':copy.deepcopy(clock),
              'trial_route':copy.deepcopy(trial),'items':[{'severity':'WARN','check':'fill','message':'pin-bound fill23%'},old_gate['items'][1]]}
        yield root,binding,gate,current


class MetadataClassificationTest(unittest.TestCase):
    def issues(self,binding,root,gate,current):
        return SB.metadata_classification_issues(binding,root,KIT,gate,current)

    def test_valid_actual_archives_committed_inputs_published_tools_and_physics(self):
        with case() as (root,binding,gate,current):self.assertEqual(self.issues(binding,root,gate,current),[])

    def test_original_consumed_record_strict(self):
        for variant in ['parent_consumed_duplicate','parent_consumed_hash','parent_consumed_schema']:
            with self.subTest(variant=variant), case(variant) as (root,binding,gate,current):
                self.assertIn('original physical consumed record',self.issues(binding,root,gate,current)[0])

    def test_missing_parent(self):
        with case() as (root,binding,gate,current):
            del binding['metadata_classification']['parent']['gate']
            self.assertTrue(self.issues(binding,root,gate,current))

    def test_missing_actual_new_archive(self):
        with case() as (root,binding,gate,current):
            binding['metadata_classification']['archive']['path']='missing.tar.gz'
            self.assertTrue(self.issues(binding,root,gate,current))

    def test_new_archive_hash_mismatch(self):
        with case() as (root,binding,gate,current):
            binding['metadata_classification']['archive']['sha256']='0'*64
            self.assertTrue(self.issues(binding,root,gate,current))

    def test_whole_original_binding_hash_mismatch(self):
        with case() as (root,binding,gate,current):
            binding['metadata_classification']['parent']['binding']['sha256']='0'*64
            self.assertTrue(self.issues(binding,root,gate,current))

    def test_parent_archive_log_mismatch(self):
        with case('log_link') as (root,binding,gate,current):
            self.assertIn('archive/log linkage',self.issues(binding,root,gate,current)[0])

    def test_spec_physical_field_change(self):
        with case('other_field') as (root,binding,gate,current):
            self.assertIn('spec change',self.issues(binding,root,gate,current)[0])

    def test_other_metadata_reason_refused(self):
        with case('extra_reason') as (root,binding,gate,current):
            self.assertIn('pin_bound',self.issues(binding,root,gate,current)[0])

    def test_physical_source_change(self):
        with case('physical') as (root,binding,gate,current):
            self.assertIn('physical input changed',self.issues(binding,root,gate,current)[0])

    def test_helper_not_published_canonical(self):
        with case('helper') as (root,binding,gate,current):
            self.assertIn('classifier helper mismatch',self.issues(binding,root,gate,current)[0])

    def test_measurement_change_refused(self):
        with case() as (root,binding,gate,current):
            gate['clock']['tt_pin_spread_ps']=1
            self.assertIn('measured clock changed',self.issues(binding,root,gate,current)[0])

    def test_fake_remote_flag_refused(self):
        with case() as (root,binding,gate,current):
            binding['remote_archive_verified']=True
            self.assertIn('must not claim',self.issues(binding,root,gate,current)[0])

    def test_staged_remeasurement_cannot_bypass_typed_metadata_checks(self):
        with case() as (root,binding,gate,current):
            binding['staged_remeasurement']={'unsupported':'mixed provenance'}
            self.assertTrue(self.issues(binding,root,gate,current))

    def test_only_authorized_issuer_kits(self):
        with case() as (root,binding,gate,current):
            self.assertIn('unsupported kit',SB.metadata_classification_issues(binding,root,'other',gate,current)[0])

    def test_kit_gate_accepts_only_valid_typed_alternative_after_regular_source_validation(self):
        with case() as (root,binding,gate,current):
            kd=root/'physical/ref_tile'/KIT;put(root,str(kd.relative_to(root)/'gate_result.json'),gate)
            with patch.object(PG,'ROOT',root),patch.object(PG,'DAEMON_TREE',root),patch.object(SB,'validate',return_value=(True,'normal source validation passed')):
                self.assertIsNotNone(PG.kit_gate_evidence(kd,current))
                binding['metadata_classification']['archive']['sha256']='bad';put(root,str(kd.relative_to(root)/'gate_result.json'),gate)
                why=[];self.assertIsNone(PG.kit_gate_evidence(kd,current,why));self.assertIn('archive hash',why[0])

    def test_generic_missing_remote_archive_stays_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);kd=root/'other';kd.mkdir();put(root,'other/spec.json',{})
            put(root,'other/gate_result.json',{'kit':'other','source_binding':{'remote_archive_verified':False},'clock':{}})
            with patch.object(PG,'ROOT',root),patch.object(PG,'DAEMON_TREE',root),patch.object(SB,'validate',return_value=(True,'normal source validation passed')):
                why=[];self.assertIsNone(PG.kit_gate_evidence(kd,why=why));self.assertEqual(why,['remote archive verification missing'])


if __name__=='__main__':unittest.main()
