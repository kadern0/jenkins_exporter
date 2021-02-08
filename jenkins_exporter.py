#!/usr/bin/python

import argparse
import re
import time
import requests
from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY


class JenkinsCollector():
    jenkins_url = ""
    api_key = ""
    def __init__(self, jenkins_url, api_key):
        self.jenkins_url = jenkins_url
        self.api_key = api_key

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

    def collect(self):
        result = requests.get(self.jenkins_url + "/metrics/" + self.api_key + "/metrics/")
        result_gauges = result.json().get('gauges')

        metric_list = []
        for gauge in result_gauges:
#            print(f"new metric found {gauge} with value {result_gauges.get(gauge).get('value')}")
            name = re.sub(r'(\.|-)', '_', gauge).lower()
            value = result_gauges.get(gauge).get('value')
            if isinstance(value, (list, str)):
                continue
            metric_list.append(GaugeMetricFamily(name, f'metric import from {gauge}', value))
        metric_list += self.get_histograms(result.json().get('timers'))
        metric_list += self.get_meters(result.json().get('meters'))
        metric_list += self.get_histograms(result.json().get('histograms'))

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
