
# bu dosya pdf bolucunun txt dosyasi bolucu halidir.
import re
import json
import os
from datetime import datetime
from typing import List, Dict

class ParagrafBolucu:
    def __init__(self):
        self.min_paragraf = 800 
        self.max_paragraf = 1200  

    def dosyadan_oku(self, dosya_yolu: str) -> str:
        """Dosyayı oku ve temizle"""
        if not os.path.exists(dosya_yolu):
            raise FileNotFoundError(f"Dosya bulunamadı: {dosya_yolu}")
        
        with open(dosya_yolu, 'r', encoding='utf-8') as f:
            metin = f.read()
        
        return re.sub(r'\s+', ' ', metin).strip()

    def bol_paragraflar(self, metin: str) -> List[str]:
        """Metni mantıklı paragraflara ayır"""
        paragraflar = [p.strip() for p in re.split(r'\n\s*\n', metin) if p.strip()]
        
        sonuc = []
        for p in paragraflar:
            if len(p) <= self.max_paragraf:
                sonuc.append(p)
            else:
                sonuc.extend(self._cumlelerden_bol(p))
        
        return self._kisa_paragraflari_birlestir(sonuc)

    def _cumlelerden_bol(self, metin: str) -> List[str]:
        """Uzun metni cümle sınırlarından böler"""
        cumleler = re.split(r'(?<=[.!?])\s+(?=[A-ZİĞÜŞÖÇ])', metin)
        paragraflar = []
        gecici_paragraf = ""
        
        for cumle in cumleler:
            if len(gecici_paragraf) + len(cumle) > self.max_paragraf:
                if gecici_paragraf:
                    paragraflar.append(gecici_paragraf)
                gecici_paragraf = cumle
            else:
                gecici_paragraf += " " + cumle if gecici_paragraf else cumle
        
        if gecici_paragraf:
            paragraflar.append(gecici_paragraf)
        
        return paragraflar

    def _kisa_paragraflari_birlestir(self, paragraflar: List[str]) -> List[str]:
        """Çok kısa paragrafları mantıklı şekilde birleştir"""
        sonuc = []
        gecici_paragraf = ""
        
        for p in paragraflar:
            if len(gecici_paragraf) + len(p) < self.min_paragraf:
                gecici_paragraf += " " + p if gecici_paragraf else p
            else:
                if gecici_paragraf:
                    sonuc.append(gecici_paragraf)
                gecici_paragraf = p
        
        if gecici_paragraf:
            sonuc.append(gecici_paragraf)
        
        return sonuc

    def json_olustur(self, paragraflar: List[str], kaynak_dosya: str) -> Dict:
        """API uyumlu JSON çıktısı oluştur"""
        return {
            "metadata": {
                "kaynak_dosya": os.path.basename(kaynak_dosya),
                "olusturulma_tarihi": datetime.now().isoformat(),
            },
            "paragraphs": [
                {
                    "paragraph_id": f"p{i+1}",
                    "content": p,
                    "charachter": len(p),
                    "word": len(p.split())
                }
                for i, p in enumerate(paragraflar)
            ],
            "istatistikler": {
                "toplam_paragraf": len(paragraflar),
                "toplam_karakter": sum(len(p) for p in paragraflar),
                "ortalama_karakter": sum(len(p) for p in paragraflar) // len(paragraflar)
            }
        }

def main():
    print("=== PARAGRAF BÖLÜCÜ ===")
    print("Çıktı: API uyumlu JSON formatında paragraflar\n")
    
    # Kullanıcı girdisi
    dosya_yolu = "data.txt"
    cikti_dosya = "cikti.json"
    
    try:
        # İşlemleri yap
        bolucu = ParagrafBolucu()
        metin = bolucu.dosyadan_oku(dosya_yolu)
        paragraflar = bolucu.bol_paragraflar(metin)
        json_data = bolucu.json_olustur(paragraflar, dosya_yolu)
        
        with open(cikti_dosya, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ {len(paragraflar)} paragraf oluşturuldu:")
        for p in json_data["paragraflar"][:3]:
            print(f"\n📝 {p['paragraf_id']} ({p['karakter']} karakter):")
            print(p["icerik"][:100] + "...")
        
        print(f"\nÇıktı başarıyla kaydedildi: {os.path.abspath(cikti_dosya)}")
    
    except Exception as e:
        print(f"\n❌ Hata: {str(e)}")

if __name__ == "__main__":
    main()