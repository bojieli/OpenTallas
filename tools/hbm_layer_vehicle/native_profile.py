"""Serial SU observation ages derived from the native multirate RTL.

This prices a declared return contract. It does not prove the die lanes, PLL
phase, reset epoch, or physical closure which implement that contract.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import re
from pathlib import Path


@dataclass(frozen=True)
class NativePretreeTiming:
    """Measured selected-source pre-tree ingress age; no revision-wide guess."""
    tree_to_reducer: int
    sources: tuple

    @classmethod
    def load(cls, path):
        receipt = json.loads(Path(path).read_text())
        if receipt.get("schema") != "opentallas.hbm.pretree-timing.v1":
            raise ValueError("selected pre-tree timing receipt required")
        if receipt.get("red_command_to_operand_sample") != 1:
            raise ValueError("selected qcore registered command-to-operand age must be one edge")
        age = receipt["join_sample_edge"] - receipt["input_sample_edge"] - 1
        if type(age) is not int or age <= 0 or age != receipt["tree_to_reducer"]:
            raise ValueError("pre-tree age differs from measured sample edges")
        sources = receipt["sources"]
        if set(sources) != {"slice", "join"}:
            raise ValueError("both selected pre-tree source identities required")
        for source in sources.values():
            selected = Path(source["path"])
            if not selected.is_absolute():
                selected = Path(path).resolve().parent / selected
            content = selected.read_bytes()
            if hashlib.sha256(content).hexdigest() != source["sha256"]:
                raise ValueError("selected pre-tree source changed; remeasure its observation age")
            if not re.search(r"\bmodule\s+" + re.escape(source["module"]) + r"\b", content.decode()):
                raise ValueError("measured pre-tree module absent from selected source")
        return cls(age, tuple(sorted((k, v["module"], v["sha256"]) for k, v in sources.items())))

    def as_dict(self):
        return dict(tree_to_reducer=self.tree_to_reducer,
                    sources={k: dict(module=m, sha256=h) for k, m, h in self.sources},
                    scope="selected source functional timing; no physical closure claim")


@dataclass(frozen=True)
class NativeTiming:
    read_return: int
    write_return: int
    # TOK-HBM-SU 2026-10-26: the die's su_<q><g> PIN_REG (pin-registered lanes: lane writes / first output +4 edges,
    # requests +2).  None = the leaf_split_latency environment default (old behaviour); a die contract passes its own.
    pin_reg: object = None

    def __post_init__(self):
        if (type(self.read_return) is not int or type(self.write_return) is not int
                or not 10 <= self.read_return or not 7 <= self.write_return <= self.read_return):
            raise ValueError("native multirate contract requires integer RR>=10 and 7<=WR<=RR")
        if self.pin_reg not in (None, 0, 1):
            raise ValueError("native PIN_REG must be 0 or 1")

    @staticmethod
    def serial_return(stream_return):
        # ot_hbm_su_multirate_bridge / su_multirate_compile.srd
        return (3 * stream_return + 18 + 3) // 4

    @property
    def fill_commit(self):
        # pgslice fd/fr publication followed by pinned-bank input and write.
        return self.serial_return(self.read_return) + 3

    @property
    def drain_done(self):
        # pgslice drain group selection presents the bridge write at E+4.
        return 4 + self.serial_return(self.write_return)

    def as_dict(self):
        return dict(asdict(self), fill_commit=self.fill_commit,
                    drain_done=self.drain_done, multirate=True,
                    topology_qualified=False,
                    source="ot_hbm_su_static_pgslice + ot_hbm_su_multirate_bridge")
