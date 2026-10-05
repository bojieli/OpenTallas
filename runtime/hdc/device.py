"""The simulated chip as a device: its register BAR, host memory, interrupts.

``SimDevice`` starts the Verilated chip (rtl/test/host_bridge_harness.cpp
around a tb_host_*.sv top) with a host-memory file mapped into both
processes.  The runtime then does what a kernel driver does with a PCIe
function: 32-bit register reads and writes of BAR0, DMA buffers carved out
of pinned host memory, and waiting for message-signalled interrupts.  Time
moves only while the device is waited on (``wait_irq``), so every cycle the
simulation runs is a cycle of the modelled chip.
"""

from __future__ import annotations

import mmap
import os
import subprocess
import tempfile
import threading
from pathlib import Path

MSI_ADDR = 0xFEE0_0000          # interrupt-controller window of the host bridge


class Regs:
    """ot_host_if register offsets (rtl/host/ot_host_if.sv)."""
    ID, CAPS, CTRL, STATUS = 0x000, 0x004, 0x008, 0x00C
    SQ_BASE_LO, SQ_BASE_HI, SQ_LOG2, SQ_TAIL, SQ_HEAD = 0x010, 0x014, 0x018, 0x01C, 0x020
    CQ_BASE_LO, CQ_BASE_HI, CQ_LOG2, CQ_HEAD, CQ_TAIL = 0x024, 0x028, 0x02C, 0x030, 0x034
    IRQ_STATUS, IRQ_MASK = 0x038, 0x03C
    MSI_ADDR_LO, MSI_ADDR_HI, MSI_DATA, MSI_CTRL = 0x040, 0x044, 0x048, 0x04C
    BATCH_GO = 0x050
    CYCLES_LO, CYCLES_HI, BUSY_LO, BUSY_HI = 0x060, 0x064, 0x068, 0x06C
    TOKENS, STEPS, REQS, MSIS, DMA_RD, DMA_WR, CQ_FULL = 0x070, 0x074, 0x078, 0x07C, 0x080, 0x084, 0x088
    SLOT = 0x100                 # + 8 * slot


class SimDevice:
    def __init__(self, exe: Path, image_dir: Path, mem_bytes: int = 1 << 20, dma_latency: int = 64,
                 extra_args: tuple[str, ...] = ()):
        self.mem_bytes = mem_bytes
        fd, self._mem_path = tempfile.mkstemp(prefix="ot_hostmem_", dir="/dev/shm" if os.path.isdir("/dev/shm") else None)
        os.ftruncate(fd, mem_bytes)
        self.mem = mmap.mmap(fd, mem_bytes)
        os.close(fd)
        self._lock = threading.Lock()
        self.proc = subprocess.Popen(
            [str(exe), f"+DIR={image_dir}", f"+HOSTMEM={self._mem_path}", f"+HOSTMEM_BYTES={mem_bytes}",
             f"+DMA_LAT={dma_latency}", *extra_args],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        line = self.proc.stdout.readline()
        if not line.startswith("ready"):
            raise RuntimeError(f"device did not start: {line!r}")
        self.cycle = int(line.split()[1])

    def _cmd(self, text: str) -> list[str]:
        with self._lock:
            self.proc.stdin.write(text + "\n")
            self.proc.stdin.flush()
            line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("device exited")
        return line.split()

    # -- BAR0 ---------------------------------------------------------------------------
    def write32(self, off: int, value: int) -> None:
        r = self._cmd(f"w {off:#x} {value & 0xFFFFFFFF:#x}")
        self.cycle = int(r[1])

    def read32(self, off: int) -> int:
        r = self._cmd(f"r {off:#x}")
        self.cycle = int(r[1])
        return int(r[0])

    def read64(self, off_lo: int) -> int:
        return self.read32(off_lo) | (self.read32(off_lo + 4) << 32)

    # -- interrupts ---------------------------------------------------------------------------
    def wait_irq(self, max_cycles: int) -> bool:
        """Clock the chip until an MSI arrives (True) or max_cycles pass."""
        r = self._cmd(f"run {max_cycles}")
        self.cycle = int(r[-1])
        return r[0] == "msi"

    # -- host memory --------------------------------------------------------------------------
    def mem_write(self, addr: int, data: bytes) -> None:
        self.mem[addr:addr + len(data)] = data

    def mem_read(self, addr: int, n: int) -> bytes:
        return bytes(self.mem[addr:addr + n])

    def close(self) -> None:
        if self.proc.poll() is None:
            try:
                self._cmd("quit")
            except Exception:
                pass
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        try:
            self.mem.close()
        except Exception:
            pass
        try:
            os.unlink(self._mem_path)
        except OSError:
            pass
