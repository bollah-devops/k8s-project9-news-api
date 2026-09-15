pipeline {
    agent any

    environment {
        IMAGE_NAME = "tawa123/news-api"
        IMAGE_TAG = "build-${BUILD_NUMBER}"
        NAMESPACE = "project9"
    }

    stages {
        stage("Checkout") {
            steps {
                git branch: "main",
                    url: "https://github.com/bollah-devops/k8s-project9-news-api"
            }
        }

        stage("Build Image") {
            steps {
                sh """
                    docker buildx build \\
                      --platform linux/amd64,linux/arm64 \\
                      -t ${IMAGE_NAME}:${IMAGE_TAG} \\
                      -t ${IMAGE_NAME}:latest \\
                      --push .
                """
            }
        }

        stage("Deploy to Kubernetes") {
            steps {
                sh """
                    kubectl set image deployment/news-api \\
                      news-api=${IMAGE_NAME}:${IMAGE_TAG} \\
                      -n ${NAMESPACE}

                    kubectl set env deployment/news-api \\
                      APP_VERSION=${IMAGE_TAG} \\
                      DEPLOY_TIME="\$(date)" \\
                      -n ${NAMESPACE}
                """
            }
        }

        stage("Verify Deployment") {
            steps {
                sh """
                    kubectl rollout status deployment/news-api \\
                      -n ${NAMESPACE} \\
                      --timeout=120s
                """
            }
        }
    }

    post {
        success {
            echo "Deployment successful — version ${IMAGE_TAG}"
        }
        failure {
            echo "Deployment FAILED — check logs above"
            sh "kubectl rollout undo deployment/news-api -n ${NAMESPACE}"
        }
    }
}
