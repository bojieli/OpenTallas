# Public-tool RTL static, CDC, and RDC campaign

**Overall status:** PASS

This campaign closes the checked public RTL against the recorded open-tool policy. It does not replace target-qualified lint, CDC/RDC, UPF, macro, PDK, or foundry signoff.

## Frontends and structural checks

| Case | Result |
|---|---|
| `verilator_stage_strict` | PASS |
| `verilator_legacy_strict` | PASS |
| `iverilog_stage_elaboration` | PASS |
| `iverilog_legacy_elaboration` | PASS |
| `yosys_stage_check` | PASS |
| `yosys_legacy_check` | PASS |

## Inventory and crossing closure

- Synthesizable RTL/package files inventoried: 35
- Declared modules inventoried: 35
- Stage-top ports classified: 76/76
- Explicit CDC/RDC crossings mapped: 12
- Source structural invariants passed: 26/26
- Immutable ROM wrappers with no write path: 3/3

The structural invariant set checks synchronizer attributes, binary-reflected Gray equations, coupled FIFO reset and online rendezvous, four-phase mailbox request/acknowledge/online structure, stable payload assignment topology, and asynchronous-assert/synchronous-release reset conditioning.

## Findings and waivers

| Tool | Category | Location | Disposition | Waiver |
|---|---|---|---|---|
| iverilog | array_sensitivity | `rtl/ot_session_table.sv:66` | waived | `WVR-IVERILOG-SESSION-ARRAY-001` |
| iverilog | array_sensitivity | `rtl/ot_credit_manager.sv:41` | waived | `WVR-IVERILOG-CREDIT-ARRAY-001` |
| iverilog | array_sensitivity | `rtl/ot_credit_manager.sv:60` | waived | `WVR-IVERILOG-CREDIT-ARRAY-001` |
| yosys | frontend_exclusion | `rtl/lib/ot_crc_pkg.sv` | waived | `WVR-YOSYS09-PACKAGE-001` |

Owned waivers consumed: 3. Unowned, ambiguous, expired, and stale waivers are campaign failures. Icarus unpacked-array sensitivity expansion notices are retained in evidence rather than hidden. Yosys memory-to-register lowering messages are recorded as transformations, then the lowered netlist must pass `check -assert`.

## Evidence boundary

- Verilator and Icarus are independent parser/elaboration frontends; Yosys is the independent structural netlist frontend.
- The installed Yosys 0.9 cannot parse package functions. The unused CRC package is independently parsed by both language frontends, guarded against synthesis imports, and covered by an expiring waiver.
- CDC/RDC source checks prove declared topology, not metastability MTBF, physical placement, reconvergence timing, or target library cell usage.
- Open-tool results are pre-NDA methodology evidence only.

## Source hashes

- `rtl/expert_mask_controller.sv`: `a565b4506035093960577415ed9d2b26224a9e49650c4fe7e78b070d7b2b4a57`
- `rtl/lib/ot_async_fifo.sv`: `18704d1313cc07a04642412e544da5dba26cd5bff349d75a479d64e8d02cdcb5`
- `rtl/lib/ot_cdc_mailbox.sv`: `f3fecaea6089477d6349144d76406e5dbd90740e127067301c352c3ebdbe2e76`
- `rtl/lib/ot_crc16_ccitt.sv`: `bc70fe269d5736df24a90e738a41ceb6dd833e161b7f7121161090cf43071f3c`
- `rtl/lib/ot_crc32c.sv`: `b564fc88e04d4e0629c8836bb610f06d652a3d029140df634bc64e130fdd36d5`
- `rtl/lib/ot_crc_pkg.sv`: `49b31710d955827b5beabc9fd63930f1d53c566f925985f16715835ae1ff7d3b`
- `rtl/lib/ot_reset_sync.sv`: `489e493c19aa1260853031fee35c14ea3394ae62ff6853cf7ea407cb8fb78bbd`
- `rtl/lib/ot_skid_buffer.sv`: `4837dc61b4a89a53e68b05f16b46e1717e79f4817bf5b812afba0dc3cd32008a`
- `rtl/lib/ot_sync_bits.sv`: `66f4c78a2fda107046c08c66acd17ed390ee8b884b6e27090db0ecfeae5d2b9f`
- `rtl/lib/ot_sync_level.sv`: `e474cac6feeb0402ac7a4794cfc7e73508b5ef0254c991204b8946b92cd08fd6`
- `rtl/opentallas_tile.sv`: `4980d62d193e1ea44353967b2eace8423d0024562d7f5e40e0d1eec24d6d3bb2`
- `rtl/ot_bist_controller.sv`: `364b3f867eeab129c54452bd46a4cf17a2e254ad452088b97848d8db69833b9e`
- `rtl/ot_cmd_frontend.sv`: `c380640877ff163d160e08534b7cbfbbd0e2fcc7601d1d46e59ce0544d722eeb`
- `rtl/ot_credit_manager.sv`: `4d61c6121b85f599fecd891ac5b4faf234df55e065e17eb28f619968e8720449`
- `rtl/ot_csr_block.sv`: `02fd9176782ca64533809dac4fc565e3c3708ce7e4977fa3896636e162d7a60a`
- `rtl/ot_dft_controller.sv`: `338dda08b2a6a5f7b83f9bf22a7d866f1ef90c8b39fddfb925cadf07c6d23225`
- `rtl/ot_format_decode.sv`: `0c309df0061f2270bb4a67157399ef00efb6563d8e64aa7a9abf41727301b847`
- `rtl/ot_hbm_frontend.sv`: `fd32a301bee0a5a5d379014fcf9c97a54500183217ff7290e5c7a4b4f706c153`
- `rtl/ot_numeric_dot.sv`: `355292201f4686aa1bae65ca62e8fbdf44a22d06b722ef0559d6143d79f7a773`
- `rtl/ot_power_reset_controller.sv`: `1c7b187ad1ada1797d66776383270b2017b2625607594eba7013b8ac53627594`
- `rtl/ot_ras_controller.sv`: `74c38119a23689cc24ccb76a0921a97be3844590d30e944f9b325ba3f84c5914`
- `rtl/ot_reduction_tree.sv`: `d8b28fb2f84cb7d0f53fd7c4ae42294d11d48cd92e15d3e2584c8b763a286962`
- `rtl/ot_rom_wrapper.sv`: `6a7b73f1877693b7dbd93e610fd5dd55f70415e395c5691724656024c175d11b`
- `rtl/ot_route_mask.sv`: `9da491e18f276a5d6be5c3cf07288bc78d2c75d57d3e4e830b3ea7ce967c4542`
- `rtl/ot_schedule_controller.sv`: `07301550750eeaedceb8116ba9b97bd95fe0c17e84b536020bd0470e3029d826`
- `rtl/ot_session_table.sv`: `f21be6574e78e5e2204bdcea9494458615ac6863c0b2e08c0760d502c245361f`
- `rtl/ot_stage_controller.sv`: `8a0eb66a48c8198211a34b04c465a715bfb9fc072854a4f70e27cfa4e3c11fef`
- `rtl/ot_stage_link_endpoint.sv`: `a6c7540911fde5b4a8e542883077973e254b0f13b570b47f0e83d37e3ac21d50`
- `rtl/ot_stage_link_rx.sv`: `07c3f90ef5dbac2b9b703d6cc2e24e972d73999833511be3e399ebc6ec01cbc7`
- `rtl/ot_stage_link_tx.sv`: `264edfe8dce50f79bee74aedc851adf32d65a0056299fbaebb8a32272eb46e45`
- `rtl/ot_stage_top.sv`: `c9e0619c962d1e024bebb9a61a3a78d31566d1cc514bf40ca3b3d5bd130088ec`
- `rtl/ot_tile.sv`: `6af21d4151ddff242b43aacf7f41af1ec191fdbc215162acd99dcabf9a8a793d`
- `rtl/rom_mac_tile.sv`: `841d5e9ab4c8278c1e7fc7f3f598c5e962041df3d94aa9e0ffb82c6d4f3e5e00`
- `rtl/static_timeslot_switch.sv`: `7ccc523874a1074f17a7ee53a496400574b99c3e2831f04c3bf9b688354fb619`
- `rtl/via_mask_rom.sv`: `203d9950d505fcab97af084746ea696154eada5e2b20282b6f45ff1e8cc78141`
- `spec/CLOCK_RESET_POWER.md`: `64e9e13e2be44325f62cb2cdf64a26cd806990903a92808d2707c7b45e44d100`
- `spec/INTERFACES.md`: `c1d2e15b5f2209c788cb08894cd1ff576a543aada79107b04ede50a3ea3bb79e`
- `spec/VERIFICATION_PLAN.md`: `f6f0cec6430c70b4b61d7cfe14c070212de0bd48bfa99fe6de691568ddd1d208`
- `spec/clock_reset_crossings.json`: `445055e40c862c3bf3439e11c8ddf1dc3b50f4cd964b1729b456283e58cd16cd`
- `spec/rtl_waivers.json`: `56f3aa73a1007f297c5aaaa81fa8cbf6afafb09b5e1c2f13afd1f11af6997c68`
- `tools/rtl_static.py`: `16012d7b377df9cc6e3a8533876476c6301c3c1310f8621251b0786df5f1cc8e`
