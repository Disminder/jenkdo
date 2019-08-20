pipeline {
    agent { label 'your_agent_label' }
    parameters {
        string(name: 'NAME', defaultValue: 'nobody', description: 'Имя')
    }
    stages {
        stage('Test') {
            steps {
                sh 'pwd'
                echo 'Hi, ' + params.NAME
                sleep 10
                echo 'Wake up'
            }
        }
    }
}
