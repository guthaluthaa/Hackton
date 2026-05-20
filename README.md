# Hackton

Plataforma de microserviços para processamento e análise de arquivos, construída com .NET 9, RabbitMQ, PostgreSQL e MinIO.

## Arquitetura

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐     ┌────────────────┐
│   Cliente   │────▶│     Gateway      │────▶│   Upload Service    │────▶│     MinIO      │
│             │     │   (YARP Proxy)   │     │                     │     │  (Storage)     │
└─────────────┘     └──────────────────┘     └─────────────────────┘     └────────────────┘
                            │                          │
                            │                          │ (evento via RabbitMQ)
                            ▼                          ▼
                    ┌──────────────────┐     ┌─────────────────────┐
                    │  Report Service  │◀────│ Orchestrator Service │
                    │                  │     │                     │
                    └──────────────────┘     └─────────────────────┘
                            │                          │
                            ▼                          ▼
                    ┌──────────────────┐     ┌─────────────────────┐
                    │   PostgreSQL     │     │     PostgreSQL       │
                    │   (report_db)    │     │  (orchestrator_db)   │
                    └──────────────────┘     └─────────────────────┘
```

### Serviços

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| **Gateway** | 5000 | Proxy reverso (YARP) que roteia requisições para os microserviços |
| **Upload Service** | 5001 | Recebe uploads de arquivos, armazena no MinIO e publica eventos |
| **Orchestrator Service** | 5002 | Coordena o fluxo de análise entre serviços |
| **Report Service** | 5003 | Gera e disponibiliza relatórios de análise |

### Infraestrutura

| Componente | Porta | Descrição |
|------------|-------|-----------|
| **PostgreSQL** | 5432 | Banco de dados relacional (3 databases isolados) |
| **RabbitMQ** | 5672 / 15672 | Message broker para comunicação assíncrona |
| **MinIO** | 9000 / 9001 | Object storage compatível com S3 |
| **Seq** | 5341 / 8081 | Agregador de logs estruturados |

## Quick Start

### Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e rodando
- [.NET 9 SDK](https://dotnet.microsoft.com/download/dotnet/9.0) (apenas para desenvolvimento local)

### Iniciar tudo com um comando

**Windows (PowerShell):**
```powershell
.\scripts\start.ps1
```

**Linux/macOS (Bash):**
```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

**Ou manualmente com Docker Compose:**
```bash
cd docker
docker compose up -d --build
```

### Parar os serviços

**Windows (PowerShell):**
```powershell
.\scripts\stop.ps1
```

**Linux/macOS (Bash):**
```bash
./scripts/stop.sh
```

**Para remover volumes (dados persistidos):**
```bash
docker compose -f docker/docker-compose.yml down -v
```

## Endpoints da API

Todas as requisições passam pelo **Gateway** (`http://localhost:5000`):

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/upload` | Envia um arquivo para análise |
| GET | `/api/status/{jobId}` | Consulta o status de um job |
| GET | `/api/report/{jobId}` | Obtém o relatório de um job concluído |

## UIs de Gerenciamento

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| RabbitMQ Management | http://localhost:15672 | `hackton` / `hackton123` |
| MinIO Console | http://localhost:9001 | `hackton` / `hackton123` |
| Seq (Logs) | http://localhost:8081 | `admin` / `hackton123` |

## Configuração

### Variáveis de Ambiente

Copie o `.env.example` para `docker/.env` e ajuste conforme necessário:

```bash
cp .env.example docker/.env
```

As variáveis disponíveis estão documentadas no arquivo `.env.example`.

> **Nota:** Os valores padrão são apenas para desenvolvimento local. Em produção, use credenciais fortes e configure via secrets management.

### Estrutura do Projeto

```
Hackton/
├── docker/
│   ├── docker-compose.yml    # Orquestração de todos os containers
│   └── init-databases.sh     # Script de inicialização do PostgreSQL
├── scripts/
│   ├── start.sh / start.ps1  # Quick start
│   └── stop.sh / stop.ps1    # Quick stop
├── src/
│   ├── gateway/              # API Gateway (YARP)
│   ├── upload-service/       # Microserviço de upload
│   ├── orchestrator-service/ # Microserviço orquestrador
│   ├── report-service/       # Microserviço de relatórios
│   └── shared/               # Contratos compartilhados (eventos, enums)
├── .env.example              # Template de variáveis de ambiente
├── .gitignore
└── Hackton.sln               # Solution .NET
```

Cada microserviço segue **Clean Architecture**:
```
service/
├── API/            # Host ASP.NET, controllers, Dockerfile
├── Application/    # Casos de uso, consumers, queries
├── Domain/         # Entidades, interfaces
└── Infrastructure/ # Implementações (EF Core, repos, serviços externos)
```

## Desenvolvimento Local

### Rodando apenas a infraestrutura (sem buildar os serviços)

```bash
cd docker
docker compose up -d postgres rabbitmq minio seq
```

### Rodando um serviço individualmente

```bash
cd src/upload-service/API/UploadService.API
dotnet run
```

### Rebuild de um serviço específico

```bash
docker compose -f docker/docker-compose.yml up -d --build upload-service
```

### Acompanhando logs

```bash
# Todos os serviços
docker compose -f docker/docker-compose.yml logs -f

# Serviço específico
docker compose -f docker/docker-compose.yml logs -f upload-service
```

## Stack Tecnológica

- **.NET 9** — Runtime e framework web
- **YARP** — Reverse proxy no gateway
- **MassTransit + RabbitMQ** — Mensageria e event-driven architecture
- **Entity Framework Core** — ORM e migrations
- **PostgreSQL 16** — Banco de dados
- **MinIO** — Object storage (compatível S3)
- **Seq + Serilog** — Logging estruturado
- **Docker Compose** — Orquestração local

## CI/CD

O projeto inclui um workflow GitHub Actions (`.github/workflows/ci-cd.yml`) para build e validação automática.

## Licença

Projeto desenvolvido para hackathon.
