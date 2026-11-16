"""FLOW-HEALTH-1 11-15 (FABLE-FLOW-2000 a/b/c): replay of the 11-15 log lines.
(a) the key reads the kit's own spec + normalised error, on every FAIL;  (b) a class the preflight does not test releases only when the die's
inputs change;  (c) one error is one class key (item names, numbers, paths stripped)."""
import json
import kit_wave as KW
import flow_guard as FG

STALE = "INFRA: infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: ValueError: STALE-CORE-VIEW ot_s%dcfg%d_seq_bfp: lib /srv/opentallas-scratch2/claude/x%d/y.lib sha %s != sha 12ab"
SDC = "INFRA: infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: sdc_lint.SdcLintError: type slice_station__t%d: constraint.sdc fails sdc_lint (%d): clocks"
ROAM = "FLOW: unclassified failure @kit_rtl (see log): KW_ROAM kit_rtl: ran on %s, outputs copied back to epyc%d"
BIND = "FLOW: unclassified failure @kit_rtl (see log): bind.py: error: unrecognized arguments: --src-tree /srv/opentallas-scratch2/claude/k%d/src"
ATTR = "INFRA: infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: AttributeError: module 'gen_phys' has no attribute 'tap_%d'"


def test_c_one_error_is_one_key():
    ks = {FG.norm_class("INFRA", STALE % (i, i + 3, i, "ab%dcdef0123" % i)) for i in range(12)}
    assert len(ks) == 1
    assert len({FG.norm_class("INFRA", SDC % (i, 40 + i)) for i in range(12)}) == 1
    assert len({FG.norm_class("FLOW", ROAM % (h, i)) for h in ("epyc7", "intel1", "epyc9") for i in range(9)}) == 1
    assert len({FG.norm_class("FLOW", BIND % i) for i in range(9)}) == 1
    assert len({FG.norm_class("INFRA", ATTR % i) for i in range(9)}) == 1
    # different errors stay different
    assert len({FG.norm_class("INFRA", STALE % (1, 1, 1, "aabbccdd0011")), FG.norm_class("INFRA", SDC % (1, 1)), FG.norm_class("FLOW", BIND % 1),
                FG.norm_class("FLOW", ROAM % ("epyc7", 1))}) == 4
    assert FG.norm_class("FLOW", ROAM % ("epyc7", 1)).endswith("no error line (progress text only)")
    assert FG.pf_kind(FG.norm_class("INFRA", ATTR % 1)) == "skew"                   # the preflight kinds still read the key
