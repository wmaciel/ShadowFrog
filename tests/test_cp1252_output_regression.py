"""Regression: the CLI helpers must stay UTF-8-safe under a narrow (cp1252)
codec, not only on a UTF-8 platform.

Linux/macOS default to UTF-8, so the Windows ``cp1252`` failure is invisible
in the normal Linux CI. These tests force the narrow-codec failure mode on
*any* OS:

  * ``PYTHONIOENCODING=cp1252`` pins a Windows-style narrow stdout codec
    (covers the stdout ``reconfigure`` fix).
  * ``LC_ALL=C`` + ``PYTHONUTF8=0`` makes the default *file* encoding narrow on
    POSIX too (covers the ``open(..., encoding="utf-8")`` fix); on Windows the
    ANSI code page already makes it ``cp1252``.

Without the Phase-1 fixes each helper raises ``UnicodeEncodeError`` /
``UnicodeDecodeError`` and exits non-zero; with them, both pass everywhere.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DEMO_SHADOW = REPO / "examples" / "coupon-demo" / ".shadow"
VIEWER = REPO / "skills" / "shadow-frog-viewer" / "shadow-viewer.py"
LINEAGE = REPO / "skills" / "shadow-frog-viewer" / "dream-lineage.py"


def _narrow_env():
    """Environment that forces a narrow (non-UTF-8) default codec everywhere."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "cp1252"  # narrow stdout/stderr codec
    env["PYTHONUTF8"] = "0"             # ensure UTF-8 Mode isn't masking it
    env["LC_ALL"] = "C"                 # narrow default file codec on POSIX
    return env


@pytest.mark.slow
@pytest.mark.integration
def test_shadow_viewer_invariants_under_narrow_codec():
    """shadow-viewer prints a non-ASCII check mark; it must survive a pipe."""
    r = subprocess.run(
        [sys.executable, str(VIEWER), "--check-invariants",
         "--shadow-dir", str(DEMO_SHADOW)],
        capture_output=True, encoding="utf-8", env=_narrow_env(),
    )
    assert r.returncode == 0, f"stderr:\n{r.stderr}"
    assert "\u2713 Invariants OK" in r.stdout  # the U+2713 check mark survived


@pytest.mark.slow
@pytest.mark.integration
def test_dream_lineage_writes_utf8_html_under_narrow_codec(tmp_path):
    """dream-lineage embeds a frog emoji + box glyphs in the HTML it writes."""
    out = tmp_path / "lineage.html"
    r = subprocess.run(
        [sys.executable, str(LINEAGE), "-o", str(out),
         "--shadow-dir", str(DEMO_SHADOW)],
        capture_output=True, encoding="utf-8", env=_narrow_env(),
    )
    assert r.returncode == 0, f"stderr:\n{r.stderr}"
    # The U+1F438 frog must round-trip as UTF-8 bytes regardless of locale.
    assert b"\xf0\x9f\x90\xb8" in out.read_bytes()
