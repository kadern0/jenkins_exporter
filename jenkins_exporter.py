#!/usr/bin/env python3

import argparse
import json
import re
import time
import urllib.error

from urllib.request import urlopen
from prometheus_client import start_http_server
from prometheus_client.core import (
    GaugeMetricFamily, CounterMetricFamily, REGISTRY
)


class JenkinsCollector():
    """Jenkins metrics collector"""
    def __init__(self, target, api_key):
        self._target = target.rstrip("/")
        self.api_key = api_key


    def get_pipeline_metrics(self, job, build_no):
        """Returns duration and status from all stages on pipeline jobs"""
        snake_case = re.sub(r'(\.|-|\(|\))', '_', job).lower()
#        snake_case = re.sub('([A-Z])', '_\\1', job).lower()
        try:
            result = json.loads(urlopen(
                "{0}/job/{1}/{2}/wfapi/describe".format(
                    self._target, job, build_no))
                                .read().decode("utf-8"))
        except urllib.error.URLError as e:
            print(e.__dict__)
            return []
        metric = GaugeMetricFamily(
            'jenkins_job_{0}_stages_duration'.format(snake_case),
            'Jenkins duration in seconds for each stage of the job {0}'.format(job),
            labels=['jobname', 'stage', 'status']
        )
        for stage in result.get('stages'):
            metric.add_metric([job, stage.get('name', ''),
                               stage.get('status', '')],
                              stage.get('durationMillis', 0) / 1000.0)

        return metric


    def get_job_metrics(self):
        """Returns metrics from jobs"""

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

        # Request exactly information we need from Jenkins
        try:
            result = json.loads(urlopen(
                "{0}/api/json?tree=jobs[name,{1}]".format(
                    self._target, ",".join([s + "[number,timestamp,duration]" for s in statuses])))
                                .read().decode("utf-8"))
        except urllib.error.URLError as e:
            print(e.__dict__)
            yield []

        for job in result['jobs']:
            name = job['name']
            for s in statuses:
                if s in job and job[s]:
                    status = job[s]
                else:
                    status = {}
                build_number = status.get('number', 0)
                metrics[s]['number'].add_metric([name], build_number)
                metrics[s]['duration'].add_metric([name], status.get('duration', 0) / 1000.0)
  #              metrics[s]['timestamp'].add_metric([name], status.get('timestamp', 0) / 1000.0)
                if (build_number != 0) and (s == "lastBuild") and job['_class'] == "org.jenkinsci.plugins.workflow.job.WorkflowJob":
                    metrics[s][name+'_stages'] = self.get_pipeline_metrics(name, build_number)

        for s in statuses:
            for m in metrics[s].values():
                yield m

    def get_meters(self, metrics_object):
        """Returns metrics list from meters"""
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


    def get_timers(self, metrics_object):
        """Returns metrics from histograms and timers"""
        metrics_list = []
        keys_to_ignore = ['values', 'duration_units', 'rate_units', 'stddev']
        for metric_entry in metrics_object.keys():
            for entry in metrics_object.get(metric_entry).keys():
                if entry in keys_to_ignore:
                    continue
                extra_labels = []
                extra_labels_value = []
                if metric_entry.startswith('jenkins.node') and metric_entry.endswith('builds'):
                    name = "jenkins_node_builds"
                    extra_labels += ['node']
                    extra_labels_value = [metric_entry[13:-7]]
                else:
                    name = re.sub(r'(\.|-|\(|\))', '_', metric_entry).lower()
                if entry in ('p50', 'p75', 'p95', 'p98', 'p99', 'p999'):
                    extra_labels += ['quantile']
                    extra_labels_value += [entry.replace('p', '0.')]
                else:
                    name += f'_{entry}'
                if extra_labels:
                    metric = GaugeMetricFamily(name, f'metric import from {metric_entry}', labels=extra_labels)
                    metric.add_metric(extra_labels_value, metrics_object.get(metric_entry).get(entry))
                else:
                    metric = GaugeMetricFamily(name, f'metric import from {metric_entry}')
                    metric.add_metric('', metrics_object.get(metric_entry).get(entry))
                metrics_list.append(metric)

        return metrics_list


    def get_gauges(self, metrics_object):
        """Returns metrics list from gauges"""
        metrics_list = []
        for gauge in metrics_object:
            name = re.sub(r'(\.|-)', '_', gauge).lower()
            value = metrics_object.get(gauge).get('value')
            if not isinstance(value, (list, str)):
                metrics_list.append(GaugeMetricFamily(name, f'metric import from {gauge}', value))
        return metrics_list

    def collect(self):
        """Main collecting function"""
        try:
            result = json.loads(urlopen(
                "{0}/metrics/{1}/metrics/".format(
                    self._target, self.api_key))
                                .read().decode("utf-8"))
        except urllib.error.URLError as e:
            print(e.__dict__)
            yield []

        metric_list = []
        metric_list += self.get_job_metrics()
        metric_list += self.get_gauges(result.get('gauges'))
        metric_list += self.get_timers(result.get('timers'))
        metric_list += self.get_meters(result.get('meters'))
        metric_list += self.get_timers(result.get('histograms'))

        for metric in metric_list:
            yield metric


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-key', required=True, help="Api key with metrics access")
    parser.add_argument('--jenkins-url', required=True, help="Jenkins server URL")
    parser.add_argument('--port', type=int, help="Jenkins server URL", default=9118)
    args = parser.parse_args()
    REGISTRY.register(JenkinsCollector(args.jenkins_url, args.api_key))
    print(f"Starting server on port: {args.port}")
    start_http_server(args.port)
    while True:
        time.sleep(30)
