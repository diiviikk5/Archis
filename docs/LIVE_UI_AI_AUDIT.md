# Live workspace and AI audit

## Desktop implementation

Live tracking now uses a compact transport bar, inline measurements, unobstructed
sensor image, a hideable inspector/world tab panel and a vertically resizable chart
strip. Overlay toggles and PNG capture operate on real sensor data. Overlays do not
modify detector input. Native Windows captures were inspected at 1160x740 and
1500x940 logical window sizes, with the host's 125% display scaling. The larger
requested capture was constrained by the physical display, not independently
verified at 1920x1080 logical pixels.

## Previous AI defects

- ONNX inference was real, but convolution and heatmap weights were hand-set.
- The coordinate head was trained against different features than its exported
  inputs, and its output was ignored by the runtime.
- Shape-based decoy rejection was described as neural discrimination.
- Load failure allowed classical detections to be labelled as the AI algorithm.
- Heatmaps were stretched across track gates rather than their actual input ROI.
- Candidate extent, peak and area contained fixed illustrative values.

## Implemented correction

- A replacement CNN trains all convolution weights on 21,600 synthetic patches
  with a reproducible seed. It has one heatmap output, no unused coordinate head.
- OpenCV DNN executes the bundled graph. Location, response, overlay and response
  component extent come from actual input-dependent inference.
- Model identity and training/validation metadata ship beside the ONNX asset.
- Missing, corrupt and runtime-failed models stop ONNX detection with explicit
  status instead of silently masquerading as AI.
- Threshold and shape-filter controls alter the actual processing path. Centroid
  refinement and shape rejection remain explicitly non-neural.

## Evidence and limits

Development validation seed 77031: 163/163 positive patches detected;
33/77 negatives accepted by the raw model, reduced to 6/77 by the shape heuristic.
Decoy rejection must not be advertised as a learned capability.

The subsequent fresh-seed runtime evaluation (918337) used 600 uint8 patches:
200/200 beacons detected, 3/200 streak false positives, 0/200 noise false positives.
Mean detected centroid error was 0.106 px, maximum 0.422 px. See
`AI_VALIDATION.json` for model hash and timings, which vary by hardware and load.

An eight-second synthetic closed-loop AI benchmark passed its five thresholds on
this machine: acquisition 0.33 s, rolling RMS 0.65 px, loss 3.75%, reacquisition
0.30 s and 252.3 processing FPS. This is one scenario, not general certification.

No independent flight-video dataset was validated. Response values are not
calibrated probabilities. Brightest-region acquisition can miss a weaker beacon
beside a brighter distractor. This model is experimental, not flight-ready.
The existing packaged executable has not been rebuilt in this pass.
