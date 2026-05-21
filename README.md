# Hackton — Análise Automatizada de Diagramas de Arquitetura

MVP de uma plataforma que recebe diagramas de arquitetura (imagem ou PDF), aplica IA para análise automática e gera um relatório técnico estruturado com componentes identificados, riscos arquiteturais e recomendações.

Plataforma de microserviços para processamento e análise de arquivos, construída com .NET 9, RabbitMQ, PostgreSQL e MinIO.

## Arquitetura

```
                          ┌─────────────────────────────────────────────────┐
                          │                   RabbitMQ                       │
                          │  (JobCreatedEvent, AnalysisRequestedEvent,       │
                          │   AnalysisCompletedEvent, AnalysisFailedEvent,   │
                          │   GenerateReportCommand, ReportGeneratedEvent)   │
                          └──────────┬──────────────┬────────────────────────┘
                                     │              │
 Cliente ──▶ Gateway (YARP) ──┬──▶ Upload      Orchestrator ──▶ Analysis Service
             :5010             │   Service       Service         (Python + GPT-4o)
                               │   :5001         :5002                │
                               │    │              │            (Claude / OpenAI)
                               │    ▼              ▼
                               │  MinIO       PostgreSQL
                               │ (storage)  (orchestrator_db)
                               │
                               ├──▶ Report Service ──▶ PostgreSQL (report_db)
                               │   :5003
                               │
                               └──▶ PostgreSQL (upload_db)
```

### Fluxo completo

```
1. POST /api/upload           → Upload Service armazena no MinIO, publica JobCreatedEvent
2. JobCreatedEvent            → Orchestrator cria Job (status: Received), publica AnalysisRequestedEvent
3. AnalysisRequestedEvent     → Analysis Service baixa arquivo, envia ao LLM, publica AnalysisCompletedEvent
4. AnalysisCompletedEvent     → Orchestrator atualiza Job (status: Analyzed), publica GenerateReportCommand
5. GenerateReportCommand      → Report Service persiste relatório, publica ReportGeneratedEvent
6. GET /api/status/{jobId}    → Consulta status do job
7. GET /api/report/{jobId}    → Obtém relatório gerado
```

### Status do Job

| Status | Descrição |
|--------|-----------|
| `Received` | Upload recebido, aguardando análise |
| `Analyzed` | Análise concluída com sucesso |
| `Failed` | Erro durante o processamento |

---

## Serviços

| Serviço | Tecnologia | Porta | Descrição |
|---------|-----------|-------|-----------|
| **Gateway** | .NET 9 / YARP | 5010 | Proxy reverso, roteamento centralizado |
| **Upload Service** | .NET 9 | 5001 | Recebe arquivos, armazena no MinIO, publica eventos |
| **Orchestrator Service** | .NET 9 | 5002 | Orquestra o fluxo entre serviços |
| **Analysis Service** | Python 3.12 | — | Processa diagrama com IA (GPT-4o ou Claude) |
| **Report Service** | .NET 9 | 5003 | Persiste e disponibiliza relatórios |

### Infraestrutura

| Componente | Porta | Descrição |
|------------|-------|-----------|
| **PostgreSQL 16** | 5432 | 3 databases isolados por serviço |
| **RabbitMQ** | 5672 / 15672 | Message broker para eventos assíncronos |
| **MinIO** | 9000 / 9001 | Object storage compatível com S3 |
| **Seq** | 5341 / 8081 | Agregador de logs estruturados |

---

## Pipeline de IA

O **Analysis Service** (Python) implementa o seguinte pipeline:

```
AnalysisRequestedEvent
        │
        ▼
1. Download do arquivo (MinIO)
        │
        ▼
2. Pré-processamento
   PDF → converte páginas para PNG (PyMuPDF, máx. 3 páginas)
   IMG → usa direto (PNG/JPEG)
        │
        ▼
3. Chamada ao LLM com Vision (GPT-4o ou Claude)
   System prompt estruturado com schema JSON obrigatório
        │
        ▼
4. Guardrails de saída (Pydantic)
   Valida JSON, campos obrigatórios, tamanho das listas
   Retry automático até 3x em caso de resposta inválida
        │
        ▼
5. Publicação do resultado
   Sucesso → AnalysisCompletedEvent { components, risks, recommendations }
   Falha   → AnalysisFailedEvent { reason }
```

### Abordagem de IA

Utiliza **LLM com Vision** (GPT-4o ou Claude com suporte a imagens), com:

- **Prompt engineering**: system prompt com schema JSON obrigatório e guardrail para entradas inválidas
- **Guardrails de saída**: validação via Pydantic antes de publicar o resultado
- **Retry com backoff**: até 3 tentativas com intervalo crescente
- **Fallback**: em caso de falha, publica `AnalysisFailedEvent` com a razão

**Limitações conhecidas:**
- Qualidade da análise depende da resolução e clareza do diagrama
- Diagramas muito complexos podem ter componentes não identificados
- O modelo pode alucinar componentes em imagens de baixa qualidade
- PDFs são limitados às primeiras 3 páginas

---

## Quick Start

### Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e rodando
- Chave de API do [OpenAI](https://platform.openai.com/api-keys) ou [Anthropic](https://console.anthropic.com)

### 1. Configurar variáveis de ambiente

```bash
cp .env.example docker/.env
```

Edite `docker/.env` e preencha:

```env
# Escolha o provedor: "openai" ou "claude"
LLM_PROVIDER=openai

# Chave OpenAI (se LLM_PROVIDER=openai)
OPENAI_API_KEY=sk-proj-...

# Chave Claude (se LLM_PROVIDER=claude)
CLAUDE_API_KEY=sk-ant-...
```

> **Atenção macOS:** A porta 5000 é usada pelo AirPlay Receiver. O Gateway usa a porta **5010**.
> Para liberar a 5000: Configurações do Sistema → Geral → AirDrop e Handoff → desligar Receptor AirPlay.

### 2. Tornar o script de init executável (apenas na primeira vez)

```bash
chmod +x docker/init-databases.sh
```

### 3. Subir todos os serviços

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

### 4. Verificar se tudo subiu

```bash
docker compose -f docker/docker-compose.yml ps
curl http://localhost:5010/health
```

---

## Endpoints da API

Todas as requisições passam pelo **Gateway** (`http://localhost:5010`):

### Upload de diagrama

```bash
POST /api/upload
Content-Type: multipart/form-data

curl -X POST http://localhost:5010/api/upload \
  -F "file=@diagrama.png"
```

**Formatos aceitos:** `.png`, `.jpg`, `.jpeg`, `.pdf`
**Tamanho máximo:** 10 MB

**Resposta:**
```json
{
  "jobId": "10be834b-ab07-48db-8921-cc172aa89525",
  "fileName": "diagrama.png",
  "filePath": "uploads/6425277e-.../diagrama.png",
  "message": "File uploaded successfully."
}
```

### Consultar status

```bash
GET /api/status/{jobId}

curl http://localhost:5010/api/status/10be834b-ab07-48db-8921-cc172aa89525
```

**Resposta:**
```json
{
  "id": "10be834b-ab07-48db-8921-cc172aa89525",
  "fileName": "diagrama.png",
  "status": "Analyzed",
  "createdAt": "2026-05-21T02:39:30Z",
  "updatedAt": "2026-05-21T02:39:39Z",
  "errorMessage": null
}
```

### Obter relatório

```bash
GET /api/report/{jobId}

curl http://localhost:5010/api/report/10be834b-ab07-48db-8921-cc172aa89525
```

**Resposta:**
```json
{
  "id": "8bb90eb4-e674-45bf-ac17-9aa15b9c02b5",
  "jobId": "10be834b-ab07-48db-8921-cc172aa89525",
  "components": "[\"API Gateway\",\"Upload Service\",\"PostgreSQL\",\"RabbitMQ\"]",
  "risks": "[\"Single Point of Failure no API Gateway\",\"Sem circuit breaker entre serviços\"]",
  "recommendations": "[\"Adicionar redundância no Gateway\",\"Implementar circuit breaker\"]",
  "createdAt": "2026-05-21T02:39:39Z"
}
```

---

## UIs de Gerenciamento

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| RabbitMQ Management | http://localhost:15672 | `hackton` / `hackton123` |
| MinIO Console | http://localhost:9001 | `hackton` / `hackton123` |
| Seq (Logs) | http://localhost:8081 | `admin` / `hackton123` |
| Swagger Upload | http://localhost:5001/swagger | — |
| Swagger Orchestrator | http://localhost:5002/swagger | — |
| Swagger Report | http://localhost:5003/swagger | — |

---

## Estrutura do Projeto

```
Hackton/
├── .github/workflows/
│   └── ci-cd.yml                  # Pipeline CI/CD (build, testes, deploy)
├── docker/
│   ├── docker-compose.yml         # Orquestração de todos os containers
│   └── init-databases.sh          # Inicialização dos databases PostgreSQL
├── scripts/
│   ├── start.sh / start.ps1       # Quick start
│   └── stop.sh / stop.ps1         # Quick stop
├── src/
│   ├── gateway/                   # API Gateway (YARP)
│   ├── upload-service/            # Microserviço de upload (.NET)
│   ├── orchestrator-service/      # Microserviço orquestrador (.NET)
│   ├── report-service/            # Microserviço de relatórios (.NET)
│   ├── analysis-service/          # Serviço de IA (Python)
│   │   ├── app/
│   │   │   ├── consumers/         # Consome AnalysisRequestedEvent
│   │   │   ├── services/          # LLM (Claude/OpenAI), MinIO, PDF, guardrails
│   │   │   ├── publishers/        # Publica eventos no formato MassTransit
│   │   │   └── models/            # Schema de validação Pydantic
│   │   ├── tests/                 # Testes unitários Python
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── shared/                    # Contratos compartilhados (eventos, enums)
├── tests/                         # Testes unitários .NET
│   ├── Gateway.Tests/
│   ├── UploadService.Tests/
│   ├── OrchestratorService.Tests/
│   └── ReportService.Tests/
├── .env.example                   # Template de variáveis de ambiente
└── Hackton.sln                    # Solution .NET
```

Cada microserviço .NET segue **Clean Architecture**:

```
service/
├── API/            # Host ASP.NET, endpoints, Dockerfile
├── Application/    # Casos de uso, consumers MassTransit, queries MediatR
├── Domain/         # Entidades, interfaces de repositório
└── Infrastructure/ # EF Core, repositórios, serviços externos
```

---

## Stack Tecnológica

### Back-end (.NET)
- **.NET 9** — Runtime e framework web (Minimal APIs)
- **YARP 2.2** — Reverse proxy no Gateway
- **MassTransit 8.4 + RabbitMQ** — Mensageria event-driven
- **MediatR 12.4** — CQRS (commands e queries)
- **Entity Framework Core 9** — ORM
- **FluentValidation 11** — Validação de entrada
- **Serilog + Seq** — Logging estruturado

### IA (Python)
- **Python 3.12**
- **OpenAI SDK** — GPT-4o com Vision
- **Anthropic SDK** — Claude com Vision (alternativa)
- **PyMuPDF** — Conversão de PDF para imagem
- **Pydantic** — Validação e guardrails de saída
- **aio-pika** — Cliente RabbitMQ assíncrono
- **minio** — Cliente MinIO/S3

### Infraestrutura
- **PostgreSQL 16** — Persistência (3 databases isolados)
- **RabbitMQ 3** — Message broker
- **MinIO** — Object storage compatível S3
- **Docker Compose** — Orquestração local

---

## Testes

### .NET
```bash
dotnet test Hackton.sln
```

### Python (Analysis Service)
```bash
cd src/analysis-service
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## CI/CD

Pipeline GitHub Actions (`.github/workflows/ci-cd.yml`):

1. **Build** — Compila a solução .NET
2. **Tests (.NET)** — Executa testes unitários com cobertura
3. **Tests (Python)** — Executa testes unitários do Analysis Service
4. **Deploy** — Sobe o ambiente completo via Docker Compose e valida health checks

Para o pipeline funcionar, configure o secret no repositório:
```
CLAUDE_API_KEY   ou   OPENAI_API_KEY
```

---

## Segurança

- **Validação de entrada**: extensões e tamanho de arquivo validados antes do upload (`.pdf`, `.png`, `.jpg`, `.jpeg`, máx. 10 MB)
- **Guardrails de IA**: respostas do LLM validadas via Pydantic antes de serem persistidas; itens truncados a 500 caracteres; máximo de 20 itens por lista
- **Prompt engineering defensivo**: system prompt instrui o modelo a retornar estrutura fixa e identificar entradas inválidas
- **Retry com falha controlada**: falhas no LLM resultam em `AnalysisFailedEvent`, nunca em dados corrompidos
- **Isolamento de dados**: cada microserviço possui seu próprio banco de dados
- **Credenciais via variáveis de ambiente**: nenhuma credencial hardcoded no código-fonte
- **Comunicação interna**: serviços se comunicam pela rede interna Docker, sem exposição desnecessária de portas
- **Riscos conhecidos**: ausência de autenticação nos endpoints (MVP), sem rate limiting, sem TLS entre serviços internos

---

## Comandos úteis

```bash
# Subir tudo
docker compose -f docker/docker-compose.yml up -d --build

# Derrubar tudo (preserva dados)
docker compose -f docker/docker-compose.yml down

# Derrubar tudo e limpar volumes
docker compose -f docker/docker-compose.yml down -v

# Rebuild de um serviço específico
docker compose -f docker/docker-compose.yml up -d --no-deps --build analysis-service

# Recriar container com novas variáveis de ambiente
docker compose -f docker/docker-compose.yml up -d --no-deps --force-recreate analysis-service

# Acompanhar logs em tempo real
docker compose -f docker/docker-compose.yml logs -f analysis-service

# Ver status de todos os containers
docker compose -f docker/docker-compose.yml ps
```
