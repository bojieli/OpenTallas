Observed cf1 in enabled TLOAD equivalence fixture
================================================

The raw positive `native_compare_calr2.log` reports cf1 at warm1150,1499,
9000. The first observation precedes the first directed descriptor start at
warm1300. TLOAD_PRODUCER PASS checks table request identity/count/latency,
image readiness and38 starts; it never checks cf. LP_LOCKSTEP PASS checks
equivalence, including equivalently asserted faults. Neither PASS qualifies
a fault-free production programme.

The retained actual TB explains why the fixture cannot provide that claim:
every iteration randomizes fi_pw75, native_ret95, kok/kwd, ss5/ag5, f16_auth83
and f16_obs38. CALRDIR overrides only mu_fault/init/ctx/fab/dh; the random
native_ret[94] foreign-fault input and direct programme PW remain active.
The dh install is not a replacement of the direct pw input. This is random
equivalence stress with a directed CALR sub-check, not a fault-clean source
programme or an intentionally isolated single-negative-control fixture.

Exact retained intel1 `qct10/ctlm/lk_fqreg` source confirms the fault path:

- `ot_qfd_native_cmd_route.sv:16` unconditionally latches native_ret[94]
  into native_fault. Its return bit94 ORs selected fault with native_fault.
- Actual `headprep13/h16za/native32_1r_param.v:628` maps native_ret[94]
  to n_1143. The actual sticky path is u_11850 OR(n_22890,n_1143)→n_22891,
  u_18261 DFF(n_22891)→n_22890. This is not inferred from module names.
- The retained native netlist has a real source-to-c_fault cone:
  u_11851→u_11852→u_18264→u_17777→u_17778→u_17779→u_17780→u_20244→u_11665.
  u_11665 drives n_1591, which is c_fault. The sticky n_22890 feeds u_11852,
  so the captured foreign fault also reaches this cone.
- `qfd_tt_ctlm_dv_lpf_hp13.sv:135` connects that fault to u_go.hr_fault;
  `qfd_tt_ctlm_dv_lpf_hp13_parts.sv:405,422` includes hr_fault in
  core_fault and registers cf=core_fault|c_fault.
- Random PW also feeds the real XPF loader. Its writes to reserved addresses
  can assert loader fault; random F16 inputs have additional fault checks.
  These are additional possible causes, not identified first triggers.

The exact first triggering input/edge cannot be recovered from these logs:
the fixture logs neither generated native_ret/PW/F16 words nor first cf
transition nor its component terms. The first observed assertion is at
warm1150; this is an upper bound on first fault, not its trigger date.
No clock/reset/calendar failure is inferred. A future fault-clean production
proof must select real PW/native-return/F16 sources and observe individual
fault terms and first assertion. Existing TLOAD latency evidence remains
valid locally; global ROOT/X/HEAD leases and fault-clean programme stay open.
No rerun was performed to manufacture missing observations.

QC/SU1 independently confirmed the corresponding readable-source path:
head_static_rk unpacks ret94 into u_me_fault(:545), enabled one-edge
u_su_me_fault(:540) feeds c_me_fault, connected to pi_me_fault(:444).
rom_core_ctrl_static:1288 aliases me_fault=pi_me_fault; :1363..1365 captures
the fault subject to reset/accepted-idle-start clear and enable conditions.
This strengthens the structural cause diagnosis while retaining the exact
first-fault observer limitation; gate/enable conditions prevent claiming an
unobserved exact propagation edge.
