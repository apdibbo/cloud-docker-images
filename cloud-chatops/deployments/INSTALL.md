# Deploying Cloud ChatOps
This document covers the following: creating a Slack Workspace and app, finding / generating Slack and GitHub tokens and deploying the app onto a host. 

> **_NOTE:_** The installation has only been tested on Ubuntu (20.04) Linux Distributions and may need to be modified to work on others such as Rocky Linux.

## Contents:
[Quick Start](#single-node-installation)<br>
[Slack Configuration](#slack-configuration)<br>
[Slack Tokens](#slack-tokens)<br>
[Deployment Configuration](#deployment-configuration)<br>
[Deployment](#deployment)<br>

### Slack Configuration:

You need a Slack Workspace and Slack App.<br>

#### Workspace:
Creating the workspace is straightforward and can be done by following this documentation [here](https://slack.com/intl/en-gb/help/articles/206845317-Create-a-Slack-workspace). There is no additional setup needed.<br>

#### App:
1. Creating a Slack App can be done [here](https://api.slack.com/quickstart).<br>
2. You should copy the app manifest from [app_manifest.yml](app_manifest.yml) and paste into `Features / App Manifest`.<br>
3. This copies all necessary config however you want to change the display information and name.<br>


### Slack Tokens:

You need the Bot Token and Signing Secret when deploying the app.
When configuring your app at https://api.slack.com/apps/ you can find / generate these tokens.<br>

- Bot User Token:
  - You can find the Bot User token under `Settings / Install App / OAuth Tokens`.
  - No scoping is required, and you **can** retrieve this token at a later date from the same location.
  
- Singing Secret:
  - You can find the Singing Secret under `Settings / Basic Information / Client Secret`

- App token (only needed for development):
  - You can generate the App token under `Settings / Basic Information / App-Level Tokens`.
  - You need to give it the scope `connections:write`.
  - The name doesn't matter, and you **can** retrieve this token at a later date from the same location.

### Deployment Configuration:

Two bespoke files required for the deployment of this app: `config.yml` and `secrets.yml`.<br>
Three other files with minor or no changes are also needed: `server.crt`, `haproxy.cfg` and `app_mainfest.yml`.<br>

#### Config:
The app configuration is stored in `config.yml`.
This includes information such as username mapping and repositories to check.<br>
Slack Channel and Member IDs can be found in Slack by:<br>
- Right-clicking the member / channel
- View member / channel details
- Near the bottom of the About tab there will be an ID with copy button

The `config.yml` should look like the below. There's a template without the comments [here](template_config.yml):
```yaml
---
users:
  # Information of users in your team
  - real_name: Real Name
    github_name: <name_on_github>
    slack_id: <slack_member_id>

repos:  # Dictionary of owners and repositories
  organisation1:
    - repo1  # E.g. github.com/organisation1/repo1
    - repo2
    - repo3
  organisation2:
    - repo1  # E.g. github.com/organisation2/repo1
    - repo2
    - repo3
  
# Channel to send global reminders to
channel: <pull-requests-channel-id>
```

The file `haproxy.cfg` can be copied into the correct directory without any changes.<br>

The file `server.crt` must be your SSL certificate for your domain and public IP address.
It must not be self-signed as Slack doesn't trust them.
You also need to ensure that the private key is prepared at the beginning of the file before the certificate.<br>
Such as the below:<br>
```
-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----
```

The file `app_manifest.yml` needs only one change.
In the `slash commands` section the URL needs to be changed to your publicly accessible domain.<br>

#### Secrets:
The `secrets.yml` file should look like the below and there's a template [here](template_secrets.yml)
```yaml
  SLACK_BOT_TOKEN: <your-token>
  SLACK_APP_TOKEN: <your-token> # Development use only
  SLACK_SIGNING_SECRET: <your-token>
  GITHUB_TOKEN: <your-token>
```
Slack:<br>
- Slack Token information can be found [here](#slack-tokens).<br>

GitHub:<br>
-  A GitHub Personal Access Token is needed to bypass rate limiting and allows access to private repositories.<br>
- Documentation on how to create a GitHub personal access token can be found 
[here](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).<br>

### Deployment Options:

The app can be run from a Docker image, source code or Kubernetes<br>


#### Dependencies:
* If running from a Docker image, ensure Docker is installed (see [installation guide](https://docs.docker.com/engine/install/)) and the user account is in the docker users group 
* If running the app from source, ensure Python 3.10 or higher is installed. The full list of required python packages can be found in [requirements.txt](../requirements.txt)<br>
* If running on Kubernetes, this documentation only describes how to apply a deployment. You will need a cluster already set up.

### Single Node Installation:

Below are instructions for deploying ChatOps on a single node / machine.
This uses docker compose to deploy the ChatOps container and a HAProxy container.<br>

#### Prerequisites:

- Set up Slack Workspace and app [here](#slack-configuration)
- Retrieved Slack bot user token and signing secret [here](#slack-tokens)
- Generated a GitHub personal access token [here](#secrets)
- Installed Docker and Docker Compose [here](https://docs.docker.com/engine/install/ubuntu/)
- DNS record, public IP address with port 443 open and SSL certificate (valid for HAProxy)

#### Installation:

1. Make a directory in `/etc` to store all ChatOps related files. Set group ownership to docker so other users (update script) can access the files.
    ```shell
    # Create directories
    sudo mkdir /etc/chatops
    sudo mkdir /etc/chatops/secrets
    sudo mkdir /etc/chatops/config
    
    # Set permissions
    sudo chown -R $USER:docker /etc/chatops
    sudo chmod 774 /etc/chatops
    sudo chmod 774 /etc/chatops/config
    sudo chmod 770 /etc/chatops/secrets
   
    # Clone repository into directory
    git clone https://github.com/stfc/cloud-docker-images.git /etc/chatops/cloud-docker-images
    ```
2. Edit the `template_config.yml` and `template_secrets.yml` to create your respective config and secrets file. See [here](#deployment-configuration) for more detail.
   ```shell
   # Copy files into secrets folder
   cp <path-to-config>/template_config.yml /etc/chatops/config/config.yml
   cp <path-to-config>/template_secrets.yml /etc/chatops/secrets/secrets.yml
   
   # If you edited the template_secrets.yml from the cloned repository in /etc/chatops/cloud-docker-images/cloud-chatops
   # You should delete / reset the file as the permissions are too open
   
   git reset --hard origin/master 
   # Or
   rm /etc/chatops/cloud-docker-images/cloud-chatops/template_secrets.yml
   ```
3. Copy HAProxy config and certificate to ChatOps directory
   ```shell
   # Copy HAProxy config file
   cp <path-to-repo>/deployments/haproxy.cfg /etc/chatops/config/haproxy.cfg
   
   # Copy certificate and rename it
   cp <path-to-certificate> /etc/chatops/config/server.crt
   ```
4. Need to add the Ubuntu user to the docker group for the cron script:
   ```shell
   sudo usermod -aG docker ubuntu
   ```
5. Move Cron script and start container:
   ```shell
   # Copy script to etc/cron.< hourly | daily | monthly >
   sudo cp /etc/chatops/cloud-docker-images/cloud-chatops/deployments/chatopscron /etc/cron.daily/

   # Check that crontab can see and run the script
   # If the chatops cron file is not in the command output then crontab will not run it
   run-parts --test /etc/cron.daily
   
   # Launch the container and verify set up is correct
   # Using sudo here to mimic crontab which runs as root user
   sudo /etc/cron.daily/chatopscron
   
   # Verify the container is running
   docker ps | grep -i cloud-chatops
   ```

> **_NOTE:_** Commands below assume you are in the cloud-chatops folder in the project.

#### Docker image:
 
> **_NOTE:_** You need to be running a proxy such as HAProxy to handle SSL connections. Slack will only send requests to HTTPS endpoints and the Docker image only accepts HTTP connection. See the docker compose file [here](/cloud-chatops/deployments/docker-compose.yaml) for ideas.
> 
You can build the image locally or pull from [STFC Harbor](https://harbor.stfc.ac.uk/harbor/projects/33528/repositories/cloud-chatops).<br>
Note: if you're pulling the image you need to specify a version tag. 
The latest version can be found in [version.txt](../version.txt)<br>
- ```shell
  # Local build and run
  docker build -t cloud_chatops cloud-chatops
  docker run cloud_chatops \
  -v <path_to>/secrets.yml/:/usr/src/app/cloud_chatops/secrets/secrets.yml \
  -v <path_to>/config.yml/:/usr/src/app/cloud_chatops/config/config.yml 
  ```
  
- ```shell
  # Pull the image and run, specifying a version
  docker run harbor.stfc.ac.uk/stfc-cloud/cloud-chatops:<version> \
  -v <path_to>/secrets.yml/:/usr/src/app/cloud_chatops/secrets/secrets.yml \
  -v <path_to>/config.yml/:/usr/src/app/cloud_chatops/config/config.yml
  ```

#### Kubernetes Deployment
You need a running cluster. Run the following commands from your management / control host (the host with your kubeconfig).

1. Clone the repository and create your config / secrets files
   ```shell
   # Start from the Home directory
   cd ~
   git clone https://github.com/stfc/cloud-docker-images.git
   
   # Edit and rename the template config and secrets file described in the "deployment configuration" section
   cd cloud-chatops
   
   vim template_config.yml
   vim template_secrets.yml
   
   mv template_config.yml config.yml
   mv template_secrets.yml secrets.yml
   ```
   
2. Create Kubernetes resources and apply deployment
   ```shell
   # Create Kubernetes resources
   kubectl create namespace cloud-chatops
   kubectl create configmap cloud-chatops-config --from-file config.yml -n cloud-chatops
   kubectl create secret generic cloud-chatops-secrets --from-file secrets.yml -n cloud-chatops
   
   # Apply the deployment
   kubectl apply -f deployment.yml -n cloud-chatops
     
   # Check the status of the pod with
   kubectl get pods -n cloud-chatops # To get pod name
   kubectl logs <pod_name> -n cloud-chatops
   ```

#### Developing new features:

When developing new features, it's easier to run the app locally to test new changes
To do this, we use Socket mode.
This means we don't have to expose any endpoints with untested changes and minimal security.
You need to have the following folder structure for the config and secrets to be accessible:

```markdown
Unix like systems:

$HOME/dev_cloud_chatops
├── config
│   ├── config.yml
├── secrets
│   ├── secrets.yml

or 

Windows:

$HOMEPATH/dev_cloud_chatops
├── config
│   ├── config.yml
├── secrets
│   ├── secrets.yml
```

You can run the code from [dev.py](../src/dev.py) which starts the Slack app.<br>
It's always recommended to create a [virtual environment](https://docs.python.org/3/library/venv.html) before installing dependencies.


```shell
# Install Venv module
python3 -m venv my_venv
# Activate venv
source my_venv/bin/activate
# Install requirements
pip3 install -r requirements.txt
# Run app
python3 src/dev.py
```
