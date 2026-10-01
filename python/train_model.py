#!/usr/bin/env python3
"""
train_model.py — Potato Leaf Disease Model Trainer
====================================================
Dataset: PlantVillage Potato subset
  - Download from: https://www.kaggle.com/datasets/emmarex/plantdisease
  - Expected folder structure:
      python/dataset/Potato/
          Early Blight/   ← subfolder name = class label
          Late Blight/
          Healthy/

Usage:
    cd python/
    python3 train_model.py
    python3 train_model.py --dataset /path/to/dataset --epochs 20

Output:
    python/leaf_disease_model.keras  (ready for analyze_leaf.py)
"""

import os
import sys
import argparse

# ── Argument parsing ───────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Train potato leaf disease classifier")
parser.add_argument(
    "--dataset",
    default=os.path.join(os.path.dirname(__file__), "dataset", "Potato"),
    help="Path to the Potato dataset folder (default: python/dataset/Potato/)"
)
parser.add_argument("--epochs",     type=int, default=15,  help="Training epochs (default: 15)")
parser.add_argument("--batch-size", type=int, default=32,  help="Batch size (default: 32)")
parser.add_argument("--img-size",   type=int, default=224, help="Image size in pixels (default: 224)")
args = parser.parse_args()

DATASET_PATH = args.dataset
EPOCHS       = args.epochs
BATCH_SIZE   = args.batch_size
IMG_SIZE     = args.img_size
OUTPUT_PATH  = os.path.join(os.path.dirname(__file__), "leaf_disease_model.keras")

# ── Pre-flight checks ──────────────────────────────────────────────────────
if not os.path.isdir(DATASET_PATH):
    print(f"\n❌ Dataset folder not found: {DATASET_PATH}")
    print("\nTo set up the dataset:")
    print("  1. Download from https://www.kaggle.com/datasets/emmarex/plantdisease")
    print("  2. Extract and place the 'Potato' folder at:")
    print(f"     {DATASET_PATH}")
    print("\nExpected subfolder structure:")
    print("  Potato/")
    print("    Early Blight/  (images...)")
    print("    Late Blight/   (images...)")
    print("    Healthy/       (images...)")
    sys.exit(1)

subfolders = [d for d in os.listdir(DATASET_PATH)
              if os.path.isdir(os.path.join(DATASET_PATH, d))]
if len(subfolders) == 0:
    print(f"❌ No class subfolders found in: {DATASET_PATH}")
    sys.exit(1)

print(f"\n🍃 Leaf Disease Model Trainer")
print(f"   Dataset  : {DATASET_PATH}")
print(f"   Classes  : {sorted(subfolders)}")
print(f"   Epochs   : {EPOCHS}")
print(f"   Batch sz : {BATCH_SIZE}")
print(f"   Img size : {IMG_SIZE}x{IMG_SIZE}")
print(f"   Output   : {OUTPUT_PATH}\n")

# ── Imports (after checks so failures are clearer) ─────────────────────────
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
except ImportError:
    print("❌ TensorFlow not installed.")
    print("   Install with: pip3 install tensorflow")
    sys.exit(1)

print(f"   TF version: {tf.__version__}\n")

# ── Load dataset ───────────────────────────────────────────────────────────
print("📂 Loading dataset...")

train_ds = tf.keras.preprocessing.image_dataset_from_directory(
    DATASET_PATH,
    validation_split=0.2,
    subset="training",
    seed=42,
    image_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH_SIZE
)

val_ds = tf.keras.preprocessing.image_dataset_from_directory(
    DATASET_PATH,
    validation_split=0.2,
    subset="validation",
    seed=42,
    image_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH_SIZE
)

class_names = train_ds.class_names
num_classes = len(class_names)
print(f"\n✅ Classes found: {class_names}")
print(f"   NOTE: The order above must match CLASS_NAMES in analyze_leaf.py")
print(f"   Current CLASS_NAMES in analyze_leaf.py: ['Early Blight', 'Late Blight', 'Healthy']")

# Warn if mismatch
expected = ['Early Blight', 'Late Blight', 'Healthy']
if class_names != expected:
    print(f"\n⚠️  WARNING: Class order mismatch!")
    print(f"   Found    : {class_names}")
    print(f"   Expected : {expected}")
    print(f"   Update CLASS_NAMES in analyze_leaf.py to match found order.\n")

# ── Performance optimisation ───────────────────────────────────────────────
AUTOTUNE = tf.data.AUTOTUNE
train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
val_ds   = val_ds.cache().prefetch(buffer_size=AUTOTUNE)

# ── Build model ───────────────────────────────────────────────────────────
print("\n🏗  Building model...")

model = keras.Sequential([
    # Normalise pixel values 0-255 → 0-1
    layers.Rescaling(1.0 / 255, input_shape=(IMG_SIZE, IMG_SIZE, 3)),

    # Data augmentation (only active during training)
    layers.RandomFlip("horizontal_and_vertical"),
    layers.RandomRotation(0.15),
    layers.RandomZoom(0.1),

    # Convolutional blocks
    layers.Conv2D(32, 3, activation='relu', padding='same'),
    layers.MaxPooling2D(),

    layers.Conv2D(64, 3, activation='relu', padding='same'),
    layers.MaxPooling2D(),

    layers.Conv2D(128, 3, activation='relu', padding='same'),
    layers.MaxPooling2D(),

    layers.Conv2D(256, 3, activation='relu', padding='same'),
    layers.MaxPooling2D(),

    # Classifier head
    layers.GlobalAveragePooling2D(),
    layers.Dense(256, activation='relu'),
    layers.Dropout(0.4),
    layers.Dense(num_classes, activation='softmax')
], name="leaf_disease_cnn")

model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=1e-3),
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

model.summary()

# ── Callbacks ─────────────────────────────────────────────────────────────
callbacks = [
    keras.callbacks.EarlyStopping(
        monitor='val_accuracy',
        patience=4,
        restore_best_weights=True,
        verbose=1
    ),
    keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=2,
        min_lr=1e-6,
        verbose=1
    ),
]

# ── Train ─────────────────────────────────────────────────────────────────
print(f"\n🚀 Training for up to {EPOCHS} epochs...\n")

history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS,
    callbacks=callbacks
)

# ── Results summary ────────────────────────────────────────────────────────
best_val_acc = max(history.history.get('val_accuracy', [0]))
final_acc    = history.history['accuracy'][-1]

print(f"\n📊 Training complete!")
print(f"   Final train accuracy : {final_acc * 100:.1f}%")
print(f"   Best val accuracy    : {best_val_acc * 100:.1f}%")

# ── Save model ─────────────────────────────────────────────────────────────
model.save(OUTPUT_PATH)
print(f"\n✅ Model saved to: {OUTPUT_PATH}")
print(f"   The model is ready. analyze_leaf.py will use it automatically.\n")