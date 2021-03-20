import unittest
from mock import patch
from prometheus_client.core import (
    GaugeMetricFamily, CounterMetricFamily)

from jenkins_exporter import JenkinsCollector


class JenkinsCollectorTests(unittest.TestCase):
    def setUp(self):
        self._fake_jenkins = JenkinsCollector(
            target="http://fake-jenkins.com", api_key="fake_key", user="", passwd="")

        self._fake_metrics = {'fake_metric': {'count': '1'}}
        self._fake_timers = {'fake_timer': {'count': '1'}}

    def test_get_meters(self):
        """Test: get_meters"""
        fake_metric_list = self._fake_jenkins.get_meters(self._fake_metrics)
        self.assertIsInstance(fake_metric_list[0], CounterMetricFamily)

    def test_get_timers(self):
        """Test: get_timers"""
        fake_metric_list = self._fake_jenkins.get_timers(
            self._fake_timers)
        self.assertIsInstance(fake_metric_list[0], GaugeMetricFamily)
