# Third-party components

The application source is AGPL-3.0-or-later. The bundled model is an export of
Ultralytics YOLOE-11s-seg, licensed under AGPL-3.0. It uses the official pretrained
weights with roll-related text prompts fused at build time. No factory fine-tuning
has been performed. Full corresponding application source and build scripts are
available at https://github.com/huybitvvt/roll-live-counter.

- Ultralytics / YOLOE: https://github.com/ultralytics/ultralytics (AGPL-3.0).
- Roboflow Trackers: https://github.com/roboflow/trackers (Apache-2.0), BoT-SORT implementation.
- Supervision: https://github.com/roboflow/supervision (MIT).
- ONNX Runtime: https://github.com/microsoft/onnxruntime (MIT).
- OpenCV: https://github.com/opencv/opencv (Apache-2.0), opencv-python packaging licenses included.
- NumPy (BSD-3-Clause), SciPy (BSD-3-Clause), Pillow (HPND), Matplotlib (PSF-based),
  Python (PSF), Tcl/Tk (BSD-style), PyAV/FFmpeg and transitive dependencies:
  full notices from installed distributions are included under assets/licenses.
- PyInstaller's bootloader exception allows distribution of the bundled program
  under the application's license.

PyTorch, the text encoder and Ultralytics Python runtime are used only to produce
the exported model and are excluded from the installer. No cloud inference API
is used. The app icon is drawn by the supplied preparation script.
