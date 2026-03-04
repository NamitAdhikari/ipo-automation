#!/usr/bin/env python3
"""
Failed Captcha Labeling Tool
============================

Manual labeling tool for failed captcha predictions.
Displays captcha images and allows user to input correct values.

Usage:
    python label_failed_captchas.py
    
Features:
    - Rich CLI interface with progress tracking
    - System image viewer integration
    - Auto-close images after labeling
    - Keyboard shortcuts (Enter=accept, s=skip, q=quit)
    - Statistics tracking (labeled, skipped, corrected)
    
Author: Auto-generated for IPO Result Checker
"""

import os
import sys
import time
import shutil
import platform
import subprocess
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from PIL import Image
except ImportError:
    print("❌ Missing required packages!")
    print("\nPlease install:")
    print("  pip install rich pillow")
    sys.exit(1)

console = Console()

# Directories
FAILED_DIR = "captcha_dataset_failed"
TARGET_DIR = "captcha_dataset_live"

# Statistics
stats = {
    'total': 0,
    'labeled': 0,
    'skipped': 0,
    'accepted': 0,  # Accepted predicted value
    'corrected': 0   # Entered new value
}

# Track currently open image process for cleanup
current_image_process: Optional[subprocess.Popen] = None


def validate_captcha_input(text: str) -> bool:
    """
    Validate captcha input.
    
    Rules:
    - Must be exactly 5 digits
    - Only digits 1-9 (no zeros)
    
    Args:
        text: Input string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if len(text) != 5:
        return False
    if not text.isdigit():
        return False
    if '0' in text:
        return False
    return True


def show_image(filepath: str) -> Optional[subprocess.Popen]:
    """
    Open image in system default viewer and return process handle.
    
    Args:
        filepath: Path to image file
        
    Returns:
        Process handle if opened successfully, None otherwise
    """
    try:
        system = platform.system()
        
        if system == 'Darwin':  # macOS
            # Use 'open' command which opens in default viewer
            process = subprocess.Popen(['open', filepath])
            return process
        elif system == 'Windows':
            # Use 'start' command
            process = subprocess.Popen(['start', filepath], shell=True)
            return process
        else:  # Linux
            # Try xdg-open
            process = subprocess.Popen(['xdg-open', filepath])
            return process
            
    except Exception as e:
        console.print(f"[yellow]⚠️  Could not open image: {e}[/yellow]")
        console.print(f"[dim]Image path: {filepath}[/dim]")
        console.print(f"[dim]Please open manually to view[/dim]")
        return None


def close_image(process: Optional[subprocess.Popen]) -> None:
    """
    Close the image viewer process.
    
    Args:
        process: Process handle from show_image()
    """
    if process is None:
        return
    
    try:
        # On macOS, we need to kill Preview.app specifically
        if platform.system() == 'Darwin':
            # Kill the process we started
            process.terminate()
            time.sleep(0.2)  # Give it time to close
        else:
            process.terminate()
            time.sleep(0.2)
    except Exception:
        pass  # Ignore errors, image might already be closed


def process_captcha(filepath: str, predicted: str, current: int, total: int) -> str:
    """
    Process a single captcha image.
    
    Args:
        filepath: Path to captcha image
        predicted: Predicted captcha value from filename
        current: Current image number (1-indexed)
        total: Total number of images
        
    Returns:
        'labeled', 'skipped', or 'quit'
    """
    global current_image_process
    
    filename = os.path.basename(filepath)
    
    # Display header
    console.print()
    console.print(Panel.fit(
        f"[bold]Image {current}/{total}[/bold]\n\n"
        f"[cyan]File: {filename}[/cyan]\n"
        f"[yellow]Predicted: {predicted}[/yellow]",
        border_style="blue"
    ))
    
    # Show image in system viewer
    current_image_process = show_image(filepath)
    
    # Get user input
    console.print("\n[bold]Options:[/bold]")
    console.print("  • Press [cyan]Enter[/cyan] to accept predicted value")
    console.print("  • Type [cyan]5 digits[/cyan] to correct")
    console.print("  • Type [yellow]'s'[/yellow] to skip")
    console.print("  • Type [red]'q'[/red] to quit")
    console.print()
    
    try:
        user_input = Prompt.ask("[bold]Enter correct captcha[/bold]", default="").strip()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Interrupted[/yellow]")
        close_image(current_image_process)
        return 'quit'
    
    # Handle input
    if user_input.lower() in ['q', 'quit']:
        console.print("[red]Quitting...[/red]")
        close_image(current_image_process)
        return 'quit'
    
    if user_input.lower() in ['s', 'skip', '']:
        if user_input == '':
            console.print("[yellow]⏭️  Skipped (empty input)[/yellow]")
        else:
            console.print("[yellow]⏭️  Skipped[/yellow]")
        stats['skipped'] += 1
        close_image(current_image_process)
        return 'skipped'
    
    # Validate new input
    if not validate_captcha_input(user_input):
        console.print("[red]✗ Invalid input! Must be 5 digits (1-9, no zeros)[/red]")
        console.print("[yellow]⏭️  Skipping this image[/yellow]")
        stats['skipped'] += 1
        close_image(current_image_process)
        return 'skipped'
    
    correct_value = user_input
    
    # Check if it's different from prediction
    if correct_value == predicted:
        stats['accepted'] += 1
        console.print(f"[green]✓ Confirmed: {correct_value}[/green]")
    else:
        stats['corrected'] += 1
        console.print(f"[green]✓ Corrected: {predicted} → {correct_value}[/green]")
    
    # Move file to target directory with correct name
    timestamp = int(time.time() * 1000)
    new_filename = f"{correct_value}_{timestamp}.png"
    target_path = os.path.join(TARGET_DIR, new_filename)
    
    try:
        # Ensure target directory exists
        os.makedirs(TARGET_DIR, exist_ok=True)
        
        # Move the file
        shutil.move(filepath, target_path)
        console.print(f"[dim]→ Saved to: {target_path}[/dim]")
        stats['labeled'] += 1
        
        # Close image viewer after successful label
        close_image(current_image_process)
        
        return 'labeled'
    except Exception as e:
        console.print(f"[red]✗ Failed to move file: {e}[/red]")
        stats['skipped'] += 1
        close_image(current_image_process)
        return 'skipped'


def main():
    """Main labeling loop"""
    # Banner
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Failed Captcha Labeling Tool[/bold cyan]\n"
        "[dim]Label failed captchas for model improvement[/dim]",
        border_style="cyan"
    ))
    console.print()
    
    # Check directories
    if not os.path.exists(FAILED_DIR):
        console.print(f"[yellow]⚠️  Directory not found: {FAILED_DIR}[/yellow]")
        console.print(f"[dim]No failed captchas have been saved yet.[/dim]")
        console.print(f"\n[dim]Failed captchas are automatically saved when running:[/dim]")
        console.print(f"[cyan]  python ipo_fully_auto_enhanced.py[/cyan]")
        return 0
    
    if not os.path.exists(TARGET_DIR):
        console.print(f"[yellow]Creating target directory: {TARGET_DIR}[/yellow]")
        os.makedirs(TARGET_DIR)
    
    # Get all failed captcha images
    images = sorted([f for f in os.listdir(FAILED_DIR) if f.endswith('.png')])
    
    if not images:
        console.print(f"[green]✓ No failed captchas to label![/green]")
        console.print(f"[dim]All caught up! Failed captchas will appear here after running the checker.[/dim]")
        return 0
    
    stats['total'] = len(images)
    console.print(f"[cyan]Found {stats['total']} failed captcha(s) to label[/cyan]")
    console.print(f"[dim]Images will open in your system's default viewer[/dim]\n")
    
    # Process each image
    for idx, filename in enumerate(images, 1):
        filepath = os.path.join(FAILED_DIR, filename)
        
        # Extract predicted value from filename (before first underscore)
        predicted = filename.split('_')[0]
        
        # Validate predicted value
        if not validate_captcha_input(predicted):
            console.print(f"[yellow]⚠️  Skipping invalid filename: {filename}[/yellow]")
            continue
        
        result = process_captcha(filepath, predicted, idx, stats['total'])
        
        if result == 'quit':
            console.print("\n[yellow]Labeling session ended by user[/yellow]")
            break
    
    # Show final statistics
    console.print()
    console.print(Panel.fit(
        f"[bold]Labeling Session Complete[/bold]\n\n"
        f"[cyan]Total:[/cyan]     {stats['total']}\n"
        f"[green]Labeled:[/green]   {stats['labeled']} "
        f"[dim](confirmed: {stats['accepted']}, corrected: {stats['corrected']})[/dim]\n"
        f"[yellow]Skipped:[/yellow]  {stats['skipped']}\n"
        f"[dim]Remaining:[/dim] {stats['total'] - stats['labeled'] - stats['skipped']}",
        border_style="cyan",
        title="[bold cyan]Summary[/bold cyan]"
    ))
    
    if stats['labeled'] > 0:
        console.print(f"\n[green]✓ {stats['labeled']} captcha(s) added to training dataset![/green]")
        console.print(f"[dim]Location: {TARGET_DIR}/[/dim]")
        console.print(f"\n[yellow]Next steps:[/yellow]")
        console.print(f"  [dim]1. Run: python generate_augmented_dataset.py[/dim]")
        console.print(f"  [dim]2. Run: python train_captcha_model_improved.py[/dim]")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)
