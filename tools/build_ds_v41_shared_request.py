#!/usr/bin/env python3
"""Build one source-sized DS deployment for prompt and generation."""
import argparse
import gzip
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from compiler.backends.hbm_sram.request_generation import build_shared_request_deployment
from runtime.abi3.capability import Capability


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ir', type=Path, required=True)
    parser.add_argument('--capability', type=Path, required=True)
    parser.add_argument('--prefill-chunk-tokens', type=int, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('output must be new; historical evidence is immutable')
    data = args.ir.read_bytes()
    graph = json.loads(gzip.decompress(data) if args.ir.suffix == '.gz' else data)
    cap = Capability.from_dict(json.loads(args.capability.read_text()))
    graph, plan, deployment, proof = build_shared_request_deployment(graph, cap,
        prefill_chunk_tokens=args.prefill_chunk_tokens)
    args.out.mkdir(parents=True)
    graph.write(args.out/'request_graph.json')
    plan.write(args.out/'physical_plan.json')
    deployment.write(args.out)
    (args.out/'handoff_dependencies.json').write_text(json.dumps(proof, indent=2)+'\n')


if __name__ == '__main__':
    main()
