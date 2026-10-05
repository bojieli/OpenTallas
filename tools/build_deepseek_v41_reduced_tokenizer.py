"""Reduce the released V4.1 tokenizer to the reduced vehicle's vocabulary.

The reduced fixture scales ``vocab_size`` by the width factor (128 000 -> 4 040)
but shipped no tokenizer, and the reduced release record pinned both tokenizer
digests *absent*.  That was consistent right up to the point where a deployment
is built: the Engram n-gram tables hash over *compressed* token ids, and
``engram.build_compressed_token_map`` derives that compression from the
tokenizer itself -- token strings that normalise alike (" The", "the", "THE")
collapse onto one id.  A model with no tokenizer therefore has no engram, and
the deployment refuses rather than guessing the table:

    tensor engram.compressed_token_map: ... tokenizer.json ... is not in the
    local cache; the compressed token map is derived from the released
    tokenizer and may not be guessed

Keeping the *released* tokenizer instead is the tempting shortcut and it is
wrong: it can emit ids up to 129 279 while the reduced embedding has 4 040 rows,
so the vehicle would tokenise text it cannot embed.  A reduced model needs a
reduced tokenizer, and this tool builds one.

The construction
----------------
The released vocabulary is a contiguous BPE id space ``0..127 999`` whose first
three ids are exactly the specials the reduced config already names -- bos 0,
eos 1, pad 2 (``engram_pad_id``).  So the reduction is a prefix: keep every
vocabulary entry with ``id < vocab_size``, keep the added-token records in that
range, and keep each merge whose two parts *and* whose joined result all
survive.  Merge order is rank in BPE, so the surviving merges keep their
relative order.  The result is a strictly weaker BPE over the same alphabet: it
tokenises any text the release does, just into more pieces.

``engram_compressed_vocab_size`` is then not a free parameter.  The release
asserts it (``engram.py`` line 146)::

    token_map, vocab_size = build_compressed_token_map(tokenizer)
    assert vocab_size == args.engram_compressed_vocab_size

so this tool reports the derived size and the fixture's config must carry it.
That is why the field moves out of the reduced builder's ``KEPT_EXACTLY`` list:
it is a property of the tokenizer, not of the architecture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.frontend.deepseek_v4_releases import V41_FLASH  # noqa: E402

DEFAULT_FIXTURE = ROOT / "build/models/deepseek-v4.1-flash-reduced-v1"


class ReducedTokenizerError(RuntimeError):
    """The reduced tokenizer cannot be built as specified."""


def released_snapshot(revision: str = V41_FLASH.revision) -> Path:
    import os

    base = Path(
        os.environ.get("OPENTALLAS_HF_HOME", Path.home() / ".cache/huggingface/hub")
    )
    path = base / "models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots" / revision
    if not path.is_dir():
        raise ReducedTokenizerError(
            f"the pinned V4.1 snapshot is not at {path}; the reduced tokenizer "
            "is a subset of the released one, so the snapshot is required"
        )
    return path


def _split_merge(entry: Any) -> tuple[str, str]:
    """A merge is stored either as ``"a b"`` or as ``["a", "b"]``."""
    if isinstance(entry, str):
        left, _, right = entry.partition(" ")
        if not right:
            raise ReducedTokenizerError(f"merge {entry!r} has no separator")
        return left, right
    if isinstance(entry, (list, tuple)) and len(entry) == 2:
        return str(entry[0]), str(entry[1])
    raise ReducedTokenizerError(f"unrecognised merge record {entry!r}")


def reduce_tokenizer(released: dict[str, Any], vocab_size: int) -> dict[str, Any]:
    """The released tokenizer restricted to ids below ``vocab_size``."""
    model = released["model"]
    if model.get("type") != "BPE":
        raise ReducedTokenizerError(
            f"the prefix reduction is defined for BPE; this is {model.get('type')!r}"
        )
    vocab = {token: ident for token, ident in model["vocab"].items() if ident < vocab_size}
    if len(vocab) != vocab_size:
        raise ReducedTokenizerError(
            f"the released id space is not contiguous below {vocab_size}: kept "
            f"{len(vocab)} entries"
        )
    kept = set(vocab)
    merges = []
    for entry in model["merges"]:
        left, right = _split_merge(entry)
        if left in kept and right in kept and left + right in kept:
            merges.append(entry)

    reduced = json.loads(json.dumps(released))
    reduced["model"]["vocab"] = vocab
    reduced["model"]["merges"] = merges
    reduced["added_tokens"] = [
        record for record in released.get("added_tokens", []) if record["id"] < vocab_size
    ]
    # truncation/padding records name lengths, not ids, and survive untouched.
    return reduced


def compressed_vocab_size(tokenizer_dir: Path) -> tuple[int, int]:
    """``build_compressed_token_map`` of the reduced tokenizer: (rows, size)."""
    snapshot = released_snapshot()
    inference = snapshot / "inference"
    if str(inference) not in sys.path:
        sys.path.insert(0, str(inference))
    import importlib

    engram = importlib.import_module("engram")
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_dir))
    lookup, size = engram.build_compressed_token_map(tokenizer)
    return len(lookup), int(size)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; report what the derivation yields",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    config = json.loads((args.fixture / "inference_config.json").read_text())
    vocab_size = int(config["vocab_size"])
    snapshot = released_snapshot()
    released = json.loads((snapshot / "tokenizer.json").read_text())
    reduced = reduce_tokenizer(released, vocab_size)

    body = json.dumps(reduced, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    config_body = (snapshot / "tokenizer_config.json").read_text()

    if not args.check:
        (args.fixture / "tokenizer.json").write_text(body)
        (args.fixture / "tokenizer_config.json").write_text(config_body)

    rows, size = compressed_vocab_size(args.fixture)
    report = {
        "vocab_size": vocab_size,
        "released_vocab": len(released["model"]["vocab"]),
        "released_merges": len(released["model"]["merges"]),
        "reduced_merges": len(reduced["model"]["merges"]),
        "added_tokens": len(reduced["added_tokens"]),
        "compressed_map_rows": rows,
        "engram_compressed_vocab_size": size,
        "tokenizer_sha256": hashlib.sha256(body.encode()).hexdigest(),
        "tokenizer_config_sha256": hashlib.sha256(config_body.encode()).hexdigest(),
    }
    if rows != vocab_size:
        raise ReducedTokenizerError(
            f"the compressed map has {rows} rows for a {vocab_size}-token "
            "vocabulary; the reduction did not produce a tokenizer of the "
            "declared length"
        )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
