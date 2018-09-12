from setuptools import setup

setup(
    name='ambassador',
    version='0.1',
    description='Collection of sample ambassador implementations and a basic ambassador framework',
    author='PolySwarm Developers',
    author_email='info@polyswarm.io',
    url='https://github.com/polyswarm/ambassador',
    license='MIT',
    include_package_data=True,
    packages=['ambassador'],
    package_dir={
        'ambassador': 'src/ambassador',
    },
    entry_points={
        'console_scripts': ['ambassador=ambassador.__main__:main']
    },
)
