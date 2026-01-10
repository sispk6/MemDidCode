"""
Script to compare benchmark results from multiple JSON files.
Path: evaluation/compare_runs.py
"""
import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

def load_result(file_path: str) -> Dict[str, Any]:
    with open(file_path, "r") as f:
        return json.load(f)

def compare_runs(file_paths: List[str]):
    results = []
    
    # Load all files
    for path in file_paths:
        if not Path(path).exists():
            print(f"[ERROR] File not found: {path}")
            continue
        results.append((path, load_result(path)))
        
    if not results:
        print("No valid results to compare.")
        return

    # Extract all unique metric keys found across all runs
    all_keys = set()
    for _, res in results:
        all_keys.update(res.get("aggregated_metrics", {}).keys())
    sorted_keys = sorted(list(all_keys))
    
    # Print Headers
    header_fmt = "{:<25} | " + " | ".join([f"{k:<15}" for k in sorted_keys])
    print(f"\n{'='*len(header_fmt.format('RUN', *['']*len(sorted_keys)))}")
    print(header_fmt.format("RUN", *[k.upper() for k in sorted_keys]))
    print(f"{'-'*len(header_fmt.format('RUN', *['']*len(sorted_keys)))}")
    
    # Print Rows
    for path, res in results:
        metrics = res.get("aggregated_metrics", {})
        
        # Format values
        values = []
        for k in sorted_keys:
            val = metrics.get(k, "N/A")
            if isinstance(val, (int, float)):
                values.append(f"{val:.4f}")
            else:
                values.append(str(val))
                
        # Shorten filename for display
        run_name = Path(path).name
        print(header_fmt.format(run_name, *values))
    
    print(f"{'='*len(header_fmt.format('RUN', *['']*len(sorted_keys)))}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare multiple benchmark result JSON files.")
    parser.add_argument("files", nargs="+", help="Paths to result JSON files to compare")
    
    args = parser.parse_args()
    compare_runs(args.files)
