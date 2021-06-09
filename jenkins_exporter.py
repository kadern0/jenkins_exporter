#!/usr/bin/env python3
"""Prometheus exporter for Jenkins"""

import argparse
import re
import sys
import time
import logging
import requests

from requests.exceptions import HTTPError
from prometheus_client import start_http_server
from prometheus_client.core import (
    GaugeMetricFamily, CounterMetricFamily, REGISTRY
)


class JenkinsCollector():
    """Jenkins metrics collector"""
    def __init__(self, target, api_key, user, passwd):
        self._target = target.rstrip("/")
        self.api_key = api_key
        self.user = user
        self.passwd = passwd

    def get_pipeline_metrics(self, job, build_no):
        """Returns duration and status from all stages on pipeline jobs"""
        snake_case = re.sub(r'(\.|-|\(|\))', '_', job).lower()

        try:
            if self.user and self.passwd:
                result = requests.get(
                    f'{self._target}/job/{job}/{build_no}/wfapi/describe',
                    auth=(self.user, self.passwd))
            else:
                result = requests.get(
                    f'{self._target}/job/{job}/{build_no}/wfapi/describe')
            result.raise_for_status()
        except HTTPError as http_err:
            logging.error('HTTP error occurred reading job stages: %s', http_err)
            return []
        except Exception as err:
            logging.error('Other error occurred reading job stages: %s', err)
            return []

        metric = GaugeMetricFamily(
            f'jenkins_job_{snake_case}_stages_duration',
            f'Jenkins duration in seconds for each stage of the job {job}',
            labels=['job', 'stage', 'status']
        )
        for stage in result.json().get('stages'):
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
                GaugeMetricFamily(f'jenkins_job_{snake_case}',
                                  f'Jenkins build number for {s}',
                                  labels=["job"]),
                'duration':
                GaugeMetricFamily(f'jenkins_job_{snake_case}_duration_seconds',
                                  f'Jenkins build duration in seconds for {s}', labels=["job"]),
                'timestamp':
                GaugeMetricFamily(f'jenkins_job_{snake_case}_timestamp_seconds',
                                  f'Jenkins build timestamp in unixtime for {s}', labels=["job"]),
            }

        # Request exactly information we need from Jenkins
        try:
            if self.user and self.passwd:
                result = requests.get(
                    f'{self._target}/api/json?tree=jobs[name,{",".join([s + "[number,timestamp,duration]" for s in statuses])}]',
                    auth=(self.user, self.passwd))
            else:
                result = requests.get(
                    f'{self._target}/api/json?tree=jobs[name,{",".join([s + "[number,timestamp,duration]" for s in statuses])}]')
            result.raise_for_status()
        except HTTPError as http_err:
            logging.error('HTTP error occurred reading jobs: %s', http_err)
            return []
        except Exception as err:
            logging.error('Other error occurred reading jobs: %s', err)
            return []
        for job in result.json().get('jobs'):
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
                if ((build_number != 0) and (s == "lastBuild")
                        and job['_class'] == "org.jenkinsci.plugins.workflow.job.WorkflowJob"):
                    metrics[s][name+'_stages'] = self.get_pipeline_metrics(name, build_number)

        for s in statuses:
            for m in metrics[s].values():
                yield m
    @staticmethod
    def get_meters(metrics_object):
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

    @staticmethod
    def get_timers(metrics_object):
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

    @staticmethod
    def get_gauges(metrics_object):
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
            result = requests.get(f'{self._target}/metrics/{self.api_key}/metrics')
            result.raise_for_status()
        except HTTPError as http_err:
            logging.error('HTTP error occurred: %s', http_err)
            sys.exit("Couldn't stablish connection to the metrics API")
        except Exception as err:
            logging.error('Other error occurred: %s', err)
            sys.exit("Couldn't stablish connection to the metrics API")

        metric_list = []
        metric_list += self.get_job_metrics()
        metric_list += self.get_gauges(result.json().get('gauges'))
        metric_list += self.get_timers(result.json().get('timers'))
        metric_list += self.get_meters(result.json().get('meters'))
        metric_list += self.get_timers(result.json().get('histograms'))

        for metric in metric_list:
            yield metric


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-key', required=True, help="Api key with metrics access")
    parser.add_argument('--jenkins-url', required=True, help="Jenkins server URL")
    parser.add_argument('--port', type=int, help="Jenkins server URL", default=9118)
    parser.add_argument('--user', required=False,
                        help="Jenkins user with jobs read access", default='')
    parser.add_argument('--passwd', required=False,
                        help="Password/token for jenkins user", default='')
    args = parser.parse_args()
    while True:
        try:
            REGISTRY.register(JenkinsCollector(args.jenkins_url, args.api_key,
                                               args.user, args.passwd))
        except:
            logging.error('Some error occurred connecting to Jenkins, please review the configuration.')
            logging.info('Sleeping for 300 seconds before retrying...')
            time.sleep(3000)
        else:
            break

    logging.info("Starting server on port: %d", args.port)
    start_http_server(args.port)
    while True:
        time.sleep(30)
