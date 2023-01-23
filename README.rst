*****************
O365-jira-connect
*****************

.. image:: https://img.shields.io/pypi/v/O365-jira-connect
    :target: https://pypi.org/project/O365-jira-connect
    :alt: PyPI version
.. image:: https://github.com/codectl/O365-jira-connect/actions/workflows/ci.yaml/badge.svg
    :target: https://github.com/codectl/O365-jira-connect/actions/workflows/ci.yaml
    :alt: CI
.. image:: https://codecov.io/gh/codectl/O365-jira-connect/branch/master/graph/badge.svg
    :target: https://app.codecov.io/gh/codectl/O365-jira-connect/branch/master
    :alt: codecov
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
    :alt: code style: black
.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
    :target: https://opensource.org/licenses/MIT
    :alt: license: MIT

An integration tool for receiving events from a *O365* subscription and integrating
them into a *Jira*.

One clear use case for this utility is the translation of incoming *O365* (*Outlook*)
messages into a Jira* project in the form of issues. In one hand, *Jira* provides
good tools for tracking and managing issues, on the other hand, *O365* is a
convenient way to receive events, such as messages in the form of e-mails. Hence,
this solution comes to merge the best of both worlds by allowing anyone to create a
*Jira* issue directly from a *O365* event. Simply put, once a new *O365* event is
received, the service picks it up and either translates into a new issue or updates an
existing issue.

Features
========
* Supports *Jira Cloud Platform* & *Jira Server Platform*
* Currently supported *O365* events include:

  * *O365 Outlook* messages

Installation
============
Install the package directly from ``PyPI`` (recommended):

.. code-block:: bash

    $ pip install -U O365-jira-connect

Configuration 📄
----------------
Since the project can read properties from the environment, one can use an ``.env``
file for application configurations. These should be set accordingly for a correct
service usage.

A possible configuration is:

.. code-block:: bash

    # database URI
    SQLALCHEMY_DATABASE_URI=sqlite:///issues.db

    # O365 settings
    O365_ID_PROVIDER=https://login.microsoftonline.com
    O365_PRINCIPAL=mailbox@example.com
    O365_TENANT_ID=...
    O365_CLIENT_ID=...
    O365_CLIENT_SECRET=...
    O365_SCOPES=...  # optional

    # Jira settings
    JIRA_PLATFORM_URL=https://atlassian.net
    JIRA_PLATFORM_USER=me@example.com
    JIRA_PLATFORM_TOKEN=...
    JIRA_ISSUE_TYPE=Task
    JIRA_ISSUE_DEFAULT_LABELS=support,tasks

    # Jira supported boards
    JIRA_SUPPORT_BOARD=support
    JIRA_BOARDS=JIRA_SUPPORT_BOARD
    JIRA_DEFAULT_BOARD=JIRA_SUPPORT_BOARD

    # filter settings
    JIRA_WHITELIST=example.com
    JIRA_BLACKLIST=malicious@example.com

O365 Auth
^^^^^^^^^
Because the service relies on *O365* services, the access is done through *oauth2*
protocol. The services runs best with the "client credentials" flow, which in that
case one simply sets the environment variables ``O365_CLIENT_ID`` and
``O365_CLIENT_SECRET``. To generate an *access token*, run the following:

.. code-block:: bash

    $ O365_connect authorize

At this point, a new *access token* is issued and stored in the default backend
provider, which is the SQL table ``access_tokens``. For each token, a *refresh token*
is also issued with an expiration date of 90 days, at which point one must issue a
new one.

Alternatively, and less recommended, the "authorization code" flow can be used. See
file ``src/O365_jira_connect/cli.py`` and apply changes mentioned there. Then run the
same instruction:

    $ O365_connect authorize
    > ... INFO in O365: Authorizing account ...
    > Visit the following url to give consent:
    > https://.../oauth2/v2.0/authorize?response_type=code&...
    > Paste the authenticated url here:
    > ...

In this flow, the *O365* user must provide proper consent for this service to
perform certain actions (see scopes) on behalf of the user, as per defined in *OAuth2*
authorization flow. For instance, the service requires access to the *O365* user's
inbox to read its content, and therefore user must consent those permissions.

The best way to go about it is simply to open the link in a browser and accept the
requested consents. The *O365* will redirect to a link containing the *authorization
code*. Simply paste that response link back to the terminal, and the service handles
the rest.

Run 🚀
======
To start listening for incoming events, it would go like this:

.. code-block:: bash

    $ O365_connect handle-incoming-events
    > ... INFO in O365: Account already authorized.
    > ... INFO in O365_mailbox: Start streaming connection for 'users/me@example.com'...
    > ... INFO in base: Open new events channel ...
    > ...

A new streaming connection is then initiated between our service and the *O365*
notification service. From this moment on, as soon as a new email reaches the inbox
folder, a *Jira* API request is performed, and a new issue is created.

A thorough explanation on how the notification streaming mechanism works, can be
found `here <https://github.com/rena2damas/O365-notifications>`__.

CLI Commands
============
The list of available supported operations is given by running the command:

.. code-block:: bash

    $ O365_connect
    ...
    > authorize                  Grant service authorization to O365 resources.
    > check-for-missing-events   Check for possible events that went missing ...
    > handle-incoming-events     Handle incoming events.

Each command contains its own instructions and properties. Enable ``--help`` flag to get
for more information on a command. Take the example below:

.. code-block:: bash

    $ O365_connect check-for-missing-events --help
    > Usage: O365_connect O365 check-for-missing-events [OPTIONS]
    >
    >   Check for possible events that went missing in the last days.
    >
    > Options:
    >   -d, --days TEXT  number of days to search back
    >   --help           Show this message and exit.

Tests & linting 🚥
==================
Run tests with ``tox``:

.. code-block:: bash

    # ensure tox is installed
    $ tox

Run linter only:

.. code-block:: bash

    $ tox -e lint

Optionally, run coverage as well with:

.. code-block:: bash

    $ tox -e coverage

License
=======
MIT licensed. See `LICENSE <LICENSE>`__.
