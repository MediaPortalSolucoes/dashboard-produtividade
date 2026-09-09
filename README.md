# Dashboard de Produtividade

Sistema de monitoramento e análise de produtividade integrado ao **Basecamp 3** e **Google Sheets**, com interface visual interativa desenvolvida em **Streamlit**.

---

## Visão Geral

O Dashboard de Produtividade consolida automaticamente as tarefas, entregas e histórico de performance dos desenvolvedores e equipes a partir do Basecamp 3. 

A arquitetura utiliza o **Google Sheets** como banco de dados intermediário, onde rotinas de ETL sincronizam as informações periodicamente via **Google Cloud API** (`gspread`), permitindo que a aplicação leia os dados atualizados sem sobrecarregar a API do Basecamp.

---

## 🔄 Fluxo de Atualização dos Dados

1. **Sincronização Programada**: A planilha é atualizada automaticamente **todos os dias nos seguintes horários**:
   * **12:30**
   * **16:30**
   * **00:00**
2. **Atualização do Dashboard**:
   * O Streamlit mantém os dados em cache de memória (`@st.cache_data`) para otimizar a navegação.
   * **Toda vez que o Dashboard é reiniciado** (ou o cache é limpo pelo atalho `C`), a aplicação executa uma nova leitura completa na planilha do Google Sheets, refletindo as alterações mais recentes.

---

## 🔑 Configuração de Credenciais e Arquivos

### 1. `google_credentials.json` (Raiz do Projeto)
Arquivo de credenciais da **Conta de Serviço** do Google Cloud Platform (GCP).
* **Localização obrigatória**: Na pasta **raiz** do repositório (`/google_credentials.json`).
* **Permissão necessária**: O e-mail da conta de serviço presente neste JSON deve estar adicionado como **Editor** no Google Sheets utilizado.

---

### 2. `.env` 
Arquivo contendo dados de autenticação do OAuth2 do Basecamp e identificadores do Google Sheets.

```env
BASECAMP_CLIENT_ID="seu_client_id"
BASECAMP_CLIENT_SECRET="seu_client_secret"
BASECAMP_REFRESH_TOKEN="seu_refresh_token"
BASECAMP_REDIRECT_URI="http://localhost:8000/callback"

SPREADSHEET_NAME="Nome da Planilha no Google Drive"
SPREADSHEET_ID="1juyOfIh..."
```

-----


## Docker

O ambiente em produção utiliza **Docker Compose** para orquestrar a imagem hospedada no Docker Hub e injetar as credenciais locais.

### 1. Preparar o Ambiente

Crie a estrutura na máquina (ex: `/opt/dashboard/`) colocando os arquivos criados na etapa anterior e crie o arquivo `docker-compose.yml`:

```yaml
version: '3.8'

services:
  dashboard:
    image: marcusfrancisco/dashboard-produtividade:latest
    container_name: app-dashboard-produtividade
    restart: always
    ports:
      - "8501:8501"
    env_file:
      - .env
    volumes:
      - ./google_credentials.json:/app/google_credentials.json:ro
      - ./google_sheet/config.ini:/app/google_sheet/config.ini:ro
      - ./logs:/app/logs
```

### 2. Iniciar a Aplicação

Dentro da pasta onde está o `docker-compose.yml`, rode o comando para baixar a imagem e subir o serviço em background:

```bash
docker compose up -d
```

### 3. Alterações no código

Quando houver alguma alteração no código, é necessário criar uma nova imagem Docker e enviá-la para o Docker Hub.

Dentro da pasta do projeto, execute:

```bash
docker build -t marcusfrancisco/dashboard-produtividade:latest .
```

Depois, envie a nova imagem para o Docker Hub:

```bash
docker push marcusfrancisco/dashboard-produtividade:latest
```

Após o push, no servidor aonde está o dashboard, atualize a imagem e recrie o container:

```bash
docker compose pull && docker compose up -d
```

### 4. Comandos Úteis

Para acompanhar os **logs**:

```bash
docker compose logs -f
```

Para **parar** o serviço:

```bash
docker compose down
```

Para **atualizar** quando houver nova versão:

```bash
docker compose pull && docker compose up -d
```

-----
