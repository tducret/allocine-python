"""Verify that an installed distribution exposes its expected metadata."""

import os
from importlib.metadata import version

import allocine

package_version = version("allocine")
assert allocine.__version__ == package_version

if release_tag := os.environ.get("RELEASE_TAG"):
    assert package_version == release_tag, f"Package version {package_version!r} does not match tag {release_tag!r}"
