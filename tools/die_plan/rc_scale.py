import sys
s=float(sys.argv[1]); out=sys.argv[2]
L={"M1":(7.04175E-02,1e-10),"M2":(2.97127E-02,1.74942E-01),"M3":(3.12870E-02,1.55554E-01),"M4":(1.80365E-02,1.78475E-01),"M5":(1.89935E-02,1.64264E-01),"M6":(1.18796E-02,1.87426E-01),"M7":(1.25096E-02,1.62979E-01),"M8":(8.44765E-03,1.03962E-01),"M9":(8.89556E-03,9.28446E-02)}
V={"V1":1.72E-02,"V2":1.72E-02,"V3":1.72E-02,"V4":1.18E-02,"V5":1.18E-02,"V6":8.20E-03,"V7":8.20E-03,"V8":6.30E-03,"V9":6.30E-03}
with open(out,"w") as f:
  f.write(f"# HBM-CORES 2026-10-25 F2 RC basis: ASAP7 setRC.tcl scaled x{s} (R and C) so GRT/placement estimates match routed RCX clock arrival (tools/die_plan/rc_fit.tcl; argmax fit zero-mean at 0.665)\n")
  for k,(r,c) in L.items(): f.write(f"set_layer_rc -layer {k} -resistance {r*s:.6e} -capacitance {c*s:.6e}\n")
  f.write(f"set_wire_rc -signal -resistance {2.65684E-02*s:.6e} -capacitance {1.65790E-01*s:.6e}\n")
  f.write(f"set_wire_rc -clock -resistance {2.14161E-02*s:.6e} -capacitance {1.45426E-01*s:.6e}\n")
  for k,r in V.items(): f.write(f"set_layer_rc -via {k} -resistance {r*s:.6e}\n")
