import setuptools

with open("README.md") as fp:
    long_description = fp.read()

version = {}
with open("life360/version.py") as fp:
    exec(fp.read(), version)

setuptools.setup(
    name="life360",
    version=version['__version__'],
    author="Phil Bruckner",
    author_email="pnbruckner@gmail.com",
    description="Life360 Communications Module",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pnbruckner/life360",
    packages=setuptools.find_packages(),
    install_requires=[
        "aiohttp",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
