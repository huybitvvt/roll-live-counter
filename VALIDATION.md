# Validation — 0.1.0

This file distinguishes verified software behavior from unverified vision accuracy.

## Scope

The bundled model is pretrained YOLOE-11s-seg with six roll/shape prompts baked into
ONNX. It has NOT been fine-tuned on factory rolls. No roll ReID model is supplied.
Generic HOG/color descriptors trigger manual review; they are not evidence of a
unique identity. No accuracy percentage on the user's factory is claimed.

Tests with scripted detections verify identity/counting logic, not the ability
of the detector to find the user's rolls. Still-image inference cannot verify
occlusion handling across video. A successful installation does not establish
24/24 reliability.

## Verification to record

- 19 tests pass: cumulative identities, five old rolls moved and five new rolls
  revealed, lost-ID review, explicit manual merge/new/ignore, co-visibility
  constraints, persistence, region membership, capacity, reset audit, CSV,
  BoT-SORT integration, low-confidence track confirmation, slow CPU with known
  camera continuity, and Unicode/BOM settings. Capture epochs distinguish a real
  source interruption from a long interval between inference results.
- Native capture process receives 30 increasing frame sequences from a generated
  1280x720 video, queue capacity 2, process exits with code 0.
- Real ONNX CPU execution and decoding succeeded. On a code-drawn scene containing
  eight illustrated rolls, the full view at the selected threshold missed them;
  the region-crop pass found four. This is a detector limitation, not an eight-roll
  accuracy success. Raw real-scene snippets were also tried locally; no recall or
  accuracy metric is claimed from them.
- Source UI smoke run with the real model confirms four identities, retains them,
  and saves two opt-in dataset images. Inference including full + crop passes is
  approximately 2.0–2.2 seconds per update on the development Intel i3-1215U CPU
  with two ONNX threads. The requested scan rate is a cap, not a guaranteed FPS.
- Slow results are shown on the exact analyzed image on request; old boxes are
  not painted over a different live image. Screenshot uses only the code-drawn input.
- Frozen executable passes the real-model UI smoke test: four confirmed identities,
  three opt-in sample images, and successful shutdown. Eight embedded application
  modules were compared to the public Python sources and match structurally.
  PyTorch and Ultralytics runtime are excluded. Latest frozen full + crop update
  measured 869 ms on the development CPU; timing varies with system load.
- Windows installer ran silently as a normal user into an isolated test directory,
  returned exit code 0 and required no restart. The installed EXE has SHA-256
  `ec113803c8dbf482138097bd1bcd8e994dca372a1bdf1d8825e16a650472cead`,
  identical to the checked frozen EXE. Its real-model UI run confirmed four
  identities and saved three opt-in images, then exited successfully.
- The published installer was downloaded through an unauthenticated HTTPS request.
  Its 176,802,808 bytes match SHA-256
  `732dd2473eb6b02d3f4e6697df5f2d0037d9478406d58fe54f63b6aeb27c18ba`.
  Public repository visibility was checked without authentication. The release
  contains `SHA256SUMS.txt` and `verification.json`.

## Not verified

- Detection recall, false positives, count error or identity switches on factory video.
- Hardware camera/RTSP device compatibility at the factory.
- Long-run 24/72-hour memory, thermal and recovery performance.
- Whether visually identical rolls can be identified after complete occlusion.
