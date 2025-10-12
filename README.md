# Gold22

## Łączenie własnego modelu ML

Repozytorium zawiera prosty moduł `ModelConnector`, który ułatwia podpięcie
wcześniej wytrenowanego modelu zapisanego w formacie pickle do innej aplikacji
lub procesu analitycznego. Narzędzie może wczytać również pipeline
przetwarzający dane (np. obiekt `sklearn` lub własną klasę), dzięki czemu w
jednym kroku można przygotować dane oraz uzyskać predykcję.

### Wymagania

* Python 3.11+
* Pliki pickle z zapisanym modelem oraz opcjonalnie z preprocesingiem
* Dane wejściowe przygotowane w formacie JSON (lista rekordów lub słowniki)

### Szybki start

1. Zapisz pipeline oraz model do plików::

       import pickle
       with open("preprocessor.pkl", "wb") as f:
           pickle.dump(preprocessor, f)
       with open("model.pkl", "wb") as f:
           pickle.dump(model, f)

2. Przygotuj dane wejściowe, np. w pliku `payload.json`::

       [
         [12.0, 0.1, 3.5],
         [3.0, 0.5, 7.1]
       ]

3. Uruchom narzędzie z wiersza poleceń::

       python -m src.model_connector \
           --model-path model.pkl \
           --preprocessor-path preprocessor.pkl \
           --input-data payload.json \
           --output predictions.json

4. Wynik zostanie wypisany w formacie JSON i można go zapisać do pliku lub
   przekierować do innego programu.

### Integracja w kodzie

Możesz również użyć `ModelConnector` bezpośrednio w swoim projekcie::

    from src.model_connector import ModelConnector

    connector = ModelConnector("model.pkl", "preprocessor.pkl")
    prediction = connector.predict([[1.2, 0.3, 5.0]])

Obiekt potrafi obsłużyć zarówno modele/przetwarzanie posiadające metodę
`predict`/`transform`, jak i obiekty wywoływalne.

### Testy

Pakiet zawiera testy jednostkowe uruchamiane poleceniem::

    python -m unittest discover -s tests

Testy wykorzystują proste obiekty przykładowe, aby potwierdzić poprawność
obsługi modeli, preprocesorów oraz błędów konfiguracyjnych.

### Eksport pełnego kodu

Jeżeli potrzebujesz szybko uzyskać kompletną zawartość projektu w jednym
pliku tekstowym (np. aby wkleić ją do konwersacji), skorzystaj ze skryptu
`scripts/generate_full_code.py`::

    python -m scripts.generate_full_code > projekt.txt

Domyślnie narzędzie wypisze zawartość `README.md`, `src/model_connector.py` oraz
`tests/test_model_connector.py`, oddzielając je czytelnymi nagłówkami. Możesz
również wskazać własne pliki (ścieżki względem katalogu głównego repozytorium)::

    python -m scripts.generate_full_code README.md src/model_connector.py > kod.txt
