# GLOBAL-LEMMATIZER

This script aims to parse all "derivative of" templates in the English Wiktionary and link the forms to their lemmas.

## Usage

- Download the Wiktionary pages/articles XML dump in the project root.
- Edit the filename in `context = etree.iterparse('enwiktionary-20240120-pages-articles.xml', tag='{http://www.mediawiki.org/xml/export-0.10/}page')` to match the filename.
- Run the python script.
- Once the script is done running, open `forms.db` and you can do stuff like:

```
sqlite> SELECT lemma, language FROM word_forms WHERE form = 'programo'; 
programar|Catalan
programar|Spanish
programar|Portuguese
```

```
sqlite> SELECT form FROM word_forms WHERE lemma = 'programar' AND language = 'Spanish';       
programo
programa
programando
programado
programad
programas
programamos
programáis
programan
programaba
programabas
programábamos
programabais
programaban
[...]
```

## Limitations

- Entries with wikitext used as the lemma form will register the wikitext as the lemma.
- See TODO comments.