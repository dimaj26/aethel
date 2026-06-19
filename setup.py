from setuptools import setup, find_packages

setup(
    name="aethel",
    version="1.0.0",
    description="Aethel: AI Context & Memory Management System CLI",
    author="Aethel Team",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        # Core python CLI standard library modules are sufficient, no major external deps needed
    ],
    entry_points={
        "console_scripts": [
            "aethel=aethel.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
