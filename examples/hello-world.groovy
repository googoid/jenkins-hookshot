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
