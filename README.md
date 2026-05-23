# GestureRecognizer

A lightweight, real-time hand gesture recognition system that runs on standard CPUs — no GPU required. Built as the implementation for the paper *"A Lightweight and Robust Framework for Real-Time Gesture Recognition and Control"* (IEEE Access, submitted).

**84.46% validation accuracy · ~0.3 ms mean inference latency · 2.3 MB model size**

---

## Overview

Most robust gesture recognition systems either require powerful GPUs (hybrid CNN-RNN models) or sacrifice reliability by misclassifying everyday hand movements as commands. This project addresses both problems with a single-model pipeline:

- **Feature-first approach**: Extracts MediaPipe hand landmarks instead of processing raw video pixels, yielding a compact 175-dimensional feature vector.
- **Bidirectional GRU**: Captures temporal dynamics of gesture sequences efficiently.
- **Large Margin Cosine Loss (LMCL)**: Trains the model to explicitly reject non-gesture movements — achieving **95% recall on the negative class** and minimizing false positives.
- **ONNX + INT8 quantization**: Post-training optimization reduces the model from 15.2 MB to 2.3 MB and cuts mean inference latency by ~34×.

---

## Recognized Gestures

The model classifies 11 gesture classes (reduced from the Jester dataset's original 27 via semantic grouping):

| Gesture | Gesture |
|---|---|
| Swiping Left | Swiping Right |
| Swiping Up | Swiping Down |
| Zooming In | Zooming Out |
| Pushing Hand Away | Stop Sign |
| Turning Hand Clockwise | Turning Hand Counterclockwise |
| **Negative (No Gesture)** | — |

The "Negative" class merges the original *"Doing other things"* and *"No gesture"* categories. The model is explicitly trained to score this class high for ambient, non-intentional hand movements.

---

## Project Structure

```
GestureRecognizer/
├── config.json                        # Paths to data, models, and reports
├── setup.json                         # Hyperparameters (edit this to retrain)
├── demo.py                            # Live webcam demo using PyTorch model
├── demo_onnx.py                       # Live webcam demo using ONNX model (recommended)
│
├── data/
│   └── raw/
│       ├── jester-v1-labels.csv       # Jester dataset labels
│       └── map-to-names.json          # Label ID → gesture name mapping
│
├── models/
│   ├── gesture_model.pth              # Trained PyTorch checkpoint
│   ├── gesture_model_fp32.onnx        # ONNX model (FP32)
│   ├── gesture_model_quant.onnx       # ONNX model (INT8 quantized) ← use this
│   ├── gesture_mapping.json           # Model output index → class mapping
│   └── hand_landmarker.task           # MediaPipe hand landmark model
│
├── preprocessing/                     # Offline data processing notebooks & scripts
│   ├── DatasetExtractor.ipynb         # Stage 1: Extract frames from Jester videos
│   ├── MediaPipeLandmarker.ipynb      # Stage 1: Run MediaPipe to get landmarks
│   ├── HDF5_converter.ipynb           # Stage 1: Consolidate .npy files into HDF5
│   ├── EDA.ipynb                      # Exploratory data analysis
│   ├── generate_kinematic.py          # Stage 2: Normalized kinematic features
│   ├── MotionVector.py                # Stage 2: First-order motion vectors
│   ├── FingertipsDistance.py          # Stage 2: Wrist-to-fingertip distances
│   ├── generate_wrist_context.py      # Stage 2: Raw wrist screen coordinates
│   ├── generate_hard_negatives.py     # Generate hard negative samples
│   └── Merger.ipynb                   # Merge feature HDF5 files
│
├── scripts/
│   ├── export_to_onnx.py              # Export trained PyTorch model to ONNX
│   └── quantize_model.py              # Apply INT8 dynamic quantization
│
├── src/gesture_recognizer/
│   ├── data/
│   │   └── dataloader.py              # JesterDataset + collate function
│   ├── models/
│   │   ├── gesture_model.py           # GestureGRU architecture
│   │   ├── losses.py                  # CosineMarginLoss (LMCL) implementation
│   │   └── inference_model.py         # Inference wrapper
│   ├── training/
│   │   ├── train_model.py             # Main training script
│   │   └── prune_model.py             # Structured pruning (optional)
│   ├── evaluation/
│   │   ├── evaluate_onnx_model.py     # Evaluate ONNX model on validation set
│   │   └── generate_report.py         # Generate per-class classification report
│   └── utils/
│       ├── mappings.py                # Label grouping and mapping utilities
│       └── demo_helpers.py            # Live feature preprocessing helpers
│
└── reports/                           # Saved evaluation CSV reports
```

---

## Installation

### Prerequisites

- Python 3.9+
- A webcam (for the live demo)
- Conda (recommended)

### Setup

**1. Clone the repository:**
```bash
git clone https://github.com/your-username/GestureRecognizer.git
cd GestureRecognizer
```

**2. Create and activate the Conda environment:**
```bash
conda env create -f environment.yml
conda activate gesture-recognizer
```

**3. Install the package in editable mode:**
```bash
pip install -e .
```

---

## Quick Start: Live Demo

Pre-trained models are included in the `models/` directory. You can run the demo immediately without any training.

**Recommended — ONNX (INT8 quantized, fastest):**
```bash
python demo_onnx.py models/gesture_model_quant.onnx
```

**FP32 ONNX:**
```bash
python demo_onnx.py models/gesture_model_fp32.onnx
```

**PyTorch model:**
```bash
python demo.py
```

Press `q` to quit. A performance report (mean latency, CPU usage) is printed on exit.

---

## Model Architecture

The core model is `GestureGRU`, a single bidirectional GRU followed by an MLP projection head:

```
Input Sequence  [Batch, Seq_Len, 175]
       ↓
2-Layer Bidirectional GRU  (hidden_size=92 per direction)
       ↓
Concatenated Hidden State  [Batch, 184]
       ↓
Linear(184 → 256) → ReLU → Dropout(0.42) → Linear(256 → 52)
       ↓
Feature Embedding  [Batch, 52]
       ↓
L2-Normalize → Cosine Similarity with L2-Normalized Class Weights
       ↓
Logits  [Batch, 11]
```

**Loss function — Large Margin Cosine Loss (LMCL / CosFace):**

$$L_i = -\log \frac{e^{s(\cos\theta_{y_i} - m)}}{e^{s(\cos\theta_{y_i} - m)} + \sum_{j \neq y_i} e^{s\cos\theta_{ji}}}$$

where `s=30.0` (scale) and `m=0.35` (margin) are the optimized hyperparameters. This forces the model to learn well-separated class clusters in the angular feature space, which is the key mechanism enabling robust rejection of non-gesture movements.

---

## Feature Engineering

Each input frame produces a **175-dimensional feature vector** assembled from four parallel streams:

| Feature Set | Dimensions | Description |
|---|---|---|
| Kinematic (normalized landmarks) | 63 | 21 landmarks × 3D, translated to wrist origin and scale-normalized |
| Motion Vectors | 63 | Frame-to-frame difference of normalized landmarks |
| Geometric (fingertip distances) | 5 | Euclidean distance from wrist to each of 5 fingertips |
| Wrist Context | 2+2 | Raw 2D screen coordinates of wrist (used by Contextual Validation Filter) |

The normalization formula for kinematic features:

$$L_{norm}(i,t) = \frac{L_{raw}(i,t) - L_{wrist}(t)}{\|L_{mcp}(t) - L_{wrist}(t)\|_2}$$

This ensures position and scale invariance.

---

## Training

### 1. Prepare the Dataset

Download the [20BN Jester Dataset](https://www.kaggle.com/datasets/toxicmender/20bn-jester) and place it at `data/raw/`. Then run the preprocessing notebooks in order:

```
preprocessing/DatasetExtractor.ipynb   → Extract video frames
preprocessing/MediaPipeLandmarker.ipynb → Extract landmarks with MediaPipe
preprocessing/HDF5_converter.ipynb     → Consolidate into HDF5
preprocessing/generate_kinematic.py    → Kinematic features
preprocessing/MotionVector.py           → Motion vectors
preprocessing/FingertipsDistance.py    → Geometric features
preprocessing/generate_wrist_context.py → Wrist context
preprocessing/Merger.ipynb             → (if merging multiple HDF5 files)
```

Update `config.json` with the paths to your generated HDF5 files.

### 2. Configure Hyperparameters

Edit `setup.json` to adjust the model and training configuration:

```json
{
  "input-size": 175,
  "hidden-size": 256,
  "num-layers": 1,
  "feature-dim": 128,
  "dropout-prob": 0.4,
  "learning-rate": 0.001,
  "batch-size": 64,
  "num-epochs": 15,
  "loss-scale": 30.0,
  "loss-margin": 0.35
}
```

> **Note:** `input-size` (175) must not be changed unless you remove feature streams. All other parameters are safe to tune.

### 3. Train

```bash
python -m src.gesture_recognizer.training.train_model
```

The model checkpoint is saved to `models/gesture_model.pth`.

### 4. Export and Optimize

```bash
# Export to ONNX (FP32)
python scripts/export_to_onnx.py

# Apply INT8 dynamic quantization
python scripts/quantize_model.py
```

---

## Evaluation

Run evaluation on the validation set using the ONNX model:

```bash
python -m src.gesture_recognizer.evaluation.evaluate_onnx_model models/gesture_model_quant.onnx
```

Generate a per-class classification report:

```bash
python -m src.gesture_recognizer.evaluation.generate_report
```

Reports are saved to `reports/`.

---

## Results

### Final Model Performance

| Metric | Value |
|---|---|
| Validation Accuracy (Micro F1) | **84.46%** |
| Macro F1-Score | 0.8377 |
| Mean Inference Latency (CPU) | **~0.3 ms** |
| Model Size | **2.3 MB** |
| Negative Class Recall | **95.24%** |

### Per-Class Breakdown

| Class | F1-Score | Precision | Recall |
|---|---|---|---|
| Negative (Merged) | 0.7294 | 0.5910 | **0.9524** |
| Turning Hand Clockwise | 0.7755 | 0.7860 | 0.7653 |
| Turning Hand Counterclockwise | 0.7982 | 0.9007 | 0.7167 |
| Swiping Right | 0.8253 | 0.9389 | 0.7363 |
| Swiping Left | 0.8314 | 0.9261 | 0.7544 |
| Swiping Down | 0.8420 | 0.8975 | 0.7930 |
| Swiping Up | 0.8481 | 0.8766 | 0.8214 |
| Pushing Hand Away | 0.8514 | 0.9069 | 0.8024 |
| Stop Sign | 0.8908 | 0.8987 | 0.8831 |
| Zooming In | 0.9018 | 0.9650 | 0.8464 |
| Zooming Out | 0.9204 | 0.9718 | 0.8742 |

### Ablation Study Summary

| Model Variant | Accuracy | Mean Latency | Model Size |
|---|---|---|---|
| Baseline GRU + Cross-Entropy | 78.50% | ~2.5 ms | 15.2 MB |
| Full Features + LMCL (PyTorch) | 82.55% | ~10.2 ms | 15.2 MB |
| **Final: Quantized ONNX (INT8)** | **84.46%** | **~0.3 ms** | **2.3 MB** |

---

## Configuration Reference

### `config.json` — Data and model paths

| Key | Description |
|---|---|
| `landmarks-hdf5-path` | Path to kinematic features HDF5 |
| `motion-vector-hdf5-path` | Path to motion vectors HDF5 |
| `fingertip-distance-hdf5-path` | Path to geometric features HDF5 |
| `wrist-context-hdf5-path` | Path to wrist context HDF5 |
| `model-path` | PyTorch checkpoint save path |
| `onnx-fp32-path` | FP32 ONNX export path |
| `onnx-quant-path` | INT8 quantized ONNX path |

### `setup.json` — Training hyperparameters

| Key | Description | Recommended Range |
|---|---|---|
| `hidden-size` | GRU hidden units per direction | 64–350 |
| `num-layers` | GRU depth | 1–3 |
| `feature-dim` | Embedding dimension | 32–256 |
| `dropout-prob` | Dropout probability | 0.2–0.5 |
| `learning-rate` | Initial learning rate | 1e-4 – 1e-2 |
| `batch-size` | Training batch size | 32–128 |
| `num-epochs` | Training epochs | 15–30 |
| `loss-scale` | LMCL scale factor `s` | 10–64 |
| `loss-margin` | LMCL margin `m` | 0.0–1.0 |

---

## Known Limitations

- **MediaPipe dependency**: Model accuracy is bounded by the quality of MediaPipe landmark extraction. Occlusions, poor lighting, or fast motion can introduce landmark jitter that degrades predictions.
- **Bidirectional architecture**: The GRU sees the full gesture window before predicting, making it ideal for command-based interaction but unsuitable for true frame-by-frame streaming (a unidirectional variant would be needed).
- **Single dataset**: Trained and validated exclusively on the Jester dataset (third-person, well-framed videos). Performance on egocentric or cluttered backgrounds has not been evaluated.
- **Feature engineering bottleneck**: The neural network inference itself takes ~0.3 ms, but the live feature engineering pipeline (computing all four feature streams per frame) contributes the majority of end-to-end latency on lower-end hardware.

---

## Citation

If you use this code or the associated paper in your research, please cite:

```bibtex
@article{chitrigi2024gesture,
  title   = {A Lightweight and Robust Framework for Real-Time Gesture Recognition and Control},
  author  = {Chitrigi, Avnish Raj and Patil, Anshul and Goel, Himanish and Rathor, Kapil and
             Vankayalapati, Hima Deepthi and Kyandoghere, Kyamakya},
  journal = {IEEE Access},
  year    = {2024}
}
```

---

## License

This project is released for academic and research use. See `LICENSE` for details.
