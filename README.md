# jenkdo
This CLI tool was created when I tired of 'Edit -> Commit -> Launch' or 'Edit -> Copy & Paste -> Launch' developing Jenkinsfile flow.
It allow you to validate your jenkinsfile, create a task from it, launch and watch its output in your console, not in browser.

Also, you can easily integrate this script into IDEA via 'Settings -> Tools -> External Tools'

## Usage
— Create `debug` folder on your Jenkins ~or change this script~

— `./launch.py --help`, it's easy and only few options :)

## Improvement plans
— Remove `termcolor` dependency because Click have the same function

— Good config for tasks folder

— Installing system-wide

— Change print to logging
