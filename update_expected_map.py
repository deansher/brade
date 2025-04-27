#\!/usr/bin/env python

from aider.io import InputOutput
from aider.models import _ModelConfigImpl
from aider.repomap import RepoMap
from pathlib import Path

# Path to the sample code base
sample_code_base = Path(__file__).parent / "tests" / "fixtures" / "sample-code-base"

# Path to the expected repo map file
expected_map_file = Path(__file__).parent / "tests" / "fixtures" / "sample-code-base-repo-map.txt"

# Initialize RepoMap with the sample code base as root
io = InputOutput()
repomap_root = Path(__file__).parent
repo_map = RepoMap(
    main_model=_ModelConfigImpl("gpt-3.5-turbo"),
    root=str(repomap_root),
    io=io,
)

# Get all files in the sample code base
other_files = [str(f) for f in sample_code_base.rglob("*") if f.is_file()]

# Generate the repo map
generated_map_str = repo_map.get_repo_map([], other_files).strip()

# Update the expected map file
with open(expected_map_file, "w", encoding="utf-8") as f:
    f.write(generated_map_str + "\n")

print(f"Updated {expected_map_file}")
