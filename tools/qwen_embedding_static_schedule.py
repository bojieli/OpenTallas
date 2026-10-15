#!/usr/bin/env python3
"""Compile reserved embedding reads for ot_qwen_embedding_static_provider.

This emits requests and expected visibility cycles, never embedding payloads.
The consumer must implement W8 x BF16 expansion and VM write visibility itself.
"""
import argparse
import json

ROWS = 151936
WORDS_PER_ROW = 64
READ_INTERVAL = 2
PROVIDER_LATENCY = 28


def compile_row(token: int, first_cycle: int = 0):
    if not 0 <= token < ROWS:
        raise ValueError(f"embedding token out of range: {token}")
    if first_cycle < 0:
        raise ValueError("negative issue cycle")
    requests = [dict(kind=1, address=token, purpose="scale")]
    requests += [dict(kind=0, address=token * WORDS_PER_ROW + chunk,
                      purpose="code", chunk=chunk) for chunk in range(WORDS_PER_ROW)]
    for index, request in enumerate(requests):
        request["issue_cycle"] = first_cycle + index * READ_INTERVAL
        request["response_cycle"] = request["issue_cycle"] + PROVIDER_LATENCY
    return dict(schema="opentallas.qwen.static_embedding_schedule.v1", token=token,
                requests=requests, next_free_issue_cycle=first_cycle + len(requests)*READ_INTERVAL,
                last_response_cycle=requests[-1]["response_cycle"],
                provider="ot_qwen_embedding_static_provider", native_qualified=False,
                remaining_contract="die clock phases/relays and W8 expansion+VM commit must be composed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("token", type=int)
    parser.add_argument("--first-cycle", type=int, default=0)
    args = parser.parse_args()
    print(json.dumps(compile_row(args.token, args.first_cycle), indent=2))


if __name__ == "__main__":
    main()
