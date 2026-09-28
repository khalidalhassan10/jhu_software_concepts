"""Sphinx configuration for the Grad Café Analytics documentation."""
import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "Grad Café Analytics"
author = "Khaled Al-Hassan"
release = "4.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "private-members": True,
    "member-order": "bysource",
}

templates_path = ["_templates"]
exclude_patterns = ["_build"]

html_theme = "sphinx_rtd_theme"
html_title = "Grad Café Analytics"
