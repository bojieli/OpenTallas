#!/usr/bin/env python3
"""Price the real writer -> distribution -> ownership-mux fixed pipeline.

This emits controller-face core intervals, not HBM command/commit reservations.
Unmeasured physical relay profiles fail closed outside component-test mode.
"""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = (
    "rtl/qwen_sys/static_kv_20261014/qkd_static_writer_ingress.sv",
    "rtl/qwen_sys/static_kv_20261014/qkd_kv_native_programme.sv",
    "rtl/physical/ot_qkd_kv_static_writer_native.sv",
    "rtl/qwen_sys/static_kv_20261014/qkd_kv_static_writer.sv",
)


def compile_ingress(programme, physical_profile=None, *, component_test=False):
    stages = programme.get("stages", [])
    if len(stages) != 36 or [s.get("stage") for s in stages] != list(range(1, 37)):
        raise ValueError("all36 ordered actual writer-stage tables required")
    if programme.get("vmap") != 1:
        raise ValueError(
            "production native writer and independent expectations require explicit VMAP1"
        )
    hashes = {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SOURCES}
    profile = physical_profile or {}
    relay = profile.get("relay_core_edges", 0 if component_test else None)
    if type(relay) is not int or relay < 0:
        raise ValueError("explicit nonnegative implemented relay_core_edges required")
    if not component_test:
        if (
            profile.get("status") != "MEASURED"
            or profile.get("source_sha256") != hashes
        ):
            raise ValueError("source-exact measured physical ingress profile required")
        receipt = ROOT / profile.get("receipt_path", "")
        if not receipt.is_file() or hashlib.sha256(
            receipt.read_bytes()
        ).hexdigest() != profile.get("receipt_sha256"):
            raise ValueError("actual source-bound physical receipt missing or changed")
    if not component_test:
        if programme.get("schema") != "opentallas.qwen-native-kv-programme-all36.v2":
            raise ValueError("actual source-bound native writer programme required")
        for stage in stages:
            source_pins = stage.get("implementation_source_sha256", {})
            if any(source_pins.get(p) != hashes[p] for p in SOURCES[1:]):
                raise ValueError(
                    "native programme source/parameter successor must be recompiled"
                )
        evidence = json.loads(receipt.read_text())
        if (
            evidence.get("status") != "QUALIFIED"
            or evidence.get("source_sha256") != hashes
            or evidence.get("relay_core_edges") != relay
        ):
            raise ValueError(
                "physical receipt does not qualify this exact source/relay profile"
            )
    emitted = []
    for s in stages:
        words = s.get("word_cycles", [])
        if (
            len(words) != 4
            or any(type(x) is not int for x in words)
            or words[0] < 4
            or words != sorted(set(words))
        ):
            raise ValueError("four fixed ascending native word intervals required")
        stop = s.get("stop_cycle")
        if type(stop) is not int or stop < words[-1] + 3:
            raise ValueError(
                "explicit writer stop interval must drain both capture edges"
            )
        high = [words[1], words[3]]
        emitted.append(
            dict(
                stage=s["stage"],
                high_half_intervals=high,
                independent_writer_descriptor_intervals=[x + 2 for x in high],
                controller_face_intervals=[x + 5 + relay for x in high],
            )
        )
    return dict(
        schema="qwen.native-writer-ingress-calendar.v1",
        status="COMPONENT_TEST_NOT_INSTALLABLE"
        if component_test
        else "CONTROLLER_FACE_WITNESS_ONLY",
        source_sha256=hashes,
        vmap=1,
        source_writer_descriptor_edges=2,
        ingress_edges=dict(
            input_pin_capture=1, group_output=1, ownership_mux=1, physical_relays=relay
        ),
        total_added_native_core_edges=3 + relay,
        stages=emitted,
        time_origin="internal accepted writer-programme start; core edge intervals",
        production_qualified=False,
        full_token_qualified=False,
        missing_joins=[
            "actual source programme and root time origin",
            "allincident physical pins/clocks and real relay profile"
            if component_test
            else "full native physical die proof",
            "core-to-HBM phase and actual native-write CDC service",
            "HBM WR reservation, commit and own-row read visibility",
            "actual native ownership enter/leave/drain calendar",
        ],
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--programme", type=Path, required=True)
    p.add_argument("--physical-profile", type=Path)
    p.add_argument("--component-test", action="store_true")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        result = compile_ingress(
            json.loads(a.programme.read_text()),
            json.loads(a.physical_profile.read_text()) if a.physical_profile else None,
            component_test=a.component_test,
        )
    except (ValueError, KeyError) as e:
        result = dict(status="REFUSED", error=str(e), production_qualified=False)
        code = 2
    else:
        code = 0
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
