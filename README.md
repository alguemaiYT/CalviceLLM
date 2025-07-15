# Grok-on-Pi: Assistente Inteligente Embarcado para Orange Pi

![Status: Em Desenvolvimento](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)

Um assistente inteligente modular e leve, projetado para rodar em hardware limitado como a Orange Pi PC. O projeto utiliza uma combinação de ferramentas locais e APIs para fornecer uma experiência de assistente ativada por voz, com reconhecimento facial para interações personalizadas.

## Tecnologias e Bibliotecas

O foco principal é a utilização de tecnologias leves e eficientes para garantir a performance no Orange Pi.

- **Hardware:** Orange Pi PC
- **Detecção de Wake Word:** [openWakeWord](https://github.com/dscripka/openWakeWord) - uma solução leve e de código aberto para detecção de wake word.
- **Speech-to-Text (STT):**
  - **Local:** [faster-whisper](https://github.com/guillaumekln/faster-whisper) - uma implementação otimizada do Whisper da OpenAI para rodar em CPU.
  - **API:** [Gladia API](https://gladia.io/) - como alternativa para transcrição na nuvem.
- **Processamento de Linguagem Natural (LLM):** [API do Grok](https://grok.x.ai/) - para geração de respostas inteligentes.
- **Reconhecimento Facial:** [OpenCV](https://opencv.org/) - para detecção e reconhecimento de rostos.
- **Text-to-Speech (TTS):** (A ser definido) - em busca de uma solução leve, possivelmente baseada em [espeak-ng](https://github.com/espeak-ng/espeak-ng) ou similar.

## Arquitetura do Sistema

O sistema é projetado para ser modular, com cada componente rodando como um script separado.

```
Entrada de Áudio --> [Wake Word Detection] --ativa--> [Speech-to-Text] --> "Texto Transcrito" --> [API do Grok] --> "Resposta Gerada" --> [Text-to-Speech / Saída de Texto]
```

Paralelamente, a câmera está sempre ativa:

```
Entrada de Vídeo --> [Reconhecimento Facial com OpenCV] --> Identifica Usuário --> Carrega Contexto/Personalidade --> Informa a Lógica Principal
```

## Instruções de Instalação (Orange Pi)

**Pré-requisitos:**
- Orange Pi PC com uma imagem de sistema operacional baseada em Debian (ex: Armbian).
- Microfone USB e Câmera USB conectados.
- Acesso à internet.

**Passo a passo:**

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/seu-usuario/grok-on-pi.git
   cd grok-on-pi
   ```

2. **Crie e ative um ambiente virtual:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Instale as dependências:**
   *As dependências exatas serão listadas no arquivo `requirements.txt`.*
   ```bash
   pip install -r requirements.txt
   ```
   *Nota: A instalação do OpenCV e outras bibliotecas pode exigir dependências de sistema. Consulte a documentação de cada uma para obter instruções detalhadas.*

## Como Rodar

Cada funcionalidade principal é um script separado. Você precisará de múltiplos terminais para rodá-los em paralelo.

1. **Terminal 1: Wake Word Detection**
   ```bash
   python wake_word_detector.py
   ```
   *Este script escutará o microfone e, ao detectar a wake word, acionará o script de STT.*

2. **Terminal 2: Speech-to-Text**
   *Este script será acionado pelo detector de wake word.*

3. **Terminal 3: Reconhecimento Facial**
   ```bash
   python facial_recognition.py
   ```
   *Este script monitora a câmera, identifica rostos e disponibiliza a identidade do usuário para os outros módulos.*

## Adicionando Novos Rostos

Para adicionar um novo rosto ao sistema:

1. **Crie uma ficha de personalidade:**
   Adicione um novo arquivo JSON em `data/faces/` com o nome da pessoa (ex: `ana.json`).
   ```json
   {
     "nome": "Ana",
     "personalidade": "amigável e curiosa",
     "contexto": "colega de trabalho, especialista em marketing"
   }
   ```

2. **Capture as imagens do rosto:**
   Execute o script de captura de imagens, que salvará as fotos no diretório `data/faces/<nome>/`.
   ```bash
   python capture_faces.py --nome ana
   ```
   *Tire várias fotos com diferentes ângulos e iluminações.*

3. **Treine o modelo de reconhecimento:**
   Execute o script de treinamento para que o sistema aprenda a reconhecer o novo rosto.
   ```bash
   python train_model.py
   ```

## Considerações de Performance

- **Hardware Limitado:** A Orange Pi PC não possui GPU dedicada. Todas as operações são otimizadas para CPU.
- **Scripts Modulares:** A separação dos scripts permite que cada processo utilize os recursos de forma mais eficiente.
- **Otimizações:**
  - `faster-whisper` é usado no lugar do Whisper original por ser mais rápido e consumir menos memória.
  - A detecção de wake word é feita localmente com uma ferramenta de baixo consumo para evitar o uso constante de recursos mais pesados.
- **Latência (Testes Iniciais):**
  - Latência "raw" do script `grok_request.py` (sem criação de sockets):
    - ⏱️ Imports: 4.302278280258179s
    - ⏱️ Instanciação do client: 0.5843939781188965s

## Roadmap

- [ ] Implementar o script de Text-to-Speech (TTS).
- [ ] Integrar a base de dados de rostos com a lógica principal para personalizar as respostas do Grok.
- [ ] Criar um script principal para orquestrar a inicialização de todos os módulos.
- [ ] Melhorar a comunicação entre os scripts (ex: usando MQTT ou um sistema de filas leve).
- [ ] Adicionar mais testes e documentação.

## Licença

Este projeto está licenciado sob a [Licença MIT](LICENSE).
