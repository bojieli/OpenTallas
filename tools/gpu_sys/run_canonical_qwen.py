"""Execute the complete released Qwen program through an attached RTL backend.

The backend factory builds the original checkpoint-backed machine and supplies
native_module, byte_module, machine and transport. It must connect persistent
KV/state to that transport. This launcher never starts or terminates a simulator
and never substitutes software arithmetic for an unavailable RTL operator.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path
import time

from tools.h4_qwen_released_provider_delivery import ReleasedProviderDelivery, wire_encode


def run(args):
    if not args.enable_canonical_qwen:
        raise ValueError("canonical Qwen RTL execution is default off")
    if args.out.exists():
        raise ValueError("output already exists; retain the previous run and choose a new output")
    module, separator, name = args.backend.partition(":")
    if not separator or not module or not name:
        raise ValueError("backend must be module:factory")
    # Factory owns the actual simulator bindings and original checkpoint loader.
    backend_args = argparse.Namespace(**{k: v for k, v in vars(args).items() if k != "expected_token"})
    backend = getattr(importlib.import_module(module), name)(backend_args)
    required = ("native_module", "byte_module", "machine", "transport")
    if not isinstance(backend, dict) or any(k not in backend for k in required):
        raise ValueError("backend must supply native_module, byte_module, machine, transport")
    delivery = ReleasedProviderDelivery(*(backend[k] for k in required), enabled=True).attach()
    started = time.monotonic()
    completed = 0

    def progress(op, store):
        nonlocal completed
        completed += 1
        print(json.dumps(dict(event="source_command_complete", pc=op["pc"],
                              completed=completed, elapsed_seconds=time.monotonic() - started)), flush=True)

    result = delivery.run_full_token(args.token, args.position, observer=progress)
    if not isinstance(result, dict) or result.get("next_token") != args.expected_token:
        raise ValueError("complete RTL token differs from the released-checkpoint reference")
    record = dict(status="complete", program_sha256=delivery.transport.native_dispatch_program_sha256,
                  source_commands=len(delivery.machine.done), input_token=args.token,
                  position=args.position, expected_token=args.expected_token, result=wire_encode(result),
                  delivery_counts=delivery.counts, elapsed_seconds=time.monotonic() - started)
    # Publishing completion happens only after the original full-token method
    # has checked all commands, deliveries and persistent-memory enrollment.
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_name(args.out.name + ".tmp")
    with temporary.open("w") as stream:
        json.dump(record, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, args.out)
    print(json.dumps(dict(event="full_token_complete", record=str(args.out))), flush=True)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable-canonical-qwen", action="store_true")
    parser.add_argument("--backend", required=True, help="actual simulator factory module:function")
    parser.add_argument("--token", type=int, required=True)
    parser.add_argument("--position", type=int, required=True)
    parser.add_argument("--expected-token", type=int, required=True,
                        help="released-checkpoint reference next token; never supplied to the RTL backend as an operand")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--released-source-root", type=Path,
                        default=Path("/home/ubuntu/OpenTallas-qwen-trained-native-execution"),
                        help="unchanged original 870c5fe runtime checkout for the released factory")
    parser.add_argument("--socket", type=Path, help="existing simulator socket, if used by backend")
    args = parser.parse_args()
    if args.token < 0 or args.position < 0 or args.expected_token < 0:
        parser.error("token, position and reference token must be nonnegative")
    run(args)


if __name__ == "__main__":
    main()
