# Compact199 BF direct die geometry

`--bf-hier-compact --bf-hier-height 198.72` now reserves two 1.188 um die seam channels. The existing 1002.888 um pair width holds two 450.144 um columns and the 100.224 um front. The east column stays MY. No cluster parent is created.

The generated planning masters use the closed views' exact rectangles for each currently transported bit: 842 column pins and 2162 front pins. This corrects the previous planning model's column clock/reset faces, qy fault feedback face and frontend FP8 pin faces. The modeled seams have 1552 same-track M4 bits, no jog, and a maximum endpoint distance of 1.326 um. `python3 tools/s81/bf_direct_audit.py --out <record>` checks those facts; a shifted-track mutant fails.

These planning masters remain placeholders for timing. This change does not bind or qualify a closed view: child access defects and the native BF16 transport are still open. The front's 1069 uncovered native pins are enumerated by port in geometry.json (1068 functional BF transport pins plus hph, a HALF=0 diagnostic). BF family control and the complete BF16 stream must reach this assembly from the production PQ broadcast before full native die release.

The v17 recipe needs `--elem-h 207.36` to hold the closed 198.72 um body and its existing 8.64 um halo requirement. A full geometry screen is running under ot-run on EPYC1; this record covers exact assembly geometry only, not full die legality or STA.
