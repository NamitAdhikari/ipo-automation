#!/usr/bin/env python3
"""
Train a digit-segmented captcha model.
Instead of predicting all 5 digits at once, we split the image into 5 regions
and train a single 9-class classifier (digits 1-9).
This often achieves better accuracy for fixed-position captchas.
"""

import os
import numpy as np
import cv2
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import json

# Configuration
DATASET_DIR = "captcha_dataset_v2"
MODEL_DIR = "captcha_model_segmented"
IMG_HEIGHT = 80  # Keep original height
IMG_WIDTH = 60   # Width of ONE digit (300 / 5)
NUM_CLASSES = 9  # Digits 1-9 (no 0)
EPOCHS = 100
BATCH_SIZE = 32
LEARNING_RATE = 0.001

# Class labels (digits 1-9)
CLASSES = list(range(1, 10))

def load_dataset():
    """Load captcha dataset and segment into individual digits."""
    print("Loading and segmenting captcha dataset...")
    
    images = []
    labels = []
    
    for filename in os.listdir(DATASET_DIR):
        if not filename.endswith('.png'):
            continue
        
        # Extract label from filename (first 5 characters are the digits)
        label_str = filename[:5]
        if not label_str.isdigit() or len(label_str) != 5:
            continue
        
        # Load image
        img_path = os.path.join(DATASET_DIR, filename)
        img = cv2.imread(img_path)
        if img is None:
            continue
        
        h, w = img.shape[:2]
        
        # Split image into 5 equal regions (one per digit)
        digit_width = w // 5
        
        for i, digit_char in enumerate(label_str):
            digit_label = int(digit_char)
            
            # Skip if digit is 0 (shouldn't happen, but safety check)
            if digit_label == 0:
                print(f"Warning: Found digit 0 in {filename}, skipping")
                continue
            
            # Extract digit region
            x_start = i * digit_width
            x_end = (i + 1) * digit_width if i < 4 else w  # Last digit gets remaining width
            
            digit_img = img[:, x_start:x_end]
            
            # Resize to standard size
            digit_img = cv2.resize(digit_img, (IMG_WIDTH, IMG_HEIGHT))
            
            # Normalize to [0, 1]
            digit_img = digit_img.astype('float32') / 255.0
            
            images.append(digit_img)
            labels.append(digit_label - 1)  # Convert 1-9 to 0-8 for class indices
    
    print(f"Loaded {len(images)} digit samples from {len(os.listdir(DATASET_DIR))} captcha images")
    
    return np.array(images), np.array(labels)

def create_augmentation():
    """Create data augmentation pipeline."""
    return keras.Sequential([
        layers.RandomRotation(0.05),  # ±5 degrees
        layers.RandomTranslation(0.1, 0.1),  # ±10% shift
        layers.RandomZoom(0.1),  # ±10% zoom
        layers.RandomBrightness(0.2),  # ±20% brightness
    ])

def build_model():
    """Build a simple CNN for single-digit classification."""
    inputs = keras.Input(shape=(IMG_HEIGHT, IMG_WIDTH, 3))
    
    # Data augmentation (only during training)
    x = create_augmentation()(inputs)
    
    # Convolutional blocks
    x = layers.Conv2D(32, (3, 3), activation='relu', padding='same')(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.25)(x)
    
    x = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.25)(x)
    
    x = layers.Conv2D(128, (3, 3), activation='relu', padding='same')(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.25)(x)
    
    # Dense layers
    x = layers.Flatten()(x)
    x = layers.Dense(256, activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.5)(x)
    
    x = layers.Dense(128, activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.5)(x)
    
    # Output layer (9 classes)
    outputs = layers.Dense(NUM_CLASSES, activation='softmax', name='digit_output')(x)
    
    model = keras.Model(inputs=inputs, outputs=outputs)
    return model

def main():
    print("=" * 70)
    print("TRAINING SEGMENTED CAPTCHA MODEL")
    print("=" * 70)
    
    # Load dataset
    X, y = load_dataset()
    
    # Split into train/val/test (70/15/15)
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )
    
    print(f"\nDataset split:")
    print(f"  Training: {len(X_train)} samples")
    print(f"  Validation: {len(X_val)} samples")
    print(f"  Test: {len(X_test)} samples")
    
    # Build model
    print("\nBuilding model...")
    model = build_model()
    
    # Compile
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LEARNING_RATE),
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    
    print("\nModel architecture:")
    model.summary()
    
    # Callbacks
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_accuracy',
            patience=15,
            restore_best_weights=True,
            verbose=1
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_accuracy',
            factor=0.5,
            patience=5,
            min_lr=1e-6,
            verbose=1
        ),
        keras.callbacks.ModelCheckpoint(
            os.path.join(MODEL_DIR, 'best_model.keras'),
            monitor='val_accuracy',
            save_best_only=True,
            verbose=1
        )
    ]
    
    # Train
    print("\nTraining model...")
    print("=" * 70)
    
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        verbose=1
    )
    
    # Evaluate on test set
    print("\n" + "=" * 70)
    print("MODEL EVALUATION")
    print("=" * 70)
    
    test_loss, test_accuracy = model.evaluate(X_test, y_test, verbose=0)
    print(f"\nTest accuracy: {test_accuracy * 100:.2f}%")
    print(f"Test loss: {test_loss:.4f}")
    
    # Calculate full-sequence accuracy estimate
    # Assuming independence: accuracy^5
    full_seq_estimate = test_accuracy ** 5
    print(f"\nEstimated full-sequence accuracy: {full_seq_estimate * 100:.2f}%")
    print(f"(Assumes digit predictions are independent)")
    
    # Per-class accuracy
    print("\nPer-digit accuracy:")
    y_pred = model.predict(X_test, verbose=0)
    y_pred_classes = np.argmax(y_pred, axis=1)
    
    for digit in range(NUM_CLASSES):
        mask = y_test == digit
        if np.sum(mask) > 0:
            digit_acc = np.mean(y_pred_classes[mask] == digit)
            actual_digit = digit + 1  # Convert back to 1-9
            print(f"  Digit {actual_digit}: {digit_acc * 100:.2f}% ({np.sum(mask)} samples)")
    
    # Confusion analysis
    print("\nMost common misclassifications:")
    confusion_pairs = []
    for true_digit in range(NUM_CLASSES):
        mask = y_test == true_digit
        if np.sum(mask) == 0:
            continue
        pred_for_true = y_pred_classes[mask]
        for pred_digit in range(NUM_CLASSES):
            if pred_digit != true_digit:
                count = np.sum(pred_for_true == pred_digit)
                if count > 0:
                    confusion_pairs.append((true_digit + 1, pred_digit + 1, count))
    
    confusion_pairs.sort(key=lambda x: x[2], reverse=True)
    for true_d, pred_d, count in confusion_pairs[:5]:
        print(f"  {true_d} → {pred_d}: {count} times")
    
    # Save model and config
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    print("\nSaving model...")
    model.save(os.path.join(MODEL_DIR, 'model.h5'))
    
    config = {
        'height': IMG_HEIGHT,
        'width': IMG_WIDTH,
        'classes': NUM_CLASSES,
        'class_labels': CLASSES,
        'test_accuracy': float(test_accuracy),
        'full_sequence_estimate': float(full_seq_estimate)
    }
    
    with open(os.path.join(MODEL_DIR, 'config.json'), 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Model saved to: {os.path.join(MODEL_DIR, 'model.h5')}")
    print(f"Config saved to: {os.path.join(MODEL_DIR, 'config.json')}")
    
    print("\n" + "=" * 70)
    
    if test_accuracy >= 0.95:
        print("✓ Target accuracy achieved! (≥95%)")
    elif test_accuracy >= 0.85:
        print("⚠ Good accuracy. May work with multi-attempt strategy.")
    else:
        print("⚠ Accuracy below target. Consider:")
        print("  1. Collect more training samples")
        print("  2. Try ensemble approach")
        print("  3. Use multi-attempt with confidence scoring")
    
    print("=" * 70)

if __name__ == '__main__':
    main()
