#!/usr/bin/env python3

import sys
import os
import pathlib

import json
import yaml
import click

from configparser import ConfigParser
from datetime import datetime, timezone
from pathlib import Path
from pyfzf.pyfzf import FzfPrompt

import boto3

fzf = FzfPrompt()

HOME_PATH = os.getenv("HOME")
CUR_PATH = pathlib.Path(__file__).parent.absolute()

ACCOUNT_LIST_PATH = HOME_PATH + "/.aws/accounts"
ACCOUNT_LIST_FILE = ACCOUNT_LIST_PATH + "/list.json"
SSO_LIST_FILE = ACCOUNT_LIST_PATH + "/sso-list.json"
SSO_URL_LIST_FILE = ACCOUNT_LIST_PATH + "/sso-urls.json"

AWS_SSO_CACHE_PATH = f"{Path.home()}/.aws/sso/cache"
AWS_CONFIG_PATH = f"{Path.home()}/.aws/config"
AWS_CREDENTIAL_PATH = f"{Path.home()}/.aws/credentials"
AWS_DEFAULT_REGION = "ap-northeast-2"

CONFIG_FILE = HOME_PATH + "/.aws/config"
CREDENTIALS_FILE = HOME_PATH + "/.aws/credentials"


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def read_config(path):
    config = ConfigParser()
    config.read(path)
    return config


def write_config(path, config):
    with open(path, "w") as destination:
        config.write(destination)


def read_file(file, view=False):
    with open(file, 'r') as fileData:
        try:
            if view:
                print(fileData.read())
            return yaml.safe_load(fileData)
        except yaml.YAMLError as e:
            print(e)

def load_json(path):
    try:
        with open(path) as context:
            return json.load(context)
    except ValueError:
        pass  # ignore invalid json

def parse_timestamp(value):
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SUTC")


def init_profile_config(sso_data):
    # sso_client = boto3.client('sso')
    # """ :type: pyboto3.sso """

    with open(CONFIG_FILE, 'w') as f:
        try:

            f.write('[default]\n')
            f.write(f'region = ap-northeast-2\n')
            f.write(f'output = json\n\n')

            for sso in sso_data:
                for sso_acnt in sso_data[sso]["SSO_ACCOUNT"]:
                    f.write(f'[profile {sso}-{sso_acnt["PROFILE"]}]\n')
                    f.write(f'region = {sso_acnt["REGION"]}\n')
                    f.write(f'output = {sso_acnt["OUTPUT"]}\n')
                    f.write(f'sso_start_url = {sso_data[sso]["SSO_URL"]}\n')
                    f.write(f'sso_region = {sso_data[sso]["SSO_REGION"]}\n')
                    f.write(f'sso_account_id = {sso_acnt["ID"]}\n')
                    f.write(f'sso_role_name = {sso_acnt["ROLE"]}\n')

                    f.write('\n')
                    pass

                print(
                    f'{bcolors.OKGREEN}aws sso login --profile {sso}-{sso_data[sso]["SSO_ACCOUNT"][0]["PROFILE"]}{bcolors.ENDC}')

                pass



        except yaml.YAMLError as e:
            print(e)

    pass

def update_aws_credentials(profile_name, profile, credentials):
    region = profile.get("region", AWS_DEFAULT_REGION)
    config = read_config(AWS_CREDENTIAL_PATH)
    if config.has_section(profile_name):
        config.remove_section(profile_name)
    config.add_section(profile_name)
    config.set(profile_name, "region", region)
    config.set(profile_name, "aws_access_key_id", credentials["accessKeyId"])
    config.set(profile_name, "aws_secret_access_key", credentials["secretAccessKey"])
    config.set(profile_name, "aws_session_token", credentials["sessionToken"])
    write_config(AWS_CREDENTIAL_PATH, config)




def get_profiles(sso_data):
    list_profile = []
    for sso in sso_data:
        for sso_acnt in sso_data[sso]["SSO_ACCOUNT"]:
            list_profile.append(f'{sso}-{sso_acnt["PROFILE"]}')

    return list_profile


def list_directory(path):
    file_paths = []
    if os.path.exists(path):
        file_paths = Path(path).iterdir()
    file_paths = sorted(file_paths, key=os.path.getmtime)
    file_paths.reverse()  # sort by recently updated
    return [str(f) for f in file_paths]

def get_sso_cached_login(profile):
    file_paths = list_directory(AWS_SSO_CACHE_PATH)
    time_now = datetime.utcnow()
    for file_path in file_paths:
        data = load_json(file_path)
        if data is None:
            continue
        if data.get("startUrl") != profile["sso_start_url"]:
            continue
        if data.get("region") != profile["sso_region"]:
            continue
        if time_now > parse_timestamp(data.get("expiresAt", "1970-01-01T00:00:00UTC")):
            continue
        return data
    raise Exception(f'Current cached SSO login is expired or invalid - {profile["sso_start_url"]}')


def get_sso_role_credentials(profile, login):
    client = boto3.client("sso", region_name=profile["sso_region"])
    response = client.get_role_credentials(
        roleName=profile["sso_role_name"],
        accountId=profile["sso_account_id"],
        accessToken=login["accessToken"],
    )
    return response["roleCredentials"]

def get_sso_account_list(sso_region, login):
    sso = boto3.client("sso", region_name=sso_region)
    """ :type: pyboto3.sso """

    list_accounts = sso.list_accounts(
        accessToken=login["accessToken"],
    )
    return list_accounts["accountList"]

def get_sso_role_list(sso_region, login, acnt_id):
    sso = boto3.client("sso", region_name=sso_region)
    """ :type: pyboto3.sso """

    list_role = sso.list_account_roles(
        accountId=acnt_id,
        accessToken=login["accessToken"],
    )
    return list_role["roleList"]


def get_aws_profile(profile_name):
    config = read_config(AWS_CONFIG_PATH)
    profile_opts = config.items(f"profile {profile_name}")
    profile = dict(profile_opts)
    return profile


def set_profile_credentials(profile_name):
    profile = get_aws_profile(profile_name)
    cache_login = get_sso_cached_login(profile)
    credentials = get_sso_role_credentials(profile, cache_login)
    update_aws_credentials(profile_name, profile, credentials)
    update_aws_credentials("default", profile, credentials)


@click.command()
@click.option('-i', '--init', is_flag=True, help='init login list print')
@click.option('-s', '--set', is_flag=True, help='init setting')
@click.option('-c', '--credentials', default="", help='write credentials file')
@click.option('-l', '--list', is_flag=True, help='profile list')
@click.option('-g', '--get-current', is_flag=True, help='current login profile')
def main(init, set, credentials, list, get_current):
    if init:
        sso_data = read_file(SSO_URL_LIST_FILE)
        init_profile_config(sso_data)
        return
    elif set:
        login_all()
        return
    elif list:
        sso_data = read_file(SSO_URL_LIST_FILE)
        pf_list = get_profiles(sso_data)
        print(f'{pf_list}')
        return
    elif get_current:
        print(f'PROFILE = {os.getenv("PROFILE")}')
        read_file(CREDENTIALS_FILE, True)
        return

    if credentials is not None:
        set_profile_credentials(credentials)
        return

    help()
    pass

def login_all():
    sso_data = read_file(SSO_URL_LIST_FILE)

    for sso in sso_data:
        sso_profile = {}
        sso_profile["sso_start_url"] = sso_data[sso]["SSO_URL"]
        sso_profile["sso_region"] = sso_data[sso]["SSO_REGION"]
        cache_login = get_sso_cached_login(sso_profile)
        list_account = get_sso_account_list(sso_data[sso]["SSO_REGION"], cache_login)

        print(f'{sso}')
        for acnt in list_account:
            print(f'{acnt}')
            list_role = get_sso_role_list(sso_data[sso]["SSO_REGION"], cache_login, acnt["accountId"])

            for role in list_role:
                print(f'{role}')
                print(f'{sso_profile}')
                sso_profile["sso_role_name"] = role["roleName"]
                sso_profile["sso_account_id"] = role["accountId"]

                credential = get_sso_role_credentials(sso_profile, cache_login)

                profile_name = f'{sso}-{acnt["accountName"]}-{role["roleName"]}'
                update_aws_credentials(profile_name, sso_profile, credential)

def update_default_credential():
    config = read_config(AWS_CREDENTIAL_PATH)
    confs = list(config.keys())
    confs.remove('DEFAULT')

    opt = f'--reverse --cycle --header "Select credential"'

    select = fzf.prompt(confs, fzf_options=opt)[0]

    print(f'{select}')

    profile_opts = config.items(f"{select}")
    profile = dict(profile_opts)

    print(f'{profile}')

    profile_name = "default"
    region = profile.get("region", AWS_DEFAULT_REGION)
    config = read_config(AWS_CREDENTIAL_PATH)
    if config.has_section(profile_name):
        config.remove_section(profile_name)
    config.add_section(profile_name)
    config.set(profile_name, "region", region)
    config.set(profile_name, "aws_access_key_id", profile["aws_access_key_id"])
    config.set(profile_name, "aws_secret_access_key", profile["aws_secret_access_key"])
    config.set(profile_name, "aws_session_token", profile["aws_session_token"])
    write_config(AWS_CREDENTIAL_PATH, config)


if __name__ == '__main__':
    if sys.argv.__len__() < 2:
        update_default_credential()
        # sys.exit(login_all())
    else:
        sys.exit(main())