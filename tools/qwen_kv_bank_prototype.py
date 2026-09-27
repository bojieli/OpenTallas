"""Executable Qwen KV write-bank and 32-byte HBM sector prototype.

This is a functional mapping model, not a cycle-closed RTL bridge. Addresses
are the logical element addresses emitted by the shipped vector stream unit.
The bank map stripes dimensions, while tile parity keeps the two K tiles
independent. Physical HBM writes are always full 32-byte sectors.
"""

from dataclasses import dataclass, field


@dataclass
class SectorAssembly:
    """Combine byte writes before a full-sector HBM write or explicit RMW."""

    sector_bytes: int = 32
    pending: dict[int, tuple[bytearray, int]] = field(default_factory=dict)
    memory: dict[int, bytes] = field(default_factory=dict)
    full_writes: int = 0
    rmw_writes: int = 0

    def put(self, byte_address: int, value: int) -> None:
        assert 0 <= value <= 255
        sector, offset = divmod(byte_address, self.sector_bytes)
        data, mask = self.pending.get(sector, (bytearray(self.sector_bytes), 0))
        data[offset] = value
        mask |= 1 << offset
        if mask == (1 << self.sector_bytes) - 1:
            self.memory[sector] = bytes(data)
            self.pending.pop(sector, None)
            self.full_writes += 1
        else:
            self.pending[sector] = (data, mask)

    def drain_partial(self) -> None:
        """Explicit read/modify/write for any sector missing bytes."""
        for sector, (data, mask) in self.pending.items():
            old = bytearray(self.memory.get(sector, bytes(self.sector_bytes)))
            for offset in range(self.sector_bytes):
                if mask & (1 << offset):
                    old[offset] = data[offset]
            self.memory[sector] = bytes(old)
            self.rmw_writes += 1
        self.pending.clear()


@dataclass
class BankedTail:
    """Two tile parities, each with SW independent one-write word banks."""

    sw: int
    width: int = 16
    head_dim: int = 128
    position_tiles: int = 512
    words: dict[tuple[int, int, int], bytearray] = field(default_factory=dict)

    def write_vector(self, writes: list[tuple[int, int]], *, v0_element: int) -> None:
        """Atomically accept one stream-unit beat of (K address, FP8 byte)."""
        assert len(writes) <= self.sw
        occupied: set[tuple[int, int]] = set()
        for address, value in writes:
            assert 0 <= address < v0_element and 0 <= value <= 255
            word, lane = divmod(address, self.width)
            tile_parity = (word // self.head_dim) & 1
            # Dimension-major K layout: adjacent dimensions are adjacent words.
            bank = word % self.sw
            key = (tile_parity, bank)
            if key in occupied:
                raise ValueError(f"two K words target one tail write port: {key}")
            occupied.add(key)
            row = ((word // (self.head_dim * self.position_tiles))
                   * (self.head_dim // self.sw) + (word % self.head_dim) // self.sw)
            dest = self.words.setdefault((tile_parity, bank, row), bytearray(self.width))
            if lane == 0:
                dest[:] = bytes(self.width)  # a new position tile opens
            dest[lane] = value

    def read_word(self, word: int) -> bytes:
        parity = (word // self.head_dim) & 1
        row = ((word // (self.head_dim * self.position_tiles))
               * (self.head_dim // self.sw) + (word % self.head_dim) // self.sw)
        return bytes(self.words.get((parity, word % self.sw, row),
                                    bytearray(self.width)))

    def flush_k_tile(self, first_word: int, sectors: SectorAssembly) -> None:
        """Reassemble one tile's dimension words into full physical sectors."""
        for word in range(first_word, first_word + self.head_dim):
            for lane, value in enumerate(self.read_word(word)):
                sectors.put(word * self.width + lane, value)


def k_element(layer: int, head: int, position: int, dimension: int, *,
              kv_heads: int, position_tiles: int, head_dim: int = 128,
              width: int = 16) -> int:
    """The address equation of tools/hdc_program.py:Layout.k_elem."""
    return (((layer * kv_heads + head) * position_tiles + position // width)
            * head_dim + dimension) * width + position % width


def v_element(layer: int, head: int, position: int, dimension: int, *,
              v0_element: int, kv_heads: int, max_positions: int,
              head_dim: int = 128) -> int:
    """The address equation of tools/hdc_program.py:Layout.v_elem."""
    return v0_element + ((layer * kv_heads + head) * max_positions + position) * head_dim + dimension
