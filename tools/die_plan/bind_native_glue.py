"""Opt-in faithful SV helpers emitted by the native Yosys backend.

Retain inferred memories as arrays. Never run memory_map, async2sync, opt,
or clock rewrites here. These helpers remove an RTL emission gap; they do
not qualify reset timing, physical memories, or a plan boundary.
"""
from contextlib import contextmanager, ExitStack
import fcntl
import hashlib
import json
import os
import re
import tempfile
import uuid
from pathlib import Path
import bind_elab as E
from native_mem2reg import mark_mem2reg
from native_memwr_merge import merge_memwr

# $mem_v2 / $shiftx (Codex 861); TOK-SCHED 10-25 adds the remaining combinational word-level primitives that the
# current S81 dissolved parents (ot_s81sl_vp, dsdv_svc_att, dsdv_svc_rs_c, ot_hdc_v41x_attn_s) carry and _glue does not
# re-emit: Yosys write_verilog prints each one with its own documented semantics; nothing is mapped or optimised.
SUPPORTED = {"$mem_v2", "$shiftx", "$shift", "$demux", "$bwmux", "$bmux", "$pmux", "$div", "$mod"}

class NativeGlueError(RuntimeError):
    pass

class NativeGlue:
    """Collect one type per pinned container with OT_BIND_NATIVE_GLUE_BATCH=1.

    Explicit native Yosys and ordinary immediate emission keep their existing
    paths. Helper receipts can be shared only by workers of this binder.
    """

    def __init__(self, directory, enabled):
        if not isinstance(enabled, list) or any(t not in SUPPORTED for t in enabled):
            raise NativeGlueError("native_glue_types must name only " + ", ".join(sorted(SUPPORTED)))
        self.enabled = set(enabled)
        self.directory = Path(directory).resolve()
        self.files = []
        self.cache = {}
        self._pending = None
        self._batch_image = (E.yosys_image_id() if os.environ.get("OT_BIND_NATIVE_GLUE_BATCH") == "1"
                             and not os.environ.get("OT_BIND_YOSYS") else None)
        self._batch_id = uuid.uuid4().hex if self._batch_image else None
        self._merge_memwr = os.environ.get("OT_NATIVE_MEMWR_MERGE", "1") != "0"

    @contextmanager
    def batch(self):
        if not self._batch_image:
            yield
            return
        self._pending = {}
        try:
            yield
            self._flush()
        finally:
            self._pending = None

    @staticmethod
    def _script(inp, sv, primitive):
        lower = {"$bwmux": "bwmuxmap\n", "$demux": "demuxmap\n", "$bmux": "bmuxmap\n"}.get(primitive, "")
        return f'read_json "{inp}"\n{lower}write_verilog -noattr "{sv}"\n'

    def _postprocess(self, sv, primitive):
        if primitive != "$mem_v2":
            return
        # Decide mem2reg from the original per-bit writes, then merge the runs.
        text, marked = mark_mem2reg(sv.read_text())
        merged = []
        merge = (self._merge_memwr if self._batch_image else os.environ.get("OT_NATIVE_MEMWR_MERGE", "1") != "0")
        if merge:
            text, merged = merge_memwr(text)
        if merged:
            sv.with_suffix(".memwr_merge.txt").write_text("".join(f"{m} {b} -> {a}\n" for m, b, a in merged))
        if marked or merged:
            sv.write_text(text)

    @staticmethod
    def _write_input(handle, text):
        handle.truncate(0)
        handle.write(text)
        handle.flush()

    def _flush(self):
        if not self._pending:
            return
        with ExitStack() as stack:
            tmp = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix=".batch-", dir=self.directory)))
            pending = []
            for module, (primitive, data) in sorted(self._pending.items()):
                inp = self.directory / (module + ".json")
                lock = stack.enter_context(inp.open("a"))
                fcntl.flock(lock, fcntl.LOCK_EX)
                sv = inp.with_suffix(".sv")
                # Only a successful sibling in this forked binder may satisfy a helper.
                marker = inp.with_suffix(".batch")
                text = json.dumps(data)
                key = self._batch_id + " " + hashlib.sha256(text.encode()).hexdigest() + " "
                if marker.is_file() and sv.is_file() and marker.read_bytes() == (
                        key + hashlib.sha256(sv.read_bytes()).hexdigest()).encode():
                    continue
                self._write_input(lock, text)
                script, log = tmp / (module + ".ys"), tmp / (module + ".log")
                script.write_text(self._script(inp, tmp / sv.name, primitive))
                pending.append((inp, sv, script, log, marker, primitive, key))
            if pending:
                try:
                    E.run_yosys_batch([(s, l) for _, _, s, l, _, _, _ in pending],
                                      [self.directory], self._batch_image)
                except E.ElabError as exc:
                    raise NativeGlueError(str(exc)) from exc
            for _, sv, _, log, _, primitive, _ in pending:
                staged = tmp / sv.name
                if not staged.is_file() or not staged.stat().st_size or not log.is_file():
                    raise NativeGlueError(f"native glue batch did not emit {sv.name} and its log")
                self._postprocess(staged, primitive)
            for inp, sv, _, log, marker, primitive, key in pending:
                staged = tmp / sv.name
                inp.with_suffix(".ys").write_text(self._script(inp, sv, primitive))
                os.replace(log, sv.with_suffix(".log"))
                detail = staged.with_suffix(".memwr_merge.txt")
                if detail.is_file():
                    os.replace(detail, sv.with_suffix(".memwr_merge.txt"))
                digest = hashlib.sha256(staged.read_bytes()).hexdigest()
                os.replace(staged, sv)
                stamp = tmp / marker.name
                stamp.write_text(key + digest)
                os.replace(stamp, marker)
        for module in self._pending:
            self.cache[module.removeprefix("ot_bind_native_")] = module
            self.files.append(self.directory / (module + ".sv"))

    def emit(self, cell, connections, instance):
        if cell.ytype not in self.enabled:
            raise NativeGlueError("primitive is not explicitly enabled")
        params = dict(cell.yparams)
        # MEMID names the private array, not external state. Each helper instance
        # owns a distinct array; normalize its local name to share identical RTL.
        if cell.ytype == "$mem_v2":
            params["MEMID"] = "\\\\native_memory"
        widths = {p: len(b) for p, b in sorted(cell.ports.items())}
        dirs = {p: cell.dirs.get(p) for p in widths}
        if any(d not in ("input", "output") for d in dirs.values()):
            raise NativeGlueError("native glue requires explicit input/output directions")
        if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", p) for p in widths):
            raise NativeGlueError("unsupported native glue port identifier")
        constants = {p: [b if isinstance(b, str) else None for b in cell.ports[p]] for p in widths}
        exposed = {p for p in widths if any(b is None for b in constants[p])}
        # TOK-SCHED 10-25: input bits that are the SAME design net (e.g. the one clock of several write ports,
        # WR_CLK [2, 2]) must stay one net inside the helper too; otherwise Yosys sees distinct write clocks with a
        # priority relation (mem.cc assert port.clk == wport.clk) and the helper would not be faithful anyway.
        first, share = {}, {}
        for p in widths:
            if dirs[p] != "input":
                continue
            for i, b in enumerate(cell.ports[p]):
                if isinstance(b, str):
                    continue
                if b in first:
                    share[(p, i)] = first[b]
                else:
                    first[b] = (p, i)
        signature = json.dumps([cell.ytype, params, widths, dirs, constants,
                                sorted([list(k) + list(v) for k, v in share.items()])], sort_keys=True)
        key = hashlib.sha256(signature.encode()).hexdigest()[:24]
        module = "ot_bind_native_" + key
        if key not in self.cache and (self._pending is None or module not in self._pending):
            self.directory.mkdir(parents=True, exist_ok=True)
            ports, conns, next_bit, allbits = {}, {}, 2, {}
            for p, width in widths.items():
                bits = list(range(next_bit, next_bit + width))
                next_bit += width
                allbits[p] = bits
            for p, width in widths.items():
                bits = allbits[p]
                # Native memory validation requires static async-read enables,
                # reset values, and unused clocks to remain literal, not ports.
                inner = [allbits[share[(p, i)][0]][share[(p, i)][1]] if (p, i) in share else b
                         for i, b in enumerate(bits)]
                conns[p] = [c if c is not None else b for b, c in zip(inner, constants[p])]
                if width and p in exposed:
                    ports[p] = {"direction": dirs[p], "bits": bits}
            data = {"modules": {module: {
                "attributes": {}, "ports": ports, "netnames": {},
                "cells": {"primitive": {"hide_name": 0, "type": cell.ytype,
                    "parameters": params, "attributes": {},
                    "port_directions": dirs, "connections": conns}}
            }}}
            inp = self.directory / (module + ".json")
            sv = self.directory / (module + ".sv")
            ys = self.directory / (module + ".ys")
            # All paths are generated below the output directory; reject names
            # that cannot be represented by Yosys's quoted filename syntax.
            if any('"' in str(p) or "\n" in str(p) for p in (inp, sv)):
                raise NativeGlueError("invalid native glue output path")
            if self._pending is not None:
                self._pending[module] = cell.ytype, data
            else:
                # Keep the original input inode locked across generation and memory postprocessing.
                with inp.open("a") as input_file:
                    fcntl.flock(input_file, fcntl.LOCK_EX)
                    self._write_input(input_file, json.dumps(data))
                    ys.write_text(self._script(inp, sv, cell.ytype))
                    try:
                        E.run_yosys(ys, self.directory / (module + ".log"),
                                    [self.directory], mem_gb=2)
                    except E.ElabError as exc:
                        raise NativeGlueError(str(exc)) from exc
                    self._postprocess(sv, cell.ytype)
                self.cache[key] = module
                self.files.append(sv)
        actual = [f".{p}({connections[p]})" for p, width in widths.items() if width and p in exposed]
        return f"    {module} {instance} (" + ", ".join(actual) + ");"
