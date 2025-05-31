import requests
import json
import os
from datetime import datetime
import time
import random

start_time = datetime.now()
print(f"İşlem başlangıç zamanı: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

# Yeni dosya adı ve tarihi içeren benzersiz bir isim oluştur
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file_path = f'trainset_qa_{timestamp}.json'
print(f"Oluşturulan soru-cevap çiftleri '{output_file_path}' dosyasına kaydedilecek.")

# Güvenli dosya yazma fonksiyonu
def safe_write_to_file(data, file_path):
    """
    Verileri önce geçici dosyaya yazar, başarılı olursa hedef dosyaya taşır.
    """
    try:
        # Geçici dosya adı oluştur
        temp_file = file_path + '.temp'
        
        # Geçici dosyaya yaz
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Başarılı yazma kontrolü
        if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
            # Geçici dosyayı hedef dosyaya taşı
            if os.path.exists(file_path):
                os.replace(temp_file, file_path)  # Varsa üzerine yaz
            else:
                os.rename(temp_file, file_path)
            
            print(f"Veriler başarıyla '{file_path}' dosyasına kaydedildi.")
            return True
        else:
            print(f"HATA: Geçici dosya yazılamadı veya boş: {temp_file}")
            return False
    except Exception as e:
        print(f"Dosya yazma hatası: {str(e)}")
        return False

# Tüm soru-cevap çiftlerini saklamak için ana liste
all_qa_pairs = []

# Giriş dosyası kontrolü (PreLidPreLim.json)
train_file_path = 'PreLidPreLim.json'
if not os.path.exists(train_file_path) or os.path.getsize(train_file_path) == 0:
    with open(train_file_path, 'w', encoding='utf-8') as file:
        json.dump({"paragraphs": []}, file, ensure_ascii=False, indent=2)
    print(f"{train_file_path} dosyası oluşturuldu.")

# İlerleme durumu kontrolü ve oluşturma
progress_file = 'progress.txt'
last_processed = 0

if os.path.exists(progress_file):
    with open(progress_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        if content and content.isdigit():
            last_processed = int(content)
            print(f"Kaldığınız yerden devam ediliyor: Paragraf {last_processed + 1}")

# Giriş dosyasını oku
with open(train_file_path, 'r', encoding='utf-8') as file:
    try:
        data = json.load(file)
    except json.JSONDecodeError:
        print(f"{train_file_path} dosyasında JSON hatası. Temel yapı oluşturuluyor.")
        data = {"paragraphs": []}
        with open(train_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

# Bekle ve tekrar dene fonksiyonu
def wait_with_backoff(retry, base_wait=5, max_wait=300):
    """
    Üstel olarak artan bekleme süresi hesaplar
    """
    wait_time = min(base_wait * (2 ** retry) + random.uniform(0, 1), max_wait)
    print(f"{wait_time:.1f} saniye bekleniyor...")
    time.sleep(wait_time)

# API istek fonksiyonu
def make_api_request(paragraph_content, paragraph_id, max_retries=5):
    """
    LM Studio API'sine istek gönderir ve sonucu döndürür.
    Başarısız olursa tekrar dener.
    """
    truncated_content = paragraph_content
    # Çok uzun paragrafları kısalt
    if len(paragraph_content) > 1500:
        truncated_content = paragraph_content[:1500] + "..."
        print(f"Uyarı: Paragraf çok uzun ({len(paragraph_content)} karakter). Kısaltıldı.")
    
    for retry in range(max_retries):
        try:
            print(f"Paragraf {paragraph_id} için API isteği gönderiliyor (Deneme {retry+1}/{max_retries})...")
            
            # Sistem mesajı ile daha açık talimatlar
            response = requests.post(
                "http://127.0.0.1:1234/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": "qwen1.5-7b-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Generate 3-5 question-answer pairs from the given text. Format your response as a valid JSON array of objects, each with 'question', 'answer', and 'type' fields (types: factual, analytical, interpretative, contextual). Ensure your response is properly formatted JSON."
                        },
                        {
                            "role": "user",
                            "content": truncated_content
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 800
                },
                timeout=300  # 5 dakika
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"HTTP isteği başarısız: {response.status_code}")
                print(f"Yanıt içeriği: {response.text}")
                wait_with_backoff(retry)
                
        except requests.exceptions.Timeout:
            print(f"API isteği zaman aşımına uğradı (deneme {retry+1}/{max_retries})")
            if retry < max_retries - 1:
                wait_with_backoff(retry)
        except requests.exceptions.ConnectionError:
            print(f"Bağlantı hatası (deneme {retry+1}/{max_retries})")
            if retry < max_retries - 1:
                wait_with_backoff(retry)
        except Exception as e:
            print(f"API isteği sırasında hata: {str(e)}")
            if retry < max_retries - 1:
                wait_with_backoff(retry)
    
    return None

# Paragraflar varsa devam et
if "paragraphs" in data and len(data["paragraphs"]) > 0:
    paragraphs_count = len(data['paragraphs'])
    print(f"Toplam {paragraphs_count} paragraf işlenecek.")
    
    # Paragrafları ID'lerine göre sırala
    sorted_paragraphs = sorted(data["paragraphs"], 
                              key=lambda p: int(p["paragraph_id"].split("_")[1]) 
                              if p["paragraph_id"].startswith("para_") and p["paragraph_id"].split("_")[1].isdigit() 
                              else 0)
    
  # Her seferinde bir paragraf işle
for i, paragraph in enumerate(sorted_paragraphs, 1):
    paragraph_id = paragraph["paragraph_id"]
    para_num = int(paragraph_id.split("_")[1]) if paragraph_id.startswith("para_") and paragraph_id.split("_")[1].isdigit() else i
    
    # Eğer bu paragraf daha önce işlendiyse atla
    if para_num <= last_processed:
        print(f"Paragraf {para_num} daha önce işlenmiş, atlanıyor...")
        continue
    
    print(f"\n===== Paragraf {para_num}/{paragraphs_count} işleniyor =====")
    
    try:
        paragraph_content = paragraph["content"]
        
        # Modele gönderilecek içeriği sınırlandır
        if len(paragraph_content) < 10:  # Çok kısa içerikleri atla
            print(f"Paragraf {para_num} çok kısa, atlanıyor...")
            last_processed = para_num
            with open(progress_file, 'w', encoding='utf-8') as f:
                f.write(str(last_processed))
            continue
        
        # Her paragraf işlemesi arasında biraz bekle (sistem dinlensin)
        if i > 1:
            cooldown_time = random.randint(10, 20)  # 10-20 saniye arası rastgele bekleme
            print(f"Sistem dinlenmesi için {cooldown_time} saniye bekleniyor...")
            time.sleep(cooldown_time)
        
        # Model isteği
        response_data = make_api_request(paragraph_content, para_num)
        
        if response_data:
            content = response_data['choices'][0]['message']['content']
            print(f"Model yanıtı alındı.")
            
            try:
                # JSON içerik kontrolü ve temizleme
                content = content.strip()
                
                # JSON olmayan prefix/suffix'leri temizle
                if '[' in content and ']' in content:
                    start_idx = content.find('[')
                    end_idx = content.rfind(']') + 1
                    content = content[start_idx:end_idx]
                
                # JSON formatı için düzeltmeler
                content = content.replace("'", '"')
                content = content.replace('\n', ' ').replace('\r', '')
                
                # Dikkatli JSON parse etme
                try:
                    parsed = json.loads(content)
                except json.JSONDecodeError as e:
                    print(f"JSON ayrıştırma hatası: {e}")
                    print("Manuel JSON temizleme deneniyor...")
                    
                    # Daha güçlü JSON temizleme dene
                    import re
                    # JSON-benzeri içerikten sadece geçerli objeleri çıkar
                    objects = re.findall(r'\{.*?\}', content)
                    if objects:
                        try:
                            parsed = [json.loads(obj) for obj in objects]
                        except:
                            print("Objeleri ayrı ayrı ayrıştırma başarısız.")
                            # Son çare: manuel soru-cevap çıkarma
                            questions = re.findall(r'"question"\s*:\s*"([^"]+)"', content)
                            answers = re.findall(r'"answer"\s*:\s*"([^"]+)"', content)
                            types = re.findall(r'"type"\s*:\s*"([^"]+)"', content)
                            
                            if questions and answers:
                                parsed = []
                                for i in range(min(len(questions), len(answers))):
                                    q_type = types[i] if i < len(types) else "factual"
                                    parsed.append({
                                        "question": questions[i],
                                        "answer": answers[i],
                                        "type": q_type
                                    })
                            else:
                                print("Manuel ayrıştırma başarısız.")
                                raise
                    else:
                        raise
                
                # Ayrıştırılan veriyi ana listeye ekle
                if isinstance(parsed, list):
                    all_qa_pairs.extend(parsed)
                else:
                    all_qa_pairs.append(parsed)
                
                # Dosyaya düzenli olarak kaydet
                if safe_write_to_file(all_qa_pairs, output_file_path):
                    print(f"Şu ana kadar toplam {len(all_qa_pairs)} soru-cevap çifti kaydedildi.")
                
                print(f"Paragraf {para_num}/{paragraphs_count} için {len(parsed) if isinstance(parsed, list) else 1} soru-cevap çifti oluşturuldu.")
                
                # İlerleme durumunu güncelle
                last_processed = para_num
                with open(progress_file, 'w', encoding='utf-8') as f:
                    f.write(str(last_processed))
                
                # TEST İÇİN EKLE: Sadece bir paragrafı işledikten sonra döngüden çık
               #  break  Bu satırı test sonrası kaldırın
                
            except Exception as e:
                print(f"JSON işleme hatası: {str(e)}")
                print(f"Ham içerik:\n{content}")
                
                # Hata olsa bile ilerleme dosyasını güncelle
                last_processed = para_num
                with open(progress_file, 'w', encoding='utf-8') as f:
                    f.write(str(last_processed))
        else:
            print(f"Paragraf {para_num}/{paragraphs_count} için model yanıtı alınamadı.")
            
    except Exception as e:
        print(f"Paragraf {para_num} işlenirken beklenmeyen hata: {str(e)}")
else:
    print(f"{train_file_path} dosyasında hiç paragraf bulunamadı.")

# Son bir kez daha dosyaya yaz
if all_qa_pairs:
    if safe_write_to_file(all_qa_pairs, output_file_path):
        print(f"İşlem tamamlandı. Toplam {len(all_qa_pairs)} soru-cevap çifti kaydedildi.")
    else:
        print("UYARI: Son dosya yazma işlemi başarısız oldu!")

# Bitiş zamanını hesapla
end_time = datetime.now()
duration = end_time - start_time
duration_min = round(duration.total_seconds() / 60, 2)

print(f"\nİşlem bitiş zamanı: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Toplam süre: {duration_min} dakika")
print(f"Toplam işlenen paragraf sayısı: {last_processed}/{len(data['paragraphs']) if 'paragraphs' in data else 0}")
print(f"Soru-cevap çiftleri '{output_file_path}' dosyasına kaydedildi.")