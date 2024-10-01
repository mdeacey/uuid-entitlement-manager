from setuptools import setup, find_packages

setup(
    name='uuid_entitlement_manager',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Flask',
        'Click',
        'requests',
    ],
)
