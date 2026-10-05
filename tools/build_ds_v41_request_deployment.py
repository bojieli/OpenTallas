#!/usr/bin/env python3
"""Build a source-sized request deployment without changing the generic CLI."""
import argparse
import gzip
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from compiler.backends.hbm_sram.request_deployment import build_request_deployment
from runtime.abi3.capability import Capability


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ir',type=Path,required=True)
    p.add_argument('--capability',type=Path,required=True)
    p.add_argument('--phase',choices=['decode','prefill'],required=True)
    p.add_argument('--prefill-chunk-tokens',type=int)
    p.add_argument('--prompt-ingestion',action='store_true')
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(argv)
    if a.out.exists():
        p.error('output must be new; historical evidence is immutable')
    cap=Capability.from_dict(json.loads(a.capability.read_text()))
    source = json.loads(gzip.decompress(a.ir.read_bytes())) if a.ir.suffix == '.gz' else a.ir
    graph,plan,deployment=build_request_deployment(source,cap,phase=a.phase,
                               prefill_chunk_tokens=a.prefill_chunk_tokens, prompt_ingestion=a.prompt_ingestion)
    a.out.mkdir(parents=True)
    graph.write(a.out/'request_graph.json')
    plan.write(a.out/'physical_plan.json')
    deployment.write(a.out)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
