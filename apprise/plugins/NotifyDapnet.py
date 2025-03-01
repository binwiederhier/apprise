# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 Chris Caron <lead2gold@gmail.com>
# All rights reserved.
#
# This code is licensed under the MIT License.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files(the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and / or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions :
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# To use this plugin, sign up with Hampager (you need to be a licensed
# ham radio operator
#  http://www.hampager.de/
#
# You're done at this point, you only need to know your user/pass that
# you signed up with.

#  The following URLs would be accepted by Apprise:
#   - dapnet://{user}:{password}@{callsign}
#   - dapnet://{user}:{password}@{callsign1}/{callsign2}

# Optional parameters:
#   - priority (NORMAL or EMERGENCY). Default: NORMAL
#   - txgroups --> comma-separated list of DAPNET transmitter
#                           groups. Default: 'dl-all'
#                           https://hampager.de/#/transmitters/groups

from json import dumps

# The API reference used to build this plugin was documented here:
#  https://hampager.de/dokuwiki/doku.php#dapnet_api
#
import requests
from requests.auth import HTTPBasicAuth

from .NotifyBase import NotifyBase
from ..AppriseLocale import gettext_lazy as _
from ..URLBase import PrivacyMode
from ..common import NotifyType
from ..utils import is_call_sign
from ..utils import parse_call_sign
from ..utils import parse_list
from ..utils import parse_bool


class DapnetPriority(object):
    NORMAL = 0
    EMERGENCY = 1


DAPNET_PRIORITIES = (
    DapnetPriority.NORMAL,
    DapnetPriority.EMERGENCY,
)


class NotifyDapnet(NotifyBase):
    """
    A wrapper for DAPNET / Hampager Notifications
    """

    # The default descriptive name associated with the Notification
    service_name = 'Dapnet'

    # The services URL
    service_url = 'https://hampager.de/'

    # The default secure protocol
    secure_protocol = 'dapnet'

    # A URL that takes you to the setup/help of the specific protocol
    setup_url = 'https://github.com/caronc/apprise/wiki/Notify_dapnet'

    # Dapnet uses the http protocol with JSON requests
    notify_url = 'http://www.hampager.de:8080/calls'

    # The maximum length of the body
    body_maxlen = 80

    # A title can not be used for Dapnet Messages.  Setting this to zero will
    # cause any title (if defined) to get placed into the message body.
    title_maxlen = 0

    # The maximum amount of emails that can reside within a single transmission
    default_batch_size = 50

    # Define object templates
    templates = ('{schema}://{user}:{password}@{targets}',)

    # Define our template tokens
    template_tokens = dict(
        NotifyBase.template_tokens,
        **{
            'user': {
                'name': _('User Name'),
                'type': 'string',
                'required': True,
            },
            'password': {
                'name': _('Password'),
                'type': 'string',
                'private': True,
                'required': True,
            },
            'target_callsign': {
                'name': _('Target Callsign'),
                'type': 'string',
                'regex': (
                    r'^[a-z0-9]{2,5}(-[a-z0-9]{1,2})?$', 'i',
                ),
                'map_to': 'targets',
            },
            'targets': {
                'name': _('Targets'),
                'type': 'list:string',
                'required': True,
            },
        }
    )

    # Define our template arguments
    template_args = dict(
        NotifyBase.template_args,
        **{
            'to': {
                'name': _('Target Callsign'),
                'type': 'string',
                'map_to': 'targets',
            },
            'priority': {
                'name': _('Priority'),
                'type': 'choice:int',
                'values': DAPNET_PRIORITIES,
                'default': DapnetPriority.NORMAL,
            },
            'txgroups': {
                'name': _('Transmitter Groups'),
                'type': 'string',
                'default': 'dl-all',
                'private': True,
            },
            'batch': {
                'name': _('Batch Mode'),
                'type': 'bool',
                'default': False,
            },
        }
    )

    def __init__(self, targets=None, priority=None, txgroups=None,
                 batch=False, **kwargs):
        """
        Initialize Dapnet Object
        """
        super(NotifyDapnet, self).__init__(**kwargs)

        # Parse our targets
        self.targets = list()

        # get the emergency prio setting
        if priority not in DAPNET_PRIORITIES:
            self.priority = self.template_args['priority']['default']
        else:
            self.priority = priority

        if not (self.user and self.password):
            msg = 'A Dapnet user/pass was not provided.'
            self.logger.warning(msg)
            raise TypeError(msg)

        # Get the transmitter group
        self.txgroups = parse_list(
            NotifyDapnet.template_args['txgroups']['default']
            if not txgroups else txgroups)

        # Prepare Batch Mode Flag
        self.batch = batch

        for target in parse_call_sign(targets):
            # Validate targets and drop bad ones:
            result = is_call_sign(target)
            if not result:
                self.logger.warning(
                    'Dropping invalid Amateur radio call sign ({}).'.format(
                        target),
                )
                continue

            # Store callsign
            self.targets.append(result['callsign'])

        return

    def send(self, body, title='', notify_type=NotifyType.INFO, **kwargs):
        """
        Perform Dapnet Notification
        """

        if not self.targets:
            # There is no one to email; we're done
            self.logger.warning(
                'There are no Amateur radio callsigns to notify')
            return False

        # Send in batches if identified to do so
        batch_size = 1 if not self.batch else self.default_batch_size

        headers = {
            'User-Agent': self.app_id,
            'Content-Type': 'application/json; charset=utf-8',
        }

        # error tracking (used for function return)
        has_error = False

        # prepare the emergency mode
        emergency_mode = True \
            if self.priority == DapnetPriority.EMERGENCY else False

        # Create a copy of the targets list
        targets = list(self.targets)

        for index in range(0, len(targets), batch_size):

            # prepare JSON payload
            payload = {
                'text': body,
                'callSignNames': targets[index:index + batch_size],
                'transmitterGroupNames': self.txgroups,
                'emergency': emergency_mode,
            }

            self.logger.debug('DAPNET POST URL: %s' % self.notify_url)
            self.logger.debug('DAPNET Payload: %s' % dumps(payload))

            # Always call throttle before any remote server i/o is made
            self.throttle()
            try:
                r = requests.post(
                    self.notify_url,
                    data=dumps(payload),
                    headers=headers,
                    auth=HTTPBasicAuth(
                        username=self.user, password=self.password),
                    verify=self.verify_certificate,
                    timeout=self.request_timeout,
                )
                if r.status_code != requests.codes.created:
                    # We had a problem

                    self.logger.warning(
                        'Failed to send DAPNET notification {} to {}: '
                        'error={}.'.format(
                            payload['text'],
                            ' to {}'.format(self.targets),
                            r.status_code
                        )
                    )

                    self.logger.debug(
                        'Response Details:\r\n{}'.format(r.content))

                    # Mark our failure
                    has_error = True

                else:
                    self.logger.info(
                        'Sent \'{}\' DAPNET notification {}'.format(
                            payload['text'], 'to {}'.format(self.targets)
                        )
                    )

            except requests.RequestException as e:
                self.logger.warning(
                    'A Connection error occurred sending DAPNET '
                    'notification to {}'.format(self.targets)
                )
                self.logger.debug('Socket Exception: %s' % str(e))

                # Mark our failure
                has_error = True

        return not has_error

    def url(self, privacy=False, *args, **kwargs):
        """
        Returns the URL built dynamically based on specified arguments.
        """

        # Define any URL parameters
        _map = {
            DapnetPriority.NORMAL: 'normal',
            DapnetPriority.EMERGENCY: 'emergency',
        }

        # Define any URL parameters
        params = {
            'priority': 'normal' if self.priority not in _map
            else _map[self.priority],
            'batch': 'yes' if self.batch else 'no',
            'txgroups': ','.join(self.txgroups),
        }

        # Extend our parameters
        params.update(self.url_parameters(privacy=privacy, *args, **kwargs))

        # Setup Authentication
        auth = '{user}:{password}@'.format(
            user=NotifyDapnet.quote(self.user, safe=""),
            password=self.pprint(
                self.password, privacy, mode=PrivacyMode.Secret, safe=''
            ),
        )

        return '{schema}://{auth}{targets}?{params}'.format(
            schema=self.secure_protocol,
            auth=auth,
            targets='/'.join([self.pprint(x, privacy, safe='')
                              for x in self.targets]),
            params=NotifyDapnet.urlencode(params),
        )

    @staticmethod
    def parse_url(url):
        """
        Parses the URL and returns enough arguments that can allow
        us to re-instantiate this object.

        """
        results = NotifyBase.parse_url(url, verify_host=False)
        if not results:
            # We're done early as we couldn't load the results
            return results

        # All elements are targets
        results['targets'] = [NotifyDapnet.unquote(results['host'])]

        # All entries after the hostname are additional targets
        results['targets'].extend(NotifyDapnet.split_path(results['fullpath']))

        # Support the 'to' variable so that we can support rooms this way too
        # The 'to' makes it easier to use yaml configuration
        if 'to' in results['qsd'] and len(results['qsd']['to']):
            results['targets'] += parse_call_sign(results['qsd']['to'])

        # Check for priority
        if 'priority' in results['qsd'] and len(results['qsd']['priority']):
            _map = {
                # Letter Assignments
                'n': DapnetPriority.NORMAL,
                'e': DapnetPriority.EMERGENCY,
                'no': DapnetPriority.NORMAL,
                'em': DapnetPriority.EMERGENCY,
                # Numeric assignments
                '0': DapnetPriority.NORMAL,
                '1': DapnetPriority.EMERGENCY,
            }
            try:
                results['priority'] = \
                    _map[results['qsd']['priority'][0:2].lower()]

            except KeyError:
                # No priority was set
                pass

        # Check for one or multiple transmitter groups (comma separated)
        # and split them up, when necessary
        if 'txgroups' in results['qsd']:
            results['txgroups'] = \
                [x.lower() for x in
                 NotifyDapnet.parse_list(results['qsd']['txgroups'])]

        # Get Batch Mode Flag
        results['batch'] = \
            parse_bool(results['qsd'].get(
                'batch', NotifyDapnet.template_args['batch']['default']))

        return results
