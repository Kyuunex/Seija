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
    description='Asynchronous osu! api wrapper',
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
        'git+https://github.com/Kyuunex/aioosuapi.git@v1',
        'git+https://github.com/Kyuunex/aioosuapi.git@v2',
        'git+https://github.com/Kyuunex/osudiscordpyembed.git@v1',
        'git+https://github.com/Kyuunex/osudiscordpyembed.git@v2',
        'python-dateutil'
    ],
)
