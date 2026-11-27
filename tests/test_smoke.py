# Author:    mikomeller
# Version:   0.1.0
# Filename:  test_smoke.py
# Pathname:  tests/test_smoke.py
# Purpose:   Smoke tests: the package and the mcp dependency import
def test_package_imports() -> None:
    import family_shopper

    assert family_shopper.__version__ == "0.1.0"


def test_mcp_imports() -> None:
    import mcp

    assert mcp is not None
