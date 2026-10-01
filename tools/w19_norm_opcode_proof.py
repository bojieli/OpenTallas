#!/usr/bin/env python3
"""Typed CPU execution of the published norm calendar recipes, not GPU timing.

Vector registers represent parallel lane invocations, not a new instruction or
free RF capacity. Norm chunk-tree/transport is an explicit supplied LOAD edge.
"""
import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import numpy as np
import hdc_golden as G
import hdc_golden_v41 as V
import w19_gpu_norm_calendar as C

F = np.float32
CALENDAR = "results/rtl/w19_checkpoint_production_20261001/gpu-norm-calendar-r1.json"
PRODUCER = "results/quality/w19_hc_residual_proof_20261001"


def sha(b):
    return hashlib.sha256(b).hexdigest()


@dataclass
class Value:
    kind: str
    data: np.ndarray

    def __post_init__(self):
        dtype = {"F32": np.float32, "U32": np.uint32, "U16": np.uint16}[self.kind]
        a = np.asarray(self.data)
        if a.dtype != dtype:
            raise ValueError("typed value dtype mismatch")
        self.data = a.copy()

    def u32(self):
        if self.kind == "U16":
            raise ValueError("U16 needs WIDEN")
        return self.data.view(np.uint32)

    def f32(self):
        if self.kind == "U16":
            raise ValueError("U16 needs WIDEN")
        return self.data.view(F)


def f32(a):
    return Value("F32", np.asarray(a, F))


def bf16_memory(a):
    a = np.asarray(a, F)
    if not np.array_equal(a.view(np.uint32), G.to_bf16(a).view(np.uint32)):
        raise ValueError("BF16 load source is not already rounded")
    return Value("U16", (a.view(np.uint32) >> 16).astype(np.uint16))


def constants(eps):
    f = {"@F5120": 5120, "@EPS": eps, "@FHALF": .5, "@FONEHALF": 1.5}
    u = {"@USEED": 0x5F3759DF, "@U16": 16, "@U1": 1, "@U7FFF": 0x7FFF, "@UFFFF0000": 0xFFFF0000, "@SIGN": 0x80000000}
    return {**{k: f32(v) for k, v in f.items()}, **{k: Value("U32", np.asarray(v, np.uint32)) for k, v in u.items()}}


class Machine:
    def __init__(self, program, memory, eps=1e-20, rf_budget=32):
        # Use the actual calendar's dependency/arity/liveness admission before
        # interpreting it. No calendar cycle count is measured hardware timing.
        self.admission = C.calendar(program, 1)
        if self.admission["peak_live_value_registers"] + 8 > rf_budget:
            raise ValueError("RF register budget exceeded")
        self.program, self.memory = program, memory
        self.constants = constants(eps)
        self.regs, self.trace, self.stores = {}, [], []

    def read(self, name):
        if name in self.constants:
            return self.constants[name]
        if name not in self.regs:
            raise ValueError("read-before-write: " + name)
        return self.regs[name]

    def run(self):
        for pc, ins in enumerate(self.program):
            op, dst, attrs = ins["op"], ins["dst"], ins["attributes"]
            args = [self.read(n) for n in ins["src"]]
            if op == "LOAD":
                source = attrs["source"]
                if source not in self.memory:
                    raise ValueError("unbound LOAD: " + source)
                v = self.memory[source]
            elif op == "WIDEN":
                if args[0].kind != "U16":
                    raise ValueError("WIDEN requires U16 memory value")
                v = Value("F32", (args[0].data.astype(np.uint32) << 16).view(F))
            elif op in ("FMUL", "FADD", "DIV"):
                a, b = [x.f32() for x in args]
                with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
                    result = a * b if op == "FMUL" else a + b if op == "FADD" else a / b
                result = np.asarray(result, F)
                v = f32(np.where(result == 0, F(0), result).astype(F))
            elif op in ("SHR", "AND", "IADD", "ISUB", "XOR"):
                a, b = [x.u32() for x in args]
                if op == "SHR" and np.any(b >= 32):
                    raise ValueError("invalid shift")
                if op == "SHR": result = a >> b
                elif op == "AND": result = a & b
                elif op == "XOR": result = a ^ b
                elif op == "IADD": result = ((a.astype(np.uint64) + b.astype(np.uint64)) & 0xFFFFFFFF).astype(np.uint32)
                else: result = ((a.astype(np.uint64) - b.astype(np.uint64)) & np.uint64(0xFFFFFFFF)).astype(np.uint32)
                v = Value("U32", np.asarray(result, np.uint32))
            elif op == "STORE16":
                if attrs.get("byte_enable") is not True or attrs.get("source_bits") != "31:16":
                    raise ValueError("STORE16 byte/bit contract")
                v = Value("U16", (args[0].u32() >> 16).astype(np.uint16))
                self.stores.append(v)
            else:
                raise ValueError("unsupported phase opcode: " + op)
            if dst:
                if dst.startswith("@"):
                    raise ValueError("constant write")
                self.regs[dst] = Value(v.kind, v.data)
            self.trace.append({"pc": pc, "op": op, "dst": dst, "src": ins["src"], "kind": v.kind,
                               "shape": list(v.data.shape), "sha256": sha(v.data.tobytes()), "value": v})
        return self

    def stored_f32(self):
        if len(self.stores) != 1:
            raise ValueError("expected one STORE16")
        return (self.stores[0].data.astype(np.uint32) << 16).view(F)


@contextmanager
def golden_trace():
    trace = []
    saved = {(m, n): getattr(m, n) for m in (G, V) for n in ("mul", "add")}
    saved[(V, "div")] = V.div
    def wrap(op, fn):
        def call(*args):
            v = fn(*args)
            trace.append((op, np.asarray(v, F).copy()))
            return v
        return call
    try:
        for (m, n), fn in saved.items():
            setattr(m, n, wrap({"mul": "FMUL", "add": "FADD", "div": "DIV"}[n], fn))
        yield trace
    finally:
        for (m, n), fn in saved.items():
            setattr(m, n, fn)


def equal(a, b):
    return a.shape == b.shape and np.array_equal(a.view(np.uint32), b.view(np.uint32))


def check_float_trace(vm, oracle):
    trace = [(r["op"], r["value"].f32()) for r in vm.trace if r["op"] in ("FMUL", "FADD", "DIV")]
    if len(trace) != len(oracle):
        raise AssertionError("float instruction count mismatch")
    for i, ((op, v), (name, ref)) in enumerate(zip(trace, oracle)):
        if op != name or not equal(v, ref):
            raise AssertionError(f"rounded opcode boundary {i} mismatch")


def phases(recipes, arrays, gain, eps):
    res, pre, post, comb, y = [arrays[n] for n in ("res", "pre_coeff", "post_coeff", "comb", "y")]
    model = SimpleNamespace(hc=4)
    mem = {f"residual[{j}][global_dim]": bf16_memory(res[j]) for j in range(4)}
    mem.update({f"pre[{j}]": f32(pre[j]) for j in range(4)})
    a = Machine(recipes["pre"], mem, eps).run()
    with golden_trace() as t:
        reference_pre = V.Model.hc_pre(model, res, pre)
    check_float_trace(a, t)
    assert equal(a.stored_f32(), reference_pre) and equal(a.stored_f32(), arrays["pre_output"])
    k = np.arange(20480) // 5120
    d = np.arange(20480) % 5120
    mem = {f"residual[{j}][global_dim]": bf16_memory(res[j, d]) for j in range(4)}
    mem.update({f"comb[{j},k]": f32(comb[j, k]) for j in range(4)})
    mem.update({"y[global_dim]": bf16_memory(y[d]), "post[k]": f32(post[k])})
    b = Machine(recipes["post"], mem, eps).run()
    with golden_trace() as t:
        reference_post = V.Model.hc_post(model, y, res, post, comb)
    # Calendar vector invocations group all k in parallel. Original method
    # emits seven mix operations per k, then mul/add per k. Preserve each
    # lane's primitive order while assembling the oracle in that same grouping.
    grouped = [(t[j][0], np.concatenate([t[7 * kk + j][1] for kk in range(4)])) for j in range(7)]
    grouped += [(t[28 + j][0], np.concatenate([t[28 + 2 * kk + j][1] for kk in range(4)])) for j in range(2)]
    check_float_trace(b, grouped)
    assert equal(b.stored_f32().reshape(4, 5120), reference_post)
    assert equal(b.stored_f32().reshape(4, 5120), arrays["post_output"])
    x = a.stored_f32()
    ordered_sum = F(V.csum(G.mul(x, x)))
    s = Machine(recipes["norm_scalar"], {"ordered global chunk8 tree result": f32(ordered_sum)}, eps).run()
    with golden_trace() as t:
        r = G.rsqrt(V.add(V.div(ordered_sum, F(5120)), F(eps)))
    check_float_trace(s, t)
    assert equal(s.regs["y"].f32(), np.asarray(r, F))
    n = Machine(recipes["scale"], {"BF16 hc_pre result": bf16_memory(x), "published norm scalar": s.regs["y"], "BF16 norm gain": bf16_memory(gain)}, eps).run()
    with golden_trace() as t:
        expected_scale = G.to_bf16(G.mul(gain, G.mul(x, r)))
    check_float_trace(n, t)
    oldmode = V.ARITH
    try:
        V.ARITH = "chunk8"
        original_norm = V.rmsnorm_bf16(x, gain, F(eps))
    finally:
        V.ARITH = oldmode
    assert equal(n.stored_f32(), expected_scale) and equal(n.stored_f32(), original_norm)
    return {"pre": a, "post": b, "norm_scalar": s, "scale": n}, gain, ordered_sum


def git_blob(repo, path):
    return subprocess.check_output(["git", "show", "HEAD:" + path], cwd=repo)


def calendar(repo):
    raw = git_blob(repo, CALENDAR)
    record = json.loads(raw)
    for p in ("tools/w19_gpu_norm_calendar.py", "tools/w19_gpu_simd_contract.py", "tools/hdc_golden.py", "tools/hdc_golden_v41.py"):
        if sha((repo / p).read_bytes()) != record["source_pins"][p]:
            raise ValueError("calendar source pin mismatch")
    expected = {"pre": C.vector_program("pre"), "post": C.vector_program("post"), "norm_scalar": C.scalar_norm_program(), "scale": C.scale_program()}
    for name, program in expected.items():
        if record["recipes"][name] != program:
            raise ValueError("published recipe differs from current source")
    return record, sha(raw)


def execute(out):
    repo = Path(__file__).resolve().parents[1]
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True).strip():
        raise ValueError("clean committed source required")
    out.mkdir(parents=True, exist_ok=False)
    cal, cal_sha = calendar(repo)
    raw = git_blob(repo, PRODUCER + "/proof.json")
    producer = json.loads(raw)
    if producer["verdict"] != "PASS":
        raise ValueError("retained residual producer not PASS")
    records = []
    for i, fixture in enumerate(producer["fixtures"]):
        name = f"fixture_{i}.npz"
        data = git_blob(repo, PRODUCER + "/" + name)
        if sha(data) != producer["artifacts"][name]:
            raise ValueError("retained fixture hash mismatch")
        with np.load(io.BytesIO(data), allow_pickle=False) as source:
            arrays = {n: source[n].copy() for n in source.files}
        gain = G.to_bf16(np.random.default_rng(190035).normal(loc=1, scale=.25, size=5120).astype(F))
        machines, gain, ordered_sum = phases(cal["recipes"], arrays, gain, 1e-20)
        traces = {phase: [{k: v for k, v in r.items() if k != "value"} for r in vm.trace] for phase, vm in machines.items()}
        (out / f"opcodes_{i}.json").write_text(json.dumps(traces, indent=2) + "\n")
        np.savez_compressed(out / f"outputs_{i}.npz", gain=gain, ordered_sum=ordered_sum, pre=machines["pre"].stored_f32(), post=machines["post"].stored_f32().reshape(4, 5120), norm_scalar=machines["norm_scalar"].regs["y"].f32(), scaled=machines["scale"].stored_f32())
        records.append({"name": fixture["name"], "producer_fixture": name, "producer_sha256": sha(data), "carry_manifest_sha256": fixture["carry_manifest_sha256"], "producer_path": PRODUCER + "/" + name,
                        "gain_disclosure": "seeded synthetic BF16 gain; no actual norm weight trajectory", "eps": 1e-20,
                        "phase_instruction_counts": {p: len(m.trace) for p, m in machines.items()}, "RF_liveness_admission": {p: m.admission for p, m in machines.items()}, "verdict": "PASS"})
    pins = ["tools/w19_norm_opcode_proof.py", "tests/test_w19_norm_opcode_proof.py", "tools/w19_gpu_norm_calendar.py", "tools/w19_gpu_simd_contract.py", "tools/hdc_golden.py", "tools/hdc_golden_v41.py"]
    proof = {"schema": "opentallas.w19.norm-opcode.cpu-proof.v1", "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(), "source_pins": {p: sha((repo / p).read_bytes()) for p in pins}, "calendar_path": CALENDAR, "calendar_sha256": cal_sha, "producer_proof_sha256": sha(raw), "fixtures": records, "verdict": "PASS", "GPU_campaign_launched": False, "physical_qualified": False, "full_token_qualified": False, "rate": None, "adoption": False, "QC_NAM": "unchanged original full FAIL", "scope": "actual pre5120/post20480/normscalar5120/scale5120 opcode execution; ordered norm chunk tree supplied at declared LOAD, collector/transport/warp timing not executed or qualified", "artifacts": {p.name: sha(p.read_bytes()) for p in sorted(out.iterdir())}}
    (out / "proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps({"verdict": "PASS", "fixtures": len(records), "opcode_boundaries": sum(sum(f["phase_instruction_counts"].values()) for f in records), "proof": str(out / "proof.json")}))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    execute(p.parse_args().out)
