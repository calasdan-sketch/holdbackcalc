# Publish checklist for holdbackcalc (for Dan)

Nothing here has been run. Do it yourself, in this order. The upload step is yours: you are signed in to PyPI, the assistant never uploads.

**Version to release: 0.2.0.** PyPI currently has 0.1.0 only (checked read-only on 2026-11-08). The repo is already marked 0.2.0 everywhere. It is a normal "minor" release: new commands, no removed ones. A few output labels changed since 0.1.0 (see CHANGELOG), which is acceptable while the version starts with 0.

## Check first
1. On GitHub, make sure the CI run on this branch is green. It now also runs on Windows, which nobody has done yet. If the Windows jobs fail, fix before releasing.
2. Run `holdbackcalc verify-sources` on your own computer (install `poppler` so Alberta PDFs can be read). Ontario rules showed as skipped last time because ontario.ca did not give a readable page; save the page from your browser and use `--from-dir` (see README). Any FAIL means the law may have changed: do not release until checked.
3. `holdbackcalc verify-sources` now stops with a non-zero result (3) if it could check nothing at all. Partial skips (Ontario) still show as SKIPPED: that is expected until you save the Ontario pages from your browser.
4. Read the top of the README once: "Not legal advice" must still be there.

## Release steps
```
git checkout main && git merge expert-2          # or open a pull request first
python -m pip install build twine
python -m build
twine check dist/*
twine upload dist/*                              # needs your PyPI login/token; this is the step that publishes
git tag v0.2.0 && git push --tags
```
After uploading, open a clean terminal and run `pip install holdbackcalc==0.2.0`, then `holdbackcalc --version`.

## Decide before releasing
- Ontario rules (20 of 35) have never been machine-verified by the tool; a lawyer or you should read the Ontario Act pages once.
- Whether to keep the GitHub URLs in the package page: they are public-repo links; only keep them if the repo is public.

## Afterwards
Delete the "install from a checkout" note in the README (the grey box under Install).
