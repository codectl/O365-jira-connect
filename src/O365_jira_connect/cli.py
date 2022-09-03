import logging

import click
import dotenv
from O365 import (
    Account,
    MSGraphProtocol,
    MSOffice365Protocol,
)

from O365_jira_connect.components import init_engine
from O365_jira_connect.components.token import DatabaseTokenBackend

logger = logging.getLogger(__name__)

# load environment if exists
dotenv.load_dotenv(".env")


@click.option(
    "--database",
    "-d",
    required=True,
    type=str,
    envvar="SQLALCHEMY_DATABASE_URI",
    show_envvar=True,
    help="the database URI used to store information on issues",
)
@click.option("--debug/--no-debug", default=False, help="Enable debug")
@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli(debug, database):
    init_engine(engine_url=database, debug=debug)
    if debug:
        click.echo(f"Debug mode is enabled")


@cli.command()
@click.option(
    "--protocol",
    required=False,
    type=click.Choice(["graph", "office"]),
    default="graph",
    show_default=True,
    help="the O365 protocol",
)
@click.option(
    "--api-version",
    required=False,
    type=str,
    help="the O365 API version",
)
@click.option(
    "--principal",
    required=True,
    type=str,
    help="the resource principal",
    envvar="O365_PRINCIPAL",
    show_envvar=True,
)
@click.option(
    "--tenant-id",
    required=True,
    type=str,
    help="the O365 tenant",
    envvar="O365_TENANT_ID",
    show_envvar=True,
)
@click.option(
    "--client-id",
    required=True,
    type=str,
    envvar="O365_CLIENT_ID",
    show_envvar=True,
    help="the O365 application/client id",
)
@click.option(
    "--client-secret",
    required=False,
    type=str,
    default=None,
    envvar="O365_CLIENT_SECRET",
    show_envvar=True,
    help="the O365 client secret",
)
@click.option(
    "--grant-type",
    required=False,
    type=click.Choice(["credentials", "authorization"]),
    default="credentials",
    show_default=True,
    help="the OAuth2 grant type",
)
@click.option(
    "--scopes",
    required=False,
    type=str,
    multiple=True,
    default=[],
    envvar="O365_SCOPES",
    show_envvar=True,
    help="the O365 scopes",
)
@click.option(
    "--retries",
    required=False,
    type=int,
    default=0,
    help="number of retries when request fails",
)
def authorize(
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
    """Grant service authorization to O365 resources."""
    return authorize_account(
        protocol=protocol,
        api_version=api_version,
        principal=principal,
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
        grant_type=grant_type,
        scopes=scopes,
        retries=retries,
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
        protocol = MSGraphProtocol(**kwargs)
    elif protocol == "office":
        protocol = MSOffice365Protocol(**kwargs)
    else:
        raise ValueError

    # ignore scopes on 'credentials' flow
    if scopes and grant_type == "credentials":
        scopes = None

    account = Account(
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
        logger.info("Authorization done.")
    return account
