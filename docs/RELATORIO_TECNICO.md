# Relatório Técnico — Hackton: Análise Automatizada de Diagramas de Arquitetura

## 1. Descrição do Problema

Equipes de engenharia de software frequentemente produzem diagramas de arquitetura durante o processo de design e documentação de sistemas. No entanto, a revisão desses diagramas em busca de riscos arquiteturais, pontos de falha e oportunidades de melhoria é um processo manual, demorado e dependente de expertise humana.

**Objetivo:** Automatizar a análise de diagramas de arquitetura de software utilizando Inteligência Artificial com capacidade de visão (Vision), gerando relatórios técnicos estruturados contendo componentes identificados, riscos arquiteturais e recomendações de melhoria.

**Problema central:** Como extrair informações semânticas de diagramas visuais (imagens/PDFs) de forma automatizada, confiável e estruturada, tratando adequadamente falhas e limitações inerentes aos modelos de linguagem?

---

## 2. Arquitetura Proposta

### 2.1 Visão Geral

A solução adota uma **arquitetura de microserviços event-driven**, onde cada serviço possui responsabilidade única e se comunica exclusivamente via mensageria assíncrona (RabbitMQ).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INFRAESTRUTURA                                  │
│  ┌──────────┐  ┌──────────────┐  ┌─────────┐  ┌─────────────────────────┐  │
│  │PostgreSQL│  │  RabbitMQ    │  │  MinIO  │  │         Seq             │  │
│  │(3 DBs)   │  │(Message Bus) │  │(Storage)│  │  (Logging Agregado)     │  │
│  └──────────┘  └──────────────┘  └─────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                             MICROSERVIÇOS                                     │
│                                                                              │
│  Cliente ──▶ Gateway (YARP :5010)                                            │
│                 │                                                             │
│                 ├──▶ Upload Service (:5001)                                   │
│                 │       └── Valida arquivo → Armazena MinIO → Publica evento  │
│                 │                                                             │
│                 ├──▶ Orchestrator Service (:5002)                             │
│                 │       └── Coordena fluxo → Gerencia status do Job           │
│                 │                                                             │
│                 ├──▶ Report Service (:5003)                                   │
│                 │       └── Persiste relatório → Disponibiliza via API        │
│                 │                                                             │
│                 └──▶ Analysis Service (Python, sem porta pública)             │
│                         └── Processa imagem → Chama LLM → Valida saída       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Diagrama de Arquitetura Detalhado

```
                    ┌──────────┐
                    │  Cliente │
                    └────┬─────┘
                         │ POST /api/upload
                         ▼
                ┌─────────────────┐
                │  API Gateway    │
                │  (YARP :5010)   │
                └───┬─────┬───┬──┘
                    │     │   │
        ┌───────────┘     │   └───────────┐
        ▼                 ▼               ▼
┌──────────────┐  ┌─────────────┐  ┌──────────────┐
│Upload Service│  │Orchestrator │  │Report Service│
│   (.NET)     │  │  (.NET)     │  │   (.NET)     │
│   :5001      │  │   :5002     │  │   :5003      │
└──────┬───────┘  └──────┬──────┘  └──────┬───────┘
       │                 │                 │
       │                 │                 │
       ▼                 ▼                 ▼
┌──────────┐      ┌──────────┐      ┌──────────┐
│upload_db │      │orch_db   │      │report_db │
│(Postgres)│      │(Postgres)│      │(Postgres)│
└──────────┘      └──────────┘      └──────────┘

       │                 │                 │
       └────────┬────────┴────────┬────────┘
                │                 │
                ▼                 ▼
        ┌──────────────┐  ┌─────────────────────┐
        │   RabbitMQ   │  │   MinIO (Storage)   │
        │ (Event Bus)  │  │   Bucket: uploads   │
        └──────┬───────┘  └─────────────────────┘
               │
               ▼
     ┌───────────────────┐
     │ Analysis Service  │
     │   (Python 3.12)   │
     │                   │
     │  ┌─────────────┐  │
     │  │ LLM Client  │  │
     │  │(Claude/GPT) │  │
     │  └──────┬──────┘  │
     │         │         │
     │         ▼         │
     │  ┌─────────────┐  │
     │  │ Guardrails  │  │
     │  │ (Pydantic)  │  │
     │  └─────────────┘  │
     └───────────────────┘
```

### 2.3 Fluxo de Eventos

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        FLUXO DE EVENTOS                                    │
│                                                                           │
│  1. JobCreatedEvent                                                       │
│     Upload Service ──────────────────────▶ Orchestrator                   │
│     (Job criado com status: Received)                                     │
│                                                                           │
│  2. AnalysisRequestedEvent                                                │
│     Orchestrator ────────────────────────▶ Analysis Service               │
│     (Job atualizado para status: Processing)                              │
│                                                                           │
│  3a. AnalysisCompletedEvent (sucesso)                                     │
│      Analysis Service ───────────────────▶ Orchestrator                   │
│                                                                           │
│  3b. AnalysisFailedEvent (falha)                                          │
│      Analysis Service ───────────────────▶ Orchestrator                   │
│                                                                           │
│  4. GenerateReportCommand (após sucesso)                                  │
│     Orchestrator ────────────────────────▶ Report Service                 │
│                                                                           │
│  5. ReportGeneratedEvent                                                  │
│     Report Service ──────────────────────▶ (finaliza fluxo)               │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Justificativa da Abordagem Escolhida

### 3.1 Por que Microserviços Event-Driven?

| Critério | Justificativa |
|----------|---------------|
| **Desacoplamento** | Cada serviço evolui independentemente; a falha do Analysis Service não impacta o Upload |
| **Resiliência** | Mensagens persistem no RabbitMQ até serem processadas; serviços podem reiniciar sem perda |
| **Escalabilidade** | O Analysis Service (gargalo por latência do LLM) pode escalar horizontalmente |
| **Observabilidade** | Cada etapa do fluxo gera eventos rastreáveis |
| **Tecnologia heterogênea** | Python para IA (ecossistema ML maduro) + .NET para APIs (performance e tipagem forte) |

### 3.2 Por que LLM com Vision (GPT-4o / Claude)?

| Alternativa Considerada | Motivo de Descarte |
|--------------------------|--------------------|
| OCR + regras manuais | Diagramas não são texto; relações entre componentes são visuais |
| Modelo de detecção de objetos treinado | Requer dataset anotado de diagramas; altíssimo custo de treinamento |
| Template matching | Diagramas variam enormemente em estilo e ferramenta de criação |

**Vantagem da abordagem com LLM Vision:**
- Entende contexto semântico (não apenas detecta formas)
- Identifica relações entre componentes
- Gera texto descritivo e recomendações em linguagem natural
- Funciona com qualquer estilo de diagrama sem treinamento específico

### 3.3 Por que Dois Provedores de LLM?

A arquitetura suporta **Claude (Anthropic)** e **GPT-4o (OpenAI)** via Strategy Pattern:

- **Redundância:** Se um provedor apresentar indisponibilidade, pode-se trocar via variável de ambiente
- **Flexibilidade de custo:** Permite escolher o provedor com melhor custo-benefício
- **Comparação de qualidade:** Facilita testes A/B entre modelos

### 3.4 Justificativa do Modelo — Qualidade, Custo e Desempenho

#### Qualidade de Análise Visual

| Critério | GPT-4o (padrão) | Claude Opus (alternativa) |
|----------|-----------------|---------------------------|
| Compreensão visual de diagramas | Excelente — treinado com grande volume de dados visuais | Excelente — forte em raciocínio visual e contextual |
| Extração de componentes | Alta precisão em diagramas claros e padronizados | Alta precisão, especialmente com texto detalhado |
| Identificação de riscos arquiteturais | Recomendações técnicas relevantes e práticas | Análises mais conservadoras e detalhadas |
| Aderência ao schema JSON obrigatório | Muito boa com prompt engineering adequado | Excelente aderência a instruções estruturadas |
| Diagramas complexos (>20 componentes) | Bom — pode omitir componentes secundários | Bom — tende a ser mais exaustivo |

#### Custo-Benefício

| Modelo | Input (1M tokens) | Output (1M tokens) | Custo médio por análise | Relação custo/qualidade |
|--------|-------------------|---------------------|-------------------------|-------------------------|
| **GPT-4o** (escolhido) | $2.50 | $10.00 | ~$0.01–0.03 | **Melhor equilíbrio** |
| Claude Opus | $15.00 | $75.00 | ~$0.05–0.15 | Maior qualidade, 5x mais caro |
| GPT-4o-mini | $0.15 | $0.60 | ~$0.001 | Barato mas qualidade visual insuficiente |
| Claude Sonnet | $3.00 | $15.00 | ~$0.02–0.05 | Alternativa viável em custo |

**Decisão:** GPT-4o como padrão oferece o melhor equilíbrio entre qualidade de análise visual e custo operacional. Claude Opus é disponibilizado como alternativa para cenários que exijam maior profundidade e detalhamento.

> **Por que não GPT-4o-mini?** Apesar de custo 15x menor, apresenta degradação significativa na interpretação de diagramas complexos, menor aderência ao schema JSON obrigatório, e tendência a retornar listas genéricas.

#### Desempenho e Latência

| Métrica | GPT-4o | Claude Opus |
|---------|--------|-------------|
| Latência média (1 imagem PNG) | 5–15 segundos | 8–20 segundos |
| Latência máxima (PDF 3 páginas) | 20–40 segundos | 25–50 segundos |
| Rate limit (tier 1) | 500 RPM | 50 RPM |
| Throughput efetivo | ~30 análises/min | ~3 análises/min |
| Disponibilidade (SLA) | 99.9% | 99.5% |

**Mitigação de latência:** Processamento 100% assíncrono via RabbitMQ — o usuário faz upload, recebe jobId imediatamente, e consulta o resultado quando pronto. A latência do LLM não bloqueia nenhuma operação do usuário.

#### Limitações Conhecidas do Modelo Escolhido

| Limitação | Impacto Real | Mitigação Implementada |
|-----------|--------------|------------------------|
| **Alucinação** — inventa componentes não visíveis | Relatório com dados incorretos | Prompt: "identify only REAL visible components"; guardrails limitam a 10 itens |
| **Inconsistência** — resultados variam entre chamadas | Não-determinismo no relatório | Guardrails garantem formato válido; variação aceita como trade-off |
| **Limite visual** — diagramas com 50+ componentes | Omissão de componentes | PDF limitado a 3 páginas; documentação clara da limitação |
| **Resolução** — imagens <300px degradam análise | Componentes ilegíveis ignorados | Pré-processamento com DPI 150 (fallback 100) |
| **Viés arquitetural** — favorece microserviços e cloud | "Projeta" padrões populares | Prompt neutro; resultado como sugestão |
| **Sem contexto de negócio** — desconhece o domínio | Riscos e recomendações genéricos | Aceito no MVP; futuro: input contextual |
| **Custo acumulado** — cada chamada consome tokens | Custo operacional crescente | max_tokens=2048; limite de 3 páginas PDF |
| **Rate limit** — provedores limitam RPM | Indisponibilidade sob carga | Retry com backoff; alternância de provider |

---

## 4. Como a IA é Acionada

### 4.1 Trigger da Análise

A IA é acionada **exclusivamente via evento assíncrono**. O fluxo é:

```
1. Orchestrator publica AnalysisRequestedEvent no RabbitMQ
   e atualiza o Job para status "Processing"
   {
     "jobId": "guid",
     "filePath": "uploads/{guid}/{filename}",
     "requestedAt": "timestamp"
   }

2. Analysis Service (Python) consome o evento via aio-pika

3. Pipeline de processamento:
   a) Download do arquivo do MinIO
   b) Pré-processamento (PDF→PNG ou encode base64)
   c) Chamada ao LLM com system prompt + imagem(ns)
   d) Validação da resposta (guardrails)
   e) Publicação do evento de resultado
```

### 4.2 System Prompt Utilizado

```
You are a software architecture expert analyzing architecture diagrams.
RULES:
1. Respond with VALID JSON ONLY
2. Use exact schema: { components[], risks[], recommendations[] }
3. Identify only REAL visible architectural components
4. Risks: technical and specific
5. Recommendations: actionable
6. Minimum 1, maximum 10 items per list

GUARDRAIL: If not an architecture diagram, return:
{
  components: ["Content not identified as architecture diagram"],
  risks: ["Invalid input for architectural analysis"],
  recommendations: ["Submit a valid software architecture diagram"]
}
```

### 4.3 Parâmetros da Chamada

| Parâmetro | Valor | Justificativa |
|-----------|-------|---------------|
| `max_tokens` | 2048 | Suficiente para JSON com 10 itens por lista |
| `detail` (OpenAI) | "high" | Melhor reconhecimento de texto em diagramas |
| PDF max pages | 3 | Controle de custo e latência |
| Image DPI | 150 (fallback 100) | Balanço entre qualidade e tamanho |

---

## 5. Como o Sistema Trata Falhas da IA

### 5.1 Estratégia de Retry

```python
MAX_RETRIES = 3
BASE_DELAY = 2 seconds

Para cada tentativa:
  try:
    response = llm.call(images, prompt)
    validated = guardrails.validate(response)
    if validated:
      return validated
  except RateLimitError:
    delay = BASE_DELAY * attempt * 2  # Exponential backoff
    sleep(delay)
  except (BadRequestError, APIError, Exception):
    delay = BASE_DELAY
    sleep(delay)

Se todas as tentativas falharem:
  publish(AnalysisFailedEvent { reason: "erro detalhado" })
```

### 5.2 Tipos de Falha Tratados

| Tipo de Falha | Comportamento | Resultado |
|---------------|---------------|-----------|
| Rate limit do LLM | Retry com backoff exponencial (2s, 4s, 6s) | Recuperação automática |
| Resposta JSON inválida | Retry (modelo pode gerar JSON válido na próxima) | Recuperação ou falha |
| Timeout do LLM | Retry com delay fixo | Recuperação ou falha |
| Schema inválido (campos faltando) | Descarta resposta, retry | Recuperação ou falha |
| Validação Pydantic falha | Tenta sanitizar; se impossível, falha | Degradação controlada |
| Todas tentativas esgotadas | Publica `AnalysisFailedEvent` | Job marcado como `Failed` |
| Exceção não prevista | Captura genérica, publica falha | Sem dados corrompidos |

### 5.3 Garantias

- **Nunca persiste dados inválidos:** Todo resultado passa por validação Pydantic antes de ser publicado
- **Nunca silencia falhas:** Toda falha resulta em evento explícito (`AnalysisFailedEvent`)
- **Status sempre reflete a realidade:** O Orchestrator atualiza o Job para `Failed` com a mensagem de erro
- **Dead Letter Queue:** MassTransit move mensagens irrecuperáveis para DLQ automaticamente

---

## 6. Como o Resultado da IA é Persistido

### 6.1 Fluxo de Persistência

```
Analysis Service                  Orchestrator                Report Service
     │                                │                           │
     │ AnalysisCompletedEvent         │                           │
     │ { components, risks,           │                           │
     │   recommendations }            │                           │
     ├───────────────────────────────▶│                           │
     │                                │ Atualiza Job status       │
     │                                │ → "Analyzed"              │
     │                                │                           │
     │                                │ GenerateReportCommand     │
     │                                │ { components, risks,      │
     │                                │   recommendations }       │
     │                                ├──────────────────────────▶│
     │                                │                           │
     │                                │              Cria Report  │
     │                                │              entity no    │
     │                                │              report_db    │
     │                                │                           │
```

### 6.2 Estrutura de Persistência

**Tabela `Report` (PostgreSQL — report_db):**

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `Id` | GUID (PK) | Identificador único do relatório |
| `JobId` | GUID | Referência ao Job original |
| `Components` | TEXT (JSON) | Lista de componentes serializada |
| `Risks` | TEXT (JSON) | Lista de riscos serializada |
| `Recommendations` | TEXT (JSON) | Lista de recomendações serializada |
| `CreatedAt` | TIMESTAMP | Data de criação |

### 6.3 Formato de Armazenamento

Os resultados são armazenados como **strings JSON** nas colunas TEXT:

```json
{
  "components": "[\"API Gateway\", \"Upload Service\", \"PostgreSQL\", \"RabbitMQ\"]",
  "risks": "[\"Single Point of Failure no Gateway\", \"Sem circuit breaker\"]",
  "recommendations": "[\"Adicionar redundância\", \"Implementar circuit breaker\"]"
}
```

**Justificativa:** Flexibilidade para evolução do schema sem migrações; consultas sempre retornam o relatório completo.

---

## 7. Como o Relatório é Gerado a Partir da Análise

### 7.1 Pipeline Completo

```
1. ENTRADA
   Diagrama (PNG/JPG/PDF) → Upload Service → MinIO

2. PRÉ-PROCESSAMENTO (Analysis Service)
   PDF: PyMuPDF converte até 3 páginas para PNG (150 DPI)
   Imagem: Encode direto para base64

3. ANÁLISE (LLM com Vision)
   System prompt + imagem(ns) → GPT-4o ou Claude
   Resposta: JSON com components[], risks[], recommendations[]

4. VALIDAÇÃO (Guardrails)
   - Extração de JSON (suporta markdown blocks)
   - Validação de schema (campos obrigatórios)
   - Validação Pydantic:
     • Máximo 20 itens por lista
     • Máximo 500 caracteres por item
     • Itens vazios removidos
     • Todos convertidos para string

5. TRANSPORTE (RabbitMQ)
   AnalysisCompletedEvent → Orchestrator → GenerateReportCommand → Report Service

6. PERSISTÊNCIA (Report Service)
   Cria entidade Report com os dados validados
   Armazena no PostgreSQL (report_db)

7. CONSUMO (API)
   GET /api/report/{jobId}
   Retorna JSON com listas deserializadas
```

### 7.2 Transformações dos Dados

| Etapa | Input | Output | Transformação |
|-------|-------|--------|---------------|
| Upload | Arquivo binário | Objeto MinIO | Armazenamento com path único |
| Pré-processamento | PDF/Imagem | Base64 PNG(s) | Conversão e resize |
| LLM | Imagem + Prompt | Texto (JSON) | Análise semântica visual |
| Guardrails | JSON bruto | Dados validados | Sanitização e truncamento |
| Persistência | Listas Python | JSON strings | Serialização |
| API Response | JSON strings | Listas JSON | Deserialização |

---

## 8. Discussão de Limitações do Modelo

### 8.1 Limitações Técnicas do LLM

| Limitação | Impacto | Mitigação |
|-----------|---------|-----------|
| **Alucinação** | Pode inventar componentes não presentes no diagrama | Prompt instrui a identificar apenas componentes "REAIS visíveis" |
| **Inconsistência** | Mesma imagem pode gerar resultados diferentes entre chamadas | Guardrails garantem formato mínimo válido |
| **Limite de contexto visual** | Diagramas muito densos podem ter partes ignoradas | Limitação a 3 páginas PDF; documentação para o usuário |
| **Dependência de resolução** | Imagens de baixa qualidade degradam a análise | Pré-processamento com DPI controlado |
| **Viés de treinamento** | Pode favorecer padrões de arquitetura comuns | Prompt neutro; resultado como sugestão, não verdade absoluta |
| **Latência** | 5-30 segundos por chamada ao LLM | Processamento assíncrono; usuário consulta status |
| **Custo** | Cada análise consome tokens da API | Limite de páginas e max_tokens definidos |

### 8.2 Limitações da Abordagem

| Limitação | Descrição |
|-----------|-----------|
| **Não interativa** | O usuário não pode pedir esclarecimentos ou refinamentos da análise |
| **Single-pass** | Não há iteração sobre o resultado (o modelo analisa uma vez) |
| **Sem memória** | Cada análise é independente; não há contexto de análises anteriores |
| **Sem validação humana no loop** | O resultado vai direto para o relatório sem revisão |
| **Escopo fixo** | Sempre retorna components/risks/recommendations; não é customizável |

### 8.3 Quando o Modelo Pode Falhar

- Diagramas desenhados à mão com caligrafia ilegível
- Diagramas com texto em idiomas não-latinos
- Screenshots de baixa resolução ou com artefatos de compressão
- Imagens que não são diagramas de arquitetura (o guardrail detecta isso)
- Diagramas com mais de 50 componentes (pode omitir alguns)

---

## 9. Segurança

### 9.1 Requisitos Básicos de Segurança Adotados

| Requisito | Implementação |
|-----------|---------------|
| **Validação de entrada** | FluentValidation verifica extensão (.pdf/.png/.jpg/.jpeg) e tamanho (≤10MB) |
| **Isolamento de dados** | Database-per-service: upload_db, orchestrator_db, report_db |
| **Credenciais seguras** | Variáveis de ambiente; nenhum secret no código-fonte |
| **Princípio do menor privilégio** | Analysis Service não expõe porta; acesso somente via fila |
| **Logging auditável** | Serilog + Seq com logs estruturados para todos os serviços |
| **Rede isolada** | Serviços comunicam pela rede Docker interna |

### 9.2 Validação e Tratamento de Entradas Não Confiáveis

#### Upload de Arquivos

```
Camada 1: Gateway (YARP)
  └── Roteamento, sem processamento de conteúdo

Camada 2: Upload Service (Validação)
  ├── Extensão permitida: .pdf, .png, .jpg, .jpeg
  ├── Tamanho máximo: 10 MB
  ├── Stream não pode ser nula
  └── Content-Type verificado

Camada 3: MinIO (Armazenamento)
  ├── Arquivo armazenado com GUID único (path traversal impossível)
  └── Bucket isolado (uploads)

Camada 4: Analysis Service (Processamento)
  ├── Tipo verificado antes do processamento
  ├── PDF: apenas primeiras 3 páginas processadas
  └── Imagem: tamanho controlado via DPI
```

#### Tratamento de Respostas do LLM

```
Camada 1: Extração JSON
  └── Regex para extrair JSON de markdown blocks ou texto livre

Camada 2: Schema Validation
  └── Verifica campos obrigatórios (components, risks, recommendations)

Camada 3: Pydantic Model
  ├── Tipo: cada item deve ser string
  ├── Comprimento: máximo 500 caracteres por item
  ├── Cardinalidade: máximo 20 itens por lista
  └── Sanitização: itens vazios removidos

Camada 4: Serialização Segura
  └── json.dumps() com dados já validados antes de persistir
```

### 9.3 Uso Controlado de Modelos de IA

#### Escopo Definido

| Aspecto | Controle |
|---------|----------|
| **Tarefa** | Exclusivamente análise de diagramas de arquitetura |
| **Output** | Formato JSON rígido com 3 campos: components, risks, recommendations |
| **Input** | Apenas imagens provenientes de uploads validados |
| **Interação** | Zero interação direta do usuário com o LLM |
| **Prompt** | System prompt fixo, não alterável pelo usuário |

#### Previsibilidade das Respostas

- **Schema obrigatório:** O LLM é instruído a retornar exclusivamente JSON com estrutura definida
- **Guardrail para inputs inválidos:** Resposta pré-definida para imagens que não são diagramas
- **Limites numéricos:** 1-10 itens por lista (instrução), validados para 1-20 (guardrail)
- **Truncamento:** Itens maiores que 500 caracteres são cortados automaticamente
- **Sem execução de código:** O output do LLM é tratado como dados, nunca como código executável

#### Prevenção de Prompt Injection

- O usuário **não tem acesso ao prompt do sistema** nem pode modificá-lo
- O input do usuário é uma **imagem**, não texto — minimiza risco de injection
- A resposta do LLM **nunca é executada** como código ou comando
- PDFs com texto embutido: apenas as imagens das páginas são enviadas, não o texto extraído

### 9.4 Tratamento Seguro de Falhas da IA

| Cenário de Falha | Tratamento | Garantia |
|------------------|------------|----------|
| LLM retorna texto livre (não JSON) | Retry; se persistir, AnalysisFailedEvent | Sem dados corrompidos no banco |
| LLM retorna JSON com campos extras | Pydantic ignora campos não-mapeados | Dados estritamente tipados |
| LLM retorna lista vazia | Validação rejeita; retry | Relatório nunca vazio |
| LLM timeout | Retry com backoff; eventual FailedEvent | Job marcado como Failed |
| LLM indisponível | 3 retries; publica falha | Status reflete realidade |
| Resposta com conteúdo ofensivo | Passa para o relatório como texto | Limitação aceita no MVP |
| API key inválida/expirada | Falha imediata com erro claro | Administrador notificado via logs |

**Princípio fundamental:** A falha da IA **nunca** resulta em dados parciais ou corrompidos no banco de dados. Ou o resultado completo e validado é persistido, ou o Job é marcado como `Failed`.

### 9.5 Segurança na Comunicação Entre Serviços

| Mecanismo | Descrição |
|-----------|-----------|
| **Rede Docker isolada** | Serviços comunicam por rede bridge interna, não acessível externamente |
| **Portas mínimas expostas** | Apenas Gateway (:5010) exposto ao host; serviços internos acessíveis só via rede Docker |
| **Mensagens persistentes** | RabbitMQ configurado com delivery_mode=2 (mensagens sobrevivem a reinícios) |
| **Filas duráveis** | Filas não são perdidas em caso de reinício do broker |
| **Formato de mensagem padronizado** | MassTransit envelope com type, messageId, correlationId |
| **Sem serialização arbitrária** | Contratos de eventos definidos em biblioteca Shared, fortemente tipados |
| **Health checks** | Todos os serviços de infraestrutura possuem health checks configurados |

### 9.6 Riscos e Limitações de Segurança Identificados

#### Riscos Aceitos (MVP)

| Risco | Severidade | Justificativa para Aceitação |
|-------|-----------|-------------------------------|
| Sem autenticação nos endpoints | Alta | MVP interno; deve ser adicionado antes de produção |
| Sem rate limiting | Média | Ambiente controlado; necessário antes de exposição pública |
| Sem TLS entre serviços internos | Média | Rede Docker isolada; necessário se houver multi-host |
| Credenciais padrão na infraestrutura | Média | Ambiente de desenvolvimento; trocar em produção |
| Sem CORS configurado | Baixa | Gateway não serve frontend diretamente no MVP |
| Sem audit log de acessos | Baixa | Logs estruturados cobrem parcialmente; dedicar recurso futuro |

#### Recomendações para Produção

1. **Autenticação:** Implementar OAuth2/JWT no Gateway com validação em cada serviço
2. **Rate Limiting:** Adicionar rate limiting no Gateway (ex: 10 uploads/minuto por usuário)
3. **TLS Interno:** Configurar mTLS entre serviços ou usar service mesh
4. **Secrets Management:** Migrar para Vault ou Azure Key Vault
5. **Scan de Malware:** Verificar arquivos uploaded antes do processamento
6. **WAF:** Adicionar Web Application Firewall antes do Gateway
7. **Backup:** Configurar backup automatizado dos bancos PostgreSQL
8. **Monitoring:** Alertas para falhas consecutivas do LLM (podem indicar problema sistêmico)

---

## 10. Instruções de Execução

### Pré-requisitos

- Windows 10/11
- Docker Desktop para Windows instalado e rodando
- Chave de API: OpenAI (GPT-4o) ou Anthropic (Claude)
- 4GB+ de RAM disponível para os containers

### Passo a Passo

```powershell
# 1. Clonar o repositório
git clone <url-do-repositorio>
cd Hackton

# 2. Configurar variáveis de ambiente
cp .env.example docker/.env
# Editar docker/.env com sua API key

# 3. Subir todos os serviços
docker compose -f docker/docker-compose.yml up -d --build

# Ou via script PowerShell:
.\scripts\start.ps1

# 4. Verificar saúde do sistema
curl http://localhost:5010/health

# 5. Fazer upload de um diagrama
curl -X POST http://localhost:5010/api/upload -F "file=@diagrama.png"

# 6. Consultar status (usar o jobId retornado)
curl http://localhost:5010/api/status/{jobId}

# 7. Obter relatório (quando status = "Analyzed")
curl http://localhost:5010/api/report/{jobId}
```

### Variáveis de Ambiente Obrigatórias

```env
LLM_PROVIDER=openai          # ou "claude"
OPENAI_API_KEY=sk-proj-...   # se LLM_PROVIDER=openai
CLAUDE_API_KEY=sk-ant-...    # se LLM_PROVIDER=claude
```

### Interfaces de Gerenciamento

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| RabbitMQ | http://localhost:15672 | hackton / hackton123 |
| MinIO | http://localhost:9001 | hackton / hackton123 |
| Seq (Logs) | http://localhost:8081 | admin / hackton123 |

---

## 11. Stack Tecnológica

| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| Gateway | .NET 9 + YARP | 2.2 |
| Microserviços | .NET 9 Minimal APIs | — |
| Serviço de IA | Python | 3.12 |
| Mensageria | RabbitMQ + MassTransit | 3.x / 8.4 |
| Banco de Dados | PostgreSQL | 16 |
| Object Storage | MinIO | Latest |
| Logging | Serilog + Seq | — |
| Validação (.NET) | FluentValidation | 11 |
| CQRS | MediatR | 12.4 |
| ORM | Entity Framework Core | 9 |
| IA (OpenAI) | openai SDK | 1.57.0 |
| IA (Claude) | anthropic SDK | 0.40.0 |
| PDF Processing | PyMuPDF | 1.25.1 |
| Guardrails | Pydantic | 2.10.4 |
| Containerização | Docker Compose | — |

---

## 12. Conclusão

A solução demonstra uma abordagem pragmática para integração de IA em sistemas distribuídos, priorizando:

1. **Confiabilidade** sobre velocidade — processamento assíncrono com validação rigorosa
2. **Previsibilidade** sobre flexibilidade — output estruturado com guardrails
3. **Observabilidade** sobre simplicidade — logging agregado e status rastreável
4. **Segurança** sobre conveniência — validação em múltiplas camadas, falha explícita

O sistema aceita suas limitações (MVP sem autenticação, dependência de APIs externas, escopo fixo de análise) e as documenta transparentemente, fornecendo um caminho claro para evolução em produção.
