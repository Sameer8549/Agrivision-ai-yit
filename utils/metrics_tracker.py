"""
CropSentinel AI  -  utils/metrics_tracker.py
Computes, stores, and retrieves validation metrics (Macro F1, per-class, confusion matrix).
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("MetricsTracker")

class MetricsTracker:
    """
    Computes full validation metrics, saves them to JSON, and provides
    a getter used by the /metrics endpoint.
    """

    METRICS_FILE = os.path.join("model", "validation_metrics.json")

    def get_metrics(self) -> dict:
        """
        Load and return the persisted metrics dict.
        Returns an error dict if the file does not exist.
        """
        try:
            with open(self.METRICS_FILE, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "status":  "error",
                "message": "No metrics found. Run training first.",
                "macro_f1": 0.0,
            }
        except Exception as e:
            logger.error(f"Failed to read metrics file: {e}")
            return {
                "status":  "error",
                "message": f"Could not read metrics: {str(e)}",
                "macro_f1": 0.0,
            }
