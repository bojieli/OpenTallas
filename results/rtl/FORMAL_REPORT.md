# Public-tool RTL formal campaign

**Overall status:** PASS

This is reproducible methodology evidence for the checked public RTL. It is not product signoff, macro qualification, or proof beyond each recorded bound. CVC4 induction is claimed only where the table explicitly lists a depth.

| Harness | Yosys SAT BMC | CVC4 BMC | Covers | Induction | Result |
|---|---:|---:|---:|---:|---|
| `f_skid_buffer` | 24 | 12 | 8 | bounded only | PASS |
| `f_async_fifo` | 24 | 12 | 14 | bounded only | PASS |
| `f_credit_manager` | 24 | 7 | 10 | 8 | PASS |
| `f_power_controller` | 24 | 12 | 10 | 8 | PASS |
| `f_route_mask` | 24 | 7 | 8 | bounded only | PASS |
| `f_schedule_controller` | 24 | 8 | 10 | bounded only | PASS |
| `f_stage_controller` | 24 | 12 | 18 | bounded only | PASS |

## Solver qualification notes

- The independent configurations are Yosys internal SAT and Yosys SMT2 with CVC4 1.8.
- Z3 4.8.12 was locally non-terminating at useful bounds for these generated models; Ubuntu Boolector 1.5.118 is too old for the interaction. Neither is counted as pass evidence.
- The credit and route CVC4 bounds are intentionally lower than SAT because solver cost rises sharply; the exact depths are part of the claim, not hidden campaign metadata.

## Source manifest

- `rtl/formal/f_async_fifo.sv`: `de23d05e6776da1e5741a0bf3158fba12de65988fc05bdcd83ea057ca10ffdf0`
- `rtl/formal/f_credit_manager.sv`: `b7c18204473b8ed433766ceeeb551ac7d86c4dd863cf312bc9c7c7a08d1c5318`
- `rtl/formal/f_power_controller.sv`: `1c5aac3840038a87fbfecd86725281397b91410bc6ed6aec63a036a85eabfe4b`
- `rtl/formal/f_route_mask.sv`: `dbe5f1a77f20c2dfbf78b873117087f3f9c2bef917f2abe11cc44ebbbbf0d0d7`
- `rtl/formal/f_schedule_controller.sv`: `681c64908e7a9d2ce5e51d7e19c35befea3c615bf63d38245f2919f562428826`
- `rtl/formal/f_skid_buffer.sv`: `fb0a6b160dd39781b7ec44af682a1a007a2b15c08bdba46a8c867d5fa5ea835b`
- `rtl/formal/f_stage_controller.sv`: `888edab61653f0e8ed04183e8b1f0d8b883bce8310df9fcfab1ff92ade87fd83`
- `rtl/lib/ot_async_fifo.sv`: `20d5573aa491e83921f7d6ac9a76961a2b5425b4a710a4364f8f0a326549893e`
- `rtl/lib/ot_skid_buffer.sv`: `4837dc61b4a89a53e68b05f16b46e1717e79f4817bf5b812afba0dc3cd32008a`
- `rtl/ot_credit_manager.sv`: `70ed9c8b70e3658d02b2b9440d2aebb889e9bbdd6d83a7408b6b2bfe951e54fc`
- `rtl/ot_power_reset_controller.sv`: `1c7b187ad1ada1797d66776383270b2017b2625607594eba7013b8ac53627594`
- `rtl/ot_route_mask.sv`: `9da491e18f276a5d6be5c3cf07288bc78d2c75d57d3e4e830b3ea7ce967c4542`
- `rtl/ot_schedule_controller.sv`: `c48a3c3fe43880f4a71b8c5603d49842729056782f929197c8bbb3777a5ac829`
- `rtl/ot_stage_controller.sv`: `3247c350d23c22fa6bf038c0a13a34bc64fc2050fb3417a7758b729b7afcc0b0`
- `spec/VERIFICATION_PLAN.md`: `f6f0cec6430c70b4b61d7cfe14c070212de0bd48bfa99fe6de691568ddd1d208`
- `spec/verification.json`: `1ef9077d39db2f5306ba1e56c19fcb8d83babaa3bfebdc8e0f87e359562a3c86`
- `tools/rtl_campaign.py`: `d615f779635072d6da45dd6b55e9eee76f643be6908ffa31445279ebf184b039`
