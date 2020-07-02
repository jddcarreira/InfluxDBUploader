"""
Based on bza.py (Blazemeter API client) module, and adopted as-is for InfluxDB
"""

import copy
import datetime
import logging
import os
import sys
import time
import traceback
import uuid
from functools import wraps
from ssl import SSLError
from influxdb import InfluxDBClient

from requests.exceptions import ReadTimeout
from datetime import datetime
from bzt import TaurusInternalException, TaurusNetworkError, TaurusConfigError
from bzt.engine import Reporter
from bzt.engine import Singletone
from bzt.modules.aggregator import DataPoint, KPISet, ResultsProvider, AggregatorListener
from bzt.six import iteritems, URLError
from bzt.utils import open_browser
from bzt.utils import to_json, dehumanize_time

NETWORK_PROBLEMS = (IOError, URLError, SSLError, ReadTimeout, TaurusNetworkError)


def send_with_retry(method):
    @wraps(method)
    def _impl(self, *args, **kwargs):
        if not isinstance(self, InfluxDBUploader):
            raise TaurusInternalException("send_with_retry should only be applied to InfluxDBUploader methods")

        try:
            method(self, *args, **kwargs)
        except (IOError, TaurusNetworkError):
            self.log.debug("Error sending data: %s", traceback.format_exc())
            self.log.warning("Failed to send data, will retry in %s sec...", self._session.timeout)
            try:
                time.sleep(self._session.timeout)
                method(self, *args, **kwargs)
                self.log.info("Succeeded with retry")
            except NETWORK_PROBLEMS:
                self.log.error("Fatal error sending data: %s", traceback.format_exc())
                self.log.warning("Will skip failed data and continue running")

    return _impl


class Session(object):
    def __init__(self, influxdb_address, influxdb_port, influxdb_user, influxdb_password, influxdb_database):
        super(Session, self).__init__()
        self.influxdb_address = influxdb_address
        self.influxdb_port = influxdb_port
        self.influxdb_user = influxdb_user
        self.influxdb_password = influxdb_password
        self.influxdb_database = influxdb_database
        self.dashboard_url = 'https://<REALM>.signalfx.com/#/dashboard/<ID>'
        self.timeout = 30
        self.logger_limit = 256
        self.log = logging.getLogger(self.__class__.__name__)
        self._retry_limit = 5
        self.uuid = None
        self._influxdb_client = InfluxDBClient(self.influxdb_address, self.influxdb_port, self.influxdb_user, self.influxdb_password, self.influxdb_database)

    def ping(self):
        """ Quick check if we can access the service """
        self._influxdb_client.ping()

    def send_kpi_data_influxdb(self, data):
        self._influxdb_client.write_points(data)


class InfluxDBUploader(Reporter, AggregatorListener, Singletone):
    """
    Reporter class

    :type _session: bzt.sfa.Session or None
    """

    def __init__(self):
        super(InfluxDBUploader, self).__init__()
        self.browser_open = 'start'
        self.project = 'myproject'
        self.custom_tags = {}
        self.additional_tags = {}
        self.kpi_buffer = []
        self.send_interval = 30
        self._last_status_check = time.time()
        self.last_dispatch = 0
        self.results_url = None
        self._test = None
        self._master = None
        self._session = None
        self.first_ts = sys.maxsize
        self.last_ts = 0
        self._dpoint_serializer = DatapointSerializer(self)

    def credentials_processor(self):
        # Read from config file
        influxdb_user = self.settings.get("influxdb-user")
        influxdb_password = self.settings.get("influxdb-password")

        if influxdb_user and influxdb_password:
            self.log.info("Credentials found in config file")
            return influxdb_user, influxdb_password
        self.log.info("Credentials not found in config file")

        try:
            influxdb_user = os.environ['INFLUXDB_USER']
            influxdb_password = os.environ['INFLUXDB_PASSWORD']
            self.log.info("InfluxDB credentials found in environment variables")
            return influxdb_user, influxdb_password
        except:
            self.log.info("InfluxDB credentials not found in environment variables")
            pass
        return None

    def prepare(self):
        """
        Read options for uploading, check that they're sane
        """
        super(InfluxDBUploader, self).prepare()
        self.send_interval = dehumanize_time(self.settings.get("send-interval", self.send_interval))
        self.browser_open = self.settings.get("browser-open", self.browser_open)
        self.project = self.settings.get("project", self.project)
        self.custom_tags = self.settings.get("custom-tags", self.custom_tags)
        self._dpoint_serializer.multi = self.settings.get("report-times-multiplier", self._dpoint_serializer.multi)
        self.sess_id = str(uuid.uuid4()).split("-")[-1]

        self.additional_tags.update({'project': self.project, 'id': self.sess_id})
        self.additional_tags.update(self.custom_tags)

        influxdb_user, influxdb_password = self.credentials_processor()
        if not (influxdb_user and influxdb_password):
            raise TaurusConfigError("No InfluxDB credentials provided")

        self._session = Session(
                                influxdb_address= self.settings.get("influxdb-address"),
                                influxdb_port=self.settings.get("influxdb-port"),
                                influxdb_user=influxdb_user,
                                influxdb_password=influxdb_password,
                                influxdb_database=self.settings.get("influxdb-database")
                                )
        self._session.log = self.log.getChild(self.__class__.__name__)
        self._session.dashboard_url = self.settings.get("dashboard-url", self._session.dashboard_url).rstrip("/")
        self._session.timeout = dehumanize_time(self.settings.get("timeout", self._session.timeout))

        try:
            self._session.ping()  # to check connectivity and auth
        except Exception:
            self.log.error("Cannot reach InfluxDB")
            raise

        if isinstance(self.engine.aggregator, ResultsProvider):
            self.engine.aggregator.add_listener(self)

    def startup(self):
        """
        Initiate online test
        """
        super(InfluxDBUploader, self).startup()

        self.results_url = self._session.dashboard_url + \
                           '?startTime=-15m&endTime=Now' + \
                           '&sources%5B%5D=' + \
                           'project:' + \
                           self.project + \
                           '&sources%5B%5D=id:' + \
                           self.sess_id + \
                           '&density=4'

        self.log.info("Started data feeding: %s", self.results_url)
        if self.browser_open in ('start', 'both'):
            open_browser(self.results_url)

    def post_process(self):
        """
        Upload results if possible
        """
        self.log.debug("KPI bulk buffer len in post-proc: %s", len(self.kpi_buffer))
        self.log.info("Sending remaining KPI data to server...")
        self.__send_data(self.kpi_buffer, False, True)
        self.kpi_buffer = []

        if self.browser_open in ('end', 'both'):
            open_browser(self.results_url)
        self.log.info("Report link: %s", self.results_url)

    def check(self):
        """
        Send data if any in buffer
        """
        self.log.debug("KPI bulk buffer len: %s", len(self.kpi_buffer))
        if self.last_dispatch < (time.time() - self.send_interval):
            self.last_dispatch = time.time()
            if len(self.kpi_buffer):
                self.__send_data(self.kpi_buffer)
                self.kpi_buffer = []
        return super(InfluxDBUploader, self).check()

    @send_with_retry
    def __send_data(self, data, do_check=True, is_final=False):
        """
        :type data: list[bzt.modules.aggregator.DataPoint]
        """

        serialized = self._dpoint_serializer.get_kpi_body(data, self.additional_tags, is_final)
        self._session.send_kpi_data_influxdb(serialized)

    def aggregated_second(self, data):
        """
        Send online data
        :param data: DataPoint
        """
        self.kpi_buffer.append(data)


class DatapointSerializer(object):
    def __init__(self, owner):
        """
        :type owner: InfluxDBUploader
        """
        super(DatapointSerializer, self).__init__()
        self.owner = owner
        self.multi = 1000  # miltiplier factor for reporting

    def get_kpi_body(self, data_buffer, tags, is_final):
        # - reporting format:
        #   {labels: <data>,    # see below
        #    sourceID: <id of BlazeMeterClient object>,
        #    [is_final: True]}  # for last report
        #
        # - elements of 'data' are described in __get_label()
        #
        # - elements of 'intervals' are described in __get_interval()
        #   every interval contains info about response codes have gotten on it.
        influxdb_labels_list = []

        if data_buffer:
            self.owner.first_ts = min(self.owner.first_ts, data_buffer[0][DataPoint.TIMESTAMP])
            self.owner.last_ts = max(self.owner.last_ts, data_buffer[-1][DataPoint.TIMESTAMP])

            # fill 'Timeline Report' tab with intervals data
            # intervals are received in the additive way
            for dpoint in data_buffer:
                timestamp = datetime.utcfromtimestamp(dpoint[DataPoint.TIMESTAMP]).strftime('%Y-%m-%dT%H:%M:%SZ')
                for label, kpi_set in iteritems(dpoint[DataPoint.CURRENT]):
                    tags = copy.deepcopy(tags)
                    tags.update({'label': label or 'OVERALL'})
                    label_data = self.__convert_data(kpi_set, timestamp, tags)
                    influxdb_labels_list.extend(label_data)

        return influxdb_labels_list

    def __convert_data(self, item, timestamp, tags):
        # Overall stats : RPS, Threads, percentiles and mix/man/avg
        tmin = int(self.multi * item[KPISet.PERCENTILES]["0.0"]) if "0.0" in item[KPISet.PERCENTILES] else 0
        tmax = int(self.multi * item[KPISet.PERCENTILES]["100.0"]) if "100.0" in item[KPISet.PERCENTILES] else 0
        tavg = self.multi * item[KPISet.AVG_RESP_TIME]

        influxdb_data = [
            {'measurement': 'RPS', 'tags': tags, 'time': timestamp, 'fields': {'value': item[KPISet.SAMPLE_COUNT]}},
            {'measurement': 'Threads', 'tags': tags, 'time': timestamp, 'fields': {'value': item[KPISet.CONCURRENCY]}},
            {'measurement': 'Failures', 'tags': tags, 'time': timestamp, 'fields': {'value': item[KPISet.FAILURES]}},
            {'measurement': 'min', 'tags': tags, 'time': timestamp, 'fields': {'value': tmin}},
            {'measurement': 'max', 'tags': tags, 'time': timestamp, 'fields': {'value': tmax}},
            {'measurement': 'avg', 'tags': tags, 'time': timestamp, 'fields': {'value': tavg}}
        ]

        for p in item[KPISet.PERCENTILES]:
            tperc = int(self.multi * item[KPISet.PERCENTILES][p])
            influxdb_data.append({'measurement': 'p' + p, 'tags': tags, 'time': timestamp, 'fields': {'value': tperc}})

        # Detailed info : Error
        for rcode in item[KPISet.RESP_CODES]:
            error_dimensions = copy.deepcopy(tags)
            error_dimensions['rc'] = rcode
            rcnt = item[KPISet.RESP_CODES][rcode]
            influxdb_data.append({'measurement': 'rc', 'tags': error_dimensions, 'time': timestamp, 'fields': {'value': rcnt}})

        return influxdb_data
