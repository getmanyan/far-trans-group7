```python
"""
Thin wrapper to execute Anastasia's run_course_encoder.py for Maria's experiment.
Ensures outputs are directed to Maria's isolated directory without modifying the original script.
"""
import subprocess
import sys
from pathlib import Path

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run Maria's Paraphrase Experiment via existing wrapper")
    parser.add_argument('--team-root', type=str, required=True, help='Path to far-trans-group7 root')
    parser.add_argument('--course-dir', type=str, required=True)
    parser.add_argument('--data-dir', type=str, required=True)
    parser.add_argument('--output-dir', type=str, required=True)
    parser.add_argument('--model', type=str, default='Qwen/Qwen3-1.7B')
    parser.add_argument('--revision', type=str, default='70d244cc86ccca08cf5af4e1e306ecf908b1ad5e')
    args = parser.parse_args()

    team_root = Path(args.team_root)
    wrapper_script = team_root / "run_course_encoder.py"

    if not wrapper_script.exists():
        print(f"ERROR: Cannot find {wrapper_script}. Ensure you are on the correct branch.")
        sys.exit(1)

    cmd = [
        sys.executable, str(wrapper_script),
        "--course-dir", args.course_dir,
        "--data-dir", args.data_dir,
        "--output-dir", args.output_dir,
        "--model", args.model,
        "--revision", args.revision,
        "--device", "cuda",
        "--dtype", "auto",
        "--on-invalid", "fallback"
    ]

    print(f"Executing: {' '.join(cmd)}")
    print("Attribution: Using Anastasia's run_course_encoder.py without modification.")

    result = subprocess.run(cmd, cwd=team_root)
    sys.exit(result.returncode)

if __name__ == '__main__':
    main()