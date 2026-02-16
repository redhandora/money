from setuptools import find_packages, setup


setup(
    name="money",
    version="0.1.0",
    description="Trend-driven content monetization pipeline",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.6",
    extras_require={
        "dev": [
            "mypy==0.971",
            "pytest==6.2.5",
            "ruff==0.0.17",
        ]
    },
)
