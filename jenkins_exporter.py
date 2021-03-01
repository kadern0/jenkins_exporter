#!/usr/bin/env python3

import argparse
import json
import re
import time
import urllib.error

from prometheus_client import start_http_server
from prometheus_client.core import (
    GaugeMetricFamily, CounterMetricFamily, REGISTRY
)
from urllib.request import urlopen


class JenkinsCollector():

    def __init__(self, target, api_key):
        self._target = target.rstrip("/")
        self.api_key = api_key

    def get_job_metrics(self):

        # The build statuses we want to export about.
        statuses = ["lastBuild", "lastCompletedBuild", "lastFailedBuild",
                    "lastStableBuild", "lastSuccessfulBuild",
                    "lastUnstableBuild", "lastUnsuccessfulBuild"]

        # The metrics we want to export.
        metrics = {}
        for s in statuses:
            snake_case = re.sub('([A-Z])', '_\\1', s).lower()
            metrics[s] = {
                'number':
                GaugeMetricFamily('jenkins_job_{0}'.format(snake_case),
                                  'Jenkins build number for {0}'.format(s),
                                  labels=["jobname"]),
                'duration':
                GaugeMetricFamily('jenkins_job_{0}_duration_seconds'.format(snake_case),
                                  'Jenkins build duration in seconds for {0}'.format(s), labels=["jobname"]),
                'timestamp':
                GaugeMetricFamily('jenkins_job_{0}_timestamp_seconds'.format(snake_case),
                                  'Jenkins build timestamp in unixtime for {0}'.format(s), labels=["jobname"]),
            }

        # Request exactly the information we need from Jenkins
        try:
            result = json.loads(urlopen(
                "{0}/api/json?tree=jobs[name,{1}]".format(
                    self._target, ",".join([s + "[number,timestamp,duration]" for s in statuses])))
                                .read().decode("utf-8"))
        except urllib.error.URLError as e:
            print(e.__dict__)
            return ""

        for job in result['jobs']:
            name = job['name']
            for s in statuses:
                if s in job and job[s]:
                    status = job[s]
                else:
                    status = {}
                metrics[s]['number'].add_metric([name], status.get('number', 0))
                metrics[s]['duration'].add_metric([name], status.get('duration', 0) / 1000.0)
                metrics[s]['timestamp'].add_metric([name], status.get('timestamp', 0) / 1000.0)

        for s in statuses:
            for m in metrics[s].values():
                yield m

    def get_meters(self, metrics_object):
        metrics_list = []
        metric = CounterMetricFamily('http_response_codes_count', '', labels=["response_code"])
        for metric_entry in metrics_object.keys():
            if metric_entry.startswith('http.responseCodes'):
                metric.add_metric([metric_entry[19:].lower()],
                                  metrics_object.get(metric_entry).get('count'))
            else:
                name = re.sub(r'(\.|-)', '_', metric_entry).lower()
                metrics_list.append(CounterMetricFamily(
                    name, f'metric import from {metric_entry}',
                    metrics_object.get(metric_entry).get('count')))
        return metrics_list

    def get_histograms(self, metrics_object):
        metrics_list = []
        for metric_entry in metrics_object.keys():
            def_labels = ["quantile"]
            extra_labels = []
            extra_labels_value = []
            if metric_entry.startswith('jenkins.node') and metric_entry.endswith('builds'):
                name = "jenkins_node_builds"
                extra_labels += ['node']
                extra_labels_value = [metric_entry[13:-7]]
                def_labels += extra_labels
            else:
                name = re.sub(r'(\.|-|\(|\))', '_', metric_entry).lower()
            # count
            counter_metric = CounterMetricFamily(name,
                                                 f'metric import from {metric_entry}',
                                                 labels=extra_labels)
            counter_metric.add_metric(extra_labels_value,
                                      metrics_object.get(metric_entry).get('count'))
            metrics_list.append(counter_metric)
            metric = GaugeMetricFamily(name, '', labels=def_labels)
            metric.add_metric(["0.5"] + extra_labels_value,
                              metrics_object.get(metric_entry).get('p50'))
            metric.add_metric(["0.75"] + extra_labels_value,
                              metrics_object.get(metric_entry).get('p75'))
            metric.add_metric(["0.95"] + extra_labels_value,
                              metrics_object.get(metric_entry).get('p95'))
            metric.add_metric(["0.98"] + extra_labels_value,
                              metrics_object.get(metric_entry).get('p98'))
            metric.add_metric(["0.99"] + extra_labels_value,
                              metrics_object.get(metric_entry).get('p99'))
            metric.add_metric(["0.999"] + extra_labels_value,
                              metrics_object.get(metric_entry).get('p999'))
            metrics_list.append(metric)
        return metrics_list

    def get_gauges(self, metrics_object):
        metrics_list = []
        for gauge in metrics_object:
            name = re.sub(r'(\.|-)', '_', gauge).lower()
            value = metrics_object.get(gauge).get('value')
            if not isinstance(value, (list, str)):
                metrics_list.append(GaugeMetricFamily(name, f'metric import from {gauge}', value))
        return metrics_list

    def collect(self):

        try:
            result = json.loads(urlopen(
                "{0}/metrics/{1}/metrics/".format(
                    self._target, self.api_key))
                                .read().decode("utf-8"))
        except urllib.error.URLError as e:
            print(e.__dict__)
            return ""

        metric_list = []
        metric_list += self.get_job_metrics()
        metric_list += self.get_gauges(result.get('gauges'))
        metric_list += self.get_histograms(result.get('timers'))
        metric_list += self.get_meters(result.get('meters'))
        metric_list += self.get_histograms(result.get('histograms'))

        for metric in metric_list:
            yield metric


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-key', required=True, help="Api key with metrics access")
    parser.add_argument('--jenkins-url', required=True, help="Jenkins server URL")
    parser.add_argument('--port', help="Jenkins server URL", default=9118)
    args = parser.parse_args()
    REGISTRY.register(JenkinsCollector(args.jenkins_url, args.api_key))
    print(f"Starting server on port: {args.port}")
    start_http_server(args.port)
    while True:
        time.sleep(15)
