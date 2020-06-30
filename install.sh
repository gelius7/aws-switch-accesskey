#!/bin/bash

command -v tput > /dev/null && TPUT=true

AWS_DIR=${HOME}/.aws
mkdir -p $AWS_DIR

_echo() {
    if [ "${TPUT}" != "" ] && [ "$2" != "" ]; then
        echo -e "$(tput setaf $2)$1$(tput sgr0)"
    else
        echo -e "$1"
    fi
}

_result() {
    _echo "# $@" 4
}

_command() {
    _echo "$ $@" 3
}

_success() {
    _echo "+ $@" 2
    exit 0
}

_error() {
    _echo "- $@" 1
    exit 1
}

################################################################################

USERNAME="11stcorp"
REPONAME="aws-switch-accesskey"

NAME="aao"

if [ -z ${VERSION} ]; then
    VERSION=$(curl -s https://api.github.com/repos/${USERNAME}/${REPONAME}/releases/latest | grep tag_name | cut -d'"' -f4)
    _result "github Version : ${VERSION}"

    if [ -z ${VERSION} ]; then
        VERSION="v1.0.0"
        _result "Default version: ${VERSION}"
    fi
fi


if [ -z ${VERSION} ]; then
    _error
fi

_result "Install start..."
sleep 1

pushd /tmp > /dev/null
curl -sL https://github.com/${USERNAME}/${REPONAME}/releases/download/${VERSION}/aao -o aao
chmod +x aao
mv aao ${AWS_DIR}
popd > /dev/null

## mac os
_command "echo \"alias aao=~/.aws/aao\" >> ${HOME}/.zshrc"

