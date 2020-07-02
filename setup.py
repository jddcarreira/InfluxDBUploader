from setuptools import setup

setup(
    name="influxdbuploader",
    version="0.0.1",

    author=["Oles Pisarenko", "João Carreira"],
    author_email=["doctornkz@ya.ru", "jddcarreira@gmail.com"],
    license="MIT",
    description="Python module for Taurus to stream reports to InfluxDB",
    url='https://github.com/johnnybus/influxdbUploader',
    keywords=[],

    packages=["influxdbuploader"],
    install_requires=['bzt', 'influxdb'],
    include_package_data=True,
)
