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
- `rtl/lib/ot_crc32c.sv`: `8cd8dda8419a9268c91ea4fbf0ef76d09e8a18362912728bdf7889b4ac487d09`
- `rtl/lib/ot_crc_pkg.sv`: `49b31710d955827b5beabc9fd63930f1d53c566f925985f16715835ae1ff7d3b`
- `rtl/lib/ot_reset_sync.sv`: `489e493c19aa1260853031fee35c14ea3394ae62ff6853cf7ea407cb8fb78bbd`
- `rtl/lib/ot_skid_buffer.sv`: `4837dc61b4a89a53e68b05f16b46e1717e79f4817bf5b812afba0dc3cd32008a`
- `rtl/lib/ot_sync_bits.sv`: `66f4c78a2fda107046c08c66acd17ed390ee8b884b6e27090db0ecfeae5d2b9f`
- `rtl/lib/ot_sync_level.sv`: `e474cac6feeb0402ac7a4794cfc7e73508b5ef0254c991204b8946b92cd08fd6`
- `rtl/opentallas_tile.sv`: `4980d62d193e1ea44353967b2eace8423d0024562d7f5e40e0d1eec24d6d3bb2`
- `rtl/ot_bist_controller.sv`: `3fa9513a494171c7f5971c41d7cf292a022e97e87fa90a6e3437e8b7d1627b9f`
- `rtl/ot_cmd_frontend.sv`: `7bab8bfc6e769a6c9ffd80817cab25fb24e31c642fb4210f2ad1f30bca58aaad`
- `rtl/ot_credit_manager.sv`: `4d61c6121b85f599fecd891ac5b4faf234df55e065e17eb28f619968e8720449`
- `rtl/ot_csr_block.sv`: `107553401553638187b4d609f2b8739ca96624af93f11b832f5ebed1f5ba83a9`
- `rtl/ot_dft_controller.sv`: `338dda08b2a6a5f7b83f9bf22a7d866f1ef90c8b39fddfb925cadf07c6d23225`
- `rtl/ot_format_decode.sv`: `b2350b6f961460f709a183a519d67a0d876c527637caf046dd9d6bebcc6ce551`
- `rtl/ot_hbm_frontend.sv`: `47b8f1def0c75d5cfaf1716f18f07f1f1a9ea4adcfcef214fc483996fd227287`
- `rtl/ot_numeric_dot.sv`: `e7c35364cb3b66ead558f0edb0d682ffd4c47ad22673d924c35bfe5ddebb304c`
- `rtl/ot_power_reset_controller.sv`: `1c7b187ad1ada1797d66776383270b2017b2625607594eba7013b8ac53627594`
- `rtl/ot_ras_controller.sv`: `388d796e7b3f134728d06366982c67bd65ccf1afef96c0a011b253c53fc6f588`
- `rtl/ot_reduction_tree.sv`: `653a1bcc033f8838f31d71220e50e3b38ec4fbf935f6901dd1fb8e6af0c297c5`
- `rtl/ot_rom_wrapper.sv`: `dae5ba91f70ea61f3351eb407728e84862b050bfaf936a397534ccc154d7b126`
- `rtl/ot_route_mask.sv`: `4bdf835a9c072bc8d1f13b7de50370ae3b7e1c928f8bb9d6a55a70c64950db0a`
- `rtl/ot_schedule_controller.sv`: `07301550750eeaedceb8116ba9b97bd95fe0c17e84b536020bd0470e3029d826`
- `rtl/ot_session_table.sv`: `f21be6574e78e5e2204bdcea9494458615ac6863c0b2e08c0760d502c245361f`
- `rtl/ot_stage_controller.sv`: `04f23234bb07f79a86d9d71efabcb0acb7d9e033192515b9029e0c9f161856f4`
- `rtl/ot_stage_link_endpoint.sv`: `a6c7540911fde5b4a8e542883077973e254b0f13b570b47f0e83d37e3ac21d50`
- `rtl/ot_stage_link_rx.sv`: `5e50965d50807c8956f7e814656dafff4fca76f9a5bedbb1bc50b7165daec36a`
- `rtl/ot_stage_link_tx.sv`: `fe26c3b031dfc5eeda5073e22ce81f9dd6b2838a3be0b7c0b56c5352d7a12c90`
- `rtl/ot_stage_top.sv`: `c9e0619c962d1e024bebb9a61a3a78d31566d1cc514bf40ca3b3d5bd130088ec`
- `rtl/ot_tile.sv`: `92f0248dc5f46e94011be658202eb0c7497d28a90cb4906414d0b449829f9f9f`
- `rtl/rom_mac_tile.sv`: `841d5e9ab4c8278c1e7fc7f3f598c5e962041df3d94aa9e0ffb82c6d4f3e5e00`
- `rtl/static_timeslot_switch.sv`: `04f1de6146d694bce80c7fea65e43d73d0a2cb11b7e37f43cbf3e1bab4d574fe`
- `rtl/via_mask_rom.sv`: `203d9950d505fcab97af084746ea696154eada5e2b20282b6f45ff1e8cc78141`
- `spec/CLOCK_RESET_POWER.md`: `d3c23eb1cf27e29e868396a6d87c5bc28089cff7e31407fa4e2b83fe080feaa2`
- `spec/INTERFACES.md`: `09ab47051bbb2bb4492d5a378a2a208291c7a19ceb3501ae968a0c287dd8471e`
- `spec/VERIFICATION_PLAN.md`: `45909ae5b943bb41b911cd6964086f8e8a67a28f9bdebaef77e1fe4a9ef5b419`
- `spec/clock_reset_crossings.json`: `445055e40c862c3bf3439e11c8ddf1dc3b50f4cd964b1729b456283e58cd16cd`
- `spec/rtl_waivers.json`: `56f3aa73a1007f297c5aaaa81fa8cbf6afafb09b5e1c2f13afd1f11af6997c68`
- `tools/rtl_static.py`: `16012d7b377df9cc6e3a8533876476c6301c3c1310f8621251b0786df5f1cc8e`
