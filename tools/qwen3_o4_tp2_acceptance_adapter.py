"""Arithmetic adapter for the Qwen O4 two-reticle signed-INT8 target.

Both dies hold full-row INT8-quantised weight slices and shared BF16 row scales.
Column-parallel matrices use the K split selected by one die's output rows.
For o/down, each die sums its input-column half in FP32; the partials are added
in rank order, and the scale is applied only after that add.  This keeps the
deployed quality emulator's nonlinear and attention arithmetic while changing
its matrix order to the O4 TP-2 contract.
"""
from __future__ import annotations

from types import MethodType

import torch

from tools import qwen3_deployment_quality as Q


def bind_tp2_target(model, groups=6144):
    if model.arith != "contract" or model.wfmt != "w8":
        raise ValueError("TP-2 acceptance adapter requires the w8 contract target")
    modes = {id(model.lm): "column"}
    for layer in model.layers:
        for name in ("qkv", "gu"):
            modes[id(layer[name])] = "column"
        for name in ("o", "down"):
            modes[id(layer[name])] = "row"

    def mv_tp2(self, x, W):
        mode = modes.get(id(W))
        if mode is None:
            raise ValueError("unregistered TP-2 target matrix")
        qT, sT = W["q"], W["s"]
        K, N = qT.shape
        if mode == "column":
            if N % 2:
                raise ValueError("column-parallel matrix needs even output rows")
            s = Q.split_for(N // 2, K, groups)
            return Q.int8_mv_t(x, qT, sT, s)
        if K % 2:
            raise ValueError("row-parallel matrix needs even input columns")
        s = Q.split_for(N, K // 2, groups)
        xb = Q.to_bf16(x)
        half = K // 2
        def partial(xh, wh):
            if xh.is_cuda:
                return Q.chunk_tree_dot_t(xh.t().contiguous()[None], wh[None], s)[0]
            return Q._chunk_tree_dot_ref(xh, wh.t(), s)
        a = partial(xb[:, :half], qT[:half])
        b = partial(xb[:, half:], qT[half:])
        return Q.mul(Q.add(a, b), sT.to(Q.F32).reshape(1, -1))

    model.mv = MethodType(mv_tp2, model)
    model.tp2_acceptance_modes = modes
    model.groups = groups
    return model
