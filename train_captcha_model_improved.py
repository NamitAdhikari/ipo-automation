"""
Improved Captcha Model Training Script (v2)
============================================

Trains a CNN model on the augmented dataset (4900 samples) with optimized hyperparameters.

Key improvements over v1:
- Trains on 4900 augmented samples (vs 700 before)
- 80-20 train-validation split (no separate test set - we test on live captchas)
- NO augmentation during training (already done offline)
- Reduced epochs (100 vs 150) since we have 14x more data per epoch
- Slightly simpler model to prevent overfitting on augmented data

Target accuracy:
- Validation: 80-85% per-digit (vs 87% before but with only 700 samples)
- Live: 70-80% per-digit = 17-33% full-sequence (vs 55% per-digit = 5% before)

Requirements:
- tensorflow >= 2.x
- PIL, numpy, opencv-python
- captcha_dataset_augmented/ with 4900 samples
"""

import os
import numpy as np
import cv2
from PIL import Image
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split
import json
from datetime import datetime

# Configuration
DATASET_DIR = "captcha_dataset_augmented"  # NEW: Augmented dataset (4900 samples)
MODEL_DIR = "captcha_model"
MODEL_NAME = "captcha_model_v2.h5"  # NEW: Save as v2
IMAGE_HEIGHT = 50
IMAGE_WIDTH = 200
NUM_DIGITS = 5
NUM_CLASSES = 9  # 1-9 (digit 0 not present in dataset)

def load_dataset(dataset_dir):
    """Load augmented captcha dataset (already preprocessed)"""
    images = []
    labels = []
    
    print(f"Loading dataset from {dataset_dir}...")
    
    for filename in os.listdir(dataset_dir):
        if not filename.endswith('.png'):
            continue
        
        # Extract label from filename (first 5 characters)
        label = filename[:5]
        if len(label) != 5 or not label.isdigit():
            print(f"Skipping invalid filename: {filename}")
            continue
        
        # Check for digit 0 (not in our dataset)
        if '0' in label:
            print(f"Skipping file with digit 0: {filename}")
            continue
        
        # Load image (already preprocessed)
        filepath = os.path.join(dataset_dir, filename)
        img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
        
        if img is None:
            print(f"Failed to load: {filename}")
            continue
        
        # Resize to standard size
        img = cv2.resize(img, (IMAGE_WIDTH, IMAGE_HEIGHT))
        
        # Normalize to [0, 1]
        img = img.astype(np.float32) / 255.0
        
        images.append(img)
        # Convert digits 1-9 to classes 0-8
        labels.append([int(d) - 1 for d in label])
    
    print(f"Loaded {len(images)} samples")
    
    # Convert to numpy arrays
    X = np.array(images)
    X = X.reshape(-1, IMAGE_HEIGHT, IMAGE_WIDTH, 1)  # Add channel dimension
    
    y = np.array(labels)
    
    return X, y

def create_model():
    """
    Create CNN model for captcha recognition
    
    Slightly simpler than v1 to prevent overfitting on augmented data:
    - Reduced dense layers: 256->128 becomes 128->64
    - Keep same conv structure (works well)
    - Keep dropout at 0.25-0.5 for regularization
    """
    
    # Input layer
    input_img = layers.Input(shape=(IMAGE_HEIGHT, IMAGE_WIDTH, 1), name='input')
    
    # Convolutional layers with batch normalization
    x = layers.Conv2D(32, (3, 3), activation='relu', padding='same')(input_img)
    x = layers.BatchNormalization()(x)
    x = layers.Conv2D(32, (3, 3), activation='relu', padding='same')(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.25)(x)
    
    x = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.25)(x)
    
    x = layers.Conv2D(128, (3, 3), activation='relu', padding='same')(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.25)(x)
    
    # Flatten
    x = layers.Flatten()(x)
    
    # REDUCED dense layers to prevent overfitting on augmented data
    x = layers.Dense(128, activation='relu')(x)  # Was 256
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(64, activation='relu')(x)  # Was 128
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.5)(x)
    
    # Output layers - one for each digit position
    outputs = []
    for i in range(NUM_DIGITS):
        output = layers.Dense(NUM_CLASSES, activation='softmax', name=f'digit_{i+1}')(x)
        outputs.append(output)
    
    # Create model
    model = keras.Model(inputs=input_img, outputs=outputs)
    
    return model

def train_model(X_train, y_train, X_val, y_val):
    """Train the model with optimized hyperparameters"""
    
    print("\nCreating model...")
    model = create_model()
    
    # Compile model
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),  # Start at 0.001
        loss=['sparse_categorical_crossentropy'] * NUM_DIGITS,
        metrics=[['accuracy']] * NUM_DIGITS
    )
    
    print("\nModel summary:")
    model.summary()
    
    # Count parameters
    trainable_params = sum([tf.size(w).numpy() for w in model.trainable_weights])
    print(f"\nTrainable parameters: {trainable_params:,}")
    
    # Split labels for each digit position
    y_train_split = [y_train[:, i] for i in range(NUM_DIGITS)]
    y_val_split = [y_val[:, i] for i in range(NUM_DIGITS)]
    
    # Callbacks
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=15,  # Increased from 10 (more data = may need more patience)
            restore_best_weights=True,
            verbose=1
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=8,  # Reduce LR if no improvement for 8 epochs
            min_lr=1e-6,
            verbose=1
        )
    ]
    
    # Train
    print("\nTraining model...")
    print(f"Training samples: {len(X_train)}")
    print(f"Validation samples: {len(X_val)}")
    print(f"Batch size: 32")
    print(f"Max epochs: 100 (with early stopping)")
    print(f"Starting learning rate: 0.001")
    print("-" * 70)
    
    history = model.fit(
        X_train,
        y_train_split,
        batch_size=32,
        epochs=100,  # REDUCED from 150 since we have 14x more data
        validation_data=(X_val, y_val_split),
        callbacks=callbacks,
        verbose=2  # Show one line per epoch
    )
    
    return model, history

def evaluate_model(model, X_val, y_val, dataset_name="Validation"):
    """Evaluate model accuracy"""
    
    print("\n" + "="*70)
    print(f"MODEL EVALUATION - {dataset_name.upper()}")
    print("="*70)
    
    predictions = model.predict(X_val, verbose=0)
    
    # Convert predictions to digit labels (remap 0-8 back to 1-9)
    predicted_labels = []
    for i in range(len(X_val)):
        pred_digits = []
        for j in range(NUM_DIGITS):
            digit_class = np.argmax(predictions[j][i])
            actual_digit = digit_class + 1  # Convert class 0-8 back to digit 1-9
            pred_digits.append(str(actual_digit))
        predicted_labels.append(''.join(pred_digits))
    
    # Convert true labels (remap 0-8 back to 1-9)
    true_labels = []
    for i in range(len(y_val)):
        true_labels.append(''.join([str(d + 1) for d in y_val[i]]))
    
    # Calculate full-sequence accuracy
    correct = sum(1 for pred, true in zip(predicted_labels, true_labels) if pred == true)
    full_seq_accuracy = correct / len(y_val) * 100
    
    print(f"\nFull Sequence Accuracy: {full_seq_accuracy:.2f}%")
    print(f"Correct: {correct}/{len(y_val)}")
    
    # Per-digit accuracy
    print("\nPer-digit accuracy:")
    digit_accuracies = []
    for digit_pos in range(NUM_DIGITS):
        correct_digit = sum(1 for i in range(len(y_val)) 
                          if predicted_labels[i][digit_pos] == true_labels[i][digit_pos])
        digit_acc = correct_digit / len(y_val) * 100
        digit_accuracies.append(digit_acc)
        print(f"  Position {digit_pos + 1}: {digit_acc:.2f}%")
    
    avg_digit_accuracy = np.mean(digit_accuracies)
    print(f"\nAverage per-digit accuracy: {avg_digit_accuracy:.2f}%")
    
    # Expected full-sequence accuracy based on per-digit accuracy
    expected_full_seq = (avg_digit_accuracy / 100) ** NUM_DIGITS * 100
    print(f"Expected full-sequence from per-digit: {expected_full_seq:.2f}%")
    
    # Show some examples
    print("\nSample predictions (first 20):")
    for i in range(min(20, len(y_val))):
        marker = "✓" if predicted_labels[i] == true_labels[i] else "✗"
        print(f"  {marker} True: {true_labels[i]}, Predicted: {predicted_labels[i]}")
    
    # Error analysis - which digits are most confused?
    print("\nError analysis:")
    digit_errors = {d: 0 for d in range(1, 10)}
    for i in range(len(y_val)):
        if predicted_labels[i] != true_labels[i]:
            for j in range(NUM_DIGITS):
                if predicted_labels[i][j] != true_labels[i][j]:
                    true_digit = int(true_labels[i][j])
                    digit_errors[true_digit] += 1
    
    print("Errors per digit:")
    for digit, errors in sorted(digit_errors.items(), key=lambda x: x[1], reverse=True):
        error_rate = errors / len(y_val) * 100
        print(f"  Digit {digit}: {errors} errors ({error_rate:.1f}%)")
    
    print("="*70)
    
    return {
        'full_sequence_accuracy': full_seq_accuracy,
        'avg_digit_accuracy': avg_digit_accuracy,
        'per_digit_accuracies': digit_accuracies
    }

def save_model(model, model_dir, model_name):
    """Save trained model"""
    os.makedirs(model_dir, exist_ok=True)
    
    # Save model
    model_path = os.path.join(model_dir, model_name)
    model.save(model_path)
    print(f"\nModel saved to: {model_path}")
    
    # Save config
    config = {
        'image_height': IMAGE_HEIGHT,
        'image_width': IMAGE_WIDTH,
        'num_digits': NUM_DIGITS,
        'num_classes': NUM_CLASSES,
        'model_version': 'v2',
        'training_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'dataset_size': 4900,
        'augmentation': 'pre-applied (14x)',
        'architecture': 'simplified (128->64 dense layers)'
    }
    
    config_path = os.path.join(model_dir, 'config_v2.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"Config saved to: {config_path}")

def main():
    """Main training pipeline"""
    
    print("="*70)
    print("IMPROVED CAPTCHA MODEL TRAINING (v2)")
    print("="*70)
    print(f"Training started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if dataset exists
    if not os.path.exists(DATASET_DIR):
        print(f"\nError: Dataset directory '{DATASET_DIR}' not found!")
        print("Please run generate_augmented_dataset.py first.")
        return
    
    # Count samples
    num_samples = len([f for f in os.listdir(DATASET_DIR) if f.endswith('.png')])
    print(f"\nFound {num_samples} samples in augmented dataset")
    
    if num_samples < 1000:
        print(f"\nWarning: Only {num_samples} samples found. Expected ~4900.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Load dataset
    X, y = load_dataset(DATASET_DIR)
    
    if len(X) < 100:
        print(f"\nError: Not enough valid samples ({len(X)}). Need at least 100.")
        return
    
    # 80-20 train-validation split (NO augmentation during training)
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, shuffle=True
    )
    
    print(f"\nDataset split (80-20):")
    print(f"  Training: {len(X_train)} samples")
    print(f"  Validation: {len(X_val)} samples")
    print(f"  NO augmentation during training (already pre-applied)")
    
    # Train model
    model, history = train_model(X_train, y_train, X_val, y_val)
    
    # Evaluate on validation set
    results = evaluate_model(model, X_val, y_val, dataset_name="Validation")
    
    # Print final results
    print("\n" + "="*70)
    print("TRAINING COMPLETE - SUMMARY")
    print("="*70)
    print(f"Training samples: {len(X_train)}")
    print(f"Validation samples: {len(X_val)}")
    print(f"Full-sequence accuracy: {results['full_sequence_accuracy']:.2f}%")
    print(f"Average per-digit accuracy: {results['avg_digit_accuracy']:.2f}%")
    
    # Estimated live performance (assume 10-15% degradation)
    estimated_live_digit = results['avg_digit_accuracy'] * 0.85  # 15% degradation
    estimated_live_full = (estimated_live_digit / 100) ** NUM_DIGITS * 100
    attempts_needed = 1 / (estimated_live_full / 100)
    
    print(f"\nEstimated LIVE performance (with ~15% degradation):")
    print(f"  Per-digit accuracy: ~{estimated_live_digit:.1f}%")
    print(f"  Full-sequence accuracy: ~{estimated_live_full:.1f}%")
    print(f"  Expected attempts needed: ~{attempts_needed:.1f}")
    
    # Check if acceptable
    if estimated_live_digit >= 70:
        print(f"\n✅ SUCCESS! Estimated live per-digit accuracy {estimated_live_digit:.1f}% meets target (70%+)")
        print(f"   With ~{attempts_needed:.1f} attempts needed on average")
        if attempts_needed <= 5:
            print("   This should work with MeroShare's 2-3 attempt limit (with retries)")
        else:
            print("   ⚠️  May need too many attempts for MeroShare's limit")
    else:
        print(f"\n⚠️  Estimated live per-digit accuracy {estimated_live_digit:.1f}% below target (70%)")
        print("\nSuggestions to improve:")
        print("  1. Collect 500 more original samples (total 850)")
        print("  2. Re-augment to ~11,900 samples")
        print("  3. Consider digit segmentation approach")
        print("  4. Or use commercial captcha solving service (2Captcha, Anti-Captcha)")
    
    # Save model
    print("\nSaving model...")
    save_model(model, MODEL_DIR, MODEL_NAME)
    
    print("\n" + "="*70)
    print("All done!")
    print(f"Training completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    print("\nNext steps:")
    print("  1. Update captcha_inference_advanced.py to use captcha_model_v2.h5")
    print("  2. Test with: python test_live_quick.py 10")
    print("  3. Deploy with: python ipo_fully_auto.py --boid 1301260001246310 --company-id 253")
    print("="*70)

if __name__ == "__main__":
    main()
