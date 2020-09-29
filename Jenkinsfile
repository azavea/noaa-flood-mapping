#!groovy

node {
  try {
    env.COMPOSE_PROJECT_NAME = "noaa-flood-mapping-${env.BRANCH_NAME}-${env.BUILD_NUMBER}"

    stage('checkout') {
      checkout scm
    }

    stage('cibuild') {
      wrap([$class: 'AnsiColorBuildWrapper']) {
        sh './scripts/cibuild'
      }
    }

    if (currentBuild.currentResult == 'SUCCESS' && currentBuild.previousBuild?.result != 'SUCCESS') {
      def slackMessage = ":jenkins: *Flood Mapping (${env.BRANCH_NAME}) #${env.BUILD_NUMBER}*"
      if (env.CHANGE_TITLE) {
        slackMessage += "\n${env.CHANGE_TITLE} - ${env.CHANGE_AUTHOR}"
      }
      slackMessage += "\n<${env.BUILD_URL}|View Build>"
      slackSend channel: '#noaa-flood-mapping', color: 'good', message: slackMessage
    }
  } catch (err) {
    // Some exception was raised in the `try` block above. Assemble
    // an appropriate error message for Slack.
    def slackMessage = ":jenkins-angry: *Flood Mapping (${env.BRANCH_NAME}) #${env.BUILD_NUMBER}*"
    if (env.CHANGE_TITLE) {
      slackMessage += "\n${env.CHANGE_TITLE} - ${env.CHANGE_AUTHOR}"
    }
    slackMessage += "\n<${env.BUILD_URL}|View Build>"
    slackSend  channel: '#noaa-flood-mapping', color: 'danger', message: slackMessage

    // Re-raise the exception so that the failure is propagated to Jenkins.
    throw err
  } finally {
    // Pass or fail, ensure that the services and networks created by Docker
    // Compose are torn down.
    sh 'docker-compose down -v'
  }
}