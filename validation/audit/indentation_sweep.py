#!/usr/bin/env python3
"""Does the tab convention decide the indentation direction on a SECOND rated
corpus, or only on Buse and Weimer's?

On the 100 Buse-Weimer snippets the number of columns a tab contributes decides
the sign of the indentation features' correlation with the human ratings: null
at one column, the published negative from two on (uncertainty_probes.py). The
Scalabrino et al. archive ships nine evaluator rows beside its 200 methods, 151
of which are tab-indented, and its own extractor reads a tab as zero columns.
So the same sweep is computable on a corpus where the zero-column convention is
not a thought experiment but the shipped reading.

Counting here is the instrument's definition of its indentation features
(leading whitespace, over all lines including blank ones,
a tab expanded to the width under test), done on the raw method text with no
scaffold, so that the sweep depends on nothing but the archive and the
convention. The rating vector is the mean of the nine evaluator rows, loaded by
the same function the end-to-end corner re-run uses, so the two probes cannot
disagree about which rating belongs to which method.

Aggregates only are printed. The archive carries no permission and is fetched
at run time into the gitignored cache (PERMISSIONS.md); a missing archive is a
hard error, never a silent skip.

output: indentation_sweep_results.txt (regenerate, never edit).
"""

from __future__ import annotations

import random
import statistics
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "bw_faithfulness"))
import policy_corner_rerun as corner  # noqa: E402
import stats  # noqa: E402

TAB_WIDTHS = (0, 1, 2, 4, 8)
BOOT_ITERS = 2000
BOOT_SEED = 0


def indentation(text: str, tab: int) -> tuple[float, int]:
    """(average, maximum) leading-whitespace columns over all lines."""
    cols = []
    for line in text.splitlines():
        lead = line[: len(line) - len(line.lstrip(" \t"))]
        cols.append(sum(tab if ch == "\t" else 1 for ch in lead))
    return (statistics.fmean(cols) if cols else 0.0), (max(cols) if cols else 0)


def main() -> int:
    if not corner.CORPUS_ZIP.exists():
        print(f"ERROR: {corner.CORPUS_ZIP} is missing; run "
              f"validation/breadth/fetch.py --all first (never tracked).",
              file=sys.stderr)
        return 1
    ratings = corner._mean_ratings()
    with zipfile.ZipFile(corner.CORPUS_ZIP) as z:
        members = {int(Path(n).stem): n for n in z.namelist()
                   if n.startswith(corner.MEMBER) and n.endswith(".jsnp")}
        texts = {i: z.read(n).decode("utf-8", "replace") for i, n in members.items()}
    ids = sorted(i for i in texts if i in ratings)
    y = [ratings[i] for i in ids]
    tabbed = sum(1 for i in ids if any(ln.startswith("\t") for ln in texts[i].splitlines()))
    print(f"corpus: {len(ids)} rated methods of the Scalabrino et al. archive, "
          f"{tabbed} tab-indented; rating = mean of the evaluator rows "
          f"({corner.RATINGS}), the vector the corner re-run also uses")

    avg = {t: [indentation(texts[i], t)[0] for i in ids] for t in TAB_WIDTHS}
    mx = {t: [float(indentation(texts[i], t)[1]) for i in ids] for t in TAB_WIDTHS}
    print("Spearman against the mean rating, by columns per tab "
          "(raw text, no scaffold, all lines):")
    for t in TAB_WIDTHS:
        print(f"  tab={t}: avg_indentation {stats.spearman(avg[t], y):+.4f}   "
              f"max_indentation {stats.spearman(mx[t], y):+.4f}"
              + ("   <- the tool's own reading (tabs count nothing)" if t == 0 else ""))

    # Paired contrasts: the corners share every method, so resample methods,
    # recompute both correlations on the same resample, and difference them.
    rng = random.Random(BOOT_SEED)
    n = len(ids)
    for feat_name, feat in (("avg_indentation", avg), ("max_indentation", mx)):
        for hi_t, lo_t in ((8, 0), (4, 0), (8, 4)):
            obs = stats.spearman(feat[hi_t], y) - stats.spearman(feat[lo_t], y)
            deltas = []
            for _ in range(BOOT_ITERS):
                idx = [rng.randrange(n) for _ in range(n)]
                ys = [y[j] for j in idx]
                deltas.append(stats.spearman([feat[hi_t][j] for j in idx], ys)
                              - stats.spearman([feat[lo_t][j] for j in idx], ys))
            deltas.sort()
            lo = deltas[int(0.025 * BOOT_ITERS)]
            hi = deltas[int(0.975 * BOOT_ITERS) - 1]
            print(f"  paired {feat_name}: rho(tab={hi_t}) - rho(tab={lo_t}) = {obs:+.4f}, "
                  f"95% CI [{lo:+.4f}, {hi:+.4f}] ({BOOT_ITERS} resamples, seed {BOOT_SEED})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
