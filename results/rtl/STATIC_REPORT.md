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

- Synthesizable RTL/package files inventoried: 77
- Declared modules inventoried: 78
- Stage-top frontend source closure: 15
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
- Every synthesizable source is inventoried. Frontend elaboration in this campaign is intentionally limited to the recorded `ot_stage_top` closure; independent ABI-3, link, ROM-service, and arithmetic tops have separate campaigns.
- The installed Yosys 0.9 cannot parse package functions. The unused CRC package is independently parsed by both language frontends, guarded against synthesis imports, and covered by an expiring waiver.
- CDC/RDC source checks prove declared topology, not metastability MTBF, physical placement, reconvergence timing, or target library cell usage.
- Open-tool results are pre-NDA methodology evidence only.

## Source hashes

- `rtl/abi3/ot_a3_collective_engine.sv`: `0230339aa6ea0d37e4266523863f15431d02f871643ce1e067d8d8872ca007d5`
- `rtl/abi3/ot_a3_dma_index_mover.sv`: `e254421fcba397e3db821c52b9acafaf3922af78653ab2d2e3029705ee166c64`
- `rtl/abi3/ot_a3_engine_array.sv`: `8e8acab89436004d03c6ad98ac229d37c783c27a6907b9043c2d35ab80b287b1`
- `rtl/abi3/ot_a3_engine_pkg.sv`: `a4e78449b610ac226127d5c676b8dfa59659c0122a1d2e62799374da1ec2d892`
- `rtl/abi3/ot_a3_event_scoreboard.sv`: `4140c93d143d53d89f0957f059eb4878df9585f1a961399bd1985d9afb88567b`
- `rtl/abi3/ot_a3_format_pkg.sv`: `dbea89ef9c450d1b9ffda1e578f1685b3e33d3b6f400e43c1784ec022de9e7f0`
- `rtl/abi3/ot_a3_instruction_decoder.sv`: `9f2390ce38f9bddf80d47c01931b6fba5dde6c2f15a3f5fd0ae089e0bf27c3e1`
- `rtl/abi3/ot_a3_link_channel.sv`: `c8856fce3b899cced1d8991f3354b0cc1249f6ee0150dbf6a90635b1f7bdc9da`
- `rtl/abi3/ot_a3_link_endpoint.sv`: `544994b3332313dc43d4ca84548d3946120a4957ec927751eaf9edc16baced0a`
- `rtl/abi3/ot_a3_link_node.sv`: `2a1d8e6fbfc22fb310bb76b89e6e92de30adf32b596c38e019b79f5129779309`
- `rtl/abi3/ot_a3_link_pkg.sv`: `a45b95523f60a1d803233c81b80b96e0351b6280c27ca686fb5dbfc45ea67c91`
- `rtl/abi3/ot_a3_loop_stack.sv`: `c1750bf4b56787239295e4fbef14ec9a948153f7fb0ad88034942f49adf63ca8`
- `rtl/abi3/ot_a3_mac_lane.sv`: `abbfa2b96164190c7730407cface079c728769be65d3188c2ad78f81ed1bbe37`
- `rtl/abi3/ot_a3_mesh_router.sv`: `641857a9f51868feba1438e2589b68d673cd969df1981effeddfda86e92ddb29`
- `rtl/abi3/ot_a3_microsequencer.sv`: `ff439f8a07e08acb9f85e309327170062f090bd7845f323668bb473ce790fc15`
- `rtl/abi3/ot_a3_pkg.sv`: `ac1cfdfae1ff9f108f7ae329fa285d26f5b56f9b4f38da9bef5bc6c534c6f803`
- `rtl/abi3/ot_a3_program_header.sv`: `50fc89219d5460ab45fed1bf40eda07c1d65fab43b9ebe1d5ac80a4aeccdfb42`
- `rtl/abi3/ot_a3_selection_argmax.sv`: `d6dfd8fb62d8b5715cd1a487b74a131c84eb4b73a33cfbbfe0af0919f135e543`
- `rtl/abi3/ot_a3_state_controller.sv`: `3fad395afdf268391c6bf52d1d71be859f0b8d5cb34ca61c09292b09fbf116ea`
- `rtl/abi3/ot_a3_vector_add.sv`: `a6a6516da202ad4dc26bd8a25c4fdac4f5c5b00fe0a934f93db06e04be5baac9`
- `rtl/abi3/ot_a3_view_resolver.sv`: `fad3a54e6b3e5a65db11546625d76c3c4c9c58ffe06f7c4740dd1a0c88001335`
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
- `rtl/ot_bf16_add_rne.sv`: `4ad5938dcd02ec99e08358067e0c755b45d82634642896d7e01fbe20a1cd7233`
- `rtl/ot_bist_controller.sv`: `3fa9513a494171c7f5971c41d7cf292a022e97e87fa90a6e3437e8b7d1627b9f`
- `rtl/ot_cmd_frontend.sv`: `7bab8bfc6e769a6c9ffd80817cab25fb24e31c642fb4210f2ad1f30bca58aaad`
- `rtl/ot_credit_manager.sv`: `4d61c6121b85f599fecd891ac5b4faf234df55e065e17eb28f619968e8720449`
- `rtl/ot_csr_block.sv`: `107553401553638187b4d609f2b8739ca96624af93f11b832f5ebed1f5ba83a9`
- `rtl/ot_dft_controller.sv`: `338dda08b2a6a5f7b83f9bf22a7d866f1ef90c8b39fddfb925cadf07c6d23225`
- `rtl/ot_format_decode.sv`: `b2350b6f961460f709a183a519d67a0d876c527637caf046dd9d6bebcc6ce551`
- `rtl/ot_fp32_rne_pkg.sv`: `3f892e737057cdfb651c0022c913d00f5e1be02b960f9afe9f57b202f1d57fa9`
- `rtl/ot_fp32_rsqrt_rne.sv`: `74ef534d4e0f8f18a74b6df39c885c10e1a12c1ee9c07b9e7bb4d8be9ec90f9b`
- `rtl/ot_hbm_frontend.sv`: `47b8f1def0c75d5cfaf1716f18f07f1f1a9ea4adcfcef214fc483996fd227287`
- `rtl/ot_numeric_dot.sv`: `e7c35364cb3b66ead558f0edb0d682ffd4c47ad22673d924c35bfe5ddebb304c`
- `rtl/ot_power_reset_controller.sv`: `1c7b187ad1ada1797d66776383270b2017b2625607594eba7013b8ac53627594`
- `rtl/ot_ras_controller.sv`: `388d796e7b3f134728d06366982c67bd65ccf1afef96c0a011b253c53fc6f588`
- `rtl/ot_reduction_tree.sv`: `653a1bcc033f8838f31d71220e50e3b38ec4fbf935f6901dd1fb8e6af0c297c5`
- `rtl/ot_rom_macro_periphery.sv`: `bec230456fbdb10ef942046e44a9b42be492d90fc7cb5bf13d3fa78372724bb2`
- `rtl/ot_rom_wrapper.sv`: `dae5ba91f70ea61f3351eb407728e84862b050bfaf936a397534ccc154d7b126`
- `rtl/ot_route_mask.sv`: `4bdf835a9c072bc8d1f13b7de50370ae3b7e1c928f8bb9d6a55a70c64950db0a`
- `rtl/ot_schedule_controller.sv`: `07301550750eeaedceb8116ba9b97bd95fe0c17e84b536020bd0470e3029d826`
- `rtl/ot_session_table.sv`: `f21be6574e78e5e2204bdcea9494458615ac6863c0b2e08c0760d502c245361f`
- `rtl/ot_stage_controller.sv`: `04f23234bb07f79a86d9d71efabcb0acb7d9e033192515b9029e0c9f161856f4`
- `rtl/ot_stage_link_endpoint.sv`: `a6c7540911fde5b4a8e542883077973e254b0f13b570b47f0e83d37e3ac21d50`
- `rtl/ot_stage_link_rx.sv`: `5e50965d50807c8956f7e814656dafff4fca76f9a5bedbb1bc50b7165daec36a`
- `rtl/ot_stage_link_tx.sv`: `fe26c3b031dfc5eeda5073e22ce81f9dd6b2838a3be0b7c0b56c5352d7a12c90`
- `rtl/ot_stage_top.sv`: `c9e0619c962d1e024bebb9a61a3a78d31566d1cc514bf40ca3b3d5bd130088ec`
- `rtl/ot_ta_add_bf16_executor.sv`: `609759d82677ee3e8d486157eb30c5aa3888c942b5aba3343154413a135b68ef`
- `rtl/ot_ta_add_bf16_sram_engine.sv`: `6ea266a72e66454f57f601a593b08d9af6e493b4589ba2c857df7f0cae51e373`
- `rtl/ot_ta_command_decoder.sv`: `181fa72b55c77c41a4cbf368a395afdb3f40d3beea94b245f019eaff4f460908`
- `rtl/ot_ta_dma_add_sequencer.sv`: `9279352a5c3c16b6f72b2011be22777ec10cbacca347b54996432447466cbf80`
- `rtl/ot_ta_dma_hbm_indexed_to_sram.sv`: `e77d538b26fcf847b2b8292b0eeced3ebfa5a54ddada16a0b4d1553000564b5c`
- `rtl/ot_ta_dma_hbm_to_sram.sv`: `c8648ed002944504155f875713d564aca22d3fb202442849d762c88bc9a631ef`
- `rtl/ot_ta_dma_head_rmsnorm_sequencer.sv`: `32fe40e8ee1020f11996c317df197c5573c1c721a193561261d4f752a6ade70f`
- `rtl/ot_ta_dma_matmul_sequencer.sv`: `051af5fec81275904ea8c75c999e51e22d68f315b7de63c86e70cce17a622d9d`
- `rtl/ot_ta_dma_rmsnorm_sequencer.sv`: `979206c49fca3bbe282d9a013e67e93666475bf3acc0b16eb4425c8e4becdfbd`
- `rtl/ot_ta_dma_rope_sequencer.sv`: `a0951264b87efb6c3eca2537e786f19fd41318a413b23a2791209cfe0eea6cc4`
- `rtl/ot_ta_head_rmsnorm_bf16_sram_engine.sv`: `e1bde4ac96c6978a79a30486c776392cb77620c68c650bbf790105d2802d1770`
- `rtl/ot_ta_matmul_bf16_sram_engine.sv`: `dcd89d0b7f048945b072b465fb26846b35bc9e267c3bc91b2e396f39a64b854f`
- `rtl/ot_ta_rmsnorm_bf16_sram_engine.sv`: `e4a3ce5fcd377b657ed785f44f2e2d3d4d10ee991d04b6a31166974247746e93`
- `rtl/ot_ta_rope_bf16_sram_engine.sv`: `efa253668f42a3fc5cbac2f12bbe39ccaa8a3e6f1ac17a1e202c76fefe971369`
- `rtl/ot_tile.sv`: `92f0248dc5f46e94011be658202eb0c7497d28a90cb4906414d0b449829f9f9f`
- `rtl/rom/ot_rom_bank_array.sv`: `69c16973bcfb96a7fefee454773f2bbe37a5815a0c1f21c07cb2f23b9c2e1921`
- `rtl/rom/ot_rom_pkg.sv`: `d42315047ec5cdde55b7a81cf50024b97eb59a53f637fa889593ecbf0e8cea3b`
- `rtl/rom/ot_rom_read_service.sv`: `b7f0dedf7e731ff65af2690a33c30dba7e750c981679f8f8432e66a430befb51`
- `rtl/rom_mac_tile.sv`: `841d5e9ab4c8278c1e7fc7f3f598c5e962041df3d94aa9e0ffb82c6d4f3e5e00`
- `rtl/static_timeslot_switch.sv`: `04f1de6146d694bce80c7fea65e43d73d0a2cb11b7e37f43cbf3e1bab4d574fe`
- `rtl/via_mask_rom.sv`: `203d9950d505fcab97af084746ea696154eada5e2b20282b6f45ff1e8cc78141`
- `spec/CLOCK_RESET_POWER.md`: `d3c23eb1cf27e29e868396a6d87c5bc28089cff7e31407fa4e2b83fe080feaa2`
- `spec/INTERFACES.md`: `09ab47051bbb2bb4492d5a378a2a208291c7a19ceb3501ae968a0c287dd8471e`
- `spec/VERIFICATION_PLAN.md`: `45909ae5b943bb41b911cd6964086f8e8a67a28f9bdebaef77e1fe4a9ef5b419`
- `spec/clock_reset_crossings.json`: `445055e40c862c3bf3439e11c8ddf1dc3b50f4cd964b1729b456283e58cd16cd`
- `spec/rtl_waivers.json`: `56f3aa73a1007f297c5aaaa81fa8cbf6afafb09b5e1c2f13afd1f11af6997c68`
- `tools/rtl_static.py`: `3afb909935cb6eadbd6a89a780c6b855b8c6b79e0db47e3a229e3a8929daf239`
