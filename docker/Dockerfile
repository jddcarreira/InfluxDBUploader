FROM python

# Installing latest InfluxDB and Taurus as dependency
RUN pip install --upgrade pip \
    && pip install --upgrade setuptools \
    && git clone https://github.com/johnnybus/InfluxDBUploader.git \
    && cd influxDBUploader \
    && pip install .
