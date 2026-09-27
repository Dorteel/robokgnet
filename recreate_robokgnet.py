"""Rebuild the four canonical RoboKGNet JSON resources in dependency order."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
STAGES = [
    ("Building WordNet", ["wordnet_to_robokgwordnet.py", "--schema", "schemas/objects.json",
                         "--root", "object.n.01", "--output", "robonet_graph/robokgwordnet.json"]),
    ("Applying ConceptNet AtLocation", ["conceptnet_to_robokgconceptnet.py"]),
    ("Building VerbNet", ["verbnet_to_robokgverbnet.py"]),
    ("Applying FrameNet enrichment", ["verbnet_framenet_enrichment.py"]),
]


def main():
    env = os.environ.copy()
    # Use the repository's installed corpora without discarding custom search paths.
    env["NLTK_DATA"] = os.pathsep.join(filter(None, [
        str(ROOT / ".venv/nltk_data"), env.get("NLTK_DATA"),
    ]))
    for index, (label, arguments) in enumerate(STAGES, 1):
        print(f"[{index}/4] {label}...", flush=True)
        try:
            subprocess.run([sys.executable, "-B", *arguments], cwd=ROOT, env=env,
                           check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as error:
            # Keep successful builds quiet, but retain useful failure messages.
            print(error.stdout or "", end="", file=sys.stderr)
            print(error.stderr or "", end="", file=sys.stderr)
            raise SystemExit(error.returncode)
    print("RoboKGNet created successfully.")


if __name__ == "__main__":
    main()
