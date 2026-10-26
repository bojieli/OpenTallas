Actual adjacent-pair physical mechanism, corrected native RC

The final native replay uses actual4W NDR and standard per-layer resistance (automatic NDR R credit once), plus profile C×1.3. TT/FF related-pair damage2.723272/2.453934ps PASS; insertion86.61..88.40/70.56..72.20ps, maxslew26.75/23.68ps. GRToverflow0. The earlier2.110/1.895 row and native4w/native8w sample files are retained diagnostics from manually divided R, which investigation found to double-count NDR width in the current binary. They do not override this corrected result.

Source physical_clock_pair.py b5e7625a4:3BUFx24,2clock stages/tap, actual276.48µm/branch, maxleg138.24µm,0data cycles, core/PHY keepouts cleared. Scope: local pair only. Native missing-segment import control failsGRT0263 before RC estimation. ODB+global-route-segments replay reproduces initial native SPEF byte-for-byte.
