# Exemplos de Arquiteturas — Boas e Ruins

---

## RUINS

---

### 1. Monolito com acoplamento total

Todos os modulos dependem diretamente uns dos outros. Qualquer mudanca pode quebrar tudo.

```mermaid
graph TD
    UI[Interface do Usuario]
    UI --> Pedidos
    UI --> Usuarios
    UI --> Pagamentos
    UI --> Relatorios
    UI --> Notificacoes

    Pedidos --> Usuarios
    Pedidos --> Pagamentos
    Pedidos --> Estoque
    Pedidos --> Relatorios
    Pedidos --> Notificacoes

    Pagamentos --> Usuarios
    Pagamentos --> Pedidos
    Pagamentos --> Relatorios

    Relatorios --> Usuarios
    Relatorios --> Pedidos
    Relatorios --> Pagamentos
    Relatorios --> Estoque

    Notificacoes --> Usuarios
    Notificacoes --> Pedidos

    Estoque --> Pedidos
    Estoque --> Relatorios

    style UI fill:#ff4444,color:#fff
    style Pedidos fill:#ff6666,color:#fff
    style Usuarios fill:#ff6666,color:#fff
    style Pagamentos fill:#ff6666,color:#fff
    style Relatorios fill:#ff6666,color:#fff
    style Notificacoes fill:#ff6666,color:#fff
    style Estoque fill:#ff6666,color:#fff
```

**Problemas:**
- Dependencia circular (Pedidos → Pagamentos → Pedidos)
- Impossivel escalar um modulo sem escalar tudo
- Um bug em Estoque pode derrubar Pagamentos

---

### 2. Microservicos chamando uns aos outros diretamente (acoplamento sincrono)

Cada servico chama o proximo via HTTP. Se um cai, todos caem.

```mermaid
sequenceDiagram
    participant C as Cliente
    participant A as Servico A
    participant B as Servico B
    participant C2 as Servico C
    participant D as Servico D

    C->>A: POST /pedido
    A->>B: GET /usuario
    B->>C2: GET /credito
    C2->>D: GET /historico
    D-->>C2: 500 ERRO
    C2-->>B: 500 ERRO
    B-->>A: 500 ERRO
    A-->>C: 500 ERRO (falha em cascata)
```

**Problemas:**
- Falha em cascata: um servico derruba a cadeia toda
- Alto acoplamento temporal (todos precisam estar no ar ao mesmo tempo)
- Latencia acumulada (A espera B, B espera C, C espera D)

---

### 3. God Service (servico que faz tudo)

Um unico servico acumula responsabilidades de varios dominios.

```mermaid
graph TD
    Cliente --> GS

    subgraph GS["GodService (faz TUDO)"]
        AU[Autenticacao]
        PD[Pedidos]
        PG[Pagamentos]
        NT[Notificacoes]
        RL[Relatorios]
        ES[Estoque]
        LG[Logs]
    end

    GS --> DB[(Banco unico gigante)]
    GS --> Email[Servico de Email]
    GS --> SMS[Servico de SMS]
    GS --> ERP[ERP Externo]

    style GS fill:#cc0000,color:#fff
    style DB fill:#880000,color:#fff
```

**Problemas:**
- Times diferentes editando o mesmo codigo = conflitos
- Impossivel fazer deploy parcial
- Banco vira gargalo de tudo
- Nao tem como escalar so a parte de Relatorios, por exemplo

---

### 4. Dependencia circular entre camadas

A camada de Infraestrutura conhece a camada de API — inversao errada.

```mermaid
graph LR
    API --> Application
    Application --> Domain
    Domain --> Infrastructure
    Infrastructure --> API

    style Domain fill:#ff4444,color:#fff
    style Infrastructure fill:#ff4444,color:#fff
```

**Problema:** Domain nao pode depender de Infrastructure (banco, HTTP, etc). Domain deve ser puro e isolado. Infrastructure que depende de Domain, nunca o contrario.

---

### 5. Banco de dados compartilhado entre microservicos

```mermaid
graph TD
    SA[Servico A - Pedidos]
    SB[Servico B - Usuarios]
    SC[Servico C - Pagamentos]
    SD[Servico D - Relatorios]

    SA --> DB[(Banco Compartilhado)]
    SB --> DB
    SC --> DB
    SD --> DB

    style DB fill:#cc0000,color:#fff
```

**Problemas:**
- Qualquer servico pode alterar dados de outro sem contrato
- Schema unico: mudar uma tabela quebra todos os servicos
- Impossivel migrar um servico para outro banco de dados
- Acoplamento invisivel via banco

---

---

## BOAS

---

### 6. Clean Architecture — dependencias corretas

As dependencias apontam sempre para dentro. Domain nao conhece nada externo.

```mermaid
graph LR
    API --> Application
    Application --> Domain
    Infrastructure --> Domain
    Infrastructure --> Application

    style Domain fill:#00aa44,color:#fff
    style Application fill:#0077cc,color:#fff
    style API fill:#5599ff,color:#fff
    style Infrastructure fill:#888,color:#fff
```

**Correto:**
- Domain: entidades puras, sem dependencias externas
- Application: casos de uso, usa interfaces definidas no Domain
- Infrastructure: implementa as interfaces (banco, HTTP, fila)
- API: ponto de entrada, delega para Application

---

### 7. Microservicos com comunicacao assincrona (Event-Driven)

Como o projeto Hackton funciona. Servicos nao se chamam diretamente — publicam eventos.

```mermaid
graph LR
    C[Cliente] --> GW[Gateway]

    GW --> US[Upload Service]
    US -->|JobCreatedEvent| MQ[[RabbitMQ]]

    MQ -->|JobCreatedEvent| OS[Orchestrator Service]
    OS -->|AnalysisRequestedEvent| MQ

    MQ -->|AnalysisRequestedEvent| AS[Analysis Service]
    AS -->|AnalysisCompletedEvent| MQ

    MQ -->|AnalysisCompletedEvent| OS
    OS -->|GenerateReportCommand| MQ

    MQ -->|GenerateReportCommand| RS[Report Service]

    US --> DB1[(upload_db)]
    OS --> DB2[(orchestrator_db)]
    RS --> DB3[(report_db)]

    style MQ fill:#ff9900,color:#000
    style GW fill:#5599ff,color:#fff
    style US fill:#00aa44,color:#fff
    style OS fill:#00aa44,color:#fff
    style AS fill:#0077cc,color:#fff
    style RS fill:#00aa44,color:#fff
```

**Vantagens:**
- Servico cai? Os eventos ficam na fila, processamento retoma depois
- Cada servico tem seu proprio banco
- Facil adicionar novo servico sem alterar os existentes

---

### 8. Banco de dados por servico (Database per Service)

```mermaid
graph TD
    SA[Servico Pedidos] --> DA[(pedidos_db)]
    SB[Servico Usuarios] --> DB[(usuarios_db)]
    SC[Servico Pagamentos] --> DC[(pagamentos_db)]
    SD[Servico Relatorios] --> DD[(relatorios_db)]

    SA <-->|eventos via fila| SB
    SA <-->|eventos via fila| SC
    SC <-->|eventos via fila| SD

    style DA fill:#00aa44,color:#fff
    style DB fill:#00aa44,color:#fff
    style DC fill:#00aa44,color:#fff
    style DD fill:#00aa44,color:#fff
```

**Vantagens:**
- Cada servico pode usar o banco mais adequado (PostgreSQL, MongoDB, Redis...)
- Schema independente: mudar pedidos_db nao afeta pagamentos_db
- Times autonomos

---

### 9. API Gateway com roteamento

Um unico ponto de entrada, sem expor servicos internos diretamente.

```mermaid
graph TD
    C[Cliente Web / Mobile]
    C --> GW[API Gateway :5000]

    GW -->|/api/upload/*| US[Upload Service :5001]
    GW -->|/api/status/*| OS[Orchestrator Service :5002]
    GW -->|/api/report/*| RS[Report Service :5003]

    subgraph Rede Interna
        US
        OS
        RS
    end

    style GW fill:#5599ff,color:#fff
    style US fill:#00aa44,color:#fff
    style OS fill:#00aa44,color:#fff
    style RS fill:#00aa44,color:#fff
```

**Vantagens:**
- Cliente conhece apenas um endereco
- Servicos internos nao ficam expostos
- Gateway centraliza autenticacao, rate limiting, logging

---

### 10. Fluxo de status de um Job (State Machine)

Estados bem definidos com transicoes claras — sem estados ambiguos.

```mermaid
stateDiagram-v2
    [*] --> Received : arquivo enviado
    Received --> Processing : orchestrator recebe evento
    Processing --> Analyzed : analysis service completa
    Processing --> Failed : analysis service falha
    Analyzed --> [*] : relatorio gerado
    Failed --> [*] : erro registrado
```

**Vantagens:**
- Sempre se sabe em que estado o Job esta
- Transicoes invalidas sao impossibles (nao tem como ir de Failed para Analyzed)
- Facil de auditar e debugar
