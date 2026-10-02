import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import uarch_topk_physical_g0_archive_replay as M

class ArchiveReplay(unittest.TestCase):
    def repo_fixture(self,td,clone=False):
        repo=Path(td)/'source';repo.mkdir()
        for path in ['tools/uarch_topk_physical_g0_inputs.py','tools/uarch_topk_integer_tree_model.py','tools/uarch_topk_physical_g0_archive_replay.py']:
            out=repo/path;out.parent.mkdir(exist_ok=True);shutil.copyfile(ROOT/path,out)
        subprocess.run(['git','init','-q',str(repo)],check=True,capture_output=True)
        if clone:
            package=repo/'results/uarch/topk_physical_g0_source_archive_20261002';package.mkdir(parents=True)
            shutil.copyfile(M.ARCHIVE/'source_manifest.json',package/'source_manifest.json')
            shutil.copytree(M.ARCHIVE/'inputs',package/'inputs')
            paths=[str(x.relative_to(repo)) for x in repo.rglob('*') if x.is_file() and '.git' not in x.parts]
            subprocess.run(['git','add',*paths],cwd=repo,check=True)
            subprocess.run(['git','-c','user.name=ArchiveTest','-c','user.email=archive-test@example.invalid','commit','-qm','source-only fresh-clone fixture'],cwd=repo,check=True,capture_output=True)
            dest=Path(td)/'clone';subprocess.run(['git','clone','--no-local','--quiet',str(repo),str(dest)],check=True,capture_output=True);repo=dest
        return repo
    def test_explicit_archive_only_is_byte_exact_and_does_not_probe_git(self):
        with mock.patch.object(M.SourceArchive,'commit_available',side_effect=AssertionError('no history probe in archive-only')):
            data,r=M.replay(ROOT,mode='archive-only')
        self.assertEqual(M.digest(data),M.MODEL_SHA);self.assertEqual(r['origins_verified'],12)
        self.assertEqual(set(r['origin_modes'].values()),{'explicit_verified_archive_only'})
        self.assertTrue(r['actual_repository_inventory_checked'])
    def test_fresh_clone_missing_all_historical_objects_replays_exact(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.repo_fixture(td,clone=True)
            for commit in ['aa745a879e20e3db598f7be9345cb7ad3b1d5d2f','1d8304647ceb7a1b64d96217c6dfa075b5704f0a','4b6708348f3938e0830c3549fbbecadbce18e798']:
                p=subprocess.run(['git','rev-parse','--verify','--quiet',commit+'^{commit}'],cwd=repo,capture_output=True)
                self.assertEqual(p.returncode,1)
            data,r=M.replay(repo,repo/'results/uarch/topk_physical_g0_source_archive_20261002')
            out=Path(td)/'fresh-clone-cli'
            result=subprocess.run([sys.executable,str(repo/'tools/uarch_topk_physical_g0_archive_replay.py'),'--repo',str(repo),'--out',str(out)],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr.decode())
            self.assertEqual((out/'model.json').read_bytes(),data)
            self.assertEqual(M.digest(data),M.MODEL_SHA)
            self.assertEqual(set(r['origin_modes'].values()),{'verified_archive_commit_unavailable'})
    def test_git_preferred_uses_actual_available_or_missing_history(self):
        data,r=M.replay(ROOT)
        self.assertEqual(M.digest(data),M.MODEL_SHA)
        archive=M.SourceArchive(ROOT)
        expected={key:('available_git_origin_verified' if archive.commit_available(entry['commit']) else 'verified_archive_commit_unavailable') for key,entry in archive.origins.items()}
        self.assertEqual(r['origin_modes'],expected)
    def test_corrupted_archive_refused_even_when_git_available(self):
        with tempfile.TemporaryDirectory() as td:
            archive=Path(td)/'archive';shutil.copytree(M.ARCHIVE,archive)
            manifest=json.loads((archive/'source_manifest.json').read_text());path=archive/manifest['origins'][0]['archive_path']
            path.write_bytes(path.read_bytes()+b'changed')
            with self.assertRaisesRegex(ValueError,'archived origin bytes changed'):M.replay(ROOT,archive)
    def test_manifest_mutation_refused(self):
        with tempfile.TemporaryDirectory() as td:
            archive=Path(td)/'archive';shutil.copytree(M.ARCHIVE,archive)
            p=archive/'source_manifest.json';p.write_bytes(p.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'manifest pin'):M.replay(ROOT,archive)
    def test_actual_repository_inventory_changed_refused(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.repo_fixture(td);p=repo/M.INVENTORY;p.write_bytes(p.read_bytes()+b'\n# changed main source\n')
            with self.assertRaisesRegex(ValueError,'actual repository inventory'):M.replay(repo,mode='archive-only')
    def test_actual_baseline_generator_changed_refused(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.repo_fixture(td);p=repo/'tools/uarch_topk_physical_g0_inputs.py';p.write_bytes(p.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'baseline generator bytehash'):M.replay(repo,mode='archive-only')
    def test_available_commit_missing_path_never_falls_back(self):
        archive=M.SourceArchive(ROOT);entry=next(iter(archive.origins.values()))
        with mock.patch.object(archive,'commit_available',return_value=True),mock.patch.object(M.subprocess,'check_output',side_effect=subprocess.CalledProcessError(128,['git','show'])):
            with self.assertRaises(subprocess.CalledProcessError):archive.read(entry['commit'],entry['path'])
        self.assertEqual(archive.used,{})
    def test_available_git_bytes_mismatch_never_falls_back(self):
        archive=M.SourceArchive(ROOT);entry=next(iter(archive.origins.values()))
        with mock.patch.object(archive,'commit_available',return_value=True),mock.patch.object(M.subprocess,'check_output',return_value=b'wrong source'):
            with self.assertRaisesRegex(ValueError,'available git origin differs'):archive.read(entry['commit'],entry['path'])
        self.assertEqual(archive.used,{})
    def test_git_probe_error_never_falls_back(self):
        archive=M.SourceArchive(ROOT);entry=next(iter(archive.origins.values()))
        with mock.patch.object(M.subprocess,'run',return_value=mock.Mock(returncode=128)):
            with self.assertRaisesRegex(RuntimeError,'probe failed'):archive.read(entry['commit'],entry['path'])
        self.assertEqual(archive.used,{})
    def test_unknown_origin_and_other_commands_refused(self):
        archive=M.SourceArchive(ROOT,mode='archive-only')
        with self.assertRaisesRegex(ValueError,'unarchived origin'):archive.read(M.FULL,'not-an-origin')
        with self.assertRaisesRegex(ValueError,'unsupported baseline'):archive.check_output(['git','status'],cwd=ROOT)
    def test_archive_only_works_without_git_database(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.repo_fixture(td);shutil.rmtree(repo/'.git')
            data,r=M.replay(repo,mode='archive-only');self.assertEqual(M.digest(data),M.MODEL_SHA)
            with self.assertRaises(subprocess.CalledProcessError):M.replay(repo,mode='git-preferred')
    def test_cli_receipt_and_first_failure_preserved_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.repo_fixture(td);out=Path(td)/'success'
            args=[sys.executable,str(ROOT/'tools/uarch_topk_physical_g0_archive_replay.py'),'--repo',str(repo),'--out',str(out)]
            p=subprocess.run(args,capture_output=True);self.assertEqual(p.returncode,0,p.stderr.decode())
            receipt=json.loads((out/'receipt.json').read_text());self.assertTrue(receipt['byte_exact_preserved_model']);self.assertEqual(receipt['jobs_launched'],0)
            before=(out/'receipt.json').read_bytes();p=subprocess.run(args,capture_output=True);self.assertNotEqual(p.returncode,0)
            self.assertEqual(before,(out/'receipt.json').read_bytes());self.assertFalse((out/'failure.json').exists())
            out=Path(td)/'fail';(repo/M.INVENTORY).write_text('bad actual inventory')
            args[-1]=str(out);p=subprocess.run(args,capture_output=True);self.assertNotEqual(p.returncode,0)
            self.assertIn('actual repository inventory',json.loads((out/'failure.json').read_text())['exception'])
            self.assertFalse((out/'model.json').exists())

if __name__=='__main__':unittest.main()
