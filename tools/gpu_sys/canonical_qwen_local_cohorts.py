"""Local endpoint0/3 responders for Euclid's actual enclosing top.

Call source_files() to add one new RTL file; no simulator, memory, ready/fence
oracle, host parent ledger, native arithmetic or synthetic retirement callback.
Connect query/response lanes to reader_services cohorts0/3. Stage root_accept
is the actual scratch-using command admission per rank*32+SM, not every child
service handshake. Retire is that SAME retained owner55's execution retirement
once all scratch children/returns finish. It is not persistent RF-version free.
State root_accept/retire span the WHOLE source byte RPC, including multisector
OLD/NEW state operations; individual sector replies cannot retire a root early.
Root admit permits gate the real NEW command accept symmetrically. Never mask
continuation requests or reverse responses: credit would otherwise deadlock.

All quiet signals must wire actual router/service/observer/STATE tap registers
and held receipt producers. No constant idle/all-ones/elapsed delay or foreign
RF/payload/CDC cohort authority. The local cohorts run on their source streaming
clock; Euclid must use actual existing CDC enrollment where crossing clocks.
Cold POR only; warm reset pauses retained roots/queries, never resets por_n.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TOP='ot_gpu_qwen_kv_local_cohorts'
def source_files(root=ROOT):
    return (Path(root)/'rtl/model/qwen_kv_connections_20261003'/ (TOP+'.sv'),)
def endpoint_lanes():
    return dict(stage=0,metadata=3)
