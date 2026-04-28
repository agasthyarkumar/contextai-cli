from setuptools import setup, find_packages

setup(
    name="aicontext",
    version="0.1.0",
    description="Maintain a compressed, LLM-friendly context of your codebase.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Your Name",
    python_requires=">=3.9",
    packages=find_packages(exclude=["scripts", "tests*"]),
    install_requires=[
        "typer[all]>=0.9.0",
        "python-dotenv>=1.0.0",
        "groq>=0.4.0",
    ],
    extras_require={
        "watch": ["watchdog>=3.0.0"],
    },
    entry_points={
        "console_scripts": [
            "aicontext=aicontext.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
        "Environment :: Console",
    ],
)
