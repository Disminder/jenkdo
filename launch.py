#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import atexit
import os
from time import sleep

import click
import jinja2
import requests
from termcolor import colored


JENKINS_URL = os.environ['JENKINS_URL']
AUTH = requests.auth.HTTPBasicAuth(os.environ['AUTH_USER'], os.environ['AUTH_TOKEN'])


@click.command()
@click.argument(
    'jenkinsfile',
    type=click.File('r'),
    required=True
)
@click.argument(
    'templatefile',
    type=click.File('r'),
    required=True,
    default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template_job.xml')
)
@click.option(
    '-k',
    '--keep',
    'keep',
    is_flag=True,
    show_default=False,
    help='Don\'t delete a job when build ended'
)
@click.option(
    '-v',
    '--verbose',
    'verbose',
    is_flag=True,
    show_default=False,
    help='Print [Pipeline] rows in console output'
)
@click.option(
    '-y',
    '--yes',
    'yes',
    is_flag=True,
    show_default=False,
    help='Automatically agree with validation result'
)
@click.option(
    '-f',
    '--force',
    'force',
    is_flag=True,
    show_default=False,
    help='Delete a job if it\'s already exists'
)
def main(jenkinsfile, templatefile, keep, verbose, yes, force):
    '''
        This script will create pipeline task from TEMPLATE_FILE with JENKINS_FILE as pipeline script

        JENKINS_FILE - File with pipeline. Should end on '.groovy' or '.jenkinsfile'

        TEMPLATE_FILE - File with job config. Should be '.xml'.
        See template_job.xml here.
        Or get it from just created pipeline task via
        'GET %JENKINS_URL%/job/%PIPELINE_TASK%/config.xml'.
        Should contain '{{ jenkinsfile | forceescape() }}' in <script> section
    '''
    if JENKINS_URL is None:
        msg = '> Please, specify JENKINS_URL and AUTH_USER/AUTH_TOKEN environment variable'
        print(colored(msg, 'red'))
        exit(1)

    job = JenkinsJob(jenkinsfile, templatefile)
    job.validate()
    if not yes:
        msg = '> Press Enter to continue or Ctrl+C to exit'
        input(colored(msg, 'green'))

    job.create(force)
    if not keep:
        atexit.register(job.delete)

    job.start()
    atexit.register(job.stop)

    if job.watch_stream(verbose) == 0:
        atexit.unregister(job.stop)


class JenkinsJob:
    def __init__(self, jenkinsfile, template):
        self.name = (
            os.path.basename(jenkinsfile.name)
                .replace('.groovy', '')
                .replace('.jenkinsfile', ''))

        self.jenkinsfile_content = jenkinsfile.read()
        jenkinsfile.close()

        self.template_content = template.read()
        template.close()

        self.build_number = None
        self.build_url = None
        self.queue_url = None

    def validate(self):
        '''Validate pipeline part of this taks on server'''

        msg = '> Validating...'
        print(colored(msg, 'green'))

        url = '{}/pipeline-model-converter/validate'.format(JENKINS_URL)
        data = {'jenkinsfile': self.jenkinsfile_content}
        res = requests.post(
            url,
            auth=AUTH,
            data=data)

        msg = '> Validation response:'
        print(colored(msg, 'green'))
        print(res.text, end='')

    def create(self, force):
        '''Create this taks on server'''
        if force:
            url = ('{}/job/debug/job/{}/config.xml'
                .format(JENKINS_URL, self.name))
            res = requests.get(url, auth=AUTH)
            if res.status_code != 404:
                self.delete()

        template = jinja2.Template(self.template_content)
        filled_template = template.render(
            jenkinsfile=self.jenkinsfile_content)

        headers = {'Content-Type': 'text/xml'}
        params = {'name': self.name}
        url = '{}/job/debug/createItem'.format(JENKINS_URL)
        res = requests.post(
            url,
            headers=headers,
            data=filled_template.encode('utf-8'),
            params=params,
            auth=AUTH
        )

        if res.status_code != 200:
            msg = "> Unable to create '{}' job".format(self.name)
            print(colored(msg,'red'))

            log_filename = self._log('create', res.text)

            msg = "> See '{}' for additional info".format(log_filename)
            print(colored(msg, 'red'))

            exit(1)

        msg = "> Job '{}' created".format(self.name)
        print(colored(msg, 'green'))

    def delete(self):
        '''Delete this taks on server'''
        url = '{}/job/debug/job/{}/doDelete'.format(JENKINS_URL, self.name)
        res = requests.post(url, auth=AUTH)

        if res.status_code != 200:
            msg = "> Unable to delete '{}' job".format(self.name)
            print(colored(msg, 'red'))

            log_filename = self._log('delete', res.text)

            msg = "> See '{}' for additional info".format(log_filename)
            print(colored(msg, 'red'))

            exit(1)

        msg = "> Job '{}' deleted".format(self.name)
        print(colored(msg, 'green'))

    def start(self):
        '''Start this taks on server'''
        msg = '> Starting...'
        print(colored(msg, 'green'))

        url = '{}/job/debug/job/{}/build'.format(JENKINS_URL, self.name)
        res = requests.post(url, auth=AUTH)

        if res.status_code != 201:
            msg = '> Something goes wrong'
            print(colored(msg, 'red'))
            print(res.text)

        self.queue_url = res.headers['location']
        self._set_build_number()

    def _set_build_number(self):
        if self.queue_url is None:
            raise RuntimeError('No queue url - build was not scheduled')

        waiting = True
        carriage_return_printed = False
        waiting_time = 0

        while waiting:
            url = '{}{}'.format(self.queue_url, 'api/json')
            res = requests.get(url)

            if res.json().get('executable') is None:
                reason = 'Unknown'
                if res.json().get('why') is not None:
                    reason = res.json().get('why')

                if waiting_time >= 9:
                    # TODO: Добавить время ожидания
                    msg = ('\r> Waiting in queue for {} seconds. Reason: {}'
                        .format(int(waiting_time / 10), reason))
                    print(colored(msg, 'yellow'), end='', flush=True)
                    carriage_return_printed = True

                sleep(0.1)
                waiting_time += 1
                continue

            if carriage_return_printed:
                print('')

            msg = "> Building '{}' started".format(self.name)
            print(colored(msg, 'green'))

            waiting = False

            self.build_number = res.json().get('executable').get('number')
            self.build_url = res.json().get('executable').get('url')
            self.queue_url = None

    def _get_queue_number(self):
        if self.queue_url is None:
            return None

        return os.path.basename(os.path.normpath(self.queue_url))

    # TODO: Проверки status_code
    def stop(self):
        '''Stop this task on server'''
        if self._get_queue_number() is not None:
            res = requests.post(
                '{}/queue/cancelItem'.format(JENKINS_URL),
                data={'id': int(self._get_queue_number())},
                auth=AUTH
            )
            msg = ("> '{}' stopped from queue, HTTP code: {}"
                .format(self.name, res.status_code))
            print(colored(msg, 'green'))
            return

        if self.build_url is not None:
            res = requests.post(
                '{}/stop'.format(self.build_url),
                auth=AUTH
            )
            msg = ("> '{}' abort request sended. Waiting for stop..."
                .format(self.name))
            print(colored(msg, 'green'))

            url = '{}/api/json'.format(self.build_url)
            stopped = False
            while not stopped:
                sleep(0.1)
                res = requests.get(url, auth=AUTH)
                if not res.json().get('building'):
                    stopped = True

            msg = ("> '{}' stopped"
                .format(self.name))
            print(colored(msg, 'green'))
            return

        msg = "> Building '{}' job already stopped".format(self.name)
        print(colored(msg, 'green'))

    def watch_stream(self, verbose):
        start_at = 0
        stream_open = True
        check_job_status = 0
        console = requests.session()

        console_url = '{}{}'.format(self.build_url, 'logText/progressiveText')
        status_url = '{}{}'.format(self.build_url, 'api/json')

        print(colored('> Attempting to get console output:', 'green'))
        print('')
        while stream_open:
            res = requests.get(status_url, auth=AUTH)
            build_going = res.json().get('building')

            if not build_going:
                stream_open = False

            res = console.post(console_url,
                data={'start': start_at},
                auth=AUTH)

            content_length = int(res.headers.get('Content-Length', -1))

            # Прикольное состояние, когда билд уже не в queue,
            #   но ещё не начался
            if res.status_code == 404:
                continue

            if res.status_code != 200:
                msg = '> Something goes wrong'
                print(colored(msg, 'red'))
                print(res.content)
                print(res.headers)

            if content_length == 0:
                sleep(0.1)
                continue

            for line in res.text.splitlines():
                if verbose:
                    print(line)
                    continue

                if '[Pipeline]' in line:
                    continue

                print(line)

            start_at = int(res.headers.get('X-Text-Size'))
            sleep(0.1)

        res = requests.get(status_url, auth=AUTH)
        build_result = res.json().get('result')
        print('')
        msg = '> Build ended with result: {}'.format(build_result)
        print(colored(msg, 'green'))

        return 0

    def _log(self, log_descripton, log_content):
        if not os.path.isdir('./logs'):
            os.mkdir('./logs')

        filename = './logs/{}_{}_log.html'.format(self.name, log_descripton)

        log_file = open(filename, 'w')
        log_file.write(log_content)
        log_file.close()

        return filename

if __name__ == '__main__':
    main()
