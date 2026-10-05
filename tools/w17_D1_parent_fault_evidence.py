"""Read-only classification of retained D1 evidence, never an actual mask oracle."""

def classify(parent, receipt, log, generated_branch, observer):
    if parent.get("runtime_exit") != 1 or receipt.get("exit_code") != 1:
        raise ValueError("expected retained failed runtime")
    if not parent.get("actual_binary_archive_program_hashes_verified"):
        raise ValueError("unverified parent inputs")
    if parent.get("objects_verified") != 3829 or parent.get("object_intersection") != 0:
        raise ValueError("unverified exact object union")
    if "D1_SOURCE_OR_LEDGER_FAULT" not in log:
        raise ValueError("missing actual fatal")
    fields = ("fault_r", "dbg_fs", "violations")
    if any(name not in generated_branch for name in fields) or "VL_STOP_MT" not in generated_branch:
        raise ValueError("missing generated fatal operands")
    if "if(fault)violations[0]<=1" not in observer:
        raise ValueError("observer fault mapping differs")
    return {"union_nonzero": True, "fault_r": None, "dbg_fs": None,
            "violations": None, "actual_masks_available": False,
            "callbacks": {name: sum(line.startswith(name + " ") for line in log.splitlines())
                          for name in ("D1_REAL_ACCEPT", "D1_REAL_RESPONSE", "D1_REAL_WRITER_ACK")},
            "original_PC24_cause": "UNOBSERVED", "fulltoken": False}
