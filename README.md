# jenkdo
This CLI tool was created when I tired of 'Edit -> Commit -> Launch' or 'Edit -> Copy & Paste -> Launch' developing Jenkinsfile flow.
It allow you to validate your jenkinsfile, create a task from it, launch and watch its output in your console, not in browser.

## Usage
— Create `debug` folder on your Jenkins ~or change this script~

— Set `AUTH_USER`, `AUTH_TOKEN` and `JENKINS_URL` environment variables

— `./launch.py --help`, it's easy and only few options :)

## Improvement plans
— Remove `termcolor` dependency because Click have the same function

— Good config for Jenkins URL, tasks folder and authorization

— Installing system-wide

— Change print to logging
