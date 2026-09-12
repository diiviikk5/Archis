"""Train all convolution weights on synthetic patches; export OpenCV-compatible ONNX.

Training dependencies: torch and onnx. Neither is required by the desktop runtime.
This is a synthetic-domain model, not a validated flight-data detector.
"""
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import onnx
from onnx import helper, numpy_helper, TensorProto
import torch
from torch import nn
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from archis_tracker.core.ai_detector import NanoSpotDetector


def batch(rng, count):
    yy, xx = np.mgrid[:64, :64]
    x = rng.uniform(7, 57, (count, 1, 1))
    y = rng.uniform(7, 57, (count, 1, 1))
    sigma = rng.uniform(1.4, 3.2, (count, 1, 1))
    kind = rng.choice(3, count, p=[0.7, 0.15, 0.15])
    signal = np.exp(-((xx-x)**2 + (yy-y)**2) / (2*sigma**2))
    truth = np.exp(-((xx-x)**2 + (yy-y)**2) / (2*2.0**2))
    angle = rng.uniform(0, np.pi, (count, 1, 1))
    rx = (xx-x)*np.cos(angle)+(yy-y)*np.sin(angle)
    ry = -(xx-x)*np.sin(angle)+(yy-y)*np.cos(angle)
    signal[kind == 1] = np.exp(-(rx**2/(2*1.5**2)+ry**2/(2*9**2)))[kind == 1]
    signal[kind == 2] = 0
    truth[kind != 0] = 0
    image = signal * rng.uniform(0.55, 0.95, (count, 1, 1))
    image += rng.uniform(0.01, 0.12, (count, 1, 1))
    image += rng.normal(size=image.shape) * rng.uniform(0.01, 0.06, (count, 1, 1))
    return np.clip(image[:, None], 0, 1).astype('float32'), truth[:, None].astype('float32'), kind, x.ravel(), y.ravel()


def main():
    torch.set_num_threads(4)
    torch.manual_seed(20260912)
    rng = np.random.default_rng(20260912)
    net = nn.Sequential(nn.Conv2d(1, 8, 5, padding=2), nn.ReLU(),
                        nn.Conv2d(8, 8, 5, padding=2), nn.ReLU(),
                        nn.Conv2d(8, 1, 1), nn.Sigmoid())
    optimizer = torch.optim.Adam(net.parameters(), lr=0.003)
    for step in range(900):
        images, targets, *_ = batch(rng, 24)
        output = net(torch.from_numpy(images))
        target = torch.from_numpy(targets)
        loss = ((output-target).square() * (1+30*target)).mean()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        if step % 150 == 0:
            print(f'step={step} loss={loss.item():.5f}', flush=True)
    net.eval()
    nodes, weights = [], []
    previous = 'input'
    for index, layer in enumerate(net):
        output = 'heatmap' if index == 5 else f'layer{index}'
        if isinstance(layer, nn.Conv2d):
            w, b = f'weight{index}', f'bias{index}'
            weights.extend([numpy_helper.from_array(layer.weight.detach().numpy(), w),
                            numpy_helper.from_array(layer.bias.detach().numpy(), b)])
            pad = layer.padding[0]
            nodes.append(helper.make_node('Conv', [previous, w, b], [output],
                                          kernel_shape=list(layer.kernel_size), pads=[pad]*4))
        else:
            nodes.append(helper.make_node('Relu' if isinstance(layer, nn.ReLU) else 'Sigmoid', [previous], [output]))
        previous = output
    graph = helper.make_graph(nodes, 'archis_learned_heatmap',
        [helper.make_tensor_value_info('input', TensorProto.FLOAT, [1, 1, 64, 64])],
        [helper.make_tensor_value_info('heatmap', TensorProto.FLOAT, [1, 1, 64, 64])], weights)
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 13)], producer_name='archis_synthetic_training')
    model.ir_version = 8
    onnx.checker.check_model(model)
    binary = model.SerializeToString()
    runtime = cv2.dnn.readNetFromONNX(np.frombuffer(binary, dtype=np.uint8))
    images, _, kind, xs, ys = batch(np.random.default_rng(77031), 240)
    detector = NanoSpotDetector(model_path='__validation_no_model__')
    detector.net, detector.is_loaded = runtime, True
    errors, false_positives, detected = [], 0, 0
    pipeline_false_positives, pipeline_positives = 0, 0
    for image, label, x, y in zip(images, kind, xs, ys):
        runtime.setInput(image[None])
        heat = runtime.forward('heatmap')[0, 0]
        py, px = np.unravel_index(heat.argmax(), heat.shape)
        if label == 0:
            errors.append(float(np.hypot(px-x, py-y)))
            detected += int(heat.max() >= 0.5)
        else:
            false_positives += int(heat.max() >= 0.5)
        result = detector.detect_spot(image[0], min_confidence=0.5, enable_decoy_filter=True)
        if label == 0:
            pipeline_positives += int(result[0])
        else:
            pipeline_false_positives += int(result[0])
    report = dict(training_seed=20260912, validation_seed=77031, training_steps=900,
                  training_examples=21600, validation_examples=240,
                  positive_examples=int(sum(kind == 0)), negative_examples=int(sum(kind != 0)),
                  detected_positives=detected, false_positives=false_positives,
                  pipeline_positives=pipeline_positives, pipeline_false_positives=pipeline_false_positives,
                  mean_peak_error_px=float(np.mean(errors)), max_peak_error_px=float(max(errors)),
                  model_type='synthetic-trained CNN', sha256=hashlib.sha256(binary).hexdigest(),
                  limitations='Synthetic patches only; response is uncalibrated. Shape rejection is a separate heuristic.')
    print(json.dumps(report, indent=2), flush=True)
    if pipeline_positives / sum(kind == 0) < 0.95 or np.mean(errors) > 1.0 or pipeline_false_positives / sum(kind != 0) > 0.1:
        raise RuntimeError('Validation gate failed; existing model not replaced')
    destination = Path(__file__).resolve().parents[1] / 'archis_tracker' / 'models' / 'nanospot_net.onnx'
    destination.write_bytes(binary)
    destination.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
