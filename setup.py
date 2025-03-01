#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 Chris Caron <lead2gold@gmail.com>
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

import os
import platform
try:
    from setuptools import setup

except ImportError:
    from distutils.core import setup

from setuptools import find_packages

cmdclass = {}
try:
    from babel.messages import frontend as babel
    cmdclass = {
        'compile_catalog': babel.compile_catalog,
        'extract_messages': babel.extract_messages,
        'init_catalog': babel.init_catalog,
        'update_catalog': babel.update_catalog,
    }
except ImportError:
    pass

install_options = os.environ.get("APPRISE_INSTALL", "").split(",")
install_requires = open('requirements.txt').readlines()
if platform.system().lower().startswith('win'):
    # Windows Notification Support
    install_requires += open('win-requirements.txt').readlines()

libonly_flags = set(["lib-only", "libonly", "no-cli", "without-cli"])
if libonly_flags.intersection(install_options):
    console_scripts = []

else:
    # Load our CLI
    console_scripts = ['apprise = apprise.cli:main']

setup(
    name='apprise',
    version='0.9.6',
    description='Push Notifications that work with just about every platform!',
    license='MIT',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    cmdclass=cmdclass,
    url='https://github.com/caronc/apprise',
    keywords='Push Notifications Alerts Email AWS SES SNS Boxcar ClickSend '
        'DAPNET Dingtalk Discord Dbus Emby Faast FCM Flock Gitter Gnome '
        'Google Chat Gotify Growl Home Assistant IFTTT Join Kavenegar KODI '
        'Kumulos LaMetric MacOS Mailgun Matrix Mattermost MessageBird MQTT '
        'MSG91 Nexmo Nextcloud NextcloudTalk Notica Notifico Office365 '
        'OneSignal Opsgenie ParsePlatform PopcornNotify Prowl PushBullet '
        'Pushjet Pushed Pushover PushSafer Reddit Rocket.Chat Ryver SendGrid '
        'ServerChan SimplePush Sinch Slack SMTP2Go SparkPost Spontit '
        'Streamlabs Stride Syslog Techulus Telegram Twilio Twist Twitter XBMC '
        'MSTeams Microsoft Windows Webex CLI API',
    author='Chris Caron',
    author_email='lead2gold@gmail.com',
    packages=find_packages(),
    package_data={
        'apprise': [
            'assets/NotifyXML-*.xsd',
            'assets/themes/default/*.png',
            'assets/themes/default/*.ico',
            'i18n/*.py',
            'i18n/*/LC_MESSAGES/*.mo',
            'py.typed',
            '*.pyi',
            '*/*.pyi'
        ],
    },
    install_requires=install_requires,
    classifiers=(
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
    ),
    entry_points={'console_scripts': console_scripts},
    python_requires='>=2.7',
    setup_requires=['babel', ],
)
