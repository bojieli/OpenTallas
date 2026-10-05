#!/usr/bin/env python3
"""Build the DMA.NGRAM_HASH (ABI 3.0 sub-opcode 0x04) RTL vector set.

Every expected value comes from `runtime.reference.engram.ngram_row_ids`, which
is written from the pinned `inference/engram.py` semantics and knows nothing
about the RTL.  This tool only arranges inputs and serializes the reference's
answers; it never computes a row id itself.

The authentic V4.1-Flash Engram layout is DERIVED here and CHECKED against the
released table extents: the per-(order, head) bucket primes are the successive
primes above `engram_vocab_size - 1`, drawn in order and never reused, and each
layer's 24 primes must sum to that layer's `engram_num_embeddings` -- 384,006,168
for layer 1 and 384,016,682 for layer 14 (SRC-DSV41-FLASH-CONFIG).  That sum is
the proof that the moduli, offsets and column order in these vectors are the
released ones and not an invention; the build fails if it does not hold.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.reference.engram import ngram_row_ids  # noqa: E402

DEFAULT_OUTPUT = ROOT / "testdata/rtl/a3_v41_ngram_hash"

#: SRC-DSV41-FLASH-CONFIG, revision dba1be0a40aa45a94ad051997016db3960a90277,
#: config.json SHA-256 8be45ce0476004a3f529fd896115a4a2e800a129ad2d3ec05b16050f52e21879
#: (the same digest `data/inventory/deepseek-v4.1-flash.json` records as
#: `config_sha256`, which is how these literals are bound to the release).
PINNED_CONFIG = {
    "engram_layer_ids": (1, 14),
    "engram_num_embeddings": (384006168, 384016682),
    "engram_max_ngram_size": 4,
    "engram_vocab_size": 16000000,
    "engram_n_heads": 8,
    "engram_head_dim": 256,
    "engram_pad_token_id": 2,
    "engram_compressed_vocab_size": 99092,
}
PINNED_CONFIG_SHA256 = "8be45ce0476004a3f529fd896115a4a2e800a129ad2d3ec05b16050f52e21879"
PINNED_ENGRAM_SOURCE_SHA256 = (
    "11f35ecbead8150c35aa002b3d180ef290b05a25afe883a11884f94d476d3897"
)

#: `compute_hash_multipliers` in the pinned source draws one multiplier per
#: (layer, look-back) from `numpy.random.default_rng(10007 * layer_id)`, bounded
#: by ((2**63 - 1) // compressed_vocab_size) // 2 and forced odd.  The values are
#: pinned here so the vector set does not depend on a NumPy stream; when NumPy is
#: importable the build RE-DERIVES them and fails on any difference.
PINNED_MULTIPLIERS = {
    1: (76632096046245, 4839876093313, 35959672319349, 73987337458391),
    14: (67716810739261, 51510806800915, 30921347202721, 82619226485591),
}

# RTL parameter defaults this vector set is built for.  The testbench checks each
# against the file header and against the device's own info_num_columns, so a
# parameter change cannot silently reduce coverage.
ID_W = 32
MULT_W = 48
MOD_W = 32
ROW_W = 32
DIVIDEND_W = 63
ORDER_MIN = 2
ORDER_MAX = 4
NUM_HEADS = 8
NUM_COLS = (ORDER_MAX - ORDER_MIN + 1) * NUM_HEADS

MAGIC = 0x4E474831
CASE_WORDS = 16
CONFIG_HEADER_WORDS = 8
FILE_HEADER_WORDS = 8

#: Refusal codes of rtl/abi3/ot_a3_dma_ngram_hash.sv.  They are an interface
#: contract of the block, not reference semantics, so they live here and the
#: reference only says whether a case is inside its contract at all.
RF_NONE = 0
RF_ORDER = 1
RF_HEAD = 2
RF_ID = 3
RF_PRODUCT = 4
RF_COLUMN = 5

CE_NONE = 0
CE_SCALAR = 4
CE_COLUMN = 5

POISON = 0xDEADBEEF

#: rtl/test/tb_a3_v41_ngram_hash.sv replays this many of the first
#: configuration's cases through its operand-write-guard phase, twice.  It is a
#: bench structure, published in the manifest so the campaign can predict the
#: exact output and refusal census rather than trusting the bench's own count.
BENCH_WRITE_GUARD_PREFIX = 8


def is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    factor = 3
    while factor * factor <= value:
        if value % factor == 0:
            return False
        factor += 2
    return True


def next_prime(start: int, seen: set[int]) -> int:
    candidate = start + 1
    while not is_prime(candidate) or candidate in seen:
        candidate += 1
    return candidate


def released_layout() -> dict[str, Any]:
    """Derive the released per-column primes, offsets and multipliers.

    Mirrors `EngramLayout.from_args` and `compute_hash_multipliers` of the pinned
    source: for every layer, for every n-gram size, draw `n_heads` successive
    unused primes above `engram_vocab_size - 1`; the offsets are the prefix sums
    over the ngram-major/head-minor flattening.
    """

    heads = PINNED_CONFIG["engram_n_heads"]
    max_ngram = PINNED_CONFIG["engram_max_ngram_size"]
    seen: set[int] = set()
    layers: list[dict[str, Any]] = []
    for index, layer_id in enumerate(PINNED_CONFIG["engram_layer_ids"]):
        rows: list[tuple[int, ...]] = []
        for _ in range(max_ngram - 1):
            sizes: list[int] = []
            current = PINNED_CONFIG["engram_vocab_size"] - 1
            for _ in range(heads):
                current = next_prime(current, seen)
                seen.add(current)
                sizes.append(current)
            rows.append(tuple(sizes))
        flat = [value for row in rows for value in row]
        offsets: list[int] = []
        total = 0
        for value in flat:
            offsets.append(total)
            total += value
        expected = PINNED_CONFIG["engram_num_embeddings"][index]
        if total != expected:
            raise SystemExit(
                f"layer {layer_id}: derived prime sum {total} is not the released "
                f"row count {expected}; the layout derivation is wrong"
            )
        layers.append(
            {
                "layer_id": layer_id,
                "primes": [list(row) for row in rows],
                "offsets": offsets,
                "table_rows": total,
                "multipliers": list(PINNED_MULTIPLIERS[layer_id]),
            }
        )
    return {"layers": layers}


def verify_multipliers_against_numpy() -> str:
    try:
        import numpy as np
    except ImportError:  # pragma: no cover - NumPy is optional here
        return "not re-derived: NumPy unavailable"
    bound = max(
        1,
        (int(np.iinfo(np.int64).max) // PINNED_CONFIG["engram_compressed_vocab_size"]) // 2,
    )
    for layer_id, pinned in PINNED_MULTIPLIERS.items():
        generator = np.random.default_rng(10007 * layer_id)
        values = generator.integers(
            low=0,
            high=bound,
            size=(PINNED_CONFIG["engram_max_ngram_size"],),
            dtype=np.int64,
        )
        derived = tuple(int(value) * 2 + 1 for value in values)
        if derived != tuple(pinned):
            raise SystemExit(
                f"layer {layer_id}: NumPy re-derivation {derived} differs from the "
                f"pinned multipliers {tuple(pinned)}"
            )
    return f"re-derived with NumPy {np.__version__}"


class CaseBuilder:
    """Turns a desired (window, order, head) into one vector case.

    The window is presented to the reference as a short sequence read backwards,
    so look-back `j` of the last position is `sequence[-1-j]`; blocking is
    expressed either as DEAD source positions or by asking for a position nearer
    the start of the sequence, which is exactly how the pinned source blocks.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.cases: list[dict[str, Any]] = []

    def _reference(
        self,
        sequence: list[int],
        position: int,
        order: int,
        head: int,
        dead: list[int],
    ) -> dict[str, Any]:
        records = ngram_row_ids(
            sequence,
            order=order,
            head=head,
            multipliers=self.config["multipliers"],
            primes=self.config["primes"],
            offsets=self.config["offsets"],
            pad_id=self.config["pad_id"],
            compressed_vocab_size=self.config["vocab"],
            dead_positions=dead,
            n_heads=NUM_HEADS,
            order_min=ORDER_MIN,
            table_rows=None,
        )
        return dict(records[position])

    def add(
        self,
        *,
        name: str,
        sequence: list[int],
        position: int,
        order: int,
        head: int,
        dead: list[int] | None = None,
        poison_unused: bool = False,
        force_ids: list[int] | None = None,
        expect_refuse: int = RF_NONE,
        expect_cfg_refuse: bool = False,
    ) -> None:
        dead = list(dead or ())
        refused = expect_refuse != RF_NONE or expect_cfg_refuse
        record: dict[str, Any] | None = None
        if not refused:
            record = self._reference(sequence, position, order, head, dead)
        else:
            # A refused case must be outside the reference contract, or inside it
            # with the refusal caused by something the reference does not model
            # (an unconfigured column).  Both are recorded, never guessed.
            try:
                record = self._reference(sequence, position, order, head, dead)
            except ValueError as error:
                record = None
                reason = str(error)
                if expect_refuse == RF_ID and "compressed vocabulary" not in reason:
                    raise SystemExit(f"{name}: expected an id refusal, got {reason}")
                if expect_refuse == RF_PRODUCT and "reaches 2**" not in reason:
                    raise SystemExit(f"{name}: expected a product refusal, got {reason}")
                if expect_refuse == RF_ORDER and "order" not in reason:
                    raise SystemExit(f"{name}: expected an order refusal, got {reason}")
            else:
                if expect_refuse in (RF_ID, RF_PRODUCT, RF_ORDER):
                    raise SystemExit(
                        f"{name}: the reference accepted a case expected to be "
                        f"outside its contract"
                    )

        if force_ids is not None:
            ids = list(force_ids)
            blocked = [False] * ORDER_MAX
        else:
            assert record is not None
            blocked = list(record["blocked"])
            sticky = []
            running = False
            for flag in blocked:
                running = running or flag
                sticky.append(running)
            ids = [
                POISON if sticky[j] else int(record["tokens"][j])
                for j in range(ORDER_MAX)
            ]
            if poison_unused:
                for j in range(order, ORDER_MAX):
                    ids[j] = POISON
                    blocked[j] = False

        if record is None or refused:
            row = residue = dividend = 0
        else:
            row = int(record["row_id"])
            residue = int(record["remainder"])
            dividend = int(record["dividend"])

        self.cases.append(
            {
                "name": name,
                "order": order,
                "head": head,
                "blocked": sum(1 << j for j, flag in enumerate(blocked) if flag),
                "ids": [int(value) & ((1 << ID_W) - 1) for value in ids],
                "expect_refuse": RF_COLUMN if expect_cfg_refuse else expect_refuse,
                "expect_row": row,
                "expect_residue": residue,
                "expect_dividend": dividend,
            }
        )


def window_cases(builder: CaseBuilder, seed: int) -> None:
    """Random and edge windows over every order and every head."""

    config = builder.config
    vocab = config["vocab"]
    rng = random.Random(seed)
    edges = [0, 1, 2, vocab - 1, vocab - 2, config["pad_id"]]
    for order in range(ORDER_MIN, ORDER_MAX + 1):
        for head in range(NUM_HEADS):
            windows: list[list[int]] = [
                [0] * ORDER_MAX,
                [vocab - 1] * ORDER_MAX,
                [0, vocab - 1, 0, vocab - 1],
                [vocab - 1, 0, vocab - 1, 0],
                [config["pad_id"]] * ORDER_MAX,
            ]
            for _ in range(9):
                windows.append([rng.randrange(vocab) for _ in range(ORDER_MAX)])
            for _ in range(4):
                windows.append([rng.choice(edges) for _ in range(ORDER_MAX)])
            for index, window in enumerate(windows):
                # sequence read backwards: look-back j of the last position is
                # window[j]
                sequence = list(reversed(window))
                builder.add(
                    name=f"window/o{order}/h{head}/{index}",
                    sequence=sequence,
                    position=ORDER_MAX - 1,
                    order=order,
                    head=head,
                )


def blocked_cases(builder: CaseBuilder, seed: int) -> None:
    """Every raw blocking mask, and every sequence-start position."""

    config = builder.config
    vocab = config["vocab"]
    rng = random.Random(seed)
    for mask in range(1 << ORDER_MAX):
        order = ORDER_MIN + (mask % (ORDER_MAX - ORDER_MIN + 1))
        head = mask % NUM_HEADS
        window = [rng.randrange(vocab) for _ in range(ORDER_MAX)]
        sequence = list(reversed(window))
        dead = [ORDER_MAX - 1 - j for j in range(ORDER_MAX) if mask & (1 << j)]
        builder.add(
            name=f"dead/mask{mask:x}",
            sequence=sequence,
            position=ORDER_MAX - 1,
            order=order,
            head=head,
            dead=dead,
        )
    for position in range(ORDER_MAX):
        for order in range(ORDER_MIN, ORDER_MAX + 1):
            window = [rng.randrange(vocab) for _ in range(ORDER_MAX)]
            sequence = list(reversed(window))
            builder.add(
                name=f"start/p{position}/o{order}",
                sequence=sequence,
                position=position,
                order=order,
                head=(position + order) % NUM_HEADS,
            )


def masking_cases(builder: CaseBuilder, seed: int) -> None:
    """Unused look-backs hold a poison id and must not reach the result."""

    config = builder.config
    rng = random.Random(seed)
    for order in range(ORDER_MIN, ORDER_MAX):
        for head in (0, 3, 7):
            window = [rng.randrange(config["vocab"]) for _ in range(ORDER_MAX)]
            sequence = list(reversed(window))
            builder.add(
                name=f"poison/o{order}/h{head}",
                sequence=sequence,
                position=ORDER_MAX - 1,
                order=order,
                head=head,
                poison_unused=True,
            )


def refusal_cases(builder: CaseBuilder, seed: int) -> None:
    """Order and id refusals, which need no special configuration."""

    config = builder.config
    rng = random.Random(seed)
    for order in (0, 1, ORDER_MAX + 1, (1 << 3) - 1):
        window = [rng.randrange(config["vocab"]) for _ in range(ORDER_MAX)]
        builder.add(
            name=f"refuse/order{order}",
            sequence=list(reversed(window)),
            position=ORDER_MAX - 1,
            order=order,
            head=order % NUM_HEADS,
            force_ids=window,
            expect_refuse=RF_ORDER,
        )
    for index, bad in enumerate([config["vocab"], config["vocab"] + 17, (1 << ID_W) - 1]):
        for order in (ORDER_MIN, ORDER_MAX):
            window = [rng.randrange(config["vocab"]) for _ in range(ORDER_MAX)]
            window[order - 1] = bad
            builder.add(
                name=f"refuse/id{index}/o{order}",
                sequence=list(reversed(window)),
                position=ORDER_MAX - 1,
                order=order,
                head=index,
                force_ids=window,
                expect_refuse=RF_ID,
            )


def build_configurations() -> list[dict[str, Any]]:
    layout = released_layout()
    configurations: list[dict[str, Any]] = []

    for index, layer in enumerate(layout["layers"]):
        config = {
            "name": f"released_layer_{layer['layer_id']}",
            "note": (
                "the released V4.1-Flash Engram layer: 24 column primes above "
                "engram_vocab_size-1 summing to the released row count, prefix-sum "
                "offsets, and the layer's own four look-back multipliers"
            ),
            "table_rows": layer["table_rows"],
            "pad_id": [2, 0][index],
            "vocab": PINNED_CONFIG["engram_compressed_vocab_size"],
            "multipliers": layer["multipliers"],
            "primes": layer["primes"],
            "offsets": layer["offsets"],
            "expect_cfg_error": 0,
            "expect_cfg_error_code": CE_NONE,
        }
        builder = CaseBuilder(config)
        window_cases(builder, seed=1000 + index)
        blocked_cases(builder, seed=2000 + index)
        masking_cases(builder, seed=3000 + index)
        refusal_cases(builder, seed=4000 + index)
        config["cases"] = builder.cases
        configurations.append(config)

    # ---- modulus probe: MOD_W extremes, not a released layout ----
    probe_primes = [
        4294967291, 4294967279, 4294967231, 2147483647,
        2147483648, 16777259, 16777216, 1000003,
        99991, 65537, 65536, 4093,
        1021, 257, 256, 127,
        64, 31, 17, 13,
        7, 5, 3, 2,
    ]
    assert len(probe_primes) == NUM_COLS
    probe_rows = max(probe_primes)
    probe = {
        "name": "modulus_probe",
        "note": (
            "one bucket range per column, every range based at row 0: a MODULUS "
            "probe, not a released layout.  It drives the reduction at the MOD_W "
            "extremes -- the largest prime below 2**32, powers of two, and a "
            "modulus of two -- which the released 24-bit primes never reach"
        ),
        "table_rows": probe_rows,
        "pad_id": 5,
        "vocab": PINNED_CONFIG["engram_compressed_vocab_size"],
        "multipliers": list(PINNED_MULTIPLIERS[1]),
        "primes": [probe_primes[0:8], probe_primes[8:16], probe_primes[16:24]],
        "offsets": [0] * NUM_COLS,
        "expect_cfg_error": 0,
        "expect_cfg_error_code": CE_NONE,
    }
    builder = CaseBuilder(probe)
    rng = random.Random(5000)
    for order in range(ORDER_MIN, ORDER_MAX + 1):
        for head in range(NUM_HEADS):
            windows = [
                [0] * ORDER_MAX,
                [probe["vocab"] - 1] * ORDER_MAX,
                [probe["vocab"] - 1, 0, probe["vocab"] - 1, 0],
            ]
            for _ in range(9):
                windows.append([rng.randrange(probe["vocab"]) for _ in range(ORDER_MAX)])
            for index, window in enumerate(windows):
                builder.add(
                    name=f"probe/o{order}/h{head}/{index}",
                    sequence=list(reversed(window)),
                    position=ORDER_MAX - 1,
                    order=order,
                    head=head,
                )
    probe["cases"] = builder.cases
    configurations.append(probe)

    # ---- a column whose bucket range leaves the table ----
    layer = released_layout()["layers"][0]
    short = {
        "name": "column_out_of_table",
        "note": (
            "the released layer-1 layout with the table one row short, so the "
            "LAST column's bucket range ends outside it.  The device must refuse "
            "that column and keep serving every other one"
        ),
        "table_rows": layer["table_rows"] - 1,
        "pad_id": 2,
        "vocab": PINNED_CONFIG["engram_compressed_vocab_size"],
        "multipliers": layer["multipliers"],
        "primes": layer["primes"],
        "offsets": layer["offsets"],
        "expect_cfg_error": 1,
        "expect_cfg_error_code": CE_COLUMN,
    }
    builder = CaseBuilder(short)
    rng = random.Random(6000)
    for repeat in range(4):
        window = [rng.randrange(short["vocab"]) for _ in range(ORDER_MAX)]
        builder.add(
            name=f"short/bad{repeat}",
            sequence=list(reversed(window)),
            position=ORDER_MAX - 1,
            order=ORDER_MAX,
            head=NUM_HEADS - 1,
            force_ids=window,
            expect_cfg_refuse=True,
        )
    for order in range(ORDER_MIN, ORDER_MAX + 1):
        for head in range(NUM_HEADS - 1):
            window = [rng.randrange(short["vocab"]) for _ in range(ORDER_MAX)]
            builder.add(
                name=f"short/good/o{order}/h{head}",
                sequence=list(reversed(window)),
                position=ORDER_MAX - 1,
                order=order,
                head=head,
            )
    short["cases"] = builder.cases
    configurations.append(short)

    # ---- a scalar operand outside its own bound ----
    bad_scalar = {
        "name": "pad_outside_vocabulary",
        "note": (
            "the pad id is at the compressed-vocabulary extent, so no beat can be "
            "served: every case must be refused, and the configuration must say "
            "why"
        ),
        "table_rows": layer["table_rows"],
        "pad_id": PINNED_CONFIG["engram_compressed_vocab_size"],
        "vocab": PINNED_CONFIG["engram_compressed_vocab_size"],
        "multipliers": layer["multipliers"],
        "primes": layer["primes"],
        "offsets": layer["offsets"],
        "expect_cfg_error": 1,
        "expect_cfg_error_code": CE_SCALAR,
    }
    builder = CaseBuilder(bad_scalar)
    rng = random.Random(7000)
    for order in range(ORDER_MIN, ORDER_MAX + 1):
        for head in range(0, NUM_HEADS, 2):
            window = [rng.randrange(bad_scalar["vocab"]) for _ in range(ORDER_MAX)]
            builder.add(
                name=f"scalar/o{order}/h{head}",
                sequence=list(reversed(window)),
                position=ORDER_MAX - 1,
                order=order,
                head=head,
                force_ids=window,
                expect_cfg_refuse=True,
            )
    bad_scalar["cases"] = builder.cases
    configurations.append(bad_scalar)

    # ---- a multiplier that takes the product past the exactness window ----
    overflow_vocab = 1 << 20
    overflow_primes = [
        [16000057, 16000079, 16000081, 16000097, 16000103, 16000121, 16000133, 16000139],
        [16000141, 16000159, 16000163, 16000181, 16000193, 16000199, 16000201, 16000207],
        [16000213, 16000223, 16000231, 16000237, 16000241, 16000249, 16000253, 16000267],
    ]
    flat = [value for row in overflow_primes for value in row]
    offsets: list[int] = []
    total = 0
    for value in flat:
        offsets.append(total)
        total += value
    overflow = {
        "name": "product_outside_window",
        "note": (
            "look-back 0 carries a multiplier near 2**47, so an id above "
            "2**63/multiplier takes the product past the DIVIDEND_W exactness "
            "window that the pinned int64 bound guarantees.  Small ids still "
            "compute; large ones must be refused, never wrapped"
        ),
        "table_rows": total,
        "pad_id": 1,
        "vocab": overflow_vocab,
        "multipliers": [(1 << 47) - 1, (1 << 43) + 1, 3, 5],
        "primes": overflow_primes,
        "offsets": offsets,
        "expect_cfg_error": 0,
        "expect_cfg_error_code": CE_NONE,
    }
    builder = CaseBuilder(overflow)
    limit = (1 << DIVIDEND_W) // overflow["multipliers"][0]
    rng = random.Random(8000)
    for order in range(ORDER_MIN, ORDER_MAX + 1):
        for head in range(4):
            safe = [rng.randrange(limit) for _ in range(ORDER_MAX)]
            builder.add(
                name=f"overflow/safe/o{order}/h{head}",
                sequence=list(reversed(safe)),
                position=ORDER_MAX - 1,
                order=order,
                head=head,
            )
            bad = list(safe)
            bad[0] = limit + 1 + head
            builder.add(
                name=f"overflow/bad/o{order}/h{head}",
                sequence=list(reversed(bad)),
                position=ORDER_MAX - 1,
                order=order,
                head=head,
                force_ids=bad,
                expect_refuse=RF_PRODUCT,
            )
    overflow["cases"] = builder.cases
    configurations.append(overflow)

    return configurations


def serialize(configurations: list[dict[str, Any]], output: Path) -> dict[str, Any]:
    total_cases = sum(len(config["cases"]) for config in configurations)
    config_words: list[int] = [
        MAGIC,
        len(configurations),
        total_cases,
        CASE_WORDS,
        ORDER_MAX,
        ORDER_MIN,
        ORDER_MAX,
        NUM_HEADS,
    ]
    case_words: list[int] = []
    refusal_counts: dict[str, int] = {}
    for config in configurations:
        config_words.extend(
            [
                len(config["cases"]),
                config["table_rows"],
                config["pad_id"],
                config["vocab"],
                ORDER_MAX,
                NUM_COLS,
                config["expect_cfg_error"],
                config["expect_cfg_error_code"],
            ]
        )
        for value in config["multipliers"]:
            if value >= (1 << MULT_W):
                raise SystemExit(f"multiplier {value} does not fit MULT_W={MULT_W}")
            config_words.extend([value & 0xFFFFFFFF, (value >> 32) & 0xFFFFFFFF])
        flat_primes = [value for row in config["primes"] for value in row]
        for column in range(NUM_COLS):
            prime = flat_primes[column]
            offset = config["offsets"][column]
            if prime >= (1 << MOD_W) or offset >= (1 << ROW_W):
                raise SystemExit(f"column {column} does not fit the device widths")
            config_words.extend([prime, offset])
        for case in config["cases"]:
            dividend = case["expect_dividend"]
            words = [
                case["order"],
                case["head"],
                case["blocked"],
                *case["ids"],
                case["expect_refuse"],
                case["expect_row"],
                case["expect_residue"],
                dividend & 0xFFFFFFFF,
                (dividend >> 32) & 0xFFFFFFFF,
                0,
                0,
                0,
                0,
            ]
            if len(words) != CASE_WORDS:
                raise SystemExit(f"case word count is {len(words)}, not {CASE_WORDS}")
            case_words.extend(words)
            key = f"code_{case['expect_refuse']}"
            refusal_counts[key] = refusal_counts.get(key, 0) + 1

    output.mkdir(parents=True, exist_ok=True)
    (output / "config.hex").write_text(
        "".join(f"{word & 0xFFFFFFFF:08x}\n" for word in config_words)
    )
    (output / "cases.hex").write_text(
        "".join(f"{word & 0xFFFFFFFF:08x}\n" for word in case_words)
    )

    manifest = {
        "schema": "opentallas.rtl.a3_v41_ngram_hash_vectors.v1",
        "unit": "rtl/abi3/ot_a3_dma_ngram_hash.sv",
        "engine": {"family": "DMA", "sub_opcode": 4, "ir_kind": "NGRAM_HASH"},
        "numeric_contract": "ngram_hash_u32_v1",
        "reference": {
            "module": "runtime/reference/engram.py",
            "function": "ngram_row_ids",
            "pinned_engram_source_sha256": PINNED_ENGRAM_SOURCE_SHA256,
            "pinned_config_sha256": PINNED_CONFIG_SHA256,
            "multiplier_derivation": verify_multipliers_against_numpy(),
        },
        "pinned_config": {key: list(value) if isinstance(value, tuple) else value
                          for key, value in PINNED_CONFIG.items()},
        "device_parameters": {
            "ID_W": ID_W,
            "MULT_W": MULT_W,
            "MOD_W": MOD_W,
            "ROW_W": ROW_W,
            "DIVIDEND_W": DIVIDEND_W,
            "ORDER_MIN": ORDER_MIN,
            "ORDER_MAX": ORDER_MAX,
            "NUM_HEADS": NUM_HEADS,
            "NUM_COLS": NUM_COLS,
        },
        "file_format": {
            "magic": MAGIC,
            "case_words": CASE_WORDS,
            "config_header_words": CONFIG_HEADER_WORDS,
            "file_header_words": FILE_HEADER_WORDS,
            "config_words": len(config_words),
            "case_hex_words": len(case_words),
        },
        "expected_pass": {
            "configs": len(configurations),
            "cases": total_cases,
            "refusals": refusal_counts,
            "bench_write_guard_prefix": BENCH_WRITE_GUARD_PREFIX,
        },
        "configurations": [
            {
                "name": config["name"],
                "note": config["note"],
                "table_rows": config["table_rows"],
                "pad_id": config["pad_id"],
                "vocab": config["vocab"],
                "multipliers": config["multipliers"],
                "primes": config["primes"],
                "offsets": config["offsets"],
                "expect_cfg_error": config["expect_cfg_error"],
                "expect_cfg_error_code": config["expect_cfg_error_code"],
                "case_count": len(config["cases"]),
                "refusal_case_count": sum(
                    1 for case in config["cases"] if case["expect_refuse"] != RF_NONE
                ),
                #: The bench runs one isolated latency beat on each
                #: configuration's FIRST case, and its write-guard phase replays
                #: the first BENCH_WRITE_GUARD_PREFIX cases of the FIRST
                #: configuration twice.  Both are published here so the campaign
                #: can predict the refusal census exactly instead of accepting
                #: whatever the bench reports.
                "first_case_refuse": config["cases"][0]["expect_refuse"],
                "guard_prefix_refuse": [
                    case["expect_refuse"]
                    for case in config["cases"][:BENCH_WRITE_GUARD_PREFIX]
                ],
            }
            for config in configurations
        ],
        "coverage": {
            "orders_covered": list(range(ORDER_MIN, ORDER_MAX + 1)),
            "heads_covered": list(range(NUM_HEADS)),
            "released_layers_covered": list(PINNED_CONFIG["engram_layer_ids"]),
            "modulus_bits_covered": sorted(
                {
                    int(prime).bit_length()
                    for config in configurations
                    for row in config["primes"]
                    for prime in row
                }
            ),
            "ids_at_zero_and_compressed_maximum": True,
            "every_raw_blocking_mask": True,
            "sequence_start_positions": list(range(ORDER_MAX)),
        },
        "claim_boundary": {
            "compressed_token_map_reproduced": False,
            "engram_row_read_executed": False,
            "engram_gate_executed": False,
            "pad_id_is_the_released_compressed_pad_id": False,
            "vector_expectations_come_from_the_reference_only": True,
        },
    }
    (output / "index.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return result


def main() -> int:
    args = parser().parse_args()
    manifest = serialize(build_configurations(), args.output)
    digests = {
        name: hashlib.sha256((args.output / name).read_bytes()).hexdigest()[:16]
        for name in ("config.hex", "cases.hex", "index.json")
    }
    print(
        "a3_v41_ngram_hash vectors "
        f"configs={manifest['expected_pass']['configs']} "
        f"cases={manifest['expected_pass']['cases']} "
        f"refusals={sum(count for key, count in manifest['expected_pass']['refusals'].items() if key != 'code_0')} "
        f"digests={digests}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
