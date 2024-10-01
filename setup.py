from setuptools import setup, find_packages

setup(
    name='uuid-entitlement-manager',
    version='0.1.0',
    description='A library for managing user UUIDs and entitlements with credits.',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/your-username/uuid-entitlement-manager',  # Update this to your repository URL
    packages=find_packages(),
    install_requires=[
        'Flask', 
        'sqlite3',
        # Add any other dependencies your project requires here
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
