"""Phase 0 placeholder.

The suite is deliberately near-empty: Phase 0 exists to prove the toolchain
and CI work before there is anything to test. Phase 1 replaces this.
"""

import guesstimate


def test_package_imports() -> None:
    assert guesstimate.__version__
