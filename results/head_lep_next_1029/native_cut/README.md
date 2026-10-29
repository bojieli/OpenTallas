# Natural HEAD endpoint and credit cuts: source preparation

The two die-local wrappers preserve the existing HEAD CORE_CRED=12, REACH=2,
CH_BOARD=700, CHB=1 profile. No state or cycle is added. They do not yet replace
the original parent or constitute qualified physical views.

- `ot_s81hd_ep_native`: original safe4 endpoint with exact derived parameters,
  private constant CHB=1, and originally unconnected statistics omitted. Its
  closure is endpoint safe4, CRC32 and oldread_b64; 36 native256x64 SRAMs,
  11,353 mapped flops in the original LEP placement.
- `ot_s81hd_credit_native`: original credit ingress and egress together, 9 native
  32x64 SRAMs, 1,749 ingress and 563 egress mapped flops. Existing parent g_lo2,
  up gating, reset tree and reverse/PHY relays remain outside this boundary.

`leaf_profiles.json` in the parent directory records original derived parameters,
ports, source closure and SRAM instances. The full fixed endpoint was flattened
with Yosys proc/opt and native SRAM blackboxes: every exposed input bit is
consumed, every exposed output bit is variable. `ep_context_mask.json` has no
unused or constant exposed bits; no physical input tie or inferred pin pruning
is justified. The full gearbox-facing 595/53 frames remain in both directions.

`prepare_miter.py` generates independent direct original-module references for
both wrappers. Verilator native SRAM models passed 1,024 random input cycles,
including initial and midrun resets. A ready-polarity mutant was caught at cycle20.
This checks wrapper wiring/profile; original source logic is unchanged. Run used
intel2 ot-run unit oth-ubuntu-356076-1793273772, runtime
`/srv/opentallas-scratch2/claude/codex-head-lep-next/native_cut`.

No P&R or STA launched. Trial7's actual full-LEP channel G1 failure remains open.
Endpoint macro area alone is51,484um², requiring a dataflow-local register/macro
placement model; an outline-only reach assertion cannot qualify it. Parent
composition and native views must be reviewed before replacing current cores.
