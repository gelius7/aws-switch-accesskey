# aws-switch-accesskey
Script for managing multiple aws account

~~awscli 는 AWS_PROFILE 환경변수를 통해 multi accesskey 를 관리할수 있도록 지원하고 있지만,~~

fzf 기능을 활용하여 switch 하기 위해 따로 제작한 스크립트 입니다.

## Usage

clone 해서 받은 a 는 bash script 입니다.

* a 파일을 적절한 위치에 옮겨놓고 바로 사용할 수 있도록 설정합니다.

```bash
chmod +x a
mv a ~/.aws
vi ~/.zshrc
```

```bash
alias a="~/.aws/a"
```

```bash
source ~/.zshrc
```

> /usr/local/bin 위치에 a 를 배치하는것도 하나의 방법입니다.

* 사용할 account 를 설정합니다.

```bash
mkdir -p ${HOME}/.aws/accouts
vi ${HOME}/.aws/accouts/your-account1
```

```json
{
  "REGION": "ap-northeast-2",
  "OUTPUT": "json",
  "ACCESS_KEY": "AKIA*****",
  "SECRET_KEY": "f++++++++++++++++++++++++++"
}
```

* 사용해봅시다.

```bash
$ a
  5/5
  Select AWS account
> your-account1
  jj1
  jj2
  jj3

```

