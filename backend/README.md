# Yazılım Geliştirme AI Agent

Bu proje, yazılım geliştirme süreçlerini otomatikleştirmek amacıyla Python ve LangChain kullanılarak geliştirilmiş bir AI Agent backend'idir.

## Özellikler (Planlanan)

*   Doğal dil komutlarını anlama.
*   Harici araçları (API'ler, script'ler) kullanarak görevleri yerine getirme:
    *   Kod oluşturma
    *   CI/CD süreçlerini tetikleme
    *   Logları analiz etme
*   Genişletilebilir araç mimarisi.
*   Konuşma geçmişi.
*   (İleride) FastAPI/Flask ile REST API sunucusu.
*   (İleride) Basit bir web arayüzü.

## Kurulum

1.  **Depoyu klonlayın:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```
2.  **Sanal ortam oluşturun ve aktive edin (önerilir):**
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```
3.  **Gereksinimleri yükleyin:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Ortam değişkenlerini ayarlayın:**
    *   Proje kök dizininde `.env` adında bir dosya oluşturun.
    *   `.env` dosyasına gerekli API anahtarlarını ekleyin. Örnek:
        ```
        # LLM Ayarları (OpenAI veya Gemini kullanın)
        LLM_PROVIDER=openai # veya gemini
        OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        GOOGLE_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # Araç API Ayarları (Gerektiğinde ekleyin)
        # CODE_GENERATOR_API_URL=https://api.example.com/codegen
        # CI_CD_API_URL=https://api.jenkins.example.com
        # LOG_ANALYZER_API_URL=https://logs.example.com/api
        ```

## Kullanım

Backend'i komut satırından çalıştırmak için:

```bash
cd backend
python main.py
```

Agent hazır olduğunda komutlarınızı yazabilirsiniz. 