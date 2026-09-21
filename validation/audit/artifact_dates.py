#!/usr/bin/env python3
"""When were the audited artifacts built, and when was the defective source
last touched? Read from the zip entry timestamps of the cached jars.

The audit records a defect in the original tool's distributed builds
(`original_extractor_rerun.py`). Figure 9 of the 2010 paper gives all five
affected features non-zero predictive power, which a constant column cannot
have, so the published analysis does not look like it ran under the defect.
The artifacts' own dates bound that from the other side: the earliest dated
artifact carrying the defect shows it existed by that date, and the per-feature
analysis was first published before it. The dates are entry timestamps inside the jars,
which a Fat-Jar build stamps uniformly at build time and a source jar carries
per file, so they are read, not inferred.

Reads the cached jars only (fetched at run time under recorded hashes, never
redistributed); a missing jar is a hard error.

output: artifact_dates.txt (regenerate, never edit).
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
ARTIFACTS = {
    "readability-original.jar": "the 2010 executable the replication page serves",
    "readability-applet.jar": "the applet build carrying the detector source",
    "rsm.jar": "the Scalabrino et al. extractor",
}
DEFECT_SOURCE = "raykernel/apps/readability/detectors/MaxLineValueDetector.java"


def stamp(info: zipfile.ZipInfo) -> str:
    y, mo, d, h, mi, _ = info.date_time
    return f"{y:04d}-{mo:02d}-{d:02d} {h:02d}:{mi:02d}"


def main() -> int:
    for name, what in ARTIFACTS.items():
        path = CACHE / name
        if not path.exists():
            print(f"ERROR: {path} is missing; run fetch.py first.", file=sys.stderr)
            return 1
        with zipfile.ZipFile(path) as z:
            infos = [i for i in z.infolist() if not i.is_dir()]
            infos.sort(key=lambda i: i.date_time)
            print(f"{name} ({what}): {len(infos)} entries, "
                  f"earliest {stamp(infos[0])}, latest {stamp(infos[-1])}")
            names = {i.filename: i for i in infos}
            if DEFECT_SOURCE in names:
                src = z.read(DEFECT_SOURCE).decode("utf-8", "replace").splitlines()
                hit = next((k + 1 for k, ln in enumerate(src)
                            if "fd.featureNames()" in ln and "max" in ln), None)
                print(f"  {DEFECT_SOURCE}: dated {stamp(names[DEFECT_SOURCE])}; "
                      f"the array-concatenation defect is at line {hit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
