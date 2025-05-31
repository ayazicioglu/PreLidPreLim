@echo off
echo Gerekli kutuphaneler yukleniyor...

pip install requests
echo requests kutuphanesi basariyla yuklendi 1/3

pip install unidecode
echo unidecode kutuphanesi basariyla yuklendi 2/3

pip install PyMuPDF
echo requPyMuPDFests kutuphanesi basariyla yuklendi 3/3

echo Tum kutuphaneler yuklendi.
pause
