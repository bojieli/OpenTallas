"""Factory construction/refusal only: no checkpoint payload or RTL token verdict."""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.gpu_sys import canonical_qwen_backend as F
from tools import h4_qwen_released_provider_delivery as D


class FactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_root = Path(os.environ.get(
            'OPENTALLAS_QWEN_RELEASED_SOURCE_ROOT', str(F.DEFAULT_SOURCE_ROOT)))
        cls.N, cls.B = F.load_originals(cls.source_root)
        cls.native = cls.B.native()
        D.validate_program(cls.native)

    def args(self, directory):
        return argparse.Namespace(enable_canonical_qwen=True, checkpoint=Path(directory),
                                  socket=Path(directory)/'rtl.sock', token=9707, position=0,
                                  released_source_root=self.source_root)

    def manifest(self, directory):
        # Metadata fixture only. No images, weights, KV or arithmetic responses
        # are created. The real original constructor checks every extent/codec.
        extents = self.B.extents(self.native)
        images = {}
        for number, ref in enumerate(sorted(self.B.immutable_refs(self.native))):
            e = extents[ref]
            images[ref] = dict(base=e['base'], bytes=e['bytes'], codec=e['codec'],
                              segments=[dict(start=0,bytes=e['bytes'],file=f'absent-{number}.bin',sha256='0'*64)])
        manifest = dict(schema='opentallas.Qwen.trained-byte-images.v1', complete=True,
                        identity=dict(native_sha256=D.PROGRAM_SHA, source_sha256={},
                                      checkpoint_lock_sha256=self.B.sha(self.source_root/'compiler/models/qwen3-8b/checkpoint_source.json')),
                        images=images)
        raw=D.canonical(manifest);(Path(directory)/'manifest.json').write_bytes(raw)
        return D.sha(raw)

    def construct(self, args, digest):
        with patch.object(F,'IMAGE_SHA',digest), patch.object(F,'load_originals',return_value=(self.N,self.B)), \
                patch.object(self.B,'native',return_value=self.native):
            return F.build(args)

    def test_actual_classes_complete_machine_socket_and_attach_without_execution(self):
        with tempfile.TemporaryDirectory() as td:
            args=self.args(td);digest=self.manifest(td)
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
                server.bind(str(args.socket));server.listen(1)
                result=self.construct(args,digest)
                with server.accept()[0] as peer:
                    try:
                        machine=result['machine'];backend=machine.weights.backend
                        self.assertIs(type(machine),self.N.TiledMachine)
                        self.assertIs(type(machine.memory),self.N.BoundKVStorage)
                        self.assertIs(type(machine.vm),self.N.NativePrimitiveVM)
                        self.assertIs(type(machine.weights),self.N.HBMByteTileProvider)
                        self.assertIs(type(backend),self.B.TrainedByteBackend)
                        self.assertEqual(len(machine.native['operations']),1737)
                        self.assertFalse(machine.done);self.assertFalse(machine.store.live)
                        self.assertEqual(backend.bytes_read,0);self.assertFalse(backend.handles)
                        self.assertFalse(machine.vm.counts)
                        with patch.object(D,'IMAGE_SHA',digest):
                            delivery=D.ReleasedProviderDelivery(*(result[k] for k in ('native_module','byte_module','machine','transport')),enabled=True).attach()
                        self.assertTrue(delivery.kv_client.installed_on(machine.memory,result['transport']))
                        self.assertEqual(delivery.sequence,0)
                        peer.setblocking(False)
                        with self.assertRaises(BlockingIOError):peer.recv(1)
                    finally:
                        result['transport'].close();backend.close()

    def test_private_original_imports_ignore_public_modules_and_leave_process_unchanged(self):
        poison={name:SimpleNamespace(poison=True) for name in F.MODULES}
        before=list(sys.path)
        with patch.dict(sys.modules,poison):
            N,B=F.load_originals(self.source_root)
            self.assertIsNot(N,self.N)
            self.assertIs(N.TiledMachine.__init__.__globals__['BoundKVStorage'],N.BoundKVStorage)
            self.assertIsNot(N.TiledMachine,self.N.TiledMachine)
            self.assertEqual(Path(B.__file__).parent,self.source_root/'tools')
            for name,value in poison.items():self.assertIs(sys.modules[name],value)
            self.assertEqual(sys.path,before)

    def test_default_off_before_loading_or_socket(self):
        args=self.args('.');args.enable_canonical_qwen=False
        with patch.object(F,'load_originals') as load,patch.object(F,'UnixRTLTransport') as connect:
            with self.assertRaisesRegex(ValueError,'default off'):F.build(args)
            load.assert_not_called();connect.assert_not_called()

    def test_private_reference_not_enrolled(self):
        args=self.args('.');args.expected_token=1
        with patch.object(F,'load_originals') as load:
            with self.assertRaisesRegex(ValueError,'private'):F.build(args)
            load.assert_not_called()

    def test_missing_socket_refused_before_source_load(self):
        args=self.args('.');args.socket=None
        with patch.object(F,'load_originals') as load:
            with self.assertRaisesRegex(ValueError,'socket'):F.build(args)
            load.assert_not_called()

    def test_unqualified_images_refused_without_source_or_socket(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td)/'manifest.json').write_text('{}')
            with patch.object(F,'load_originals') as load,patch.object(F,'UnixRTLTransport') as connect:
                with self.assertRaisesRegex(ValueError,'manifest'):F.build(self.args(td))
                load.assert_not_called();connect.assert_not_called()

    def test_reduced_program_refused_before_backend_or_socket(self):
        with tempfile.TemporaryDirectory() as td:
            digest=self.manifest(td);reduced=dict(self.native,operations=self.native['operations'][:41])
            with patch.object(F,'IMAGE_SHA',digest),patch.object(F,'load_originals',return_value=(self.N,self.B)), \
                    patch.object(self.B,'native',return_value=reduced),patch.object(F,'UnixRTLTransport') as connect, \
                    patch.object(self.B,'TrainedByteBackend') as backend:
                with self.assertRaisesRegex(ValueError,'canonical'):F.build(self.args(td))
                connect.assert_not_called();backend.assert_not_called()

    def test_source_commit_refused(self):
        with patch.object(F.subprocess,'check_output',return_value='moving-main\n'):
            with self.assertRaisesRegex(ValueError,'commit'):F.load_originals(self.source_root)

    def test_tampered_source_refused_before_import(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for row in json.loads(D.PINS.read_text()):
                dest=root/row['source_path'];dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(self.source_root/row['source_path'],dest)
            (root/'tools/h3_qwen_bounded_native.py').write_text('raise RuntimeError("must never import")')
            with patch.object(F.subprocess,'check_output',return_value=F.SOURCE_COMMIT+'\n'):
                with self.assertRaisesRegex(ValueError,'original runtime source'):F.load_originals(root)

    def test_token_and_context_bounds_refused_before_socket(self):
        with tempfile.TemporaryDirectory() as td:
            digest=self.manifest(td)
            for name,bad in [('token',True),('token',self.native['source_program']['config']['vocab_size']),
                             ('position',-1),('position',self.native['source_program']['context_capacity'])]:
                args=self.args(td);setattr(args,name,bad)
                with patch.object(F,'UnixRTLTransport') as connect:
                    with self.assertRaises(ValueError):self.construct(args,digest)
                    connect.assert_not_called()

    def test_socket_failure_closes_backend_and_never_runs(self):
        with tempfile.TemporaryDirectory() as td:
            digest=self.manifest(td)
            with patch.object(F,'UnixRTLTransport',side_effect=ConnectionRefusedError('no handler server')), \
                    patch.object(self.B.TrainedByteBackend,'close',autospec=True) as close, \
                    patch.object(self.N.TiledMachine,'run',autospec=True) as run:
                with self.assertRaises(ConnectionRefusedError):self.construct(self.args(td),digest)
                close.assert_called_once();run.assert_not_called()


if __name__=='__main__':unittest.main()
