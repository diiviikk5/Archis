"""Fresh-seed synthetic evaluation of the bundled runtime, without training dependencies."""
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from archis_tracker.core.ai_detector import NanoSpotDetector


def main():
    detector = NanoSpotDetector()
    if not detector.is_loaded:
        raise RuntimeError(detector.status)
    rng = np.random.default_rng(918337)
    yy, xx = np.mgrid[:64, :64]
    counts = {name: {'samples': 0, 'detections': 0} for name in ('beacon', 'streak', 'noise')}
    errors, latency = [], []
    for index in range(600):
        label = ('beacon', 'streak', 'noise')[index % 3]
        x, y = rng.uniform(8, 56, 2)
        sigma = rng.uniform(1.4, 3.2)
        patch = rng.normal(rng.uniform(0.02, 0.12), rng.uniform(0.01, 0.06), (64, 64))
        if label == 'beacon':
            patch += rng.uniform(0.55, 0.95) * np.exp(-((xx-x)**2+(yy-y)**2)/(2*sigma**2))
        elif label == 'streak':
            angle = rng.uniform(0, np.pi)
            rx = (xx-x)*np.cos(angle)+(yy-y)*np.sin(angle)
            ry = -(xx-x)*np.sin(angle)+(yy-y)*np.cos(angle)
            patch += rng.uniform(0.55, 0.95)*np.exp(-(rx**2/(2*1.5**2)+ry**2/(2*9**2)))
        start = time.perf_counter()
        result = detector.detect_spot(np.clip(patch*255, 0, 255).astype(np.uint8))
        latency.append((time.perf_counter()-start)*1000)
        counts[label]['samples'] += 1
        counts[label]['detections'] += int(result[0])
        if label == 'beacon' and result[0]:
            errors.append(float(np.hypot(result[1]-x, result[2]-y)))
    report = dict(seed=918337, model_sha256=hashlib.sha256(Path(detector.model_path).read_bytes()).hexdigest(),
                  counts=counts, mean_detected_centroid_error_px=float(np.mean(errors)),
                  max_detected_centroid_error_px=float(max(errors)),
                  mean_inference_and_postprocess_ms=float(np.mean(latency)),
                  limitations='Synthetic patches, not flight data. Includes non-neural shape filter. No calibrated confidence claim.')
    path = Path(__file__).resolve().parents[1] / 'docs' / 'AI_VALIDATION.json'
    path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
