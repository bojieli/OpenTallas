"""How much of the V4 streaming engine already works for V4.1?

Monkeypatch only the vendor-source table and the encoding module name, then try to
build the engine.  If the skeleton builds, the port is small and only Engram
residency remains; if it fails deeper, the failure names the real work.
"""
import hashlib, importlib, sys, traceback
from pathlib import Path
ROOT = Path('/home/ubuntu/OpenTallas'); sys.path.insert(0, str(ROOT))
V41 = Path('/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277')
from runtime.reference import deepseek_v4_oracle as O

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
srcs = ['inference/model.py','inference/kernel.py','inference/convert.py','inference/engram.py','encoding/encoding.py','inference/config.json']
O.VENDOR_SOURCE_SHA256 = {s: sha(V41/s) for s in srcs if (V41/s).exists()}
print('pinned V4.1 vendor sources:', len(O.VENDOR_SOURCE_SHA256))

def import_vendor_v41(snapshot):
    for entry in (str(snapshot/'inference'), str(snapshot/'encoding')):
        if entry not in sys.path: sys.path.insert(0, entry)
    return (importlib.import_module('model'), importlib.import_module('kernel'),
            importlib.import_module('convert'), importlib.import_module('encoding'))
O.import_vendor = import_vendor_v41

# The V4.1 fp8_gemm asserts a different expert-scale shape than V4's, so the V4
# probe cannot build its test operand.  Bypass the PROBE only -- the expert path
# is then the documented fp8 recast, which is what the reduced oracle already
# uses -- to find out whether the 96,085-tensor skeleton builds at all.
O.verify_fp4_gemm = lambda *a, **k: {
    'fp4_gemm_agrees': False, 'fp8_gemm_agrees': True,
    'fp4_path_max_abs_error': float('nan'), 'fp8_path_max_abs_error': 0.0,
    'tolerance': 0.0, 'probe_tensor': 'BYPASSED for this probe',
    'reference_mean_abs': 0.0,
}

# V4.1's Transformer builds an NgramHashState, which needs a tokenizer whose
# ``.backend_tokenizer`` the vendor's build_compressed_token_map can read.  The V4
# engine passes none because V4 has no Engram.  The committed verified loader
# supplies the backend; a one-attribute shim bridges the attribute name.
from compiler.frontend.deepseek_v41_tokenizer import load_verified_deepseek_v41_tokenizer
_verified = load_verified_deepseek_v41_tokenizer(V41)
_backend = getattr(_verified, 'backend', None) or getattr(_verified, '_backend', None)
print('verified tokenizer backend:', type(_backend).__name__)
class _TokShim:
    #: build_compressed_token_map needs exactly two things from a tokenizer:
    #: ``.backend_tokenizer`` and ``len()``.  Nothing else is touched.
    def __init__(self, backend):
        self.backend_tokenizer = backend
    def __len__(self):
        return self.backend_tokenizer.get_vocab_size(with_added_tokens=True)
_tok = _TokShim(_backend)
_real_transformer = None
def _patch_transformer(model_mod):
    global _real_transformer
    _real_transformer = model_mod.Transformer
    class _T(_real_transformer):
        def __init__(self, args, tokenizer=None):
            super().__init__(args, _tok if tokenizer is None else tokenizer)
    model_mod.Transformer = _T

cfg = O.OracleConfig(snapshot=V41, max_seq_len=256, device='cuda', verbose=True)
# patch Transformer after the vendor import the engine performs
_orig_import = O.import_vendor
def _import_and_patch(snapshot):
    out = _orig_import(snapshot)
    _patch_transformer(out[0])
    return out
O.import_vendor = _import_and_patch
try:
    eng = O.StreamingDeepSeekV4(cfg)
    print()
    print('ENGINE BUILT against the V4.1 snapshot')
    print('  layers                 :', len(eng.model.layers))
    print('  parameter slots on meta:', len(eng._slots))
    print('  expert numeric path    :', eng.expert_dtype)
    eng_mods = [n for n,_ in eng.model.named_modules() if 'engram' in n.lower()]
    print('  engram modules         :', len(eng_mods), eng_mods[:3])
except Exception as e:
    print()
    print('FAILED:', type(e).__name__, str(e)[:300])
    for line in traceback.format_exc().splitlines()[-12:]:
        print('   ', line)
