"""Evidence checks for DMA.NGRAM_HASH: the reference, the RTL text, the record.

The RTL simulation itself is `tools/run_a3_v41_ngram_hash_rtl_campaign.py` and
its artifact.  What is checked here:

1. the independent reference `runtime.reference.engram.ngram_row_ids` against a
   THIRD path -- the identity written out directly in this test with Python big
   integers -- plus the rules the pinned source states: the XOR fold, the sticky
   look-back blocking, the per-(order, head) column modulus, the prefix-sum
   offset, and every refusal;
2. that the released V4.1-Flash Engram geometry is NOT frozen anywhere: the
   derived per-column primes must sum to the released row counts (so the layout
   is the released one), and no released number may appear in
   `rtl/abi3/ot_a3_dma_ngram_hash.sv` at all -- every one of them reaches the
   device as a parameter default or a run-time operand;
3. that the pinned digests the vector builder cites still match
   `docs/SOURCES.md` and `data/inventory/`;
4. the campaign record, including that its `source_sha256` still matches the
   files on disk -- a record whose sources have moved underneath it is stale
   evidence, not evidence.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import re

import pytest

from runtime.reference.engram import ngram_row_ids
from tools.build_a3_v41_ngram_hash_vectors import (
    PINNED_CONFIG,
    PINNED_CONFIG_SHA256,
    PINNED_ENGRAM_SOURCE_SHA256,
    PINNED_MULTIPLIERS,
    released_layout,
)

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl/abi3/ot_a3_dma_ngram_hash.sv"
BENCH = ROOT / "rtl/test/tb_a3_v41_ngram_hash.sv"
VECTOR_DIR = ROOT / "testdata/rtl/a3_v41_ngram_hash"
CAMPAIGN_JSON = ROOT / "results/rtl/a3_v41_ngram_hash_campaign.json"
SOURCES = ROOT / "docs/SOURCES.md"
INVENTORY = ROOT / "data/inventory/deepseek-v4.1-flash.json"

HEADS = PINNED_CONFIG["engram_n_heads"]
MAX_NGRAM = PINNED_CONFIG["engram_max_ngram_size"]
VOCAB = PINNED_CONFIG["engram_compressed_vocab_size"]


def _layer(index: int = 0) -> dict[str, object]:
    return released_layout()["layers"][index]


def _third_path(
    window: list[int],
    order: int,
    head: int,
    layer: dict[str, object],
) -> int:
    """The identity written out directly, independent of the reference's code."""

    multipliers = layer["multipliers"]
    value = 0
    for index in range(order):
        value = value ^ (window[index] * multipliers[index])
    prime = layer["primes"][order - 2][head]
    offset = layer["offsets"][(order - 2) * HEADS + head]
    return value % prime + offset


# ----- the reference -------------------------------------------------------
def test_reference_matches_a_third_path_over_every_order_and_head() -> None:
    layer = _layer()
    rng = random.Random(4242)
    for order in range(2, MAX_NGRAM + 1):
        for head in range(HEADS):
            for _ in range(8):
                window = [rng.randrange(VOCAB) for _ in range(MAX_NGRAM)]
                record = ngram_row_ids(
                    list(reversed(window)),
                    order=order,
                    head=head,
                    multipliers=layer["multipliers"],
                    primes=layer["primes"],
                    offsets=layer["offsets"],
                    pad_id=2,
                    compressed_vocab_size=VOCAB,
                    n_heads=HEADS,
                    table_rows=layer["table_rows"],
                )[MAX_NGRAM - 1]
                assert record["tokens"] == tuple(window)
                assert record["row_id"] == _third_path(window, order, head, layer)
                assert record["row_id"] < layer["table_rows"]
                assert 0 <= record["remainder"] < record["prime"]


def test_fold_is_xor_not_addition() -> None:
    layer = _layer()
    window = [11, 22, 33, 44]
    record = ngram_row_ids(
        list(reversed(window)),
        order=2,
        head=0,
        multipliers=layer["multipliers"],
        primes=layer["primes"],
        offsets=layer["offsets"],
        pad_id=2,
        compressed_vocab_size=VOCAB,
        n_heads=HEADS,
    )[MAX_NGRAM - 1]
    products = [window[i] * layer["multipliers"][i] for i in range(2)]
    assert record["dividend"] == products[0] ^ products[1]
    assert record["dividend"] != products[0] + products[1]


def test_edge_ids_at_zero_and_the_compressed_maximum() -> None:
    layer = _layer()
    for window in ([0] * MAX_NGRAM, [VOCAB - 1] * MAX_NGRAM):
        for order in range(2, MAX_NGRAM + 1):
            record = ngram_row_ids(
                list(reversed(window)),
                order=order,
                head=HEADS - 1,
                multipliers=layer["multipliers"],
                primes=layer["primes"],
                offsets=layer["offsets"],
                pad_id=2,
                compressed_vocab_size=VOCAB,
                n_heads=HEADS,
            )[MAX_NGRAM - 1]
            assert record["row_id"] == _third_path(window, order, HEADS - 1, layer)
            assert record["dividend"] < (1 << 63)


def test_look_back_blocking_is_sticky_and_substitutes_the_pad() -> None:
    layer = _layer()
    sequence = [101, 202, 303, 404]
    records = ngram_row_ids(
        sequence,
        order=MAX_NGRAM,
        head=0,
        multipliers=layer["multipliers"],
        primes=layer["primes"],
        offsets=layer["offsets"],
        pad_id=9,
        compressed_vocab_size=VOCAB,
        dead_positions=[2],
        n_heads=HEADS,
    )
    # Position 3 looks back over 3, 2, 1, 0; position 2 is DEAD, so look-backs 1,
    # 2 and 3 are all blocked -- not only the one that hit the dead token.
    last = records[3]
    assert last["blocked"] == (False, True, False, False)
    assert last["tokens"] == (404, 9, 9, 9)
    # At the start of the sequence, blocking comes from the position itself.
    assert records[0]["tokens"] == (101, 9, 9, 9)
    assert records[1]["tokens"] == (202, 101, 9, 9)


def test_each_order_and_head_lands_in_its_own_bucket_range() -> None:
    layer = _layer()
    rng = random.Random(77)
    for order in range(2, MAX_NGRAM + 1):
        for head in range(HEADS):
            column = (order - 2) * HEADS + head
            low = layer["offsets"][column]
            high = low + layer["primes"][order - 2][head]
            for _ in range(4):
                window = [rng.randrange(VOCAB) for _ in range(MAX_NGRAM)]
                row = ngram_row_ids(
                    list(reversed(window)),
                    order=order,
                    head=head,
                    multipliers=layer["multipliers"],
                    primes=layer["primes"],
                    offsets=layer["offsets"],
                    pad_id=2,
                    compressed_vocab_size=VOCAB,
                    n_heads=HEADS,
                )[MAX_NGRAM - 1]["row_id"]
                assert low <= row < high


def test_reference_refuses_everything_outside_its_contract() -> None:
    layer = _layer()
    common = {
        "multipliers": layer["multipliers"],
        "primes": layer["primes"],
        "offsets": layer["offsets"],
        "pad_id": 2,
        "compressed_vocab_size": VOCAB,
        "n_heads": HEADS,
    }
    with pytest.raises(ValueError):
        ngram_row_ids([1, 2, 3, 4], order=1, head=0, **common)
    with pytest.raises(ValueError):
        ngram_row_ids([1, 2, 3, 4], order=MAX_NGRAM + 1, head=0, **common)
    with pytest.raises(ValueError):
        ngram_row_ids([1, 2, 3, 4], order=2, head=HEADS, **common)
    with pytest.raises(ValueError):
        ngram_row_ids([1, 2, 3, VOCAB], order=2, head=0, **common)
    with pytest.raises(ValueError):
        ngram_row_ids([1, 2, 3, 4], order=2, head=0, **{**common, "pad_id": VOCAB})
    with pytest.raises(ValueError):
        ngram_row_ids(
            [1, 2, 3, 4],
            order=2,
            head=0,
            **{**common, "multipliers": [1 << 62, 1, 1, 1]},
        )
    with pytest.raises(ValueError):
        ngram_row_ids(
            [1, 2, 3, 4],
            order=2,
            head=0,
            table_rows=layer["table_rows"] - 1,
            **common,
        )


def test_reference_carries_no_frozen_geometry() -> None:
    """A two-head, order-2-and-3 layout with tiny primes has to work as well."""

    records = ngram_row_ids(
        [5, 6, 7],
        order=3,
        head=1,
        multipliers=[3, 5, 7],
        primes=[[101, 103], [107, 109]],
        offsets=[0, 101, 204, 311],
        pad_id=1,
        compressed_vocab_size=64,
        n_heads=2,
        table_rows=420,
    )
    assert len(records) == 3
    last = records[2]
    assert last["dividend"] == (7 * 3) ^ (6 * 5) ^ (5 * 7)
    assert last["row_id"] == last["dividend"] % 109 + 311


# ----- the released layout -------------------------------------------------
def test_derived_column_primes_sum_to_the_released_row_counts() -> None:
    layout = released_layout()
    for index, layer in enumerate(layout["layers"]):
        flat = [value for row in layer["primes"] for value in row]
        assert len(flat) == (MAX_NGRAM - 1) * HEADS == 24
        assert sum(flat) == PINNED_CONFIG["engram_num_embeddings"][index]
        assert layer["offsets"][0] == 0
        assert all(
            layer["offsets"][column + 1] == layer["offsets"][column] + flat[column]
            for column in range(len(flat) - 1)
        )
        assert len(set(flat)) == len(flat)


def test_released_layers_share_no_bucket_prime() -> None:
    layers = released_layout()["layers"]
    first = {value for row in layers[0]["primes"] for value in row}
    second = {value for row in layers[1]["primes"] for value in row}
    assert not (first & second)


def test_pinned_digests_match_the_source_registry() -> None:
    text = SOURCES.read_text()
    assert PINNED_ENGRAM_SOURCE_SHA256 in text
    assert PINNED_CONFIG_SHA256 in text
    inventory = json.loads(INVENTORY.read_text())
    assert inventory["config_sha256"] == PINNED_CONFIG_SHA256
    assert inventory["revision"] == "dba1be0a40aa45a94ad051997016db3960a90277"


# ----- the RTL text --------------------------------------------------------
def test_rtl_holds_no_released_model_number() -> None:
    body = RTL.read_text()
    code = "\n".join(
        line.split("//")[0] for line in body.splitlines() if not line.strip().startswith("//")
    )
    forbidden: set[int] = {
        *PINNED_CONFIG["engram_num_embeddings"],
        PINNED_CONFIG["engram_vocab_size"],
        PINNED_CONFIG["engram_compressed_vocab_size"],
    }
    for layer in released_layout()["layers"]:
        forbidden.update(value for row in layer["primes"] for value in row)
        forbidden.update(layer["offsets"][1:])
        forbidden.update(layer["multipliers"])
    for value in forbidden:
        assert str(value) not in code, f"released number {value} is frozen into the RTL"


def test_rtl_declares_every_extent_as_a_parameter() -> None:
    body = RTL.read_text()
    module = body.split("module ot_a3_dma_ngram_hash", 1)[1].split(");", 1)[0]
    for name in (
        "ID_W",
        "MULT_W",
        "MOD_W",
        "ROW_W",
        "DIVIDEND_W",
        "ORDER_MAX",
        "ORDER_MIN",
        "NUM_HEADS",
        "MUL_DIGIT_W",
        "TAG_W",
    ):
        assert re.search(rf"parameter integer {name}\s*=", module), name
    # The column count and the reduction's widths are DERIVED from those, never
    # declared independently.
    assert "localparam integer NUM_COLS    = NUM_ORDERS * NUM_HEADS;" in body
    assert "localparam integer MU_W        = DIVIDEND_W + 2;" in body


def test_rtl_states_its_stage_count_and_initiation_interval() -> None:
    text = RTL.read_text()
    header = text.split("module ot_a3_ngram_mul_pipe", 1)[0]
    body = text.split("module ot_a3_dma_ngram_hash", 1)[1]
    assert "INITIATION INTERVAL 1" in header
    assert "BARRETT" in header
    # The header names the stage count SYMBOLICALLY rather than mirroring a
    # number that would rot the moment the pipeline is retimed: LATENCY is
    # derived from the stage map, and published on info_pipe_stages, which the
    # bench measures the device against.
    assert "LATENCY register stages" in header
    assert "info_pipe_stages" in header
    assert "localparam integer LATENCY    = ST_RED + 2;" in body
    # And every stage the header's map names is a real localparam, so the map
    # cannot drift away from the pipeline it describes.
    named = re.findall(r"^//\s+(ST_[A-Z0-9]+)\s", header, re.M)
    assert len(named) >= 8
    for stage in named:
        assert f"localparam integer {stage}" in body, stage


def test_bench_reads_its_geometry_from_the_vectors_and_the_device() -> None:
    body = BENCH.read_text()
    assert "info_pipe_stages" in body
    assert "device column count" in body
    assert "vector magic" in body


# ----- the record ----------------------------------------------------------
@pytest.mark.skipif(not CAMPAIGN_JSON.is_file(), reason="campaign has not been run")
def test_campaign_record_is_a_passing_dual_simulator_run() -> None:
    record = json.loads(CAMPAIGN_JSON.read_text())
    assert record["schema"] == "opentallas.rtl.a3_v41_ngram_hash_campaign.v1"
    assert record["status"] == "pass"
    assert record["simulators_agree"] is True
    assert record["unit"]["engine_sub_opcode"] == 4
    assert record["unit"]["ir_kind"] == "NGRAM_HASH"
    assert record["pipeline"]["initiation_interval"] == 1
    assert record["pipeline"]["latency_equals_device_info_port"] is True
    assert record["normalized_pass"]["ii_violations"] == 0
    assert record["checks_per_simulator"] > 10000
    assert "5.050" in record["tools"]["verilator"]["version"]
    assert record["claim_boundary"]["establishes_token_latency_or_tpot"] is False
    assert record["claim_boundary"]["is_placed_or_routed"] is False
    moduli = {
        bits
        for config in record["geometry"]["configurations_exercised"]
        for bits in config["modulus_bits"]
    }
    assert 24 in moduli, "the released 24-bit column primes must be exercised"
    assert 32 in moduli, "a modulus near 2**32 must be exercised"
    assert 2 in moduli, "the smallest legal modulus must be exercised"


@pytest.mark.skipif(not CAMPAIGN_JSON.is_file(), reason="campaign has not been run")
def test_campaign_record_sources_have_not_moved() -> None:
    from tools.run_a3_v41_ngram_hash_rtl_campaign import validate_retained

    assert validate_retained() == []


@pytest.mark.skipif(not CAMPAIGN_JSON.is_file(), reason="campaign has not been run")
def test_campaign_vectors_are_the_checked_in_vectors() -> None:
    record = json.loads(CAMPAIGN_JSON.read_text())
    for name, digest in record["vector_sha256"].items():
        assert (
            hashlib.sha256((VECTOR_DIR / name).read_bytes()).hexdigest() == digest
        ), name
