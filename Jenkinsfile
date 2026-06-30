pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Verify Services') {
            steps {
                bat 'python --version'
                bat 'ollama list'
            }
        }

        stage('Install Dependencies') {
            steps {
                bat '''
                    if not exist venv (
                        python -m venv venv
                    )
                    call venv\\Scripts\\activate
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Run CCT') {
            steps {
                bat '''
                    call venv\\Scripts\\activate
                    python main.py data/sample_c_files/
                '''
            }
        }

        stage('Archive Report') {
            steps {
                archiveArtifacts artifacts: 'output/*.xlsx', fingerprint: true
            }
        }
    }

    post {
        success {
            echo 'Compliance report generated successfully.'
        }
        failure {
            echo 'Pipeline failed.'
        }
    }
}