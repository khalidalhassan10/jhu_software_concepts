"""Packaging for the Grad Café analytics service: makes ``src`` installable (pip install -e .)."""
from setuptools import find_packages, setup

setup(
    name="gradcafe-analytics",
    version="5.0.0",
    description="Flask + PostgreSQL analysis of Grad Café admission results",
    author="Khaled Al-Hassan",
    python_requires=">=3.12",
    packages=find_packages(include=["src", "src.*"]),
    package_data={"src": ["templates/*.html", "static/*.css"]},
    install_requires=[
        "flask>=3.0",
        "psycopg[binary]>=3.1",
        "sqlalchemy>=2.0",
        "beautifulsoup4>=4.12",
        "urllib3>=2.0",
    ],
    extras_require={
        "dev": ["pytest>=8.0", "pytest-cov>=5.0", "pylint>=3.0", "pydeps>=1.12"],
    },
)