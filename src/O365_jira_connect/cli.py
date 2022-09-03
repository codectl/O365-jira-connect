import logging

import click
from O365 import (
    Account,
    MSGraphProtocol,
    MSOffice365Protocol,
)

from O365_jira_connect.components.token import DatabaseTokenBackend

logger = logging.getLogger(__name__)


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
    if protocol == "graph":
        protocol = MSGraphProtocol(api_version=api_version)
    if protocol == "office":
        protocol = MSOffice365Protocol(api_version=api_version)
    else:
        raise ValueError

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


@click.group(name="O365_connect")
def cli():
    pass


@click.command()
@click.option(
    "--protocol",
    required=False,
    type=click.Choice(["graph", "office"]),
    default="graph",
    show_default=True,
)
@click.option(
    "--api-version",
    required=False,
    type=str,
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
@click.option("--debug/--no-debug", default=False)
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
    debug,
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
