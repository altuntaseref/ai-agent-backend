# AI Agent Projesi

Bu proje, Postman koleksiyonlarını işleyebilen ve Jenkins CI/CD araçlarıyla entegre çalışabilen gelişmiş bir AI agent sistemidir.

## 🚀 Özellikler

### 1. Postman Koleksiyon İşleme
- Postman koleksiyonlarını analiz edebilme
- Koleksiyonlardan proje oluşturabilme
- API endpoint'lerini otomatik tespit edebilme

### 2. Jenkins CI/CD Entegrasyonu
- Pipeline oluşturma
- Pipeline tetikleme
- Pipeline durumu sorgulama
- Uygulama sağlık kontrolü

## 🛠️ Araçlar (Tools)

### 1. Project Generator Tool
- **Amaç**: Postman koleksiyonlarından proje oluşturma
- **Kullanım**: `project_generator` aracı ile koleksiyon analizi ve proje oluşturma
- **Gerekli Parametreler**: `collectionUrl` (Postman koleksiyon URL'si)

### 2. Jenkins Pipeline Araçları
- **Create Pipeline Tool**
  - Pipeline oluşturma
  - Gerekli parametre: `jobName`
  
- **Trigger Pipeline Tool**
  - Mevcut pipeline'ı tetikleme
  - Gerekli parametre: `jobName`
  
- **Pipeline Status Tool**
  - Pipeline durumunu sorgulama
  - Gerekli parametre: `jobName`

### 3. App Health Check Tool
- Uygulama sağlık durumunu kontrol etme
- Uygulama URL'sini görüntüleme
- Gerekli parametre: `appName`

## 💡 Prompt Sistemi

### 1. Sistem Promptları
- `SYSTEM_PROMPT`: Agent'ın temel davranış ve yeteneklerini tanımlar
- `PROJECT_GENERATOR_PROMPT`: Proje oluşturma sürecini yönetir
- `JENKINS_PIPELINE_PROMPT`: Jenkins pipeline işlemlerini yönetir
- `APP_HEALTH_CHECK_PROMPT`: Uygulama sağlık kontrolü için yönergeler
- `APP_URL_CHECK_PROMPT`: Uygulama URL sorguları için yönergeler

### 2. Hata Yönetimi
- `API_ERROR_PROMPT`: API hatalarını kullanıcıya anlaşılır şekilde iletir
- `COLLECTION_ERROR_PROMPT`: Koleksiyon işleme hatalarını yönetir

## 🔧 Kurulum

1. Gerekli bağımlılıkları yükleyin:
```bash
pip install -r requirements.txt
```

2. `.env` dosyasını oluşturun:
```env
JENKINS_API_BASE_URL=http://localhost:8080
```

3. Uygulamayı başlatın:
```bash
python main.py
```

## 📝 Kullanım Örnekleri

### 1. Proje Oluşturma
```
"Bu Postman koleksiyonundan bir proje oluştur: [koleksiyon URL'si]"
```

### 2. Pipeline İşlemleri
```
"customer-service için bir pipeline oluştur"
"customer-service pipeline'ını tetikle"
"customer-service pipeline'ının durumunu kontrol et"
```

### 3. Sağlık Kontrolü
```
"customer-service uygulamasının sağlık durumunu kontrol et"
"customer-service uygulamasının URL'sini göster"
```

## 🔍 API Endpoint'leri

### Jenkins API
- Pipeline Oluşturma: `POST /api/v1/jenkins/create/pipeline`
- Pipeline Tetikleme: `POST /api/v1/jenkins/trigger/{jobName}`
- Pipeline Durumu: `GET /api/v1/jenkins/status/{jobName}`

### Sağlık Kontrolü API
- Uygulama Sağlık Kontrolü: `GET /api/v1/app-health/check/{appName}`

## ⚠️ Hata Yönetimi

Sistem, aşağıdaki hata durumlarını yönetir:
- API bağlantı hataları
- Geçersiz parametreler
- Zaman aşımı durumları
- JSON parse hataları

## 🔄 Geliştirme

### Yeni Tool Ekleme
1. `tools` klasöründe yeni tool sınıfı oluşturun
2. `main.py`'da tool'u kaydedin
3. `prompts.py`'da gerekli prompt'ları ekleyin

### Yeni Prompt Ekleme
1. `prompts.py`'da yeni prompt tanımlayın
2. İlgili tool ile entegre edin
3. Sistem prompt'una ekleyin

## 📚 Bağımlılıklar

- langchain
- pydantic
- requests
- fastapi
- uvicorn
- python-dotenv

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'feat: Add amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun 