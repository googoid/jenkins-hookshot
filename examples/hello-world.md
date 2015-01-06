# hello-world
This is a basic example of a Jenkins Job DSL script. It defines a single job,
performs a Git checkout, echoes "Hello, world!", and ships the build result
and console output to Logstash. It is triggered as soon as the seed job runs.

```groovy
def basename = "${REPO_NAMESPACE}__${REPO_NAME}__${UUID}"

job {
  // Ship it all to Logstash when the build completes
  configure { ->
    project / publishers << 'jenkins.plugins.logstash.LogstashNotifier' {
      maxLines(-1)
      failBuild(true)
    }
  }

  // Job config
  name "${basename}__test-job"
  description "${REPO_DESCRIPTION}"
  label "mesos"
  scm {
    git("${REPO_URL}", "${GIT_SHA}")
  }
  steps {
    shell('echo "Hello, world!"')
  }
}

// Trigger the newly created job(s)
queue("${basename}__test-job")
```