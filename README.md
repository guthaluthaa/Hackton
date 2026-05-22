# Hackton — Análise Automatizada de Diagramas de Arquitetura

MVP de uma plataforma que recebe diagramas de arquitetura (imagem ou PDF), aplica IA para análise automática e gera um relatório técnico estruturado com componentes identificados, riscos arquiteturais e recomendações.

Plataforma de microserviços para processamento e análise de arquivos, construída com .NET 9, RabbitMQ, PostgreSQL e MinIO.

---

## Como Rodar o Projeto

### Pré-requisitos

- Windows 10/11
- [Docker Desktop para Windows](https://www.docker.com/products/docker-desktop/) instalado e rodando
- Chave de API: [OpenAI](https://platform.openai.com/api-keys) (GPT-4o) **ou** [Anthropic](https://console.anthropic.com) (Claude)

### 1. Configurar a API Key

```bash
# Copiar template de variáveis de ambiente
cp .env.example docker/.env
```

Edite `docker/.env` e preencha **apenas** a chave do provedor escolhido:

```env
# Escolha: "openai" ou "claude"
LLM_PROVIDER=openai

# Se escolheu openai:
OPENAI_API_KEY=sk-proj-sua-chave-aqui

# Se escolheu claude:
CLAUDE_API_KEY=sk-ant-sua-chave-aqui
```

### 2. Subir Tudo com Um Comando

**PowerShell:**
```powershell
.\scripts\start.ps1
```

**Ou diretamente via Docker Compose:**
```bash
docker compose -f docker/docker-compose.yml up -d --build
```

> O script automaticamente: cria o `.env` se não existir, aguarda a infraestrutura ficar saudável (PostgreSQL, RabbitMQ, MinIO), e sobe todos os microserviços incluindo o **Analysis Service (IA)**.

### 3. Verificar se Tudo Subiu

```bash
# Health check do Gateway
curl http://localhost:5010/health

# Status de todos os containers
docker compose -f docker/docker-compose.yml ps
```

### 4. Testar o Fluxo Completo

```bash
# Upload de um diagrama
curl -X POST http://localhost:5010/api/upload -F "file=@seu-diagrama.png"

# Consultar status (use o jobId retornado)
curl http://localhost:5010/api/status/{jobId}

# Obter relatório (quando status = "Analyzed")
curl http://localhost:5010/api/report/{jobId}
```

### 5. Parar Tudo

**PowerShell:**
```powershell
.\scripts\stop.ps1
```

**Ou diretamente:**
```bash
# Parar (preserva dados)
docker compose -f docker/docker-compose.yml down

# Parar e limpar volumes (reset completo)
docker compose -f docker/docker-compose.yml down -v
```

### Comandos Úteis

```bash
# Rebuild apenas o serviço de IA
docker compose -f docker/docker-compose.yml up -d --no-deps --build analysis-service

# Logs em tempo real do serviço de IA
docker compose -f docker/docker-compose.yml logs -f analysis-service

# Logs de todos os serviços
docker compose -f docker/docker-compose.yml logs -f

# Recriar serviço com novas variáveis de ambiente
docker compose -f docker/docker-compose.yml up -d --no-deps --force-recreate analysis-service
```

---

## Justificativa do Modelo de IA

### Modelo Escolhido: GPT-4o (padrão) / Claude Opus (alternativa)

#### Qualidade

| Critério | GPT-4o | Claude Opus |
|----------|--------|-------------|
| Compreensão visual de diagramas | Excelente — treinado com grande volume de dados visuais | Excelente — forte em raciocínio visual e contextual |
| Extração de componentes | Alta precisão com diagramas claros | Alta precisão, especialmente com texto |
| Identificação de riscos | Recomendações técnicas relevantes | Recomendações mais conservadoras e detalhadas |
| Aderência ao schema JSON | Muito boa com prompt engineering | Excelente aderência a instruções estruturadas |

#### Custo-Benefício

| Modelo | Custo Input (1M tokens) | Custo Output (1M tokens) | Custo médio/análise |
|--------|-------------------------|--------------------------|---------------------|
| **GPT-4o** | $2.50 | $10.00 | ~$0.01–0.03 |
| **Claude Opus** | $15.00 | $75.00 | ~$0.05–0.15 |
| GPT-4o-mini | $0.15 | $0.60 | ~$0.001 |

**Decisão:** GPT-4o como padrão oferece o melhor equilíbrio entre qualidade visual e custo. Claude Opus é disponibilizado como alternativa para cenários que exigem maior profundidade de análise.

> **Por que não GPT-4o-mini?** Apesar do custo 15x menor, apresenta degradação significativa na interpretação de diagramas complexos e menor aderência ao schema JSON obrigatório.

#### Desempenho

| Métrica | GPT-4o | Claude Opus |
|---------|--------|-------------|
| Latência média (1 imagem) | 5–15s | 8–20s |
| Latência máxima (3 páginas PDF) | 20–40s | 25–50s |
| Rate limit (tier 1) | 500 RPM | 50 RPM |
| Disponibilidade (SLA) | 99.9% | 99.5% |

**Mitigação de latência:** Processamento 100% assíncrono — o usuário faz upload e consulta o status depois.

#### Limitações Conhecidas do Modelo

| Limitação | Impacto | Mitigação Adotada |
|-----------|---------|-------------------|
| **Alucinação** — pode inventar componentes não visíveis | Relatório com dados incorretos | Prompt instrui "identify only REAL visible components" |
| **Inconsistência** — mesma imagem gera resultados diferentes | Resultados não-determinísticos | Guardrails validam formato mínimo; aceitar variação como feature |
| **Limite visual** — diagramas muito densos (50+ componentes) | Componentes podem ser omitidos | Documentar limitação; PDF limitado a 3 páginas |
| **Dependência de resolução** — imagens <300px degradam qualidade | Análise imprecisa | Pré-processamento com DPI controlado (150/100) |
| **Viés de arquitetura** — favorece padrões populares (microserviços, cloud) | Pode "projetar" padrões conhecidos | Prompt neutro; resultado apresentado como sugestão |
| **Sem contexto de negócio** — não conhece o domínio do sistema | Riscos genéricos | Aceito no MVP; futuro: permitir contexto adicional |
| **Custo por chamada** — cada análise consome tokens | Custo operacional | Limitar páginas PDF; max_tokens=2048 |
| **Rate limiting** — provedores limitam requisições | Indisponibilidade temporária | Retry com backoff exponencial |

---

## Arquitetura

```
                                    ┌──────────────┐
                                    │    MinIO      │
                                    │ (Blob Storage)│
                                    └──────┬───────┘
                                  Save file│   │Get file
                                           │   │
┌──────────┐    ┌─────────────┐    ┌───────▼───┴───┐         ┌─────────────────┐
│          │    │  API Gateway │    │    Upload     │         │ Analysis Service│
│ Frontend │───▶│  (YARP Proxy)│───▶│   Service    │         │  (Python + LLM) │
│  :3000   │    │    :5010     │    │    :5001     │         │  Claude/OpenAI  │
└──────────┘    └─────────────┘    └───────┬───────┘         └────────┬────────┘
                                           │                          │
                                           │ JobCreatedEvent          │ AnalysisCompletedEvent
                                           ▼                          │ AnalysisFailedEvent
                              ┌────────────────────────────┐          │
                              │        RabbitMQ            │◀─────────┘
                              │     (Message Broker)       │
                              └─────┬──────────────┬───────┘
                                    │              │
                  AnalysisRequested  │              │ GenerateReportCommand
                  Event             │              │
                                    ▼              ▼
                          ┌─────────────────┐  ┌─────────────────┐
                          │  Orchestrator   │  │  Report Service  │
                          │   Service :5002 │  │     :5003       │
                          └────────┬────────┘  └────────┬────────┘
                                   │                    │
                                   ▼                    ▼
          ┌───────────┐   ┌───────────────┐   ┌───────────────┐
          │ upload_db │   │orchestrator_db│   │  report_db    │
          └───────────┘   └───────────────┘   └───────────────┘
          └────────────── PostgreSQL 16 (1 instância) ──────────────┘
```

### Decisões de Arquitetura

| Decisão | Escolha | Justificativa |
|---------|---------|---------------|
| **Comunicação entre serviços** | Mensageria assíncrona (RabbitMQ) | Desacoplamento total; cada serviço opera independente; resiliência a falhas temporárias |
| **Padrão de orquestração** | Orchestrator centralizado | Controle de estado do fluxo em um único ponto; facilita rastreabilidade e tratamento de falhas |
| **Banco de dados** | Database-per-service (3 DBs lógicos, 1 instância PostgreSQL) | Isolamento de domínio; cada serviço é dono dos seus dados; simplifica deploy no MVP com instância única |
| **Object Storage** | MinIO (S3-compatible) | Arquivos binários não pertencem ao banco relacional; MinIO é drop-in replacement para AWS S3 em produção |
| **Analysis Service stateless** | Sem banco próprio | Não precisa guardar estado; recebe evento, processa e publica resultado — facilita escalabilidade horizontal |
| **API Gateway** | YARP (reverse proxy .NET) | Single entry point; roteamento centralizado; mesmo ecossistema .NET; suporte nativo a health checks |
| **Serialização de mensagens** | MassTransit envelope format | Compatibilidade entre .NET (MassTransit) e Python (aio-pika); schema tipado via contratos compartilhados |
| **Clean Architecture (.NET)** | API / Application / Domain / Infrastructure | Separação de responsabilidades; testabilidade; inversão de dependências |
| **LLM provider plugável** | Interface abstrata (Claude ou OpenAI) | Evita vendor lock-in; permite trocar ou comparar provedores sem alterar o pipeline |

### Fluxo de Eventos

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FLUXO COMPLETO DO PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  1. POST /api/upload                                                            │
│     └──▶ Upload Service salva arquivo no MinIO + metadata no upload_db          │
│          └──▶ Publica: JobCreatedEvent                                          │
│                                                                                 │
│  2. JobCreatedEvent                                                             │
│     └──▶ Orchestrator cria Job (status: Received) no orchestrator_db            │
│          └──▶ Publica: AnalysisRequestedEvent (status → Processing)             │
│                                                                                 │
│  3. AnalysisRequestedEvent                                                      │
│     └──▶ Analysis Service:                                                      │
│          ├── Baixa arquivo do MinIO                                             │
│          ├── Converte PDF → imagens (se necessário)                             │
│          ├── Envia para LLM (Claude/OpenAI) com prompt estruturado              │
│          ├── Aplica guardrails (Pydantic + heurísticas + aderência semântica)   │
│          └──▶ Publica: AnalysisCompletedEvent ou AnalysisFailedEvent            │
│                                                                                 │
│  4. AnalysisCompletedEvent                                                      │
│     └──▶ Orchestrator atualiza Job (status: Analyzed)                           │
│          └──▶ Publica: GenerateReportCommand                                    │
│                                                                                 │
│     AnalysisFailedEvent                                                         │
│     └──▶ Orchestrator atualiza Job (status: Failed, errorMessage)               │
│                                                                                 │
│  5. GenerateReportCommand                                                       │
│     └──▶ Report Service serializa resultado em JSON e persiste no report_db     │
│          └──▶ Publica: ReportGeneratedEvent                                     │
│                                                                                 │
│  6. ReportGeneratedEvent                                                        │
│     └──▶ Orchestrator marca Job como concluído                                  │
│                                                                                 │
│  7. GET /api/status/{jobId}  → Consulta estado atual do job                     │
│  8. GET /api/report/{jobId}  → Retorna relatório completo                       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Mapa de Eventos

| Evento | Producer | Consumer | Payload principal |
|--------|----------|----------|-------------------|
| `JobCreatedEvent` | Upload Service | Orchestrator | JobId, FileName, FilePath, ContentType, FileSize, LlmProvider, LlmApiKey |
| `AnalysisRequestedEvent` | Orchestrator | Analysis Service | JobId, FilePath, LlmProvider, LlmApiKey |
| `AnalysisCompletedEvent` | Analysis Service | Orchestrator | JobId, Components, Risks, Recommendations, SecurityFindings, ScalabilityAssessments, ArchitectureType, OverallRiskScore |
| `AnalysisFailedEvent` | Analysis Service | Orchestrator | JobId, Reason |
| `GenerateReportCommand` | Orchestrator | Report Service | JobId, Components, Risks, Recommendations |
| `ReportGeneratedEvent` | Report Service | Orchestrator | JobId, ReportId, GeneratedAt |

### Modelo de Dados (PostgreSQL)

**1 instância PostgreSQL 16** com **3 databases isolados** (padrão database-per-service):

#### `upload_db` — Tabela `UploadJobs`

| Campo | Tipo | Constraint |
|-------|------|------------|
| `Id` | Guid | PK |
| `FileName` | string(256) | NOT NULL |
| `FilePath` | string(1024) | NOT NULL |
| `ContentType` | string(128) | NOT NULL |
| `FileSize` | long | NOT NULL |
| `Status` | enum → string | NOT NULL (Created) |
| `CreatedAt` | DateTime | NOT NULL |
| `UpdatedAt` | DateTime | NOT NULL |

#### `orchestrator_db` — Tabela `Jobs`

| Campo | Tipo | Constraint |
|-------|------|------------|
| `Id` | Guid | PK |
| `FileName` | string(500) | NOT NULL |
| `FilePath` | string(1000) | NOT NULL |
| `Status` | enum → string | NOT NULL (Received → Processing → Analyzed / Failed) |
| `CreatedAt` | DateTime | NOT NULL |
| `UpdatedAt` | DateTime | NOT NULL |
| `ErrorMessage` | string(2000) | nullable |

#### `report_db` — Tabela `Reports`

| Campo | Tipo | Constraint |
|-------|------|------------|
| `Id` | Guid | PK |
| `JobId` | Guid | UNIQUE INDEX |
| `Components` | string (JSON) | NOT NULL |
| `Risks` | string (JSON) | NOT NULL |
| `Recommendations` | string (JSON) | NOT NULL |
| `CreatedAt` | DateTime | NOT NULL |

#### Analysis Service — **Sem banco de dados** (stateless)
Acessa apenas o MinIO para download de arquivos. Todo estado é gerenciado pelo Orchestrator via eventos.

### Segurança da API Key do Usuário

A chave de API fornecida pelo usuário no frontend:

- **Trafega apenas em memória** via RabbitMQ (mensagens transientes, descartadas após consumo)
- **NÃO é persistida** em banco de dados (PostgreSQL), object storage (MinIO), ou disco
- **É descartada imediatamente** após o processamento da análise pelo LLM
- **Cada requisição** usa a chave apenas para aquela análise específica
- **Nunca é logada** — os logs registram apenas o provider escolhido, nunca a chave

### Status do Job

| Status | Descrição |
|--------|-----------|
| `Received` | Upload recebido, aguardando início da análise |
| `Processing` | Análise em processamento pelo serviço de IA |
| `Analyzed` | Análise concluída com sucesso |
| `Failed` | Erro durante o processamento |

---

## Serviços

| Serviço | Tecnologia | Porta | Descrição |
|---------|-----------|-------|-----------|
| **Frontend** | HTML/CSS/JS + nginx | 3000 | Interface web para upload, acompanhamento e download |
| **Gateway** | .NET 9 / YARP | 5010 | Proxy reverso, roteamento centralizado |
| **Upload Service** | .NET 9 | 5001 | Recebe arquivos, armazena no MinIO, publica eventos |
| **Orchestrator Service** | .NET 9 | 5002 | Orquestra o fluxo entre serviços |
| **Analysis Service** | Python 3.12 | — | Análise com IA: segurança, escalabilidade e arquitetura |
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

O **Analysis Service** (Python) implementa o seguinte pipeline com análise de segurança, escalabilidade e arquitetura:

```
AnalysisRequestedEvent
        │
        ▼
[STEP 1/5] Download do arquivo (MinIO)
        │   Logs: tamanho, content_type, tempo de download
        ▼
[STEP 2/5] Pré-processamento
        │   PDF → converte páginas para PNG (PyMuPDF, máx. 3 páginas)
        │   IMG → usa direto (PNG/JPEG)
        │   Logs: número de páginas, media_type, tempo de conversão
        ▼
[STEP 3/5] Chamada ao LLM com Vision (GPT-4o ou Claude)
        │   Prompt estruturado com foco em:
        │   • Auditoria de segurança (13 categorias)
        │   • Avaliação de escalabilidade (por componente)
        │   • Análise arquitetural (tipo, acoplamento, resiliência)
        │   Logs: tempo de resposta, tokens consumidos, tentativas
        ▼
[STEP 4/5] Guardrails de saída (Pydantic + Heurísticas + Aderência Semântica)
        │   1. Validação Pydantic — tipos, campos obrigatórios, limites
        │   2. Heurísticas — rejeita componentes genéricos, riscos não-técnicos,
        │      recomendações não-acionáveis, duplicatas
        │   3. Aderência semântica — verifica cobertura de segurança e escalabilidade,
        │      coerência entre severidade e urgência das recomendações
        │   Logs: cada etapa de validação com resultado detalhado
        ▼
[STEP 5/5] Publicação do resultado
        │   Sucesso → AnalysisCompletedEvent (com security_findings, scalability, risk_score)
        │   Falha   → AnalysisFailedEvent { reason }
        ▼
[PIPELINE COMPLETE] Resumo com tempos por etapa e métricas finais
```

### Modelo de Análise

O resultado da IA contém as seguintes dimensões:

| Campo | Descrição |
|-------|-----------|
| `components` | Componentes arquiteturais identificados no diagrama |
| `risks` | Riscos técnicos com descrição específica |
| `recommendations` | Recomendações acionáveis e priorizadas |
| `securityFindings` | Auditoria de segurança com categoria, severidade e componente afetado |
| `scalabilityAssessments` | Avaliação de escalabilidade por componente com padrão atual e gargalos |
| `architectureType` | Tipo de arquitetura identificada (microservices, monolith, serverless, etc.) |
| `overallRiskScore` | Score de risco calculado (0.0–10.0) baseado na severidade dos findings |

### Auditoria de Segurança

A IA avalia 13 categorias de segurança com severidade classificada:

| Categoria | Descrição |
|-----------|-----------|
| `authentication` | Autenticação de usuários e serviços |
| `authorization` | Controle de acesso e permissões |
| `encryption` | Criptografia em trânsito e repouso |
| `data_exposure` | Exposição indevida de dados sensíveis |
| `injection` | Vulnerabilidades de injeção (SQL, command) |
| `misconfiguration` | Configurações inseguras |
| `single_point_of_failure` | Ausência de redundância |
| `network_security` | Segurança de rede |
| `api_security` | Proteção de APIs |
| `secrets_management` | Gestão de credenciais |
| `logging_monitoring` | Observabilidade e auditoria |
| `compliance` | Conformidade com padrões |
| `access_control` | Controle de acesso insuficiente |

**Severidades:** `critical` > `high` > `medium` > `low` > `info`

### Avaliação de Escalabilidade

Cada componente é avaliado quanto ao padrão de escala:

| Padrão | Descrição |
|--------|-----------|
| `horizontal` | Escala adicionando mais instâncias |
| `vertical` | Escala aumentando recursos da instância |
| `hybrid` | Combinação de horizontal e vertical |
| `none` | Sem estratégia de escalabilidade identificada |

### Guardrails e Validação

O sistema aplica 3 camadas de validação antes de aceitar a resposta da IA:

**1. Validação Pydantic (estrutural)**
- Campos obrigatórios presentes e tipados
- Categorias de segurança validadas contra lista fechada
- Severidades e padrões de escala como enums
- Limites: máx. 500 chars/item, máx. 20 itens/lista

**2. Heurísticas (qualidade)**
- Rejeita componentes genéricos ("sistema", "service")
- Exige termos técnicos em riscos (regex para padrões como API, SQL, SPOF)
- Exige verbos de ação em recomendações (adicionar, implementar, configurar)
- Detecta duplicatas
- Valida referência cruzada entre security_findings e components

**3. Aderência Semântica (completude)**
- Alerta se análise não contém avaliação de segurança
- Alerta se não há avaliação de escalabilidade
- Verifica coerência entre findings críticos e urgência nas recomendações
- Valida que componentes em scalability_assessments existem na lista principal

### Observabilidade

Todos os logs seguem prefixo estruturado para fácil filtro:

```
[PIPELINE START]     — Início do processamento
[STEP N/5]           — Cada etapa com métricas de tempo
[GUARDRAIL]          — Validação principal
[GUARDRAIL][HEURISTIC] — Violações de heurística
[GUARDRAIL][SEMANTIC]  — Avisos de aderência semântica
[PIPELINE COMPLETE]  — Resumo final com breakdown de tempos
[PIPELINE FAILED]    — Falha com razão
[PIPELINE ERROR]     — Erro inesperado com stacktrace
```

Exemplo de log de pipeline completo:
```
[PIPELINE START] job_id=abc-123 | file=uploads/guid/diagram.pdf
[STEP 1/5] Downloading file from storage | job_id=abc-123
[STEP 1/5] Download complete | job_id=abc-123 | size=245000 bytes | content_type=application/pdf | elapsed=120ms
[STEP 2/5] Converting file to images | job_id=abc-123
[STEP 2/5] Conversion complete | job_id=abc-123 | pages=2 | media_type=image/png | elapsed=850ms
[STEP 3/5] Sending to LLM for analysis (security + scalability + architecture) | job_id=abc-123
[STEP 3/5] LLM response received | job_id=abc-123 | elapsed=12500ms | valid=True
[GUARDRAIL] Starting LLM response validation
[GUARDRAIL] Pydantic validation passed
[GUARDRAIL] Running heuristic checks
[GUARDRAIL] Heuristic checks passed
[GUARDRAIL] Running semantic adherence checks
[GUARDRAIL] Semantic adherence checks passed — full coverage
[GUARDRAIL] Validation complete | components=5 | risks=3 | recommendations=4 | security_findings=2 | scalability_assessments=3 | architecture_type=microservices | risk_score=7.5
[STEP 4/5] Validation passed | job_id=abc-123 | ...
[STEP 5/5] Publishing AnalysisCompletedEvent | job_id=abc-123
[PIPELINE COMPLETE] job_id=abc-123 | total_elapsed=13800ms | steps: download=120ms convert=850ms llm=12500ms | security_findings=2 | scalability_assessments=3 | risk_score=7.5
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

**Resposta (em processamento):**
```json
{
  "id": "10be834b-ab07-48db-8921-cc172aa89525",
  "fileName": "diagrama.png",
  "status": "Processing",
  "createdAt": "2026-05-21T02:39:30Z",
  "updatedAt": "2026-05-21T02:39:31Z",
  "errorMessage": null
}
```

**Resposta (análise concluída):**
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
| **Frontend** | http://localhost:3000 | — |
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
│   ├── frontend/                  # Interface web (HTML/CSS/JS + nginx)
│   │   ├── index.html             # SPA: upload, status stepper, relatório
│   │   ├── css/styles.css         # Dark theme responsivo
│   │   ├── js/app.js              # Lógica: upload, polling, download
│   │   ├── nginx.conf             # Proxy reverso /api/ → gateway
│   │   └── Dockerfile
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

O **Frontend** segue separação de responsabilidades (presentation layer pura):

```
frontend/
├── index.html      # Estrutura e semântica (View)
├── css/            # Apresentação visual (Styling)
├── js/             # Lógica de interação e comunicação com API (Controller)
├── nginx.conf      # Infraestrutura de rede (proxy reverso)
└── Dockerfile      # Empacotamento e deploy
```

> O frontend não contém lógica de negócio — apenas consome a API do Gateway e apresenta os dados. Toda regra de negócio permanece nos microserviços backend.

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
- **Pydantic** — Validação estrutural, heurísticas e guardrails de saída
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

### Plataforma

- **Validação de entrada**: extensões e tamanho de arquivo validados antes do upload (`.pdf`, `.png`, `.jpg`, `.jpeg`, máx. 10 MB)
- **API Key do usuário em trânsito apenas**: a chave fornecida pelo usuário nunca é persistida — trafega via mensageria em memória e é descartada após uso
- **Isolamento de dados**: cada microserviço possui seu próprio banco de dados
- **Credenciais via variáveis de ambiente**: nenhuma credencial hardcoded no código-fonte
- **Comunicação interna**: serviços se comunicam pela rede interna Docker, sem exposição desnecessária de portas
- **Riscos conhecidos (MVP)**: ausência de autenticação nos endpoints, sem rate limiting, sem TLS entre serviços internos

### IA — Guardrails de Segurança

- **Validação Pydantic estrita**: respostas do LLM validadas com tipos, enums e constraints antes de serem persistidas
- **Heurísticas anti-alucinação**: rejeição automática de respostas com componentes genéricos, riscos não-técnicos ou recomendações vagas
- **Aderência semântica**: verificação de que a análise cobre segurança e escalabilidade, com alertas de coerência
- **Categorias de segurança fechadas**: apenas categorias pré-definidas são aceitas (authentication, encryption, injection, etc.)
- **Severidade tipada**: enum estrito (`critical`, `high`, `medium`, `low`, `info`) — valores fora do enum são rejeitados
- **Risk score automático**: score calculado a partir da severidade dos findings, sem depender do LLM
- **Retry com falha controlada**: falhas no LLM resultam em `AnalysisFailedEvent`, nunca em dados corrompidos
- **Prompt engineering defensivo**: system prompt instrui o modelo a retornar estrutura fixa e identificar entradas inválidas
- **Truncamento defensivo**: itens limitados a 500 caracteres; máximo de 20 itens por lista
- **Referência cruzada**: security findings e scalability assessments são validados contra os componentes listados
