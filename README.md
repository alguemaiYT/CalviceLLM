# Grok-on-Pi: Assistente Inteligente Embarcado

*Um projeto de pesquisa e desenvolvimento em sistemas embarcados, nascido no [IFSP-Sorocaba](https://sor.ifsp.edu.br/) com o apoio institucional do grupo de robótica [DragonBotz (G.E.R.A.)](https://www.instagram.com/dragonbotz/).*

![Status: Em Desenvolvimento](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)

## Visão Geral

O Grok-on-Pi é um assistente de voz projetado para rodar em hardware de baixo custo e recursos limitados, como a **Orange Pi PC**. A principal filosofia do projeto é a **modularidade** e a **eficiência**, permitindo que cada componente (wake word, STT, LLM, TTS) seja executado de forma independente e otimizada para a arquitetura ARMv7.

Este projeto, embora desenvolvido de forma independente, contou com o apoio institucional não-oficial e o incentivo da equipe DragonBotz, com colaboração especial de Heiton Curto Gomes. A iniciativa nasceu dentro de um ambiente de pesquisa em robótica educacional e sistemas embarcados.

## Arquitetura e Fluxo de Execução

O sistema opera em um pipeline claro e desacoplado:

1.  **Detecção de Wake Word:** O sistema é ativado por uma palavra-chave, detectada localmente por uma ferramenta leve como `openWakeWord`.
2.  **Speech-to-Text (STT):** O áudio capturado é enviado para a **API do Google Cloud Speech-to-Text**, que oferece alta precisão e baixo impacto no hardware local. *Nota: A solução inicial com `faster-whisper` foi descontinuada devido a problemas de compatibilidade e performance na arquitetura ARMv7.*
3.  **Processamento de Linguagem (LLM):** O texto transcrito é enviado para a **API do Grok**, que gera a resposta.
4.  **Text-to-Speech (TTS):** A resposta textual é convertida em áudio (em desenvolvimento).
5.  **Reconhecimento Facial (Paralelo):** Uma thread separada utiliza `OpenCV` para detectar e reconhecer rostos, permitindo interações personalizadas com base em um banco de dados local.

## Stack de Tecnologias

-   **Hardware Primário:** Orange Pi PC (ARMv7-A Cortex-A7)
-   **Sistema Operacional:** Linux customizado (baseado em `buildroot` e `crosstool-ng`) com otimizações de compilação (`-O3`, `-mfpu=neon-vfpv4`, `-mfloat-abi=hard`).
-   **Wake Word:** `openWakeWord`
-   **Speech-to-Text (STT):** Google Cloud Speech-to-Text API
-   **LLM:** Grok API (via `x.ai`)
-   **Reconhecimento Facial:** `OpenCV`
-   **TTS (em avaliação):** `piper_tts`, `rhvoice`, `espeak-ng`

## Estrutura do Projeto

O repositório é organizado em fases, representando cada módulo do pipeline:

```
/
├── Wake Word Detection/
│   └── openwakeword/
├── Speech to Text/
│   ├── google_cloud_stt/
│   └── ibm_cloud_stt/
├── Language Model/
│   └── grok_api/
├── Text to Speech/
│   └── ...
└── README.md
```

Cada subdiretório contém um `README.md` específico e scripts de exemplo.

## Histórico de Desenvolvimento

### Fase 0: Prototipagem e Otimização do Ambiente

-   **Desde o início do projeto:** Foco na criação de um ambiente de desenvolvimento otimizado para a Orange Pi PC. Isso envolveu a construção de uma toolchain de **cross-compilação com `-O3`**, ajustes de `CFLAGS`/`LDFLAGS` e a configuração de um `sysroot` com `crosstool-ng` e `buildroot`. Foram aplicados patches no kernel e reconfigurado o GCC para a arquitetura ARMv7-A com `floating point hard`.
-   **Protótipos iniciais:** Os primeiros testes revelaram problemas de compilação e instabilidade com bibliotecas otimizadas apenas para x86, exigindo uma abordagem mais customizada.

### Fase 1: Testes, Integração e Versionamento

-   **07/06/2025:** Início dos testes de soluções de STT. A avaliação de modelos locais como `faster-whisper` mostrou-se inviável, levando à decisão de usar APIs na nuvem.
-   **08/06/2025:** Tentativa de integração com o Home Assistant, abandonada pela falta de suporte a ARMv7 na comunidade de addons.
-   **20/06/2025:** Estruturação do projeto no GitHub para controle de versão.
-   **24/06/2025:** Refatoração do ambiente com base nos aprendizados, melhorando a modularidade.
-   **16/06/2025 - 17/06/2025:** Aquisição e configuração dos serviços de API do Google Cloud (Speech-to-Text) e Grok (LLM).
-   **19/07/2025:** Conclusão da primeira versão do algoritmo de wake word, com a integração do **Porcupine Picovoice**, escolhido por sua alta precisão. O processo exigiu a compilação de toolchains e uma cross-compilação para ARMv7 com suporte a NEON.

## Licença

Este projeto está licenciado sob a [Licença MIT](LICENSE).
