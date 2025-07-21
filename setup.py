from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="halodoc-homecare-assistant",
    version="1.0.0",
    description="AI Multi-Agent Assistant for Halodoc Homecare Services",
    author="Your Name",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "halodoc-assistant=main:main",
        ],
    },
)