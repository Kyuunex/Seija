from setuptools import setup

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
        'discord.py[voice]==2.5.2',
        'pycountry',
        'aiosqlite',
        'psutil',
        'aioosuapi @ git+https://github.com/Kyuunex/aioosuapi.git@1.4.1',
        'aioosuwebapi @ git+https://github.com/Kyuunex/aioosuapi.git@2.0.dev10',
        'python-dateutil',
        'appdirs',
        'beautifulsoup4'
    ],
)
