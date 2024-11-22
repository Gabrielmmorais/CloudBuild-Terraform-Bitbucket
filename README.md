# CI/CD Pipeline Integration with Bitbucket and Google Cloud Build Using Terraform and Secured Access to a Single Repository

![Architecture Diagram](./Untitled%20Diagram.drawio(1).svg)

## Project Overview

This repository demonstrates the creation and integration of a CI/CD pipeline between Bitbucket and Google Cloud Build, using **Terraform** for provisioning. A key feature of this implementation is the **secured access** configuration, where the connection only allows access to a specific repository, enhancing the security of the integration.

## Table of Contents
- [Architecture](#architecture)
- [Steps to Implement](#steps-to-implement)
- [Pipeline Stages](#pipeline-stages)
- [Securing Access](#securing-access)
- [Testing](#testing)
- [Follow Me](#follow-me)

## Architecture

The architecture for this CI/CD pipeline is shown in the diagram above. It outlines the main components of the system and how they interact within the pipeline.

## Steps to Implement

1. **Create Host Connection**:  
   Start by establishing a connection with the host in Google Cloud Build. This connection will be linked to the Bitbucket repository.  
   The access token generated is scoped to allow access **only to the specific repository** rather than the entire workspace, ensuring better control and security.

2. **Link Repository**:  
   After creating the host connection, link it to the repository using the access token that was generated from the repository itself.

3. **Configure Pipeline**:  
   The pipeline configuration is handled via a YAML file. This file leverages **Terraform** to provision all the necessary resources automatically.

4. **Run the Pipeline**:  
   Once the setup is complete, commit and push your changes. This will trigger the pipeline, handling the building, deploying, and testing of the application in the cloud environment.

## Pipeline Stages

The pipeline consists of five key stages:

1. **Authenticate Docker with GCP**: Ensures Docker is authenticated with Google Cloud.
2. **Build Stage**: Builds the application and creates a Docker image.
3. **Provision Artifact Registry**: Using Terraform, the Artifact Registry is provisioned to store the Docker image.
4. **Push Docker Image**: The Docker image is pushed to the Artifact Registry.
5. **Deploy Services**: The final stage calls Terraform to link all services and complete the deployment.

## Securing Access

A crucial part of this project is securing access between Bitbucket and Google Cloud Build. Instead of allowing the connection to access the entire workspace, we restrict access to only the **specific repository** needed for this pipeline.  

This security configuration is achieved by generating an access token scoped to the repository, ensuring that other repositories remain isolated and inaccessible from this connection. This adds a layer of protection to your CI/CD pipeline.

## Testing

After the pipeline runs successfully, verify the deployment by checking if the service is up and running. For this project, NGINX serves as the web server, displaying the message "Pipeline Works."

To test the pipeline's ability to handle changes, modify the text on the web server, push the change, and verify if the updated text is reflected in the deployed service.

## Follow Me

Feel free to connect with me on [LinkedIn](https://www.linkedin.com/in/gabriel-morais-b1a37022a/) for more details on my work and future projects!
