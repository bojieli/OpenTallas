"""Exclude proven input/input aliases from derived physical core-hop contracts."""
import re
from pathlib import Path


def lef_directions(path):
    directions, pin = {}, None
    for line in Path(path).read_text().splitlines():
        words = line.split()
        if not words:
            continue
        if words[0] == "PIN" and len(words) > 1:
            pin = re.sub(r"\[\d+\]$", "", words[1])
        elif words[0] == "DIRECTION" and pin:
            direction = words[1].rstrip(";")
            previous = directions.setdefault(pin, direction)
            if previous != direction:
                raise ValueError(f"inconsistent bus direction: {path}:{pin}")
        elif words[0] == "END" and len(words) > 1 and words[1] != "PORT":
            pin = None
    return directions


def filter_shared_inputs(partition_type, connections, repo):
    directions = {h["inst"]: lef_directions(Path(repo) / h["lef"])
                  for h in partition_type["hard_cores"] if h.get("lef")}
    result = {}
    for core, ports in connections.items():
        for pin, targets in ports.items():
            kept = []
            for target in targets:
                kind, _, other = target.partition(":")
                reciprocal = [q for q, ts in connections.get(other, {}).items() if "core:" + core in ts]
                shared_input = (kind == "core" and directions.get(core, {}).get(pin) == "INPUT"
                                and reciprocal and all(directions.get(other, {}).get(q) == "INPUT"
                                                       for q in reciprocal))
                if not shared_input:
                    kept.append(target)
            if kept:
                result.setdefault(core, {})[pin] = kept
    return result
