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
        self._fake_histograms = {'fake_histogram': {'count': '1'}}

    def test_get_meters(self):
        """Test: get_histograms"""
        fake_metric_list = self._fake_jenkins.get_meters(self._fake_metrics)
        self.assertIsInstance(fake_metric_list[0], CounterMetricFamily)

    def test_get_histograms(self):
        """Test: get_histograms"""
        fake_metric_list = self._fake_jenkins.get_histograms(
            self._fake_histograms)
        self.assertIsInstance(fake_metric_list[1], GaugeMetricFamily)
