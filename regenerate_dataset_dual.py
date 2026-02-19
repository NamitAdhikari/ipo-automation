#!/usr/bin/env python3
"""
Regenerate entire dataset with BOTH v3_light and v7_hybrid preprocessing
This doubles the dataset size and provides variation
"""

import cv2
import numpy as np
from pathlib import Path
import shutil

def preprocess_v3_morphology_light(img):
    """Morphology with light sharpening"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    
    # NO brightness normalization for training data - keep original brightness
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    closed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced = clahe.apply(closed)
    
    kernel_sharpen = np.array([[0,-1,0],
                                [-1,5,-1],
                                [0,-1,0]])
    sharpened = cv2.filter2D(enhanced, -1, kernel_sharpen)
    
    return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)

def preprocess_v7_hybrid(img):
    """Hybrid approach with denoising"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    
    # NO brightness normalization for training data - keep original brightness
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    closed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    
    clahe = cv2.createCLAHE(clipLimit=4.5, tileGridSize=(4,4))
    enhanced = clahe.apply(closed)
    
    denoised = cv2.fastNlMeansDenoising(enhanced, None, 8, 7, 21)
    
    kernel_sharpen = np.array([[0,-1,0],
                                [-1,5,-1],
                                [0,-1,0]])
    sharpened = cv2.filter2D(denoised, -1, kernel_sharpen)
    
    return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)


def regenerate_dataset_dual(input_dir, output_dir):
    """
    Process all images with BOTH methods
    Output: 2x the original dataset size
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Backup old cleaned dataset if exists
    if output_path.exists():
        backup_path = Path(f"{output_dir}_backup")
        if backup_path.exists():
            shutil.rmtree(backup_path)
        print(f"Backing up existing {output_dir} to {backup_path}")
        shutil.move(str(output_path), str(backup_path))
    
    output_path.mkdir(exist_ok=True)
    
    all_files = sorted(list(input_path.glob("*.png")))
    
    print("=" * 80)
    print(f"DUAL PREPROCESSING DATASET GENERATION")
    print(f"Input:  {input_dir} ({len(all_files)} images)")
    print(f"Output: {output_dir} ({len(all_files) * 2} images - 2x dataset size!)")
    print("=" * 80)
    print("\nProcessing methods:")
    print("  1. v3_morphology_light (suffix: _v3)")
    print("  2. v7_hybrid (suffix: _v7)")
    print("=" * 80)
    
    v3_success = 0
    v7_success = 0
    errors = 0
    
    for i, img_path in enumerate(all_files, 1):
        # Extract base name (label + timestamp)
        base_name = img_path.stem
        label = base_name.split('_')[0]
        
        # Load original
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"[{i}/{len(all_files)}] ✗ Error loading {img_path.name}")
            errors += 1
            continue
        
        # Process with v3_light
        try:
            v3_result = preprocess_v3_morphology_light(img)
            v3_filename = f"{base_name}_v3.png"
            v3_output = output_path / v3_filename
            cv2.imwrite(str(v3_output), v3_result)
            v3_success += 1
        except Exception as e:
            print(f"[{i}/{len(all_files)}] ✗ v3 failed for {img_path.name}: {e}")
            errors += 1
        
        # Process with v7_hybrid
        try:
            v7_result = preprocess_v7_hybrid(img)
            v7_filename = f"{base_name}_v7.png"
            v7_output = output_path / v7_filename
            cv2.imwrite(str(v7_output), v7_result)
            v7_success += 1
        except Exception as e:
            print(f"[{i}/{len(all_files)}] ✗ v7 failed for {img_path.name}: {e}")
            errors += 1
        
        # Progress update every 20 images
        if i % 20 == 0 or i == len(all_files):
            print(f"[{i}/{len(all_files)}] Processed: {v3_success} v3, {v7_success} v7 (errors: {errors})")
    
    print("\n" + "=" * 80)
    print("DATASET GENERATION COMPLETE!")
    print(f"✓ v3_light images:  {v3_success}")
    print(f"✓ v7_hybrid images: {v7_success}")
    print(f"✓ Total images:     {v3_success + v7_success}")
    print(f"✗ Errors:           {errors}")
    print("=" * 80)
    print(f"\nNew dataset location: {output_dir}/")
    print(f"Original dataset:     {input_dir}/ (unchanged)")
    print("\nNEXT STEP: Retrain the model with the new dual-method dataset!")
    print("Run: python train_captcha_model.py")
    print("=" * 80)


if __name__ == "__main__":
    input_dir = "captcha_dataset"
    output_dir = "captcha_dataset_v2"
    
    print("\n🚀 Starting dual-preprocessing dataset generation...")
    print("This will create TWO versions of each captcha (v3_light + v7_hybrid)\n")
    
    regenerate_dataset_dual(input_dir, output_dir)
