"""
CropSentinel AI  -  train/run_training.py
CLI script to kick off the two-phase ResNet50 training pipeline.
"""

import argparse
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, ".")


from model.trainer import ModelTrainer


def main():
    parser = argparse.ArgumentParser(
        description="CropSentinel AI  -  Training CLI"
    )
    parser.add_argument(
        "--data",
        type=str,
        default=r"C:\Users\Rohith\OneDrive\Desktop\dataset\plantvillage_dataset\color",
        help="Path to the 'color' folder inside PlantVillage dataset.",
    )
    parser.add_argument(
        "--epochs_phase1",
        type=int,
        default=3,
        help="Phase 1 epochs (FC head only).",
    )
    parser.add_argument(
        "--epochs_phase2",
        type=int,
        default=5,
        help="Phase 2 epochs (layer3 + layer4 + FC fine-tune).",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=16,
        help="Batch size (16 suits the ~1k fast dataset on CPU).",
    )
    args = parser.parse_args()

    print("=" * 65)
    print("  CropSentinel AI  -  ResNet50 Training Pipeline  [FAST MODE]")
    print("  Enterprise  -  AI Production 2026")
    print("=" * 65)
    print(f"  Dataset    : {args.data}")
    print( "  Crops      : Apple, Grape, Tomato (60 images/class max)")
    print(f"  Phase 1    : {args.epochs_phase1} epochs (FC layer only)")
    print(f"  Phase 2    : {args.epochs_phase2} epochs (layer3 + layer4 + FC)")
    print(f"  Batch Size : {args.batch_size}")
    print("=" * 65)

    trainer = ModelTrainer(
        dataset_path=args.data,
        batch_size=args.batch_size,
        num_workers=0,           # Windows requirement  -  must stay 0
        epochs_phase1=args.epochs_phase1,
        epochs_phase2=args.epochs_phase2,
    )

    t0 = time.time()
    try:
        results = trainer.train()
    except Exception as e:
        print(f"\n[ERROR] Training failed: {e}")
        sys.exit(1)
    elapsed = time.time() - t0

    print("\n" + "=" * 65)
    print("  TRAINING COMPLETE")
    print("=" * 65)
    print(f"  Time Taken      : {elapsed / 60:.1f} minutes")
    print(f"  Best Macro F1   : {results['best_macro_f1'] * 100:.2f}%")
    print(f"  Final Accuracy  : {results['final_accuracy'] * 100:.2f}%")
    print(f"  Model saved to  : model/crop_model.pth")
    print(f"  Classes saved   : model/classes.json")
    print(f"  Metrics saved   : model/validation_metrics.json")
    print("=" * 65)
    print("\n  Next step: python app.py")
    print("  Then open: http://localhost:8000/docs\n")


if __name__ == "__main__":
    main()
