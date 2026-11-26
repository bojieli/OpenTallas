"""FLOW-GEN-2 CTS-0114 (DIE-HEAD-14/15/17): opt-in forwarded-clock export buffer and tap pass-through of hard-core
island ft clock inputs.  The export form defaults to fwd_buffer since AUTOBUILD-PIPE-3 10-31 (explicit "tie" = legacy
text); tap_passthrough stays opt-in."""
import copy
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import landing_contract as LC  # noqa: E402
import schema  # noqa: E402


class _P:
    def __init__(self, clock):
        self.types = {"T": {"clock": clock}}


PINS = [{"name": "fclk_out_o", "kind": "clock", "dir": "out", "source_clock_port": "clk"},
        {"name": "clk_in_l", "kind": "clock", "dir": "in"}]
LEGACY = ("set cland_block [ord::get_db_block]\n"
          "set cland_dst [$cland_block findBTerm {fclk_out_o}]\n"
          "set cland_src [$cland_block findBTerm {clk}]\n"
          'if {$cland_dst eq "NULL" || $cland_src eq "NULL"} { error "clock landing export endpoint missing" }\n'
          "set cland_net [$cland_src getNet]\n"
          'if {$cland_net eq "NULL"} { error "clock landing source tap has no physical net" }\n'
          "$cland_dst disconnect\n$cland_dst connect $cland_net\n$cland_net setSigType CLOCK\n"
          "puts {OT_CLAND_EXPORT fclk_out_o <- clk}\n")


def test_explicit_tie_export_is_byte_identical_legacy():
    assert LC.export_tcl(_P({"landing_contract": {"pins": PINS}, "landing_export_form": "tie"}), "T") == LEGACY


def test_default_export_is_fwd_buffer():
    """AUTOBUILD-PIPE-3 10-31: the tie text always hits TritonCTS CTS-0114 under the kit SDC generated export clock,
    so an unset form is the fwd_buffer form (byte-identical to the explicit opt-in)."""
    dflt = LC.export_tcl(_P({"landing_contract": {"pins": PINS}}), "T")
    assert dflt == LC.export_tcl(_P({"landing_contract": {"pins": PINS}, "landing_export_form": "fwd_buffer"}), "T")
    assert dflt != LEGACY and "$cland_dst connect $cland_fn" in dflt
    assert LC.export_form(_P({"landing_contract": {"pins": PINS}}), "T") == "fwd_buffer"


def test_fwd_buffer_export_keeps_port_off_the_root_net():
    s = LC.export_tcl(_P({"landing_contract": {"pins": PINS}, "landing_export_form": "fwd_buffer"}), "T")
    # the CTS-0114 cause: the port BTerm joined onto the source (root) net
    assert "$cland_dst connect $cland_net" not in s
    assert "[$cland_i findITerm A] connect $cland_net" in s
    assert "set cland_i [odb::dbInst_create $cland_block $cland_m {cland_fwd_fclk_out_o}]" in s
    assert "set cland_fn [odb::dbNet_create $cland_block {cland_fwd_net_fclk_out_o}]" in s
    assert "ot_cland_existing $cland_i $cland_m $cland_net $cland_dst {cland_fwd_net_fclk_out_o}" in s
    assert "$cland_dst connect $cland_fn" in s
    assert f"findMaster {{{LC.FWD_BUFFER_MASTER}}}" in s
    assert "ot_cland_drop_orphan $cland_old" in s and "is not a buffer" in s
    assert "clk_in_l" not in s and s.count("dbInst_create") == 1
    # TritonCTS must be free to rewire the forward buffer input (ODB-0370 on dont_touch)
    assert "setDoNotTouch" not in s


def test_unknown_export_form_fails_closed():
    with pytest.raises(ValueError):
        LC.export_tcl(_P({"landing_contract": {"pins": PINS}, "landing_export_form": "wire"}), "T")


def test_schema_declares_both_opt_ins():
    ck = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    assert ck["landing_export_form"] == {"enum": ["tie", "fwd_buffer"]}
    assert ck["tap_passthrough"] == {"type": "boolean"}


_MOCK = r'''
namespace eval sta {}
set ::rs ""
proc sta::redirect_string_begin {} {set ::rs ""}
proc sta::redirect_string_end {} {return $::rs}
proc get_pins {p} {return $p}
proc report_edges {args} {
  set p [lindex $args end]
  if {[dict exists $::edges $p]} {append ::rs [dict get $::edges $p]} else {error "no pin $p"}
}
# root net -> hard core ft_ck0_i (comb to ft_ck0_o) and a flop; ft_ck0_o net -> flop f2;
# hard core u_hc/clk_i (setup check) stays a sink
set ::edges [dict create u_hc/ft_ck0_i "ft_ck0_i -> ft_ck0_o combinational\n  ^ -> ^ 5:5\n" \
  u_hc/clk_i "clk_i -> d_i setup\n  ^ -> ^ 3:3\nclk_i -> q_o rising_edge\n  ^ -> ^ 40:40\n"]
proc mk {name body} {proc $name {m args} $body}
mk root {switch $m {getName {return root} getITerms {return {i_ft i_ck i_f1}}}}
mk ftnet {switch $m {getName {return ftnet} getITerms {return {i_f2}}}}
mk i_ft {switch $m {getMTerm {return mt_ft} getInst {return u_hc} getNet {return root}}}
mk i_ck {switch $m {getMTerm {return mt_ck} getInst {return u_hc} getNet {return root}}}
mk i_fo {switch $m {getMTerm {return mt_fo} getInst {return u_hc} getNet {return ftnet}}}
mk i_f1 {switch $m {getMTerm {return mt_ff} getInst {return f1}}}
mk i_f2 {switch $m {getMTerm {return mt_ff} getInst {return f2}}}
mk mt_ft {switch $m {getIoType {return INPUT} getName {return ft_ck0_i}}}
mk mt_ck {switch $m {getIoType {return INPUT} getName {return clk_i}}}
mk mt_fo {switch $m {getIoType {return OUTPUT} getName {return ft_ck0_o}}}
mk mt_ff {switch $m {getIoType {return INPUT} getName {return CLK}}}
mk u_hc {switch $m {getName {return u_hc} getMaster {return m_hc} findITerm {if {[lindex $args 0] eq "ft_ck0_o"} {return i_fo}; return NULL}}}
mk f1 {switch $m {getName {return f1} getMaster {return m_ff}}}
mk f2 {switch $m {getName {return f2} getMaster {return m_ff}}}
mk m_hc {switch $m {getName {return hc} isBlock {return 1}}}
mk m_ff {switch $m {getName {return DFFHQNx1_ASAP7_75t_R} isBlock {return 0}}}
'''


def _procs(names):
    text = (HERE / "tap_balance.tcl").read_text()
    out = []
    for n in names:
        m = re.search(r"^proc " + n + r" \{.*?^\}\n", text, re.S | re.M)
        assert m, n
        out.append(m.group(0))
    return "".join(out)


def _sinks(env_on):
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    script = _MOCK + _procs(["tb_is_buf", "tb_passthru", "tb_sinks"]) + "puts [lsort [tb_sinks root]]\n"
    env = {k: v for k, v in os.environ.items() if not k.startswith("OT_TAP_")}
    if env_on:
        env["OT_TAP_PASSTHRU"] = "1"
    r = subprocess.run(["tclsh"], input=script, text=True, capture_output=True, env=env)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip().splitlines()


def test_tap_sinks_unchanged_by_default():
    # legacy: the island ft pass-through input is measured as a sink (OT_CLOCK_FAMILY then stops on it)
    assert _sinks(False)[-1] == "f1/CLK u_hc/clk_i u_hc/ft_ck0_i"


def test_tap_passthru_follows_combinational_ft_pin_only():
    out = _sinks(True)
    assert out[-1] == "f1/CLK f2/CLK u_hc/clk_i"
    assert any(l.startswith("OT_TAP_PASSTHRU u_hc/ft_ck0_i -> ft_ck0_o") for l in out)


def test_gen_phys_exports_passthru_only_when_planned():
    s = (HERE / "gen_phys.py").read_text()
    assert 'if t.get("clock", {}).get("tap_passthrough"):' in s
    assert 'cfg.append("export OT_TAP_PASSTHRU = 1")' in s


# ---- KV-HUB-LEG405 11-26: optional forwarded-export relays (pin.export_relay_xy_um) ---------------------------------------
def _relay_pins(rel):
    return [{"name": "fclk_out_o", "kind": "clock", "dir": "out", "source_clock_port": "clk", "export_relay_xy_um": rel}]


def test_relay_export_chains_bufx6f_between_buffer_and_port():
    s = LC.export_tcl(_P({"landing_contract": {"pins": _relay_pins([[10.5, 3.25], [20.0, 4.0]])}}), "T")
    assert s.count("dbInst_create") == 3 and s.count(LC.FWD_RELAY_MASTER) == 1 + 0 or LC.FWD_RELAY_MASTER in s
    assert "{cland_rly_fclk_out_o_0}" in s and "{cland_rly_fclk_out_o_1}" in s
    assert "$cland_dst connect $cland_fn" not in s and "$cland_dst connect $cland_prev" in s
    assert s.index("cland_rly_net_fclk_out_o_0") < s.index("cland_rly_net_fclk_out_o_1") < s.index("$cland_dst connect $cland_prev")
    assert "ot_cland_existing_relay $cland_i $cland_m $cland_net $cland_dst {cland_fwd_net_fclk_out_o} {cland_rly_fclk_out_o_0 cland_rly_fclk_out_o_1} $cland_rm" in s
    assert "2 BUFx6f_ASAP7_75t_R relay(s)" in s
    # every generated braces/brackets balance as complete Tcl
    if shutil.which("tclsh"):
        r = subprocess.run(["tclsh"], input="puts [info complete {" + s.replace("{", "\\{").replace("}", "\\}") + "}]\n", text=True, capture_output=True)
        assert r.returncode == 0, r.stderr


def test_unrelayed_export_text_unchanged_by_relay_support():
    s = LC.export_tcl(_P({"landing_contract": {"pins": PINS}}), "T")
    assert "relay" not in s and "cland_rm" not in s and "cland_dbu" not in s


class _Q:
    def __init__(self, pins, w=100.0, h=100.0):
        self.types = {"T": {"outline_um": [w, h], "clock": {"landing_contract": {"pins": pins}}}}


def test_check_export_relays_rejects_bad_declarations():
    ok = LC.check_export_relays(_P({}) if False else _Q([{"name": "x", "kind": "clock", "dir": "in", "export_relay_xy_um": [[1, 1]]}]))
    assert any("non forwarded-clock output" in e for e in ok["errors"])
    bad = LC.check_export_relays(_Q([{"name": "x", "kind": "clock", "dir": "out", "export_relay_xy_um": [[1]]}]))
    assert any("finite [x,y]" in e for e in bad["errors"])
    out = LC.check_export_relays(_Q([{"name": "x", "kind": "clock", "dir": "out", "export_relay_xy_um": [[500, 1]]}]))
    assert any("outside the type outline" in e for e in out["errors"])
    assert LC.check_export_relays(_Q([{"name": "x", "kind": "clock", "dir": "out"}])) == {"errors": [], "legs": []}


_RELAY_MOCK = r'''
set ::log {}
proc L {m} {lappend ::log $m}
proc mkobj {name body} {proc $name {m args} $body}
namespace eval ord {}
namespace eval odb {}
proc ord::get_db_block {} {return blk}
proc ord::get_db {} {return db}
mkobj db {switch $m {findMaster {set n [lindex $args 0]; return m_$n}}}
foreach mn {BUFx24_ASAP7_75t_R BUFx6f_ASAP7_75t_R} {mkobj m_$mn "switch \$m {getWidth {return 1000} getHeight {return 270} getName {return $mn}}"}
mkobj ca {switch $m {xMin {return 0} xMax {return 3000000} yMin {return 0} yMax {return 2000000}}}
mkobj bb {switch $m {xMin {return 1000000} xMax {return 1001000} yMin {return 20000} yMax {return 20270}}}
mkobj net_src {switch $m {setSigType {L "sig src $args"} getName {return clk}}}
mkobj bt_src {switch $m {getNet {return net_src} getBBox {return bb}}}
mkobj bt_dst {switch $m {getNet {return NULL} disconnect {L "dst disconnect"} connect {L "dst connect $args"}}}
mkobj blk {switch $m {findBTerm {if {[lindex $args 0] eq "fclk_out_o"} {return bt_dst}; return bt_src} findInst {return NULL} getCoreArea {return ca} getDbUnitsPerMicron {return 1000}}}
set ::n 0
proc odb::dbInst_create {blk master name} {set o inst_$name; mkobj $o "switch \$m {setLocation {L \"$name loc \$args\"} setPlacementStatus {} findITerm {return it_${name}_\[lindex \$args 0\]}}"
 foreach p {A Y} {mkobj it_${name}_$p "switch \$m {connect {L \"$name.$p connect \$args\"}}"}
 L "create $name [$master getName]"; return $o}
proc odb::dbNet_create {blk name} {set o net_$name; mkobj $o "switch \$m {setSigType {} getName {return $name}}"; L "net $name"; return $o}
'''


def test_relay_export_executes_against_a_mock_odb_chain():
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    pins = _relay_pins([[1762.911, 17.145], [1800.0, 20.0]])
    tcl = LC.export_tcl(_P({"landing_contract": {"pins": pins}}), "T")
    r = subprocess.run(["tclsh"], input=_RELAY_MOCK + tcl + "\nforeach l $::log {puts $l}\n", text=True, capture_output=True)
    assert r.returncode == 0, r.stderr
    out = r.stdout.splitlines()
    want = ["create cland_fwd_fclk_out_o BUFx24_ASAP7_75t_R", "create cland_rly_fclk_out_o_0 BUFx6f_ASAP7_75t_R",
            "cland_rly_fclk_out_o_0.A connect net_cland_fwd_net_fclk_out_o",
            "create cland_rly_fclk_out_o_1 BUFx6f_ASAP7_75t_R",
            "cland_rly_fclk_out_o_1.A connect net_cland_rly_net_fclk_out_o_0",
            "dst connect net_cland_rly_net_fclk_out_o_1"]
    assert [l for l in out if l in want] == want
    # relay sites are centred (um * 1000 dbu minus half the 1000x270 master)
    assert "cland_rly_fclk_out_o_0 loc 1762411 17010" in out
