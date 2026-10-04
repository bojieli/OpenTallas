"""Original released checkpoint machine factory for run_canonical_qwen.

Use --backend tools.gpu_sys.canonical_qwen_backend:build and --checkpoint
<qualified trained-byte image directory> --socket <existing RTL server>.
--released-source-root selects the unchanged 870c5fe runtime checkout.
Construction never executes a recipe, reads an activation or starts a server.
"""
import builtins
import json
from pathlib import Path
import subprocess
from types import ModuleType
import uuid

from tools.h4_qwen_released_provider_delivery import (
    IMAGE_SHA, PINS, PROGRAM_SHA, UnixRTLTransport, require, sha, validate_program,
)

SOURCE_COMMIT = '870c5fe581b768df28dd2998b2d0aecc24510c23'
DEFAULT_SOURCE_ROOT = Path('/home/ubuntu/OpenTallas-qwen-trained-native-execution')
# The only additional import of the original native runtime, also frozen.
PROGRAM_MODULE_SHA = '4ecc9eadc4de9e3a65cb66e3977cd2db6eb514a4459117c15aad61ec7e4014e1'
MODULES = ('qwen_hbm_complete_program', 'h3_qwen_complete_native',
           'h3_qwen_bounded_native', 'qwen_trained_byte_provider')


def load_originals(source_root):
    """Private original modules; never replace sys.modules or edit sys.path.

    Original absolute imports resolve within this per-factory module map.
    Every source is validated before execution. Other dependencies use Python's
    ordinary importer. __file__ and ROOT remain the original source paths, so
    TrainedByteBackend's own producer/lock checks are preserved.
    """
    root = Path(source_root).resolve(strict=True)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    require(head == SOURCE_COMMIT, 'released runtime commit must be exact870c5fe')
    pins = json.loads(PINS.read_text())
    checked = {}
    for row in pins:
        raw = (root / row['source_path']).read_bytes()
        require(sha(raw) == row['sha256'], 'original runtime source ' + row['source_path'])
        checked[row['source_path']] = raw
    path = 'tools/qwen_hbm_complete_program.py'
    checked[path] = (root / path).read_bytes()
    require(sha(checked[path]) == PROGRAM_MODULE_SHA, 'original program import source')
    private = {}
    namespace = '_released_qwen_' + uuid.uuid4().hex
    public_import = builtins.__import__

    def private_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 0 and name in MODULES:
            require(name in private, 'original runtime import dependency order')
            return private[name]
        return public_import(name, globals, locals, fromlist, level)

    for name in MODULES:
        source = root / 'tools' / (name + '.py')
        module = ModuleType(namespace + '.' + name)
        module.__file__ = str(source)
        module.__builtins__ = dict(vars(builtins), __import__=private_import)
        exec(compile(checked['tools/' + name + '.py'], str(source), 'exec'), module.__dict__)
        private[name] = module
    return private['h3_qwen_bounded_native'], private['qwen_trained_byte_provider']


def build(args):
    """Factory contract: native_module, byte_module, machine, transport.

    The launcher installs ReleasedProviderDelivery (including actual KV hooks)
    before run. Socket connection is last: refusals cannot issue RTL requests.
    --checkpoint is the existing qualified byte image directory, not a raw HF
    snapshot. Missing images are refused; no producer/codec job is launched.
    """
    require(getattr(args, 'enable_canonical_qwen', False) is True, 'canonical factory default off')
    require(not hasattr(args, 'expected_token'), 'reference token is private to the launcher')
    require(getattr(args, 'socket', None) is not None, 'existing actual RTL socket required')
    images = Path(args.checkpoint).resolve(strict=True)
    require(sha((images / 'manifest.json').read_bytes()) == IMAGE_SHA,
            'qualified original trained-byte image manifest')
    source_root = getattr(args, 'released_source_root', DEFAULT_SOURCE_ROOT)
    native_module, byte_module = load_originals(source_root)
    native = byte_module.native()
    validate_program(native)
    require(type(args.token) is int and 0 <= args.token < native['source_program']['config']['vocab_size'],
            'source vocabulary token bounds')
    require(type(args.position) is int and 0 <= args.position < native['source_program']['context_capacity'],
            'source persistent context bounds')
    backend = byte_module.TrainedByteBackend(images, native)
    try:
        machine = native_module.TiledMachine(native, native_module.HBMByteTileProvider(backend))
        transport = UnixRTLTransport(args.socket, PROGRAM_SHA)
    except BaseException:
        backend.close()
        raise
    return dict(native_module=native_module, byte_module=byte_module,
                machine=machine, transport=transport)
