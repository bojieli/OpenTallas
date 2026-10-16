#!/usr/bin/env python3
"""Fail-closed bench coverage and controlled mutants for emitted S81 stations.

Width comes from the emitted module ABI. Reset-sensitive x2 bit positions come
independently from the real BF consumer's named input decoding, not DUT results.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def interface(text):
    match = re.search(r"module\s+(\w+)\s*\((.*?)\);", text, re.S)
    assert match, "no literal emitted module interface"
    pattern = r"(input|output)\s+wire\s+\[(\d+):(\d+)\]\s+(\w+)"
    rows = re.findall(pattern, match[2])
    assert not re.sub(pattern, "", match[2]).strip(" \t\r\n,"), "unparsed declared ports"
    ports = {name: dict(direction=direction, width=int(hi) - int(lo) + 1)
             for direction, hi, lo, name in rows if int(lo) == 0 and int(hi) >= int(lo)}
    assert len(ports) == len(rows), "duplicate, nonzero-based or invalid emitted ports"
    return match[1], ports


def inspect(text, consumer):
    master, ports = interface(text)
    expected = dict(ck=("input", 1), rs=("input", 1))
    if master.startswith("dsfd_rstg"):
        expected.update(i=("input", 66), o=("output", 66))
    else:
        expected.update(cci=("input", 15), so=("output", 2), xa=("output", 283), xai=("input", 283),
                        xb=("output", 266), xbi=("input", 266), c0=("input", 2), e0=("input", 2))
        for name, direction, width in [("cc", "output", 15), ("si", "input", 2), ("nf", "input", 1),
                                       ("c1", "input", 2), ("e1", "input", 2)]:
            if name in ports:
                expected[name] = direction, width
        assert ("c1" in ports) == ("e1" in ports), "c1/e1 pair is incomplete"
    x2 = "x2i" in ports or "x2" in ports
    result = dict(master=master, ports=ports, source_sha256=hashlib.sha256(text.encode()).hexdigest(),
                  normal_capture_edge="posedge ck[0]", reset="active-low rs[0], asynchronous control clear", x2=x2)
    flags = []
    if x2:
        assert "x2i" in ports and "x2" in ports, "x2 producer/consumer port pair is incomplete"
        width = ports["x2i"]["width"]
        expected.update(x2i=("input", width), x2=("output", width))
        consumer_text = consumer.read_text()
        control = {}
        for field in ("go_bf", "xb_v"):
            indices = re.findall(r"assign\s+w_" + field + r"\s*=\s*xb\[(\d+)\]\s*;", consumer_text)
            assert len(indices) == 1, "missing/ambiguous real BF consumer field " + field
            control[field] = int(indices[0])
        assert len(set(control.values())) == 2 and all(0 <= b < width for b in control.values()), "invalid x2 reset fields"
        payload = [b for b in range(width) if b not in control.values()]
        assert payload, "no x2 payload bits"
        result.update(x2_width=width, reset_bits=control, payload_mutant_bit=payload[-1],
                      consumer=str(consumer), consumer_sha256=hashlib.sha256(consumer_text.encode()).hexdigest())
        flags = ["-DHAS_X2", f"-DX2_W={width}", f"-DX2_RESET_0={control['go_bf']}", f"-DX2_RESET_1={control['xb_v']}"]
    assert ports == {n: dict(direction=d, width=w) for n, (d, w) in expected.items()}, "declared port lacks exact bench coverage"
    return result, flags


def mutate(text, mode, abi):
    assert abi["x2"], mode + " requires an emitted x2 ABI"
    if mode in ("mut_x2_drop", "mut_x2_payload"):
        pattern = r"(assign\s+x2\s*=\s*)([^;]+)(;)"
        replacement = (lambda m: m[1] + "'0" + m[3]) if mode == "mut_x2_drop" else (
            lambda m: m[1] + f"({m[2]}) ^ ({abi['x2_width']}'d1 << {abi['payload_mutant_bit']})" + m[3])
        changed, count = re.subn(pattern, replacement, text)
    elif mode == "mut_x2_reset":
        pattern = (r"always\s*@\(posedge ck\[0\] or negedge rs\[0\]\)\s*if\s*\(!rs\[0\]\)\s*"
                   r"(?P<reg>\w+)\s*<=\s*2'b00;\s*else\s*(?P=reg)\s*<=\s*(?P<data>\{x2i\[\d+\],\s*x2i\[\d+\]\});")
        changed, count = re.subn(pattern, lambda m: "always @(posedge ck[0]) " + m["reg"] + " <= " + m["data"] + ";", text)
    elif mode == "mut_x2_edge":
        pattern = r"always\s*@\(posedge ck\[0\]\)\s*(?P<reg>\w+)\s*<=\s*x2i;"
        changed, count = re.subn(pattern, lambda m: "always @(negedge ck[0]) " + m["reg"] + " <= x2i;", text)
    else:
        raise ValueError("unknown x2 mutant " + mode)
    assert count == 1 and changed != text, "x2 mutant not applied exactly once"
    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["flags", "mut_x2_drop", "mut_x2_payload", "mut_x2_reset", "mut_x2_edge"])
    parser.add_argument("source", type=Path)
    parser.add_argument("consumer", type=Path)
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    text = args.source.read_text()
    if args.mode == "flags":
        abi, flags = inspect(text, args.consumer)
        args.record.write_text(json.dumps(abi, indent=1) + "\n")
        print(" ".join(flags))
    else:
        args.source.write_text(mutate(text, args.mode, json.loads(args.record.read_text())))


if __name__ == "__main__":
    main()
