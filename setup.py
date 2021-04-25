from distutils.core import setup

from seija.manifest import VERSION

setup(
    name='seija',
    packages=[
        'seija',
        'seija.cogs',
        'seija.embeds',
        'seija.modules',
        'seija.reusables'
    ],
    version=VERSION,
    description='The heart of The Mapset Management Server on Discord.',
    author='Kyuunex',
    author_email='kyuunex@protonmail.ch',
    url='https://github.com/Kyuunex/Seija',
    install_requires=[
        'discord.py[voice]',
        'upsidedown',
        'pycountry',
        'Pillow',
        'aiosqlite',
        'bs4',
        'aiohttp',
        'beautifulsoup4',
        'psutil',
        'aioosuapi @ git+https://github.com/Kyuunex/aioosuapi.git@v1',
        'aioosuwebapi @ git+https://github.com/Kyuunex/aioosuapi.git@v2',
        'python-dateutil',
        'appdirs'
    ],
)
