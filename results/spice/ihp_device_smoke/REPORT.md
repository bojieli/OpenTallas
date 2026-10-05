# IHP SG13G2 official-device and portable-OSDI smoke campaign

**Status:** PASS  
**Evidence class:** public-PDK official-device model smoke; not ROM PPA or silicon  
**PDK:** IHP Open PDK v0.3.0 / SG13G2 public preview

## Portable model compilation

| Model | Source SHA-256 | OSDI bytes | OSDI SHA-256 | Compile warnings | Replay |
|---|---|---:|---|---:|---|
| `psp103` | `127be82891919323e60eec7ae02b0c034b396800884e8daf5561c9d3588684ba` | 725,928 | `97b6aeb215fbe98b6cb6ad71e4fbf50a468955e8530895e75cd603b09ef21091` | 0 | byte-identical |
| `psp103_nqs` | `5612aa9e75aa467e320f19db7cc40f01dbb9a81212e9660e3939cf3bc2cac00d` | 1,124,704 | `e82230ea41719cac2d9bfccf06d235d4a7d6b0530d9383af2ea4d6cb33b1f84d` | 0 | byte-identical |
| `r3_cmc` | `398746f45048a9e075913e85a982258b929c9042257339bf1fc47d7e25303551` | 117,144 | `ad6b78a518677111dccc920007b9a7b2024d2625383fd8311ebc336a1522c009` | 3 | byte-identical |
| `mosvar` | `146eec0c2a9c3c437c53109f8ec42af68f75bd9d341e79797d2feda0340a19f6` | 101,536 | `b62bae8ecbdada070a4c6524b015b11a69e0810a26f76873954b8175fa90eb12` | 0 | byte-identical |

All modules were compiled twice with `-D__NGSPICE__ --target_cpu generic` 
outside the immutable PDK checkout. The three R3_CMC diagnostics are the 
declared upstream `$simparam` constant warnings; no other compile warning is accepted.

## Official low-voltage CMOS smoke result

| Measure | Value |
|---|---:|
| DC output, input low | 1.199998 V |
| DC output, input high | 1.924622e-07 V |
| Transient output low | 1.924775e-07 V |
| Transient output high | 1.197298 V |
| High-to-low delay | 49.792 ps |
| Low-to-high delay | 179.691 ps |

The simple 10-fF inverter uses the official `sg13_lv_nmos` and 
`sg13_lv_pmos` wrappers at the public `mos_tt` corner, 1.2 V and 27 °C. 
These values are a tool/model sanity check only.

## Claim boundary

This establishes a pristine, reproducible IHP device-model path before the 
independent physical ROM replication. It does not establish a ROM cell, compact 
array, density, read path, yield, target-node scaling, wafer behavior, or GPU speedup. 
No result may be scaled into N7 or N4.

Exact commands, identities, hashes, thresholds, replay status, and logs are in 
`results/spice/ihp_device_smoke/device_smoke.json` and its `artifacts/` directory.
