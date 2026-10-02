"""Offline verification of the one approved D1 debugger capture."""
import re


def verify_capture(receipt, log):
    captures = re.findall(r"D1_ACTUAL_FATAL_MASK fault_r=0x([0-9a-f]+) dbg_fs=0x([0-9a-f]+) violations=0x([0-9a-f]+)", log)
    if len(captures) != 1:
        raise ValueError("exactly one actual mask capture required")
    masks = dict(zip(("fault_r", "dbg_fs", "violations"),
                     (int(v, 16) for v in captures[0])))
    if masks != receipt.get("actual_masks") or not any(masks.values()):
        raise ValueError("nonzero fatal operand capture mismatch")
    if masks["fault_r"] > 255 or masks["dbg_fs"] > 0xffffff or masks["violations"] > 255:
        raise ValueError("mask outside actual field width")
    if receipt.get("inferior_exit_code") != 1 or "D1_SOURCE_OR_LEDGER_FAULT" not in log:
        raise ValueError("original runtime failure not preserved")
    if receipt.get("GDB_exit_code") != 0:
        raise ValueError("debugger did not finish normally")
    if receipt.get("input_postcheck") is not True or receipt.get("input_hashes_before") != receipt.get("input_hashes_after"):
        raise ValueError("immutable input postcheck failed")
    if receipt.get("simulator_launches") != 1 or receipt.get("compiler_or_link_launches") != 0:
        raise ValueError("approved execution count mismatch")
    if receipt.get("runtime_qualification") is not False or receipt.get("fulltoken") is not False:
        raise ValueError("diagnostic failure cannot qualify runtime or fulltoken")
    return {"actual_masks": masks, "fatal_union_nonzero": True,
            "WINDOW_kv_fault_bit_observed": bool(masks["fault_r"] & 0x40),
            "original_PC24_cause": "UNOBSERVED", "service_bound": "BOUND_MISSING",
            "row0_invalid_directly_observed": False}
