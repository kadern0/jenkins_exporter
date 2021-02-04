# jenkins_exporter
Prometheus exporter for Jenkins' metrics plugin

Initial POC for a replacement for the [Jenkins Prometheus Metrics Plugin](https://plugins.jenkins.io/prometheus/). Since this plugin currently has some memory leaking problems.

Unlike with a plugin, if this exporter stops working it will never impact Jenkins (it doesn't even have to run in the same machine).

It requires the installation of the [Metrics-plugin](https://github.com/jenkinsci/metrics-plugin) and an API with read access to the Metrics servelet, as explained [here](https://plugins.jenkins.io/metrics/).

# Usage
```bash
./jenkins_exporter.py --jenkins-url https://my.jenkins.com --api-key XXXXXXX
```
# Metrics

Metrics will be available on the specified port. By default is set to 9118.
```bash
# HELP process_start_time_seconds Start time of the process since unix epoch in seconds.
# TYPE process_start_time_seconds gauge
process_start_time_seconds 1.61247413886e+09
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total 0.62
# HELP process_open_fds Number of open file descriptors.
# TYPE process_open_fds gauge
process_open_fds 6.0
# HELP process_max_fds Maximum number of open file descriptors.
# TYPE process_max_fds gauge
process_max_fds 1024.0
# HELP jenkins_executor_count_value metric import from jenkins.executor.count.value
# TYPE jenkins_executor_count_value gauge
jenkins_executor_count_value 28.0
# HELP jenkins_executor_free_value metric import from jenkins.executor.free.value
# TYPE jenkins_executor_free_value gauge
jenkins_executor_free_value 25.0
# HELP jenkins_executor_in_use_value metric import from jenkins.executor.in-use.value
# TYPE jenkins_executor_in_use_value gauge
jenkins_executor_in_use_value 3.0
# HELP jenkins_health_check_count metric import from jenkins.health-check.count
# TYPE jenkins_health_check_count gauge
jenkins_health_check_count 4.0
# HELP jenkins_health_check_inverse_score metric import from jenkins.health-check.inverse-score
# TYPE jenkins_health_check_inverse_score gauge
jenkins_health_check_inverse_score 0.0
# HELP jenkins_health_check_score metric import from jenkins.health-check.score
# TYPE jenkins_health_check_score gauge
jenkins_health_check_score 1.0
# HELP jenkins_job_averagedepth metric import from jenkins.job.averageDepth
# TYPE jenkins_job_averagedepth gauge
jenkins_job_averagedepth 1.0079787234042554
# HELP jenkins_job_count_value metric import from jenkins.job.count.value
# TYPE jenkins_job_count_value gauge
jenkins_job_count_value 752.0
# HELP jenkins_node_count_value metric import from jenkins.node.count.value
# TYPE jenkins_node_count_value gauge
jenkins_node_count_value 30.0
# HELP jenkins_node_offline_value metric import from jenkins.node.offline.value
# TYPE jenkins_node_offline_value gauge
jenkins_node_offline_value 10.0
# HELP jenkins_node_online_value metric import from jenkins.node.online.value
# TYPE jenkins_node_online_value gauge
jenkins_node_online_value 20.0
# HELP jenkins_plugins_active metric import from jenkins.plugins.active
# TYPE jenkins_plugins_active gauge
jenkins_plugins_active 208.0
# HELP jenkins_plugins_failed metric import from jenkins.plugins.failed
# TYPE jenkins_plugins_failed gauge
...
```

# Author

[Pablo Caderno](https://github.com/kadern0)
