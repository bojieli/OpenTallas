"""Proposed OpenTallas V4.1 four-die/four-stack compressed-KV placement v1.

This is an executable address and ownership contract, not a vendor DMA layout
or a claim that the current reduced HDC can read these compressed rows.
"""

from dataclasses import dataclass

from .v41_main_kv_row import ROW_BYTES as MAIN_BYTES, parse_main_row
from .v41_aux_kv_rows import INDEX_ROW_BYTES, WINDOW_ROW_BYTES, parse_index_row, parse_window_row


PROFILE = "opentallas.deepseek_v41.hbm_kv_4die_4stack.v2"
DIES = STACKS = 4
GROUP = 16
SECTOR = 32
INDEX_BLOCK = 4096
INDEX_KEYS_PER_SUPERBLOCK = 1024
INDEX_SUPERBLOCK_BYTES = 17 * INDEX_BLOCK
WINDOW_SLOTS = 128
MAX_CONTEXT = 1_048_576
STACK_CAPACITY_BYTES = 22_500_000_000  # configs/hardware/technology.json hbm3e
OWNERS = (2, 8, 14, 20)
RATIOS = {2: 2, 8: 2, 14: 2, 20: 1}
LAYERS = 40


def _pitch(size):
    return ((size + SECTOR - 1) // SECTOR) * SECTOR


def _align(size, alignment):
    return ((size + alignment - 1) // alignment) * alignment


@dataclass(frozen=True)
class Region:
    die: int
    stack: int
    role: str
    owner: int
    base: int
    rows: int
    pitch: int

    @property
    def end(self):
        if self.role == "index":
            return self.base + ((self.rows + INDEX_KEYS_PER_SUPERBLOCK - 1) // INDEX_KEYS_PER_SUPERBLOCK) * INDEX_SUPERBLOCK_BYTES
        return self.base + self.rows * self.pitch


@dataclass(frozen=True)
class Address:
    """A row address; for index keys, byte is the 64-B code start, scale_byte
    is the separate 4-B scale start, size is the 68-B logical record and pitch
    is zero because the records are not linearly strided in HBM.
    """
    die: int
    stack: int
    byte: int
    size: int
    pitch: int
    role: str
    owner: int
    row: int
    scale_byte: int | None = None  # index keys: four scales live in block 0


class Placement:
    def __init__(self, max_context=MAX_CONTEXT, stack_capacity_bytes=STACK_CAPACITY_BYTES,
                 owners=OWNERS, window_layers=range(LAYERS)):
        if max_context <= 0 or max_context % (DIES * STACKS * GROUP):
            raise ValueError("max_context must be a positive multiple of 256")
        if stack_capacity_bytes <= 0:
            raise ValueError("stack capacity must be positive")
        self.owners = tuple(owners)
        self.window_layers = tuple(window_layers)
        if len(set(self.owners)) != len(self.owners) or any(o not in OWNERS for o in self.owners):
            raise ValueError("invalid or duplicate compressed owner")
        if len(set(self.window_layers)) != len(self.window_layers) or any(not 0 <= l < LAYERS for l in self.window_layers):
            raise ValueError("invalid or duplicate window layer")
        self.max_context = max_context
        self.stack_capacity_bytes = stack_capacity_bytes
        self.regions = {}
        self.used_bytes = {}
        for die in range(DIES):
            for stack in range(STACKS):
                base = 0
                for owner in self.owners:
                    rows = max_context // RATIOS[owner] // (DIES * STACKS)
                    for role, size in (("main", MAIN_BYTES), ("index", INDEX_ROW_BYTES)):
                        if role == "index":
                            base = _align(base, INDEX_BLOCK)
                        region = Region(die, stack, role, owner, base, rows,
                                        0 if role == "index" else _pitch(size))
                        self.regions[(die, stack, role, owner)] = region
                        base = region.end
                # All four dies hold their own window state. Layer l is assigned
                # to stack l mod 4, so each stack holds ten layer rings per die.
                for layer in self.window_layers:
                    if layer % STACKS == stack:
                        region = Region(die, stack, "window", layer, base, WINDOW_SLOTS, _pitch(WINDOW_ROW_BYTES))
                        self.regions[(die, stack, "window", layer)] = region
                        base = region.end
                if base > stack_capacity_bytes:
                    raise ValueError(f"die {die} stack {stack} needs {base} bytes, capacity {stack_capacity_bytes}")
                self.used_bytes[(die, stack)] = base

    @staticmethod
    def owner_for_layer(layer):
        if not 0 <= layer < LAYERS:
            raise ValueError("layer is outside 0..39")
        return max((owner for owner in OWNERS if owner <= layer), default=None)

    def compressed(self, role, owner, row):
        if role not in ("main", "index") or owner not in self.owners:
            raise ValueError("compressed role or owner is invalid")
        limit = self.max_context // RATIOS[owner]
        if not 0 <= row < limit:
            raise ValueError("compressed row outside owner capacity")
        group = row // GROUP
        die = group % DIES
        stack = (group // DIES) % STACKS
        local_group = group // (DIES * STACKS)
        local_row = local_group * GROUP + row % GROUP
        region = self.regions[(die, stack, role, owner)]
        assert local_row < region.rows
        if role == "index":
            superblock, key = divmod(local_row, INDEX_KEYS_PER_SUPERBLOCK)
            block = region.base + superblock * INDEX_SUPERBLOCK_BYTES
            code = block + (1 + key // 64) * INDEX_BLOCK + (key % 64) * 64
            scale = block + key * 4
            return Address(die, stack, code, INDEX_ROW_BYTES, 0, role, owner, row, scale)
        return Address(die, stack, region.base + local_row * region.pitch,
                       MAIN_BYTES, region.pitch, role, owner, row)

    def window(self, layer, position, die):
        if layer not in self.window_layers or not 0 <= position < self.max_context or not 0 <= die < DIES:
            raise ValueError("invalid window layer, position, or die")
        stack = layer % STACKS
        region = self.regions[(die, stack, "window", layer)]
        slot = position % WINDOW_SLOTS
        return Address(die, stack, region.base + slot * region.pitch,
                       WINDOW_ROW_BYTES, region.pitch, "window", layer, position)

    @staticmethod
    def read_convert(role, row):
        """Main yields FP8 codes; index/window yield exact scaled values."""
        if role == "main":
            return parse_main_row(row).fp8_codes
        if role == "index":
            return parse_index_row(row).exact_values
        if role == "window":
            return parse_window_row(row).exact_values
        raise ValueError("unknown KV role")


class SparseHBM:
    """Small logical ingest model; tags prevent stale ring reads after rollover."""

    def __init__(self, placement):
        self.placement = placement
        self.rows = {}  # (die, stack, address) -> bytes
        self.window_tags = {}  # (die, layer, slot) -> absolute position

    def write_compressed(self, role, owner, row, data):
        address = self.placement.compressed(role, owner, row)
        self.placement.read_convert(role, data)  # validate before committing
        if role == "index":
            self.rows[(address.die, address.stack, address.byte)] = data[:64]
            self.rows[(address.die, address.stack, address.scale_byte)] = data[64:68]
        else:
            self.rows[(address.die, address.stack, address.byte)] = data
        return address

    def read_compressed(self, role, reader_layer, row):
        owner = self.placement.owner_for_layer(reader_layer)
        if owner is None:
            raise ValueError("pure window layer has no compressed cache")
        address = self.placement.compressed(role, owner, row)
        data = self.rows[(address.die, address.stack, address.byte)]
        if role == "index":
            data += self.rows[(address.die, address.stack, address.scale_byte)]
        return self.placement.read_convert(role, data)

    def write_window(self, layer, position, data):
        self.placement.read_convert("window", data)
        addresses = []
        for die in range(DIES):
            address = self.placement.window(layer, position, die)
            self.rows[(die, address.stack, address.byte)] = data
            self.window_tags[(die, layer, position % WINDOW_SLOTS)] = position
            addresses.append(address)
        return addresses

    def read_window(self, layer, position, die):
        address = self.placement.window(layer, position, die)
        if self.window_tags.get((die, layer, position % WINDOW_SLOTS)) != position:
            raise ValueError("window slot is stale or unwritten")
        return self.placement.read_convert("window", self.rows[(die, address.stack, address.byte)])
