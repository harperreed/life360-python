import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="life360",
    version="2.0.0",
    author="Phil Bruckner",
    author_email="pnbruckner@gmail.com",
    description="Life360 Communications Module",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pnbruckner/life360",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
