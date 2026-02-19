"""
Captcha Model Training Script
==============================

Trains a CNN model to recognize 5-digit captchas with 95%+ accuracy.

Architecture:
- CNN for feature extraction
- Works on full captcha image (doesn't segment digits)
- Outputs 5 digits (one per position)
- Uses categorical crossentropy for each digit position

Requirements:
- tensorflow >= 2.x
- PIL, numpy, opencv-python
- At least 150 labeled samples in captcha_dataset/
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

# Configuration
DATASET_DIR = "captcha_dataset_v2"  # NEW: Dual-method preprocessed dataset (310 images)
MODEL_DIR = "captcha_model"
IMAGE_HEIGHT = 50
IMAGE_WIDTH = 200
NUM_DIGITS = 5
NUM_CLASSES = 9  # 1-9 (digit 0 not present in dataset)

def load_dataset(dataset_dir):
    """Load and preprocess captcha dataset"""
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
        
        # Load image
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

def augment_data(X, y, augmentation_factor=2):
    """
    Augment dataset with transformations
    
    Args:
        X: Input images (shape: N, H, W, 1)
        y: Labels
        augmentation_factor: How many augmented copies to create per sample
    
    Returns:
        Augmented X and y
    """
    print(f"\nAugmenting dataset (factor={augmentation_factor})...")
    
    augmented_X = [X]
    augmented_y = [y]
    
    for _ in range(augmentation_factor):
        aug_X = []
        for img in X:
            # Remove channel dimension for processing
            img_2d = img.squeeze()
            
            # Random slight rotations (-5 to +5 degrees)
            angle = np.random.uniform(-5, 5)
            h, w = img_2d.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(img_2d, M, (w, h), borderValue=255)
            
            # Random slight translations (-3 to +3 pixels)
            tx = np.random.randint(-3, 4)
            ty = np.random.randint(-2, 3)
            M = np.float32([[1, 0, tx], [0, 1, ty]])
            translated = cv2.warpAffine(rotated, M, (w, h), borderValue=255)
            
            # Random slight scaling (0.95 to 1.05)
            scale = np.random.uniform(0.95, 1.05)
            scaled = cv2.resize(translated, None, fx=scale, fy=scale)
            # Crop or pad back to original size
            if scale > 1:
                # Crop center
                y_start = (scaled.shape[0] - h) // 2
                x_start = (scaled.shape[1] - w) // 2
                scaled = scaled[y_start:y_start+h, x_start:x_start+w]
            else:
                # Pad
                pad_h = (h - scaled.shape[0]) // 2
                pad_w = (w - scaled.shape[1]) // 2
                scaled = cv2.copyMakeBorder(scaled, pad_h, h-scaled.shape[0]-pad_h,
                                           pad_w, w-scaled.shape[1]-pad_w,
                                           cv2.BORDER_CONSTANT, value=255)
            
            # Random brightness adjustment - WIDE RANGE to handle live captcha brightness
            # Training data ~175, live data ~239 (36% difference)
            # So we augment from 0.7x to 1.4x to cover this range
            brightness = np.random.uniform(0.7, 1.4)
            adjusted = np.clip(scaled * brightness, 0, 255).astype(np.uint8)
            
            # Add channel dimension back
            adjusted = adjusted.reshape(h, w, 1)
            
            aug_X.append(adjusted)
        
        augmented_X.append(np.array(aug_X))
        augmented_y.append(y)
    
    # Concatenate all
    X_aug = np.concatenate(augmented_X, axis=0)
    y_aug = np.concatenate(augmented_y, axis=0)
    
    print(f"Dataset size increased from {len(X)} to {len(X_aug)} samples")
    
    return X_aug, y_aug

def create_model():
    """Create CNN model for captcha recognition - deeper architecture"""
    
    # Input layer
    input_img = layers.Input(shape=(IMAGE_HEIGHT, IMAGE_WIDTH, 1), name='input')
    
    # Deeper convolutional layers with batch normalization
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
    x = layers.Dense(256, activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(128, activation='relu')(x)
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
    """Train the model"""
    
    print("\nCreating model...")
    model = create_model()
    
    # Compile model
    model.compile(
        optimizer='adam',
        loss=['sparse_categorical_crossentropy'] * NUM_DIGITS,
        metrics=[['accuracy']] * NUM_DIGITS  # One metric list per output
    )
    
    print("\nModel summary:")
    model.summary()
    
    # Split labels for each digit position
    y_train_split = [y_train[:, i] for i in range(NUM_DIGITS)]
    y_val_split = [y_val[:, i] for i in range(NUM_DIGITS)]
    
    # Callbacks
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=1e-6
        )
    ]
    
    # Train
    print("\nTraining model...")
    history = model.fit(
        X_train,
        y_train_split,
        batch_size=32,
        epochs=150,
        validation_data=(X_val, y_val_split),
        callbacks=callbacks,
        verbose=1
    )
    
    return model, history

def evaluate_model(model, X_test, y_test):
    """Evaluate model accuracy"""
    
    print("\n" + "="*70)
    print("MODEL EVALUATION")
    print("="*70)
    
    predictions = model.predict(X_test, verbose=0)
    
    # Convert predictions to digit labels (remap 0-8 back to 1-9)
    predicted_labels = []
    for i in range(len(X_test)):
        pred_digits = []
        for j in range(NUM_DIGITS):
            digit_class = np.argmax(predictions[j][i])
            actual_digit = digit_class + 1  # Convert class 0-8 back to digit 1-9
            pred_digits.append(str(actual_digit))
        predicted_labels.append(''.join(pred_digits))
    
    # Convert true labels (remap 0-8 back to 1-9)
    true_labels = []
    for i in range(len(y_test)):
        true_labels.append(''.join([str(d + 1) for d in y_test[i]]))
    
    # Calculate accuracy
    correct = sum(1 for pred, true in zip(predicted_labels, true_labels) if pred == true)
    accuracy = correct / len(y_test) * 100
    
    print(f"\nFull Sequence Accuracy: {accuracy:.2f}%")
    print(f"Correct: {correct}/{len(y_test)}")
    
    # Per-digit accuracy
    print("\nPer-digit accuracy:")
    for digit_pos in range(NUM_DIGITS):
        correct_digit = sum(1 for i in range(len(y_test)) 
                          if predicted_labels[i][digit_pos] == true_labels[i][digit_pos])
        digit_acc = correct_digit / len(y_test) * 100
        print(f"  Position {digit_pos + 1}: {digit_acc:.2f}%")
    
    # Show some examples
    print("\nSample predictions:")
    for i in range(min(10, len(y_test))):
        marker = "✓" if predicted_labels[i] == true_labels[i] else "✗"
        print(f"  {marker} True: {true_labels[i]}, Predicted: {predicted_labels[i]}")
    
    print("="*70)
    
    return accuracy

def save_model(model, model_dir):
    """Save trained model"""
    os.makedirs(model_dir, exist_ok=True)
    
    # Save model
    model_path = os.path.join(model_dir, 'captcha_model.h5')
    model.save(model_path)
    print(f"\nModel saved to: {model_path}")
    
    # Save config
    config = {
        'image_height': IMAGE_HEIGHT,
        'image_width': IMAGE_WIDTH,
        'num_digits': NUM_DIGITS,
        'num_classes': NUM_CLASSES
    }
    
    config_path = os.path.join(model_dir, 'config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"Config saved to: {config_path}")

def main():
    """Main training pipeline"""
    
    print("="*70)
    print("CAPTCHA MODEL TRAINING")
    print("="*70)
    
    # Check if dataset exists
    if not os.path.exists(DATASET_DIR):
        print(f"\nError: Dataset directory '{DATASET_DIR}' not found!")
        print("Please run collect_captcha_data.py first to collect samples.")
        return
    
    # Count samples
    num_samples = len([f for f in os.listdir(DATASET_DIR) if f.endswith('.png')])
    print(f"\nFound {num_samples} samples in dataset")
    
    if num_samples < 100:
        print(f"\nWarning: Only {num_samples} samples found.")
        print("Recommended: 150-200 samples for 95%+ accuracy")
        print("Continuing anyway...")
        # Allow training with fewer samples for testing
    
    # Load dataset
    X, y = load_dataset(DATASET_DIR)
    
    if len(X) < 50:
        print(f"\nError: Not enough valid samples ({len(X)}). Need at least 50.")
        return
    
    # Split into train/val/test FIRST (before augmentation)
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)
    
    # Augment ONLY the training data (not validation or test)
    X_train, y_train = augment_data(X_train, y_train, augmentation_factor=3)
    
    print(f"\nDataset split:")
    print(f"  Training: {len(X_train)} samples (augmented)")
    print(f"  Validation: {len(X_val)} samples")
    print(f"  Test: {len(X_test)} samples")
    
    # Train model
    model, history = train_model(X_train, y_train, X_val, y_val)
    
    # Evaluate
    accuracy = evaluate_model(model, X_test, y_test)
    
    # Check if accuracy meets target
    if accuracy >= 95.0:
        print(f"\n✅ SUCCESS! Accuracy {accuracy:.2f}% meets target (95%+)")
        save_model(model, MODEL_DIR)
    else:
        print(f"\n⚠️  Accuracy {accuracy:.2f}% below target (95%)")
        print("\nSuggestions to improve:")
        print("  1. Collect more training samples (target: 150-200)")
        print("  2. Check if labels are correct")
        print("  3. Ensure captcha images are clear")
        print("\nSaving model anyway for testing...")
        save_model(model, MODEL_DIR)
    
    print("\n" + "="*70)
    print("Training complete!")
    print("="*70)

if __name__ == "__main__":
    main()
