from setuptools import setup


# pip install .
setup(
    name="pyrobot-app",
    version="1.0",
    author="Your Name",
    author_email="your@email.com",
    description="A Pyrogram application",
    long_description="A Pyrogram application for working with the Telegram API",
    packages=["pyrobot_app"],
    include_package_data=True,
    install_requires=[
        "anyio == 3.6.2",
        "arrow == 1.2.3",
        "hashids == 1.3.1",
        "httpx == 0.23.3",
        "lxml == 4.9.2",
        "Markdown == 3.4.1",
        "Pillow == 9.4.0",
        "playwright == 1.29.1",
        "pony == 0.7.16",
        "psutil == 5.9.4",
        "py_cpuinfo == 9.0.0",
        "pydantic == 1.10.4",
        "Pyrogram == 2.0.97",
        "setuptools == 65.7.0",
        "Telethon == 1.26.1",
        "torch == 1.13.1",
        "torchaudio == 0.13.1",
        "transliterate == 1.10.2",
        "urllib3 == 1.26.14",
        "openai == 0.25.0",
        "urllib3==1.26.13",
    ],
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License"
    ],
    python_requires=">=3.8"
)
