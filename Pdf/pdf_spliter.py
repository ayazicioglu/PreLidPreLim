import re
import json
import os
import fitz  # PyMuPDF
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from unidecode import unidecode  # Özel karakter düzeltme için

class PDFParagraphProcessor:
    def __init__(self):
        self.min_paragraph = 800  # Minimum karakter sayısı
        self.max_paragraph = 1400  # Maksimum karakter sayısı
        
        self.header_pattern = re.compile(r'^\d+\.\s+[A-Z][a-zA-Z\s]+$')  # Başlık deseni
        self.hyphen_pattern = re.compile(r'(\w+)-\s+(\w+)')  # Satır sonu tireleme
        self.footnote_pattern = re.compile(r'\s*$$\d+$$\s*')  # Dipnotlar
        self.sentence_pattern = re.compile(r'(?<=[.!?])\s+')  # Cümle ayırıcı

    def advanced_clean(self, text: str) -> str:
        """Tüm metin temizleme işlemlerini uygular"""
        # Satır sonu tirelemelerini düzelt
        text = self.hyphen_pattern.sub(r'\1\2', text)
        
        # Başlıkları kaldır
        text = self.header_pattern.sub('', text)
        
        # Dipnotları kaldır
        text = self.footnote_pattern.sub(' ', text)
        
        # Özel karakterleri düzelt
        text = unidecode(text)
        
        # Fazla boşlukları temizle
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Tırnak işaretlerini standartlaştır
        text = text.replace('"', '"').replace('"', '"')
        
        return text

    def extract_text(self, pdf_path: str, start_page: int = 1, end_page: int = None) -> str:
        """PDF'den gelişmiş metin çıkarma"""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF bulunamadı: {pdf_path}")
        
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        end_page = end_page or total_pages
        end_page = min(end_page, total_pages)
        
        full_text = []
        for page_num in range(start_page-1, end_page):
            page = doc.load_page(page_num)
            text = page.get_text("text", flags=
                               fitz.TEXT_DEHYPHENATE |  # Tirelemeyi düzelt
                               fitz.TEXT_PRESERVE_LIGATURES |
                               fitz.TEXT_MEDIABOX_CLIP)
            full_text.append(f"<!-- PAGE {page_num+1} -->\n{text}")
        
        doc.close()
        return "\n\n".join(full_text)

    def process_text(self, text: str) -> List[Dict]:
        """Metni işlerken tüm temizlik adımlarını uygula ve cümle bazlı böl"""
        paragraphs = []
        current_page = 1
        current_text = ""
        
        # Önce tüm metni temizle
        clean_text = self.advanced_clean(text)
        
        # Sayfa işaretlerini ayıkla
        page_marks = [(m.start(), m.end(), int(m.group(1))) 
                     for m in re.finditer(r'<!-- PAGE (\d+) -->', clean_text)]
        
        # Sayfa işaretlerini kaldır
        clean_text = re.sub(r'<!-- PAGE \d+ -->', '', clean_text)
        
        # Cümleleri ayır (nokta, ünlem, soru işareti ile bitenleri ayır)
        sentences = re.split(r'(?<=[.!?])\s+', clean_text)
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            # Cümlenin hangi sayfada olduğunu bul
            sentence_pos = clean_text.find(sentence)
            page = current_page
            for mark in page_marks:
                if sentence_pos >= mark[0]:
                    page = mark[2]
                else:
                    break
                    
            if current_text:
                current_text += " " + sentence
            else:
                current_text = sentence
                
            if len(re.sub(r'\s', '', current_text)) >= self.min_paragraph:
                paragraphs.append({
                    "text": current_text.strip(),
                    "page": page,
                    "word_count": len(current_text.split())
                })
                current_text = ""
        
        if current_text:
            paragraphs.append({
                "text": current_text.strip(),
                "page": page,
                "word_count": len(current_text.split())
            })
        
        return paragraphs

    def generate_output(self, paragraphs: List[Dict]) -> List[Dict]:
        """Nihai çıktıyı oluştururken cümle bütünlüğünü koru"""
        output = []
        buffer = ""
        buffer_page = 1
        buffer_word_count = 0
        
        for para in paragraphs:
            if not buffer:
                buffer = para["text"]
                buffer_page = para["page"]
                buffer_word_count = para["word_count"]
                continue
            
            # Yeni paragrafın ilk cümlesini al
            first_sentence = self._get_first_sentence(para["text"])
            
            # Kombine edilmiş metin
            combined = f"{buffer} {first_sentence}"
            combined_clean = re.sub(r'\s+', ' ', combined)
            combined_word_count = buffer_word_count + len(first_sentence.split())
            
            # Eğer limitler içindeyse buffer'a ekle
            if combined_word_count * 6 <= self.max_paragraph:  # Ortalama kelime uzunluğu 6 karakter
                buffer = combined_clean
                buffer_word_count = combined_word_count
                
                # Eğer bu paragrafın tamamını eklemeye gerek yoksa
                if para["text"] != first_sentence:
                    remaining_text = para["text"][len(first_sentence):].strip()
                    if remaining_text:
                        # Kalan metni yeni paragraf olarak işle
                        paragraphs.insert(paragraphs.index(para) + 1, {
                            "text": remaining_text,
                            "page": para["page"],
                            "word_count": len(remaining_text.split())
                        })
            else:
                # Buffer'ı çıktıya ekle
                output.append(self._create_paragraph(buffer, buffer_page, len(output)+1))
                
                # Yeni buffer'ı oluştur
                buffer = para["text"]
                buffer_page = para["page"]
                buffer_word_count = para["word_count"]
        
        # Kalan buffer'ı ekle
        if buffer:
            output.append(self._create_paragraph(buffer, buffer_page, len(output)+1))
        
        return output

    def _get_first_sentence(self, text: str) -> str:
        """Metnin ilk cümlesini döndürür"""
        match = re.search(r'^.*?[.!?](?=\s|$)', text)
        if match:
            return match.group(0)
        return text

    def _create_paragraph(self, text: str, page: int, id_num: int) -> Dict:
        """Standart paragraf nesnesi oluştur"""
        clean_text = re.sub(r'\s+', ' ', text).strip()
        return {
            "paragraph_id": f"para_{id_num}",
            "content": clean_text,
            "char_count": len(re.sub(r'\s', '', clean_text)),
            "word_count": len(clean_text.split()),
            "source_page": page
        }

def get_page_range() -> Tuple[int, int]:
    """Kullanıcıdan sayfa aralığını al"""
    while True:
        try:
            input_str = input("Sayfa aralığı (örn: 12-15 veya tümü için enter): ").strip()
            if not input_str:
                return (1, None)
            if '-' in input_str:
                start, end = map(int, input_str.split('-'))
                return (max(1, start), end)
            single_page = int(input_str)
            return (single_page, single_page)
        except ValueError:
            print("Geçersiz giriş! Örnek format: '12-15' veya '5'")

def main():
    print("=== PDF ULTIMATE PROCESSOR ===")
    print("Tireleme düzeltme ve gelişmiş temizleme aktif\n")
    
    pdf_path = input("PDF dosya yolu (varsayılan: kitap.pdf): ").strip() or "kitap.pdf"
    output_file = input("Çıktı dosyası (varsayılan: output.json): ").strip() or "output.json"
    
    # Sayfa aralığını al
    print("\nSayfa Aralığı Seçimi:")
    start_page, end_page = get_page_range()
    
    try:
        processor = PDFParagraphProcessor()
        
        print(f"\n🔍 PDF işleniyor (Sayfalar: {start_page}-{end_page or 'son'})...")
        text = processor.extract_text(pdf_path, start_page, end_page)
        
        print("✂️ Paragraflar ayrıştırılıyor...")
        raw_paragraphs = processor.process_text(text)
        final_output = processor.generate_output(raw_paragraphs)
        
        # İstatistikler
        stats = {
            "total_paragraphs": len(final_output),
            "total_characters": sum(p["char_count"] for p in final_output),
            "total_words": sum(p["word_count"] for p in final_output),
            "pages_processed": f"{start_page}-{end_page or list(set(p['source_page'] for p in final_output))[-1]}"
        }
        
        # JSON çıktısı
        result = {
            "metadata": {
                "source_file": os.path.basename(pdf_path),
                "processed_at": datetime.now().isoformat(),
                "processing_settings": {
                    "hyphen_fix": True,
                    "header_cleaning": True,
                    "min_paragraph_chars": processor.min_paragraph,
                    "max_paragraph_chars": processor.max_paragraph
                }
            },
            "statistics": stats,
            "paragraphs": final_output
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            
        print(f"\n✅ İşlem tamamlandı!")
        print(f"📊 İstatistikler:")
        print(f"- Paragraf sayısı: {stats['total_paragraphs']}")
        print(f"- İşlenen sayfalar: {stats['pages_processed']}")
        print(f"- Toplam kelime: {stats['total_words']}")
        print(f"💾 Çıktı: {os.path.abspath(output_file)}")
        
    except Exception as e:
        print(f"\n❌ Hata: {str(e)}")

if __name__ == "__main__":
    main()