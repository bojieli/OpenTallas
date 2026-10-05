#!/usr/bin/env python3
"""Copy the layer-0 tensors the phase-merge bench reads out of the released DeepSeek-V4.1-Flash snapshot into a
one-file safetensors mini-snapshot (bytes copied verbatim; the record pins each tensor's sha256), so the bench can
run on a simulation host that does not hold the 476 GB snapshot.

    python3 make_mini_snapshot.py --snapshot <HF snapshot dba1be0a...> --out DIR
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

# the phase-merge bench's tensors plus the unmodified gate's own phase list (the same-binary control)
NAMES = [f"layers.0.{t}.{s}" for t in ("attn.wq_a", "attn.wkv", "attn.wq_b", "attn.wo_b", "ffn.experts.110.w1",
                                        "ffn.experts.110.w3", "ffn.experts.141.w2", "ffn.shared_experts.w2")
         for s in ("weight", "scale")] + ["layers.0.ffn.gate.weight"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    idx = json.loads((a.snapshot / "model.safetensors.index.json").read_text())["weight_map"]
    hdr, blobs, off, pins = {}, [], 0, {}
    for n in NAMES:
        p = a.snapshot / idx[n]
        with p.open("rb") as h:
            hn = struct.unpack("<Q", h.read(8))[0]
            meta = json.loads(h.read(hn))[n]
            s, e = meta["data_offsets"]
            h.seek(8 + hn + s)
            buf = h.read(e - s)
        hdr[n] = dict(dtype=meta["dtype"], shape=meta["shape"], data_offsets=[off, off + len(buf)])
        blobs.append(buf)
        off += len(buf)
        pins[n] = dict(source_file=idx[n], dtype=meta["dtype"], shape=meta["shape"],
                       sha256=hashlib.sha256(buf).hexdigest())
    hb = json.dumps(hdr).encode()
    hb += b" " * (-len(hb) % 8)
    a.out.mkdir(parents=True, exist_ok=True)
    with (a.out / "mini.safetensors").open("wb") as f:
        f.write(struct.pack("<Q", len(hb)) + hb)
        for b in blobs:
            f.write(b)
    (a.out / "model.safetensors.index.json").write_text(json.dumps({"weight_map": {n: "mini.safetensors" for n in NAMES}}))
    (a.out / "tensor_pins.json").write_text(json.dumps(dict(source_snapshot=a.snapshot.name, tensors=pins), indent=1) + "\n")
    print(json.dumps(pins, indent=1))


if __name__ == "__main__":
    main()
