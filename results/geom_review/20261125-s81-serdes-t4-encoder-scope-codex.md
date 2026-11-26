# S81 SerDes t4 scoped encoder CTS screen

2026-11-25 PST. Reviewed the exact retained SerDes t4 placed floorplan and density views linked from the 60→85 µm CTS review. This arm reuses the same placed checkpoint, PMA seats and R11 proxy reset selection. The north PMA wall channels and center block ends remain the dense regions. Extending the pair distance only for equal encoder-instance and bit keys within d2–d5 avoids extending searches around unrelated macro and reset logic in these regions.

Release a private CTS comparison with global 60 µm and the scoped 85 µm encoder distance. Compare identical post-hook phase reports, reset removal, FF cross-tap hold, setup and maximum measured tap fanout. Full route requires further placed clock and pin access evidence.
