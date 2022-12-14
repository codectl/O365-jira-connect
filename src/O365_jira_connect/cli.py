import logging
import sys

import click
import O365
from O365_notifications.streaming import O365StreamingSubscriber
from O365_notifications.constants import O365EventType

from O365_jira_connect.backend import DatabaseTokenBackend
from O365_jira_connect.filters import (
    BlacklistFilter,
    JiraCommentNotificationFilter,
    RecipientControlFilter,
    ValidateMetadataFilter,
    WhitelistFilter,
)
from O365_jira_connect.handlers import JiraNotificationHandler
from O365_jira_connect.session import init_engine

# configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.option("--debug/--no-debug", default=False, help="Enable debug")
@click.option(
    "--database",
    "-d",
    required=True,
    type=str,
    envvar="SQLALCHEMY_DATABASE_URI",
    show_envvar=True,
    help="the database URI used to store information on issues",
)
@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli(debug, database):
    if debug:
        click.echo("Debug mode is enabled")
        logger.setLevel(logging.DEBUG)
    init_engine(engine_url=database, debug=debug)


def o365_options(f):
    f = click.option(
        "--retries",
        required=False,
        type=int,
        default=0,
        help="number of retries when request fails",
    )(f)
    f = click.option(
        "--scopes",
        required=False,
        type=str,
        multiple=True,
        default=[],
        envvar="O365_SCOPES",
        show_envvar=True,
        help="the O365 scopes",
    )(f)
    f = click.option(
        "--client-secret",
        required=False,
        type=str,
        default=None,
        envvar="O365_CLIENT_SECRET",
        show_envvar=True,
        help="the O365 client secret",
    )(f)
    f = click.option(
        "--client-id",
        required=True,
        type=str,
        envvar="O365_CLIENT_ID",
        show_envvar=True,
        help="the O365 application/client id",
    )(f)
    f = click.option(
        "--grant-type",
        required=True,
        type=click.Choice(["credentials", "authorization"]),
        default="credentials",
        show_default=True,
        help="the OAuth2 grant type",
    )(f)
    f = click.option(
        "--principal",
        required=True,
        type=str,
        help="the resource principal",
        envvar="O365_PRINCIPAL",
        show_envvar=True,
    )(f)
    f = click.option(
        "--tenant-id",
        required=True,
        type=str,
        help="the O365 tenant",
        envvar="O365_TENANT_ID",
        show_envvar=True,
    )(f)
    f = click.option(
        "--api-version",
        required=False,
        type=str,
        help="the O365 API version",
    )(f)
    f = click.option(
        "--protocol",
        required=True,
        type=click.Choice(["graph", "office"]),
        default="graph",
        show_default=True,
        help="the O365 protocol",
    )(f)
    return f


def jira_options(f):
    f = click.option(
        "--project",
        required=True,
        type=str,
        envvar="JIRA_PROJECT_KEY",
        show_envvar=True,
        help="the project key to add the issue to",
    )(f)
    f = click.option(
        "--issue-type",
        required=True,
        type=str,
        default="Task",
        envvar="JIRA_ISSUE_TYPE",
        show_envvar=True,
        help="the type of issue to create",
    )(f)
    f = click.option(
        "--default-labels",
        required=True,
        type=str,
        multiple=True,
        default=["support"],
        envvar="JIRA_DEFAULT_LABELS",
        show_envvar=True,
        help="the default labels assigned to issue",
    )(f)
    return f


@cli.command()
@o365_options
def authorize(**params):
    """Grant service authorization to O365 resources."""
    return authorize_account(**params)


@cli.group()
@o365_options
def messages(**_):
    """Operations involving O365 messages."""
    pass


@click.option(
    "--keep-alive-interval",
    required=True,
    type=int,
    default=300,
    envvar="KEEP_ALIVE_INTERVAL_IN_SECONDS",
    show_envvar=True,
    help="the interval of seconds a keep-alive message is sent",
)
@click.option(
    "--connection-timeout",
    required=True,
    type=int,
    default=120,
    envvar="CONNECTION_TIMEOUT_IN_MINUTES",
    show_envvar=True,
    help="the O365 connection timeout in minutes",
)
@click.option(
    "--blacklist",
    required=True,
    type=str,
    multiple=True,
    default=[],
    envvar="BLACKLIST",
    show_envvar=True,
    help="the blacklist filter",
)
@click.option(
    "--whitelist",
    required=True,
    type=str,
    multiple=True,
    default=[],
    envvar="WHITELIST",
    show_envvar=True,
    help="the whitelist filter",
)
@jira_options
@messages.command()
@click.pass_context
def streaming(ctx, connection_timeout, keep_alive_interval, **params):
    """Start streaming connection for handling incoming O365 events."""
    parent_params = ctx.parent.params
    if parent_params["grant_type"] == "credentials":
        click.echo(
            "Streaming is incompatible with grant type 'credentials'",
            err=True,
            color=True,
        )
        sys.exit(0)

    subscriber = create_subscriber(**parent_params)
    handler = create_handler(subscriber, **params)

    # start listening for streaming events ...
    subscriber.start_streaming(
        notification_handler=handler,
        connection_timeout=connection_timeout,
        keep_alive_interval=keep_alive_interval,
        refresh_after_expire=True,
    )


def authorize_account(
    protocol,
    api_version,
    principal,
    tenant_id,
    client_id,
    client_secret,
    grant_type,
    scopes,
    retries,
):
    kwargs = {"api_version": api_version} if api_version else {}
    if protocol == "graph":
        protocol = O365.MSGraphProtocol(**kwargs)
    elif protocol == "office":
        protocol = O365.MSOffice365Protocol(**kwargs)

    # ignore scopes on 'credentials' flow
    if scopes and grant_type == "credentials":
        scopes = None

    account = O365.Account(
        credentials=(client_id, client_secret),
        protocol=protocol,
        tenant_id=tenant_id,
        main_resource=principal,
        auth_flow_type=grant_type,
        scopes=scopes,
        request_retries=retries,
        token_backend=DatabaseTokenBackend(),
    )

    if account.is_authenticated:
        logger.info("Account already authorized.")
    else:
        logger.info("Authorizing account ...")
        account.authenticate(tenant_id=tenant_id)
    return account


def create_subscriber(principal: str = None, **kwargs):
    account = authorize_account(principal=principal, **kwargs)
    mailbox = account.mailbox()

    # create a new streaming subscriber
    subscriber = O365StreamingSubscriber(parent=account)

    # subscribe to inbox and sent items folder events
    events = [O365EventType.CREATED]
    subscriber.subscribe(resource=mailbox.inbox_folder(), events=events)
    subscriber.subscribe(resource=mailbox.sent_folder(), events=events)
    return subscriber


def create_handler(subscriber, **configs):
    resources = [sub.resource for sub in subscriber.subscriptions]
    main_resource = subscriber.main_resource
    filters = [
        BlacklistFilter(blacklist=configs.pop("blacklist")),
        JiraCommentNotificationFilter(folder=resources[0]),
        RecipientControlFilter(email=main_resource, ignore=[resources[1]]),
        ValidateMetadataFilter(),
        WhitelistFilter(whitelist=configs.pop("whitelist")),
    ]

    return JiraNotificationHandler(
        parent=subscriber,
        namespace=subscriber.namespace,
        filters=filters,
        issue_type=configs["issue_type"],
        default_labels=configs["default_labels"],
    )
