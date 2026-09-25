"""Runtime of the hardwired decode chips: sessions, user slots, token streams.

``HdcRuntime(target)`` builds (or reuses) the Verilated chip and the model's
program/ROM images, opens the device, and runs one pump thread that owns it:
the thread assigns requests to user-context slots, submits them through the
host interface's submission ring, clocks the chip until an interrupt, and
routes each completion entry -- one per generated token -- to the request's
stream.  Callers get a ``Request`` whose ``tokens()`` iterator yields ids as
the chip produces them.

Scheduling follows the engine (``Target.mode``):
* step engines (one decode core): a request takes any free slot and is
  submitted at once; the chip interleaves running slots step by step, or --
  for engines holding one user's state -- runs them one after another;
* the ROM array: the package controllers run a batch of users with one prompt
  and generation length, so the pump groups waiting requests of equal
  lengths into slots 0..n-1 and starts them together with BATCH_GO.

Counters: the chip's own (cycles, engine busy cycles, tokens, steps, MSIs,
DMA beats) and, per request, the chip cycles from submission to its last
token.  Seconds and tokens/s are those cycles at the modelled clock: the
slowest routed block of the target's decode engine (``Target.modelled_clock``).
"""

from __future__ import annotations

import itertools
import queue
import threading
import time
from dataclasses import dataclass, field

from runtime.hdc.build import build_chip, build_images
from runtime.hdc.device import SimDevice
from runtime.hdc.driver import HostDriver
from runtime.hdc.targets import TARGETS, Target


@dataclass
class Request:
    prompt: list[int]
    max_new: int
    stop_eos: bool = True
    tag: int = 0
    slot: int = -1
    submit_cycle: int = 0
    tokens_out: list[int] = field(default_factory=list)
    step_cycles: list[int] = field(default_factory=list)
    token_cycles: list[int] = field(default_factory=list)   # chip cycle at which each token was consumed
    status: str = ""
    done_cycle: int = 0
    _q: queue.Queue = field(default_factory=queue.Queue)
    _done: threading.Event = field(default_factory=threading.Event)

    def tokens(self, timeout: float | None = None):
        """Yield generated token ids as the chip streams them."""
        while True:
            item = self._q.get(timeout=timeout)
            if item is None:
                return
            yield item

    def result(self, timeout: float | None = None) -> "Request":
        if not self._done.wait(timeout):
            raise TimeoutError("request did not finish")
        return self

    @property
    def cycles(self) -> int:
        return self.done_cycle - self.submit_cycle


class HdcRuntime:
    def __init__(self, target: str | Target, clock_hz: float | None = None, dma_latency: int = 64,
                 chunk_cycles: int = 20000):
        self.target = TARGETS[target] if isinstance(target, str) else target
        clk = self.target.modelled_clock()
        self.clock_hz = clock_hz or clk["hz"]
        self.clock_source = "override" if clock_hz else clk
        self.exe = build_chip(self.target)
        self.images = build_images(self.target)
        self.dev = SimDevice(self.exe, self.images, dma_latency=dma_latency)
        self.drv = HostDriver(self.dev)
        self.chunk = chunk_cycles
        self._pending: queue.Queue[Request] = queue.Queue()
        self._waiting: list[Request] = []
        self._active: dict[int, Request] = {}
        self._tags = itertools.count(1)
        self._stop = threading.Event()
        self._err: BaseException | None = None
        self.wall_seconds = 0.0
        self._thread = threading.Thread(target=self._pump, name=f"hdc-{self.target.name}", daemon=True)
        self._thread.start()

    # -- API ---------------------------------------------------------------------------
    def submit(self, prompt: list[int], max_new: int, stop_eos: bool = True) -> Request:
        if self._err:
            raise RuntimeError("device pump failed") from self._err
        if not prompt or max_new < 1:
            raise ValueError("need a non-empty prompt and max_new >= 1")
        if len(prompt) + max_new - 1 > self.target.ctx_max:
            raise ValueError(f"prompt ({len(prompt)}) + max_new ({max_new}) - 1 exceeds the "
                             f"{self.target.ctx_max} positions of a user context")
        if any(not 0 <= t < self.target.vocab for t in prompt):
            raise ValueError("token id outside the model's vocabulary")
        r = Request(prompt=list(prompt), max_new=max_new, stop_eos=stop_eos, tag=next(self._tags) & 0xFFFF)
        self._pending.put(r)
        return r

    def generate(self, prompt: list[int], max_new: int, stop_eos: bool = True, timeout: float | None = None):
        return self.submit(prompt, max_new, stop_eos).result(timeout)

    def counters(self) -> dict:
        done = threading.Event()
        box = {}

        def read():
            if not self._active:                 # let posted writes (the last MSI) complete
                self.dev.wait_irq(4 * 256)
            box["c"] = self.drv.counters()
            done.set()
        self._pending.put(read)          # device access belongs to the pump thread
        done.wait(60)
        c = box.get("c", {})
        if c:
            secs = c["cycles"] / self.clock_hz
            c["modelled_seconds"] = secs
            c["modelled_tokens_per_second"] = c["tokens"] / secs if secs else 0.0
            c["clock_hz"] = self.clock_hz
            c["wall_seconds_simulating"] = round(self.wall_seconds, 3)
        return c

    def request_stats(self, r: Request) -> dict:
        secs = r.cycles / self.clock_hz
        return {"target": self.target.name, "model": self.target.model_id, "slot": r.slot,
                "prompt_tokens": len(r.prompt), "generated_tokens": len(r.tokens_out), "token_ids": r.tokens_out,
                "status": r.status, "chip_cycles": r.cycles, "step_cycles": r.step_cycles,
                "clock_hz": self.clock_hz, "modelled_seconds": secs,
                "modelled_tokens_per_second": len(r.tokens_out) / secs if secs else 0.0,
                # step engines: engine cycles of each decode step; the array: cycles between the user's tokens
                "modelled_decode_tokens_per_second": (self.clock_hz * len(r.step_cycles) / sum(r.step_cycles)
                                                      if r.step_cycles and sum(r.step_cycles) else 0.0)}

    def close(self) -> None:
        self._stop.set()
        self._pending.put(None)
        self._thread.join(timeout=30)
        self.dev.close()

    # -- pump --------------------------------------------------------------------------
    def _pump(self) -> None:
        try:
            while not self._stop.is_set():
                self._take_pending(block=not self._active and not self._waiting)
                self._schedule()
                if self._active:
                    t0 = time.time()
                    self.dev.wait_irq(self.chunk)
                    self.wall_seconds += time.time() - t0
                    for c in self.drv.poll():
                        self._complete(c)
        except BaseException as e:            # surface to callers
            self._err = e
            for r in list(self._active.values()) + self._waiting:
                r.status = f"error: {e}"
                r._q.put(None)
                r._done.set()

    def _take_pending(self, block: bool) -> None:
        try:
            item = self._pending.get(timeout=0.5) if block else self._pending.get_nowait()
        except queue.Empty:
            return
        while True:
            if item is None:
                return
            if callable(item):
                item()
            else:
                self._waiting.append(item)
            try:
                item = self._pending.get_nowait()
            except queue.Empty:
                return

    def _schedule(self) -> None:
        eos = self.target.eos
        if self.target.mode == 0:
            free = [s for s in range(self.drv.slots) if s not in self._active]
            while self._waiting and free:
                r = self._waiting.pop(0)
                r.slot = free.pop(0)
                r.submit_cycle = self.dev.cycle
                self._active[r.slot] = r
                self.drv.submit(r.slot, r.tag, r.prompt, r.max_new, eos if r.stop_eos else ())
            return
        # ROM array: one batch at a time, equal lengths, slots 0..n-1
        if self._active or not self._waiting:
            return
        key = (len(self._waiting[0].prompt), self._waiting[0].max_new)
        batch = [r for r in self._waiting if (len(r.prompt), r.max_new) == key][:self.drv.slots]
        for s, r in enumerate(batch):
            self._waiting.remove(r)
            r.slot = s
            r.submit_cycle = self.dev.cycle
            self._active[s] = r
            self.drv.submit(s, r.tag, r.prompt, r.max_new, eos if r.stop_eos else ())
        # every slot must be loaded (descriptor fetched and prompt DMA'd: slot state RUN)
        # before the batch starts, or BATCH_GO is refused
        while any(self.dev.read32(0x100 + 8 * s) & 3 != 1 for s in range(len(batch))):
            self.dev.wait_irq(256)
        self.drv.batch_go(len(batch))
        if (self.dev.read32(0x050) >> 10) & 3:
            raise RuntimeError("BATCH_GO refused by the host interface")

    def _complete(self, c) -> None:
        r = self._active.get(c.slot)
        if r is None or r.tag != c.tag:
            return
        if c.kind in ("token", "last"):
            r.tokens_out.append(c.token)
            r.step_cycles.append(c.cycles)
            r.token_cycles.append(c.device_cycle)
            r._q.put(c.token)
        if c.kind in ("last", "error"):
            r.status = c.status
            r.done_cycle = c.device_cycle
            del self._active[c.slot]
            r._q.put(None)
            r._done.set()
