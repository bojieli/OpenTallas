"""Run from this directory; bounded actual-source capsule and rejecting controls."""
from pathlib import Path
import importlib.util
import copy
root = Path(__file__).resolve().parents[2]
sp = importlib.util.spec_from_file_location("kit_core_clocks", root / "tools/die_plan/kit_core_clocks.py")
m = importlib.util.module_from_spec(sp)
sp.loader.exec_module(m)
cs = [{"inst": i, "module": "ot_hgi_sm_xload_cl2_bdring", "native_port_adapter": {"slice": {"bsel": {"msb": 24, "lsb": 0, "source_width": 26, "evidence": "results/brmw_pin_1106/event.json"}}}} for i in ["u_xq_Q_p0_bd", "u_xq_Q_p1_bd"]]
checks = 0
for t in ["nw", "ne"]:
    s = (Path(__file__).parent / f"brmw_native_{t}_capsule.sv").read_text()
    a, rr = m.adapt_core_ports(s, cs)
    assert len(rr) == 2 and a.count(".bsel(w_u_xl_Q_ctl_q1_bsel[24:0])") == 2
    assert "wire [25:0] w_u_xl_Q_ctl_q1_bsel;" in a
    assert m.adapt_core_ports(s, []) == (s, [])
    checks += 3
    for bad in [s.replace("wire [25:0]", "wire [24:0]"), s.replace("wire [25:0]", "wire [0:25]"), s.replace("w_u_xl_Q_ctl_q1_bsel[25:0])", "w_u_xl_Q_ctl_q1_bsel[24:0])"), s.replace(".bsel(w_u_xl_Q_ctl_q1_bsel[25:0]),", "")]:
        try:
            m.adapt_core_ports(bad, cs)
        except ValueError:
            checks += 1
        else:
            raise AssertionError("invalid source accepted")
    one = copy.deepcopy(cs)
    for c in one:
        c["native_port_adapter"]["slice"]["bsel"].update(msb=0, lsb=0)
    a, _ = m.adapt_core_ports(s, one)
    assert a.count(".bsel(w_u_xl_Q_ctl_q1_bsel[0:0])") == 2
    checks += 1
print(f"PASS {checks} native-capsule/default/width/missing/range/one-bit checks")
