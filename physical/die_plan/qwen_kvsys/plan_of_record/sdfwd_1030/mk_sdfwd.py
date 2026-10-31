"""DIE-KV-49-SD 2026-10-30: one-block plan fix for kv3_sys_SD / kv3_sys_SD_v1 (12.20 freeze, one-block).
Sets partition_types.<T>.clock.landing_export_form = "fwd_buffer" (FLOW-GEN-2 CTS-0114 opt-in, landing_contract.export_tcl_fwd)
on the two SD types only: their 3 forwarded clock outputs (fclk_out_o_serdes_{W,E}_rx_flit/_tx_up, fclk_out_cland_up,
source clk) are tied onto the clk root net in the default "tie" form -> kits48b kv3_sys_SD_v1 CTS-0114
("Clock fclk_out_o_serdes_E_rx_flit overlaps a previous clock"). Text edit (file layout kept), fail-closed:
the result must differ from the input JSON only in those two keys."""
import json, sys, copy
src, dst = sys.argv[1], sys.argv[2]
text = open(src).read(); P0 = json.loads(text)
TYPES = ("kv3_sys_SD", "kv3_sys_SD_v1")
for t in TYPES:
    c = P0["partition_types"][t]["clock"]
    assert "landing_export_form" not in c, t
    outs = [p["name"] for p in c["landing_contract"]["pins"] if p["kind"] == "clock" and p["dir"] == "out"]
    assert len(outs) == 3, (t, outs)
    key = "\n  \"%s\": {" % t
    assert text.count(key) == 1, t
    i = text.index(key)
    j = text.index("\n   \"clock\": {", i)
    assert j < text.index("\n  \"", i + len(key)), t  # the clock block belongs to this type
    k = j + len("\n   \"clock\": {")
    text = text[:k] + "\n    \"landing_export_form\": \"fwd_buffer\"," + text[k:]
P1 = json.loads(text)
want = copy.deepcopy(P0)
for t in TYPES:
    want["partition_types"][t]["clock"]["landing_export_form"] = "fwd_buffer"
assert P1 == want
open(dst, "w").write(text)
print("SDFWD OK", TYPES)
