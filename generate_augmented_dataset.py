#!/usr/bin/env python3
"""
Aggressive Data Augmentation for Captcha Dataset
=================================================

Generates many augmented variations from each original captcha to create
a large training dataset from limited samples.

Target: Generate 5000+ samples from 350 originals (14+ per original)

Usage:
  python generate_augmented_dataset.py                           # Use captcha_dataset (default)
  python generate_augmented_dataset.py --source captcha_dataset_live  # Use live captchas
"""

import cv2
import numpy as np
from pathlib import Path
import os
import argparse
from tqdm import tqdm

# Configuration (can be overridden by command line args)
ORIGINAL_DATASET = "captcha_dataset"  # 350 original captchas
OUTPUT_DATASET = "captcha_dataset_augmented"  # Output directory
AUGMENTATIONS_PER_IMAGE = 14  # Target: 350 × 14 = 4900 samples
TARGET_SIZE = (300, 80)  # Original size

def preprocess_v7_hybrid(img):
    """Preprocessing v7 (hybrid) - MATCHES INFERENCE!"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    
    # Brightness normalization (if needed)
    current_mean = np.mean(gray)
    target_mean = 175.0
    if current_mean > 200:
        gray = np.clip(gray * (target_mean / current_mean), 0, 255).astype(np.uint8)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    closed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    clahe = cv2.createCLAHE(clipLimit=4.5, tileGridSize=(4, 4))
    enhanced = clahe.apply(closed)
    denoised = cv2.fastNlMeansDenoising(enhanced, None, 8, 7, 21)
    kernel_sharpen = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(denoised, -1, kernel_sharpen)
    
    return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)

def augment_captcha(img, aug_index):
    """
    Apply various augmentations to a captcha image.
    
    Augmentation techniques:
    1. Rotation (-7 to +7 degrees)
    2. Translation (-5 to +5 pixels horizontal, -3 to +3 vertical)
    3. Scaling (0.9 to 1.1)
    4. Brightness (0.7 to 1.4x)
    5. Contrast adjustment
    6. Slight blur
    7. Addnoise
    8. Horizontal flipping (for symmetric digits)
    9. Shearing
    10. Perspective transform (slight)
    """
    
    h, w = img.shape[:2]
    augmented = img.copy()
    
    # Set random seed based on aug_index for reproducibility
    np.random.seed(aug_index)
    
    # 1. Random rotation (-7 to +7 degrees)
    angle = np.random.uniform(-7, 7)
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    augmented = cv2.warpAffine(augmented, M, (w, h), 
                               borderMode=cv2.BORDER_REPLICATE,
                               borderValue=(255, 255, 255))
    
    # 2. Random translation (-5 to +5 horizontal, -3 to +3 vertical)
    tx = np.random.randint(-5, 6)
    ty = np.random.randint(-3, 4)
    M = np.float32([[1, 0, tx], [0, 1, ty]])
    augmented = cv2.warpAffine(augmented, M, (w, h),
                               borderMode=cv2.BORDER_REPLICATE,
                               borderValue=(255, 255, 255))
    
    # 3. Random scaling (0.92 to 1.08)
    scale = np.random.uniform(0.92, 1.08)
    new_w, new_h = int(w * scale), int(h * scale)
    scaled = cv2.resize(augmented, (new_w, new_h))
    
    # Crop or pad back to original size
    if scale > 1:
        # Crop center
        y_start = max(0, (new_h - h) // 2)
        x_start = max(0, (new_w - w) // 2)
        augmented = scaled[y_start:y_start+h, x_start:x_start+w]
        # Handle edge cases
        if augmented.shape[0] < h or augmented.shape[1] < w:
            augmented = cv2.resize(augmented, (w, h))
    else:
        # Pad
        pad_h_top = (h - new_h) // 2
        pad_h_bottom = h - new_h - pad_h_top
        pad_w_left = (w - new_w) // 2
        pad_w_right = w - new_w - pad_w_left
        augmented = cv2.copyMakeBorder(scaled, pad_h_top, pad_h_bottom,
                                       pad_w_left, pad_w_right,
                                       cv2.BORDER_REPLICATE)
    
    # 4. Random brightness (0.7 to 1.4x) - CRITICAL for matching live captchas
    brightness = np.random.uniform(0.7, 1.4)
    augmented = np.clip(augmented.astype(float) * brightness, 0, 255).astype(np.uint8)
    
    # 5. Random contrast adjustment (with 50% probability)
    if np.random.random() > 0.5:
        alpha = np.random.uniform(0.8, 1.2)  # Contrast control
        beta = np.random.uniform(-10, 10)    # Brightness control
        augmented = cv2.convertScaleAbs(augmented, alpha=alpha, beta=beta)
    
    # 6. Slight blur (with 30% probability)
    if np.random.random() > 0.7:
        kernel_size = np.random.choice([3, 5])
        augmented = cv2.GaussianBlur(augmented, (kernel_size, kernel_size), 0)
    
    # 7. Add noise (with 25% probability)
    if np.random.random() > 0.75:
        noise = np.random.normal(0, 5, augmented.shape).astype(np.int16)
        augmented = np.clip(augmented.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    # 8. Slight shearing (with 40% probability)
    if np.random.random() > 0.6:
        shear_factor = np.random.uniform(-0.1, 0.1)
        M = np.float32([[1, shear_factor, 0], [0, 1, 0]])
        augmented = cv2.warpAffine(augmented, M, (w, h),
                                   borderMode=cv2.BORDER_REPLICATE,
                                   borderValue=(255, 255, 255))
    
    # 9. Slight perspective transform (with 20% probability)
    if np.random.random() > 0.8:
        # Small random perspective distortion
        pts1 = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
        offset = 5
        pts2 = np.float32([
            [np.random.randint(0, offset), np.random.randint(0, offset)],
            [w - np.random.randint(0, offset), np.random.randint(0, offset)],
            [np.random.randint(0, offset), h - np.random.randint(0, offset)],
            [w - np.random.randint(0, offset), h - np.random.randint(0, offset)]
        ])
        M = cv2.getPerspectiveTransform(pts1, pts2)
        augmented = cv2.warpPerspective(augmented, M, (w, h),
                                        borderMode=cv2.BORDER_REPLICATE,
                                        borderValue=(255, 255, 255))
    
    return augmented

def generate_augmented_dataset(source_dirs=None):
    """Generate augmented dataset from originals.
    
    Args:
        source_dirs: List of source directories to combine. If None, uses ORIGINAL_DATASET global.
    """
    
    print("="*80)
    print("AGGRESSIVE DATA AUGMENTATION")
    print("="*80)
    
    # Create output directory
    output_dir = Path(OUTPUT_DATASET)
    output_dir.mkdir(exist_ok=True)
    
    # Get all original images from all source directories
    if source_dirs is None:
        source_dirs = [ORIGINAL_DATASET]
    
    image_files = []
    for source_dir in source_dirs:
        src_path = Path(source_dir)
        if src_path.exists():
            files = list(src_path.glob("*.png"))
            image_files.extend(files)
            print(f"✓ Found {len(files)} images in {source_dir}")
        else:
            print(f"⚠️  Directory not found: {source_dir}")
    
    print(f"\nTotal: {len(image_files)} original captchas from {len(source_dirs)} source(s)")
    print(f"Generating {AUGMENTATIONS_PER_IMAGE} augmentations per image")
    print(f"Target dataset size: {len(image_files) * AUGMENTATIONS_PER_IMAGE} samples\n")
    
    total_generated = 0
    
    for img_file in tqdm(image_files, desc="Augmenting captchas"):
        # Extract label from filename (format: 12345_timestamp.png)
        label = img_file.stem.split('_')[0]
        if len(label) != 5 or not label.isdigit() or '0' in label:
            continue
        
        # Load original image
        img = cv2.imread(str(img_file))
        if img is None:
            continue
        
        # Resize to standard size if needed
        if img.shape[:2] != TARGET_SIZE[::-1]:  # (h, w)
            img = cv2.resize(img, TARGET_SIZE)
        
        # Save original (preprocessed)
        preprocessed = preprocess_v7_hybrid(img)
        output_file = output_dir / f"{label}_{total_generated:06d}_original.png"
        cv2.imwrite(str(output_file), preprocessed)
        total_generated += 1
        
        # Generate augmented variations
        for aug_idx in range(AUGMENTATIONS_PER_IMAGE - 1):  # -1 because we saved original
            # Apply augmentation to ORIGINAL image (not preprocessed)
            # Use modulo to keep seed within valid range (0 to 2^32 - 1)
            seed_value = (aug_idx + int(img_file.stem.split('_')[-1])) % (2**32)
            augmented = augment_captcha(img, seed_value)
            
            # Then preprocess the augmented image
            preprocessed = preprocess_v7_hybrid(augmented)
            
            # Save
            output_file = output_dir / f"{label}_{total_generated:06d}_aug{aug_idx+1:02d}.png"
            cv2.imwrite(str(output_file), preprocessed)
            total_generated += 1
    
    print(f"\n{'='*80}")
    print(f"✅ AUGMENTATION COMPLETE")
    print(f"{'='*80}")
    print(f"Generated {total_generated} samples")
    print(f"Saved to: {output_dir}")
    print(f"{'='*80}\n")
    
    return total_generated

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate augmented captcha dataset")
    parser.add_argument('--source', type=str, nargs='+', 
                       default=['captcha_dataset'],
                       help='Source directory(ies) containing original captchas (can specify multiple)')
    parser.add_argument('--combine', action='store_true',
                       help='Combine original dataset + live dataset automatically')
    parser.add_argument('--output', type=str, default='captcha_dataset_augmented',
                       help='Output directory for augmented dataset (default: captcha_dataset_augmented)')
    parser.add_argument('--augmentations', type=int, default=14,
                       help='Number of augmented variations per image (default: 14)')
    
    args = parser.parse_args()
    
    # Handle --combine flag
    if args.combine:
        source_dirs = ['captcha_dataset', 'captcha_dataset_live']
        print("🔀 Combining datasets: captcha_dataset + captcha_dataset_live")
    else:
        source_dirs = args.source if isinstance(args.source, list) else [args.source]
    
    # Update global config
    OUTPUT_DATASET = args.output
    AUGMENTATIONS_PER_IMAGE = args.augmentations
    
    print(f"\n{'='*80}")
    print(f"AUGMENTATION CONFIGURATION")
    print(f"{'='*80}")
    print(f"Source directories: {', '.join(source_dirs)}")
    print(f"Output directory: {OUTPUT_DATASET}")
    print(f"Augmentations per image: {AUGMENTATIONS_PER_IMAGE}")
    print(f"{'='*80}\n")
    
    total = generate_augmented_dataset(source_dirs=source_dirs)
    print(f"\n✓ Ready for training with {total} samples!")
    print(f"  Run: python train_captcha_model_improved.py")
