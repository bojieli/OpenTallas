#!/usr/bin/env python3
"""Inspect one replay VM word using an existing pre-SHOWVAL slice binary.

Every bit is checked against zero at the same edge.  The old bench records a
failure for one bits and a commit for zero bits.  This is a diagnostic replay,
never a numerical acceptance or layer/token proof.  Original inputs and VM
preload are copied unchanged.  The compiled event-array capacity is required.
"""
import argparse
import json
import re
import shutil
from pathlib import Path


def make(source, output, cycle, port, capacity):
    source, output = Path(source), Path(output)
    words = {n: [int(x, 16) for x in (source / f"{n}.mem").read_text().split()]
             for n in ("hdr", "val", "msk")}
    if len({len(v) for v in words.values()}) != 1:
        raise ValueError("replay arrays differ in length")
    checks = [(h, v, m) for h, v, m in zip(*words.values())
              if h >> 62 == 2 and (h >> 60) & 3 == 1
              and h & 0xffffffff == cycle and (h >> 44) & 0xffff == port]
    if len(checks) != 1 or not port & 0x8000:
        raise ValueError("require one original serial VM-word check")
    _, expected, original_mask = checks[0]
    if original_mask != (1 << 256) - 1:
        raise ValueError("require a complete 256-bit original word")
    # Keep every drive; split_replay's preloaded state is unchanged.  Checks
    # never drive hardware, so replacing them cannot affect the observed word.
    events = [(h, v, m) for h, v, m in zip(*words.values()) if h >> 62 == 1]
    for bit in range(256):
        h = (2 << 62) | (1 << 60) | (port << 44) | ((bit + 1) << 32) | cycle
        events.append((h, 0, 1 << bit))
    events.sort(key=lambda x: ((x[0] >> 60) & 3, x[0] & 0xffffffff, x[0] >> 62))
    if len(events) >= capacity:
        raise ValueError(f"{len(events)} events plus sentinel exceed capacity {capacity}")
    events.extend([(3 << 62, 0, 0)] * (capacity - len(events)))
    output.mkdir(parents=True, exist_ok=False)
    for col, name in enumerate(("hdr", "val", "msk")):
        (output / f"{name}.mem").write_text("".join(f"{r[col]:x}\n" for r in events))
    shutil.copyfile(source / "vm_pre.txt", output / "vm_pre.txt")
    meta = dict(schema="opentallas.vm_word_diagnostic.v1", scope="diagnostic_only",
                source=str(source), cycle=cycle, port=port, bits=256,
                expected=f"{expected:064x}", capacity=capacity,
                qualifies_native_layer=False, qualifies_full_token=False)
    (output / "diagnostic.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def collect(replay, log):
    meta = json.loads((Path(replay) / "diagnostic.json").read_text())
    bits = {}
    for line in Path(log).read_text().splitlines():
        m = re.fullmatch(r"SLICE_REC rec=(\d+) cyc=(\d+) (FAIL|COMMIT_OK)", line)
        if m and int(m[2]) == meta["cycle"]:
            bit = int(m[1])
            if not 0 <= bit < 256 or bit in bits:
                raise ValueError("invalid or repeated diagnostic bit")
            bits[bit] = m[3] == "FAIL"
    if len(bits) != 256:
        raise ValueError(f"incomplete word: {len(bits)}/256 bits")
    got = sum(int(value) << bit for bit, value in bits.items())
    expected = int(meta["expected"], 16)
    return dict(meta, observed=f"{got:064x}", xor=f"{got ^ expected:064x}",
                matches_original=got == expected)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    s = p.add_subparsers(dest="mode", required=True)
    m = s.add_parser("make")
    m.add_argument("source"); m.add_argument("output")
    m.add_argument("--cycle", type=int, required=True)
    m.add_argument("--port", type=int, required=True)
    m.add_argument("--capacity", type=int, required=True)
    c = s.add_parser("collect")
    c.add_argument("replay"); c.add_argument("log")
    a = p.parse_args()
    result = (make(a.source, a.output, a.cycle, a.port, a.capacity)
              if a.mode == "make" else collect(a.replay, a.log))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
