"""Driver of the host interface (rtl/host/ot_host_if.sv): rings, doorbells, MSI.

This is the part of the runtime a kernel driver would own.  It lays out the
submission and completion rings and the per-user prompt buffers in host
memory, programs the ring bases, the MSI address and data and the interrupt
mask, writes descriptors and rings the SQ_TAIL doorbell, and consumes
completion entries by their phase bit, returning them through the CQ_HEAD
doorbell.  Formats are the ones documented at the top of ot_host_if.sv.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from runtime.hdc.device import MSI_ADDR, Regs, SimDevice

ID_OTHI = 0x4F54_4849
OP_GENERATE = 1
FLAG_GREEDY, FLAG_STOP_EOS = 1, 2
KIND = {1: "token", 2: "last", 3: "error"}
STATUS = {0: "ok", 1: "eos", 2: "length", 3: "bad_opcode", 4: "unsupported_sampling", 5: "slot_unavailable",
          6: "bad_length", 7: "engine_fault", 8: "dma_error"}

SQ_BASE, SQ_LOG2 = 0x0000, 6            # 64 descriptors of 32 bytes
CQ_BASE, CQ_LOG2 = 0x1000, 8            # 256 entries of 16 bytes
PROMPT_BASE, PROMPT_STRIDE = 0x10000, 0x400


@dataclass
class Completion:
    kind: str
    status: str
    slot: int
    tag: int
    position: int
    token: int
    cycles: int
    generated: int
    device_cycle: int                   # chip cycle at which the driver consumed it


class HostDriver:
    def __init__(self, dev: SimDevice):
        self.dev = dev
        if dev.read32(Regs.ID) != ID_OTHI:
            raise RuntimeError("no OpenTallas host interface at BAR0")
        caps = dev.read32(Regs.CAPS)
        self.slots, self.mode, self.eng_ctx, self.version = (caps & 0xFF, (caps >> 8) & 0xFF, (caps >> 16) & 0xFF,
                                                             caps >> 24)
        self.sq_n, self.cq_n = 1 << SQ_LOG2, 1 << CQ_LOG2
        self.sq_tail = 0
        self.cq_head, self.phase = 0, 1
        self.inflight_desc = 0
        dev.mem_write(0, bytes(PROMPT_BASE + self.slots * PROMPT_STRIDE))
        for off, v in ((Regs.SQ_BASE_LO, SQ_BASE), (Regs.SQ_BASE_HI, 0), (Regs.SQ_LOG2, SQ_LOG2),
                       (Regs.CQ_BASE_LO, CQ_BASE), (Regs.CQ_BASE_HI, 0), (Regs.CQ_LOG2, CQ_LOG2),
                       (Regs.MSI_ADDR_LO, MSI_ADDR), (Regs.MSI_ADDR_HI, 0), (Regs.MSI_DATA, 0x4F54),
                       (Regs.MSI_CTRL, 1), (Regs.IRQ_MASK, 3), (Regs.CTRL, 1)):
            dev.write32(off, v)

    def submit(self, slot: int, tag: int, prompt: list[int], max_new: int, eos: tuple[int, ...] = (),
               flags: int = FLAG_GREEDY) -> None:
        if ((self.sq_tail + 1) % self.sq_n) == self.dev.read32(Regs.SQ_HEAD):
            raise RuntimeError("submission queue full")
        paddr = PROMPT_BASE + slot * PROMPT_STRIDE
        self.dev.mem_write(paddr, struct.pack(f"<{len(prompt)}H", *prompt))
        e = list(eos) + [eos[0] if eos else 0] * 2
        if eos:
            flags |= FLAG_STOP_EOS
        w0 = OP_GENERATE | (flags << 8) | ((tag & 0xFFFF) << 16) | (len(prompt) << 32) | (max_new << 48)
        desc = struct.pack("<QQQQ", w0, paddr, slot, (e[0] & 0xFFFF) | ((e[1] & 0xFFFF) << 16))
        self.dev.mem_write(SQ_BASE + 32 * self.sq_tail, desc)
        self.sq_tail = (self.sq_tail + 1) % self.sq_n
        self.dev.write32(Regs.SQ_TAIL, self.sq_tail)

    def batch_go(self, users: int) -> None:
        self.dev.write32(Regs.BATCH_GO, users)

    def poll(self) -> list[Completion]:
        out = []
        while True:
            w0, w1 = struct.unpack("<QQ", self.dev.mem_read(CQ_BASE + 16 * self.cq_head, 16))
            if (w0 & 1) != self.phase:
                break
            out.append(Completion(kind=KIND.get((w0 >> 1) & 3, "?"), status=STATUS.get((w0 >> 4) & 0xF, "?"),
                                  slot=(w0 >> 8) & 0xFF, tag=(w0 >> 16) & 0xFFFF, position=(w0 >> 32) & 0xFFFF,
                                  token=(w0 >> 48) & 0xFFFF, cycles=w1 & 0xFFFFFFFF,
                                  generated=(w1 >> 32) & 0xFFFF, device_cycle=self.dev.cycle))
            self.cq_head = (self.cq_head + 1) % self.cq_n
            if self.cq_head == 0:
                self.phase ^= 1
        if out:
            self.dev.write32(Regs.CQ_HEAD, self.cq_head)
            self.dev.write32(Regs.IRQ_STATUS, 1)
        return out

    def counters(self) -> dict:
        d = self.dev
        return {"cycles": d.read64(Regs.CYCLES_LO), "engine_busy_cycles": d.read64(Regs.BUSY_LO),
                "tokens": d.read32(Regs.TOKENS), "steps": d.read32(Regs.STEPS),
                "requests": d.read32(Regs.REQS), "msis": d.read32(Regs.MSIS),
                "dma_read_beats": d.read32(Regs.DMA_RD), "dma_write_beats": d.read32(Regs.DMA_WR),
                "cq_full_cycles": d.read32(Regs.CQ_FULL), "status": d.read32(Regs.STATUS)}
