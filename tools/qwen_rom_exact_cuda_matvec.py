#!/usr/bin/env python3
"""Opt-in exact host CUDA matvec; existing oracle/producer sources stay unchanged.

compile: NVRTC -> PTX, no GPU/context or C++ extension required (run remotely).
compare: ONE tiny GPU fixture, only after the GPU owner grants a slot.
run: explicit future caller opt-in; install the leaf then call the original main.
No hardware frequency/rate claim. Inputs remain BF16-rounded by hdc_golden.
"""
import argparse
import ctypes as C
import hashlib
import json
import sys
import time
from pathlib import Path

SOURCE = Path(__file__).with_name('cuda') / 'qwen_exact_matvec.cu'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bind(lib, name, args):
    fn = getattr(lib, name)
    fn.argtypes, fn.restype = args, C.c_int
    return fn


def checked(code, operation):
    if code:
        raise RuntimeError(f'{operation}: CUDA/NVRTC status {code}')


def compile_ptx(library, arch, output):
    """No torch import, CUDA context or GPU work. Supply the owner's architecture."""
    if not arch.startswith('compute_') or not arch[8:].isdigit():
        raise ValueError('architecture must be compute_<numeric capability>')
    if output.exists() or output.with_suffix('.json').exists():
        raise FileExistsError('fresh output required; never overwrite prior evidence')
    lib = C.CDLL(str(library))
    create = bind(lib, 'nvrtcCreateProgram', [C.POINTER(C.c_void_p), C.c_char_p, C.c_char_p,
                                             C.c_int, C.c_void_p, C.c_void_p])
    compile_ = bind(lib, 'nvrtcCompileProgram', [C.c_void_p, C.c_int, C.POINTER(C.c_char_p)])
    destroy = bind(lib, 'nvrtcDestroyProgram', [C.POINTER(C.c_void_p)])
    program = C.c_void_p()
    checked(create(C.byref(program), SOURCE.read_bytes(), SOURCE.name.encode(), 0, None, None), 'create')
    options = ['--gpu-architecture='+arch, '--std=c++11', '--fmad=false', '--ftz=false',
               '--prec-div=true', '--prec-sqrt=true']
    try:
        result = compile_(program, len(options), (C.c_char_p*len(options))(*(x.encode() for x in options)))
        size = C.c_size_t()
        checked(bind(lib, 'nvrtcGetProgramLogSize', [C.c_void_p, C.POINTER(C.c_size_t)])(program, C.byref(size)), 'log size')
        log = C.create_string_buffer(size.value)
        checked(bind(lib, 'nvrtcGetProgramLog', [C.c_void_p, C.c_void_p])(program, log), 'log')
        if result:
            raise RuntimeError(f'NVRTC compile {result}: {log.value.decode()}')
        checked(bind(lib, 'nvrtcGetPTXSize', [C.c_void_p, C.POINTER(C.c_size_t)])(program, C.byref(size)), 'PTX size')
        ptx = C.create_string_buffer(size.value)
        checked(bind(lib, 'nvrtcGetPTX', [C.c_void_p, C.c_void_p])(program, ptx), 'PTX')
        major, minor = C.c_int(), C.c_int()
        checked(bind(lib, 'nvrtcVersion', [C.POINTER(C.c_int), C.POINTER(C.c_int)])(C.byref(major), C.byref(minor)), 'version')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(ptx.raw)
        assembly = ptx.value.decode()
        if 'fma.rn.f32' in assembly or '.ftz' in assembly or 'mul.rn.f32' not in assembly or 'add.rn.f32' not in assembly:
            raise RuntimeError('unexpected fused/FTZ or missing explicit RN PTX arithmetic')
        record = dict(scope='HOST_SIMULATION_ONLY', source_sha256=sha(SOURCE),
                      ptx_sha256=sha(output), nvrtc_library_sha256=sha(library),
                      nvrtc_version=[major.value, minor.value], options=options, compile_log=log.value.decode(),
                      ptx_explicit_rn_no_fma_no_ftz=True)
        output.with_suffix('.json').write_text(json.dumps(record, indent=2)+'\n')
        return record
    finally:
        checked(destroy(C.byref(program)), 'destroy')


def validate_shape(shape, strides, split):
    if type(split) is not int or split < 1 or split & (split-1):
        raise ValueError('split must be a positive power of two')
    if len(shape) != 3 or any(type(x) is not int or x <= 0 for x in shape) or shape[1] != split:
        raise ValueError('wT must have shape [positive kc, split, positive rows]')
    if len(strides) != 3 or any(type(x) is not int or x <= 0 for x in strides):
        raise ValueError('positive weight strides required')
    kc, _, n = shape
    if split*n > 128*((1 << 31)-1) or sum((a-1)*b for a,b in zip(shape,strides)) >= (1 << 63):
        raise ValueError('CUDA index/grid overflow')
    return kc, n


class ExactMatvec:
    """Borrow tensors/current stream; retain loaded modules per actual CUDA context."""
    def __init__(self, ptx):
        self.ptx = Path(ptx)
        book = json.loads(self.ptx.with_suffix('.json').read_text())
        if book['source_sha256'] != sha(SOURCE) or book['ptx_sha256'] != sha(self.ptx):
            raise ValueError('source/PTX enrollment mismatch')
        if book['options'] != ['--gpu-architecture='+book['options'][0].split('=',1)[1],
                               '--std=c++11','--fmad=false','--ftz=false','--prec-div=true','--prec-sqrt=true']:
            raise ValueError('unsafe compile options')
        self.driver = C.CDLL('libcuda.so.1')
        self.context = bind(self.driver, 'cuCtxGetCurrent', [C.POINTER(C.c_void_p)])
        self.load = bind(self.driver, 'cuModuleLoadData', [C.POINTER(C.c_void_p), C.c_void_p])
        self.function = bind(self.driver, 'cuModuleGetFunction', [C.POINTER(C.c_void_p), C.c_void_p, C.c_char_p])
        self.launch = bind(self.driver, 'cuLaunchKernel', [C.c_void_p]+[C.c_uint]*7+[C.c_void_p,C.POINTER(C.c_void_p),C.c_void_p])
        self.modules = {}

    def _functions(self):
        context = C.c_void_p()
        checked(self.context(C.byref(context)), 'current context')
        if not context.value:
            raise RuntimeError('PyTorch must initialize the selected CUDA context')
        if context.value not in self.modules:
            module = C.c_void_p()
            data = C.create_string_buffer(self.ptx.read_bytes())
            checked(self.load(C.byref(module), data), 'load PTX')
            fs = []
            for name in (b'qwen_serial_k', b'qwen_split_pair'):
                f = C.c_void_p()
                checked(self.function(C.byref(f), module, name), 'get function')
                fs.append(f)
            self.modules[context.value] = (module, fs)
        return self.modules[context.value][1]

    def _launch(self, function, count, stream, pointers, integers):
        values = [C.c_void_p(p) for p in pointers]+[C.c_longlong(v) for v in integers]
        args = (C.c_void_p*len(values))(*(C.cast(C.pointer(v),C.c_void_p) for v in values))
        checked(self.launch(function, (count+127)//128,1,1,128,1,1,0,
                            C.c_void_p(stream.cuda_stream), args, None), 'launch')

    def rounded(self, wT, xb, split):
        """xb is already BF16-rounded FP32 [split,kc], as in the existing oracle."""
        import torch
        kc, n = validate_shape(tuple(wT.shape), tuple(wT.stride()), split)
        if wT.dtype != torch.float32 or xb.dtype != torch.float32 or not wT.is_cuda or not xb.is_cuda:
            raise ValueError('CUDA FP32 weights and rounded inputs required')
        if xb.device != wT.device or tuple(xb.shape) != (split,kc) or not xb.is_contiguous():
            raise ValueError('contiguous [split,kc] inputs on the weight device required')
        with torch.cuda.device(wT.device):
            stream = torch.cuda.current_stream(wT.device)
            serial, pair = self._functions()
            a = torch.empty((split,n),dtype=torch.float32,device=wT.device)
            b = torch.empty((max(1,split//2),n),dtype=torch.float32,device=wT.device) if split > 1 else None
            self._launch(serial, split*n, stream, [wT.data_ptr(),xb.data_ptr(),a.data_ptr()],
                         [kc,split,n,*wT.stride()])
            levels = split
            while levels > 1:
                self._launch(pair, (levels//2)*n, stream, [a.data_ptr(),b.data_ptr()], [levels//2,n])
                a,b = b,a
                levels //= 2
            # Same-stream allocator ownership covers asynchronous temporary uses.
            wT.record_stream(stream)
            xb.record_stream(stream)
            return a[0]

    def install(self, oracle):
        import numpy as np
        import torch
        def gpu_matvec(wT, x, split):
            kc = wT.shape[0]
            xb = oracle.G.to_bf16(np.asarray(x,dtype=np.float32))
            xr = torch.as_tensor(xb.reshape(split,kc),device=wT.device)
            return self.rounded(wT,xr,split).cpu().numpy()
        oracle.gpu_matvec = torch.no_grad()(gpu_matvec)


def compare(ptx, output):
    """Tiny finite fixture, not inference. GPU owner must authorize before invoking."""
    import numpy as np
    import torch
    torch.set_num_threads(1)
    import hdc_golden as G
    import qwen_rom_dspark_oracle_gpu_w12 as oracle
    if output.exists():
        raise FileExistsError('fresh comparison receipt required')
    torch.set_num_threads(1)
    engine = ExactMatvec(ptx)
    rng = np.random.default_rng(904)
    records = []
    timing = None
    for kind, split, k in [('normal',8,128), ('subnormal',4,32), ('cancel',8,64),
                           ('signed_zero',1,8), ('rounding',1,2), ('tree_order',4,4)]:
        w = rng.integers(-128,128,(19,k)).astype(np.float32)
        x = rng.normal(size=k).astype(np.float32)
        if kind == 'subnormal':
            x *= np.float32(1e-39)
        elif kind == 'cancel':
            w[:,1::2] = -w[:,0::2]; x[1::2] = x[0::2]
        elif kind == 'signed_zero':
            w[:] = -0.; x[:] = 1.
        elif kind == 'rounding':
            w[:,0] = -1.; w[:,1] = np.float32(1.+2**-23)
            x[:] = np.float32(1.-2**-8)  # representable BF16; FMA differs from two roundings
        elif kind == 'tree_order':
            w[:] = [2**24,1,-2**24,1]; x[:] = 1.
        full = oracle.gpu_wT(w,split)
        weights = full[:,:,2:17]  # non-contiguous head row slice (original row strides)
        golden = G.matvec(w[2:17],x,split)
        baseline = oracle.gpu_matvec(weights,x,split)
        xb = torch.as_tensor(G.to_bf16(x).reshape(split,k//split),device=weights.device)
        stream = torch.cuda.Stream()
        with torch.cuda.stream(stream):
            stream.wait_stream(torch.cuda.default_stream())
            actual = engine.rounded(weights,xb,split).cpu().numpy()
        ok = bool(np.array_equal(G.bits(actual),G.bits(baseline)) and np.array_equal(G.bits(actual),G.bits(golden)))
        if kind == 'normal':
            times = {}
            for label, call in [('baseline',lambda: oracle.gpu_matvec(weights,x,split)),
                                ('leaf',lambda: engine.rounded(weights,torch.as_tensor(
                                    G.to_bf16(x).reshape(split,k//split),device=weights.device),split).cpu().numpy())]:
                start = time.perf_counter()
                for _ in range(3):
                    call()
                times[label+'_seconds_per_call'] = (time.perf_counter()-start)/3
            timing = dict(**times, includes_same_bf16_round_upload_download=True,
                          shape=[15,k,split], repetitions=3, whole_producer_speedup=None)
        records.append(dict(kind=kind,split=split,k=k,rows=15,bit_exact=ok,
                            result_sha256=hashlib.sha256(G.bits(actual).tobytes()).hexdigest()))
    record = dict(scope='TINY_HOST_NUMERICAL_FIXTURE_ONLY', cases=records,
                  status='PASS' if all(r['bit_exact'] for r in records) else 'FAIL',
                  source_sha256=sha(SOURCE), wrapper_sha256=sha(__file__), ptx_sha256=sha(ptx),
                  oracle_sha256=sha(oracle.__file__),golden_sha256=sha(G.__file__),
                  gpu=torch.cuda.get_device_name(),torch_version=torch.__version__,
                  max_weight_tensor_bytes=19*128*4, tiny_timing=timing,
                  tensor_working_set_upper_bytes=65536, full_inference=False)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(record,indent=2)+'\n')
    if record['status'] != 'PASS':
        raise RuntimeError('CUDA fixture mismatch; failed receipt retained')
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command',required=True)
    c = sub.add_parser('compile'); c.add_argument('--nvrtc',type=Path,required=True)
    c.add_argument('--arch',required=True); c.add_argument('--output',type=Path,required=True)
    c = sub.add_parser('compare'); c.add_argument('--ptx',type=Path,required=True); c.add_argument('--output',type=Path,required=True)
    c = sub.add_parser('run'); c.add_argument('--ptx',type=Path,required=True)
    c.add_argument('--script',choices=['oracle','producer'],required=True); c.add_argument('argv',nargs=argparse.REMAINDER)
    a = p.parse_args()
    if a.command == 'compile':
        print(json.dumps(compile_ptx(a.nvrtc,a.arch,a.output),indent=2))
    elif a.command == 'compare':
        print(json.dumps(compare(a.ptx,a.output),indent=2))
    else:
        import qwen_rom_dspark_oracle_gpu_w12 as oracle
        engine = ExactMatvec(a.ptx); engine.install(oracle)
        script = oracle if a.script == 'oracle' else __import__('qwen_rom_dspark_np4_producer')
        sys.argv = [script.__file__]+(a.argv[1:] if a.argv[:1] == ['--'] else a.argv)
        script.main()


if __name__ == '__main__':
    main()
