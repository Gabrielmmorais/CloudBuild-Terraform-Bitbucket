import base64
import json
import requests
import functions_framework

# Constants
TELEGRAM_BOT_TOKEN = ''
TELEGRAM_CHAT_ID = ''
BITBUCKET_USERNAME = '' 
BITBUCKET_APP_PASSWORD = '' 
BITBUCKET_REPO_OWNER = ''  
BITBUCKET_REPO_SLUG = ''  
BITBUCKET_BRANCH = ''  

# Put all trigger names, notifications from which you want to receive notifications
TARGET_TRIGGER_NAMES = ['']

@functions_framework.cloud_event
def cloud_build_pubsub(cloud_event):
    # Decode the Pub/Sub message
    pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode('utf-8')
    pubsub_data = json.loads(pubsub_message)

    # Extract the status field
    status = pubsub_data.get("status")
    trigger_name = pubsub_data.get("substitutions", {}).get("TRIGGER_NAME")
    commit_sha = pubsub_data.get("substitutions", {}).get("COMMIT_SHA")

    # Buscar a mensagem do commit no Bitbucket
    commit_message = get_commit_message(commit_sha)

    # Check if this trigger is in your list
    if trigger_name in TARGET_TRIGGER_NAMES:
        if status == "WORKING":
            # Send initial message to Telegram indicating the pipeline is running
            message = f"Build status: Executando \nPipeline: {trigger_name} \nCommit: {commit_message} \n\nCommit SHA: {commit_sha}"
            send_telegram_message(message)
        elif status in ["SUCCESS", "FAILURE"]:
            # Prepare message for Telegram with final status
            message = f"Build status: {status} \nPipeline-trigger: {trigger_name}\nCommit: {commit_message} \n\nCommit SHA: {commit_sha}"
            send_telegram_message(message)

def get_commit_message(commit_sha):
    # URL para buscar a mensagem do commit na branch especificada
    url = f'https://api.bitbucket.org/2.0/repositories/{BITBUCKET_REPO_OWNER}/{BITBUCKET_REPO_SLUG}/commit/{commit_sha}'
    
    # Faz a requisição à API do Bitbucket para obter a mensagem do commit
    response = requests.get(url, auth=(BITBUCKET_USERNAME, BITBUCKET_APP_PASSWORD))
    
    # Verifica se a requisição foi bem-sucedida
    if response.status_code == 200:
        commit_data = response.json()
        return commit_data.get("message", "Mensagem do commit não disponível")
    else:
        print(f'Erro ao obter mensagem do commit: {response.status_code} {response.text}')
        return "Mensagem do commit não disponível"

def send_telegram_message(message):
    # Telegram Bot API endpoint para envio de mensagens
    telegram_api_url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'

    # Parâmetros para a requisição API
    params = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
    }

    # Envia a mensagem para o Telegram
    response = requests.post(telegram_api_url, params=params)

    # Tratamento de erro
    if response.status_code != 200:
        print(f'Erro ao enviar mensagem para o Telegram: {response.status_code} {response.text}')
